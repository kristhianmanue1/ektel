# Caracterización M2 — Darwin arm64 (clase L)

**Fecha:** 2026-09-09. **Gate:** G-M2-13, brazo Darwin.
**Clase de evidencia:** **L** (host de desarrollo, no contenedor fijado).

## Entorno

| Qué | Valor |
|---|---|
| Sistema | Darwin 25.6.0 arm64 |
| Python | 3.12.12 (`.venv` del repo) |
| Ejecución | host, sin contenedor |

## Resultados

| Gate | Resultado |
|---|---|
| Suite completa `tests/` | **339 OK, 4 skips** |
| `mypy --strict src` | limpio, 34 archivos |
| Vectores dorados | 91 regenerados, **diff cero** |
| `fuzz_admision.py` (M1) | sin divergencias; fingerprint bases `795c3a96…` |
| `fuzz_start_revalidation.py` (M2) | `gate: OK`, 3000 iteraciones, 0 divergencias, 0 crashes |

## Skips y degradaciones — declarados, no convertidos en verde

Los 4 skips de Darwin son **ausencias de capacidad, no pruebas superadas**:

1. tres pruebas Linux-only heredadas de la caracterización M0/M1;
2. `test_linux_activa_subreaper_realmente`, saltada por diseño.

**Degradación declarada:** `PR_SET_CHILD_SUBREAPER` **no existe en Darwin**.
`platform_caps.detect()` reporta `subreaper_available=False` y
`multilevel_accounting=unsupported`. El terminal del supervisor publica
`subreaper_requested=False` y `subreaper_applied=False`.

Consecuencia medida y **no mitigada**: el CPU y la recolección de un nieto
huérfano —cuyo padre inmediato murió sin `wait()`— son irrecuperables para el
proceso raíz. **No hay mitigación conocida en Darwin.** Este hecho no se
compensa ni se disimula: se declara.

## RSS — caracterizado, nunca declarado como cota

El RSS del supervisor se **observa** (vía `ps` en Darwin, `/proc` en Linux) y
se comprueba que es finito y positivo. **No** se compara con las fórmulas de
payload de D-M2-1(a), que acotan **payload retenido y no memoria del
proceso**. Si la medición no puede obtenerse, la prueba se **salta
declarándolo** en vez de darla por buena.

## Lo que esta corrida NO acredita

- No es clase V: el host no está fijado por digest ni aislado.
- No mide RSS como garantía: la caracterización de memoria es observación.
- x86_64 sigue fuera (puerta de pre-producción, ADR-006/N12).
