#!/usr/bin/env bash
# Ejecuta la suite de caracterización (tests/escape/) dentro de un contenedor
# Linux desechable. No construye ni depende de código de ektel, que todavía
# no existe: solo corre las pruebas de primitivas POSIX descritas en
# tests/escape/README.md.
#
# Uso:
#   scripts/characterize-linux.sh
#
# Requiere Docker con el daemon activo. El contenedor se destruye al salir
# (--rm) y el repositorio se monta solo lectura: el script no puede escribir
# dentro del árbol de trabajo ni persistir estado entre corridas.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${EKTEL_CHARACTERIZATION_IMAGE:-python@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a}"

if ! docker info >/dev/null 2>&1; then
  echo "error: el daemon de Docker no está activo." >&2
  exit 1
fi

echo "Imagen: ${IMAGE}"
docker run --rm \
  --pull=missing \
  -v "${REPO_ROOT}:/repo:ro" \
  -w /repo \
  "${IMAGE}" \
  bash -c '
    set -e
    echo "--- entorno ---"
    cat /etc/os-release | grep PRETTY_NAME
    uname -srm
    python3 --version
    echo "--- suite ---"
    python3 -m unittest discover -s tests/escape -v
  '
