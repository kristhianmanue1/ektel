# Acta de enmienda transversal — ronda correctiva v2 (B1–B8)

**Fecha del acta:** 2026-08-19.
**Origen:** revisión externa de Codex
(`docs/revisiones/revision-externa-codex-espec-2026-08-19.txt`, veredicto
PARCIAL/NO-GO sobre el rango `9f41fbf..3f9ea06`). La revisión cumple el
criterio de independencia F5 (revisor distinto del autor, acceso al repo y
a la evidencia, hallazgos numerados y comprobables).
**Regla aplicada:** la adoptada en `enmienda-adr-007-durabilidad-2026-08-19.md`
— toda enmienda posterior al consenso lleva acta explícita.

**Dueño:** Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com).

## Enmiendas a los ADR

| # | Hallazgo | Enmienda aplicada | Documento |
|---|---|---|---|
| B1 | Recibos con dos contratos incompatibles (ADR-007 sin MAC; spec/N8/N14 con HMAC); C8 absoluto | **v1 mínima:** recibos v1 sin MAC; la cadena detecta **enlaces rotos respecto de un head confiable**, no «modificación posterior» a secas; recibo autenticado queda como propuesta v2 | ADR-007 punto 5; tabla C8, N8, N14 |
| B2 | `terminate(ActionId, …)` no recibe la autoridad que la prosa exige | `terminate(ExecutionHandle, TerminationReason)`: el handle porta un token opaco de terminación emitido en `start` tras verificar el `admitted_action`; la regla de autorización de R1 se mantiene y ahora es implementable | Especificación §8 |
| B3 | Reserva de nonce y consumo de `admitted_action` confundidos | Dos registros CAS durable: `nonce_reservation` (en `admit`) y `start_token_consumption` (inmediatamente antes del spawn); crash entre CAS y spawn = token gastado, nunca replay | ADR-003 punto 7, ADR-004 punto 4 |
| B4 | C2 promete más identidad de la que existe | C2 reformulado: vinculación al **descriptor admitido y la ruta declarada**, no al contenido ejecutado | Tabla C2 |
| B5 | `alg` fuera del MAC; tres HMAC sin dominios; concatenación ambigua | Sobre `{protected_header_b64, payload_b64, signature}` con firma sobre `header.payload` (alg autenticado); prefijos de dominio `ektel/capability/v1`, `ektel/pop/v1`, `ektel/admission/v1` con codificación por longitudes; cambio de familia criptográfica exige **envelope v2** | ADR-002 punto 2, ADR-003 puntos 3–6 |
| B6 | Mecánica de salida diferida dentro de un ADR aceptado; gracia invisible | **Drenar y descartar** tras `output_limits` decidido ahora (con conteo de bytes descartados); la gracia SIGTERM→SIGKILL descontada del deadline se declara en `GuaranteePlan` y resultado | ADR-009 puntos 1 y 3, A1 |
| B7 | `valid_until` delegado por completo al adaptador | División: la corrección de la política es del adaptador; la validación del sobre de respuesta (forma, `decision_id`, vigencia contra reloj de pared con tolerancia, timeout) es del núcleo; `Allow` expirado o tardío → `Indeterminate`/rechazo cuando el puerto sea requerido | ADR-008 punto 1; tabla N16 |
| B8 | B2-de-durabilidad mitigado, no probado | `durable` = «protocolo de plataforma completado bajo supuestos declarados», no supervivencia demostrada; test renombrado a `test_flush_primitive_available`; el protocolo completo (fsync de directorio, rename, crash) se valida en M3 | ADR-007 punto 3; `tests/escape/` |

## Enmiendas a la tabla pública (`docs/claims-y-no-claims.md`)

| Fila | Cambio |
|---|---|
| C2 | «…vinculada al descriptor admitido y a la ruta declarada…», no a la ejecución del contenido |
| C8 | «…detecta enlaces rotos respecto de un head confiable conservado fuera del almacén» |
| N8 | Los recibos v1 **no llevan MAC**: sin no-repudio ni verificación por terceros; las capacidades sí usan HMAC |
| N14 | La clave filtrada fabrica **capacidades** (C1, C2, C7 caen); C8 cae por reescritura del almacén, no por fabricación de recibos |
| N16 | El núcleo sí valida forma, identidad y vigencia del `Allow`; no valida la corrección de la política |

## Fuera de alcance de este acta

- La divergencia P0–P3 → M0–M3 tiene acta propia
  (`divergencia-p0-p3-m0-m3-2026-08-19.md`).
- La regularización de la enmienda previa de ADR-007 tiene acta propia
  (`enmienda-adr-007-durabilidad-2026-08-19.md`).
- La segunda revisión externa centrada en estados, atomicidad y límites de
  confianza (paso 5 de la ruta de Codex) se solicita **después** de
  regenerar la especificación v1.1 con estas enmiendas.

## Aprobación

| Resolución | Dueño | Fecha |
|---|---|---|
| Aplicar las ocho enmiendas y regenerar la especificación como v1.1 candidata | Kristhian Manuel Jimenez Sanchez | 2026-08-19 |
