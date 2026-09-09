# Caracterización M2 — Linux aarch64 en contenedor (clase V)

**Fecha:** 2026-09-09. **Gate:** G-M2-13, brazo Linux.
**Clase de evidencia:** **V** (contenedor desechable, imagen fijada por
digest, sin red, solo lectura, no root).

## Entorno

| Qué | Valor |
|---|---|
| Imagen | `python@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a` |
| Os/Arch | `linux/arm64` |
| Distribución | Debian GNU/Linux 13 (trixie) |
| Kernel | `Linux 6.11.11-linuxkit aarch64` |
| Python | 3.12.14 |
| Runner | `scripts/characterize-m2.sh` |

## Método

Heredado del gate G15 de M1: imagen **por digest, nunca sólo tag**;
repositorio montado `:ro`; `--read-only`; `--network none`; `--tmpfs /tmp`;
usuario no root `10001:10001`; sin `--privileged` y sin socket de Docker. El
contenedor se destruye al salir.

`mypy` **no** se ejecuta aquí: es herramienta de desarrollo (ADR-006 A8) e
instalarla exigiría red dentro del contenedor. Su gate corre en el host y así
queda declarado, no dado por hecho.

## Resultados

| Gate | Resultado |
|---|---|
| Suite completa `tests/` | **314 OK, 1 skip** |
| `fuzz_admision.py` (M1) | sin divergencias; fingerprint bases `795c3a96…` |
| `fuzz_start_revalidation.py` (M2) | `gate: OK`, 1000 iteraciones, 0 divergencias, 0 crashes |

El único skip es la prueba **Darwin-only** que declara la ausencia de
subreaper; en Linux no aplica.

## Capacidad medida que Darwin no tiene

`PR_SET_CHILD_SUBREAPER` **se activó realmente**:
`platform_caps.detect()` reporta `subreaper_available=True` y
`multilevel_accounting=supported`, y el terminal del supervisor publica
`subreaper_applied=True`. Lo activa **sólo el supervisor de acción**, nunca el
coordinador, conforme a D-M2-2(a).

## Defecto de portabilidad que esta corrida encontró

Dos pruebas descubrían el proceso ejecutado invocando `pgrep`, ausente en la
imagen slim. Fallaban con `FileNotFoundError`. Se corrigieron eliminando la
dependencia del binario externo: el propio proceso publica su PID por stdout,
y el conteo de supervisores usa `/proc` en Linux con salto **declarado** donde
no hay vía portable.

Es exactamente el valor de ejecutar la segunda plataforma por separado en vez
de asumir equivalencia.

## Lo que esta corrida NO acredita

- No cubre `mypy` (corre en el host).
- No mide RSS como garantía.
- x86_64 real sigue pendiente (ADR-006/N12).
- No sustituye la revisión adversarial externa de G-M2-15.
