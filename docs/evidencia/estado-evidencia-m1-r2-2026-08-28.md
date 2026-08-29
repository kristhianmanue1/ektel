# Estado de evidencia local — M1-R2

**Fecha:** 2026-08-28. **Clase:** local, Darwin arm64. **Base:**
`9cb731ba707544e20f6af3fa84ae8b0166b1b58e`.

## Objeto verificado

M1-R2 corrige exclusivamente la proyección contractual del `GuaranteePlan`
que ya emitía `AdmissionService`: sustituye `failure_mode=""` por
`failure_mode="guarantee_not_enforced_in_m1"`. La declaración continúa siendo
honesta: las garantías solicitadas siguen clasificadas `unsupported` y no se
promueve mecanismo alguno de M2/M3.

La prueba nueva construye la alternativa wire `admitted` a partir del resultado
real del servicio y exige aceptación tanto del parser de referencia como del
parser clean-room congelados en M0. No se modifica ningún schema, vector,
token, replay store, frontera de proceso ni workflow.

## Gates locales

Los resultados finales se registran sobre el diff exacto publicado:

| Gate | Resultado |
|---|---|
| Prueba focal M1-R2 | 1 OK; ambos parsers `accept/ok` |
| Suite completa Darwin | 151 OK, 3 skips Linux-only |
| `mypy==1.19.1 --strict src/` | limpio, 22 archivos |
| Fuzz contractual bytes y semántico | 91 bases / 1547 mutaciones / 0 divergencias; 19 bases / 172 mutaciones / 0 divergencias / 0 fallos de oráculo |
| Fuzz de admisión | 2 bases / 63 mutaciones / 0 fallos de oráculo / 0 crashes |
| Regeneración de 91 vectores | diff recursivo cero |
| Higiene Git | `git diff --check` limpio |
| Revisión adversarial final | OpenCode/GLM-5.3-Flash: `PROCEED`, 0 P0-P2; 4 P3 no bloqueantes, con el marcador documental corregido antes del commit |

Manifest del overlay:
`docs/evidencia/manifest-m1-r2-sha256.txt`.
Registro de revisión:
`docs/revisiones/revision-adversarial-m1-r2-2026-08-28.md`.

## Límites

- La evidencia es local en Darwin; no se reactiva ni ejecuta CI remota.
- Se preservan sin reinterpretación los resultados Linux aarch64 de M1-R1;
  esta corrección no constituye una reproducción Linux nueva.
- M1-R2 no autoriza ni implementa `start`, supervisión, procesos reales,
  salida capturada, terminación ni auditoría M2/M3.
