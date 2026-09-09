#!/usr/bin/env bash
# Suite M2 sobre Linux en contenedor desechable (G-M2-13).
#
# G-M2-13 exige la suite COMPLETA ejecutada POR SEPARADO en cada plataforma,
# con skips y degradaciones explícitos y nunca convertidos en verde
# equivalente. Este script cubre el brazo Linux; el brazo Darwin se ejecuta
# en el host.
#
# Método heredado del gate G15 de M1: imagen fijada por DIGEST (nunca sólo
# tag), repositorio montado en solo lectura, sin red, sin privilegios y sin
# socket de Docker. El contenedor se destruye al salir.
#
# `mypy` NO se ejecuta aquí: es herramienta de desarrollo (ADR-006 A8) e
# instalarla exigiría red dentro del contenedor. Su gate corre en el host.
#
# Uso:
#   scripts/characterize-m2.sh
#
# Variable opcional:
#   EKTEL_M2_IMAGE   imagen por digest (default: python 3.12 slim bookworm)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${EKTEL_M2_IMAGE:-python@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a}"

if ! docker info >/dev/null 2>&1; then
  echo "error: el daemon de Docker no está activo." >&2
  exit 1
fi

echo "=== imagen (fijada por digest) ==="
echo "${IMAGE}"
docker image inspect "${IMAGE}" --format \
  'Os/Arch: {{.Os}}/{{.Architecture}} | Id: {{.Id}}' 2>/dev/null || true

echo
echo "=== corrida (read-only, sin red, no root) ==="
docker run --rm \
  --pull=missing \
  --read-only \
  --network none \
  --tmpfs /tmp:rw,exec,size=512m \
  --user 10001:10001 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e HOME=/tmp \
  -v "${REPO_ROOT}:/repo:ro" \
  -w /repo \
  "${IMAGE}" \
  bash -c '
    set -e
    echo "--- entorno ---"
    grep PRETTY_NAME /etc/os-release
    uname -srm
    python3 --version
    echo "--- suite completa M0+M1+M2 ---"
    python3 -m unittest discover -s tests -t .
    echo "--- fuzz de admision (M1) ---"
    python3 scripts/fuzz_admision.py --iteraciones 500 | tail -c 400
    echo
    echo "--- fuzz de revalidacion (M2, G-M2-01) ---"
    python3 scripts/fuzz_start_revalidation.py --iteraciones 1000 | tail -c 400
    echo
  '
