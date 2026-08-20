# Acta de enmienda transversal v3 — segunda ronda externa (C1–C6, D1–D5)

**Fecha del acta:** 2026-08-20.
**Origen:** segunda revisión externa de Codex sobre la especificación v1.1
(`docs/revisiones/revision-externa-codex-v11-2026-08-20.txt`, veredicto
PARCIAL/NO-GO, bloqueantes C1–C6 más inconsistencias) y pase de
verificación de Claude
(`docs/revisiones/revision-externa-claude-v11-2026-08-20.txt`, D1–D5).
Ambas cumplen el criterio de independencia F5.
**Regla aplicada:** «enmienda = acta»
(`enmienda-adr-007-durabilidad-2026-08-19.md`).

**Dueño:** Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com).

## Enmiendas a los ADR y contratos

| # | Hallazgo | Enmienda aplicada | Documento |
|---|---|---|---|
| C1 | Un único `ExecutionResult` con estados pre-inicio no es implementable (sin handle tras rechazo de admisión) | Tipos de resultado por operación: `AdmissionOutcome` (`Admitted`/`AdmissionRejected` con `reason_code`, incluido `capability_rejected`), `StartOutcome` (`Started{handle}`/`StartFailed{reason_code}` con `start_failed` y `start_failed_indeterminate`), `ExecutionResult` sólo post-inicio, `TerminationOutcome` (`TerminationAccepted{receipt}`/`TerminationRejected{reason_code}`) | ADR-005 punto 1 |
| C2 | Tres construcciones HMAC mezcladas (header.payload, dominio+payload, HKDF) admiten implementaciones incompatibles; faltan decisiones de bytes | Perfil byte-exacto único: HS256 fijo; base64url **sin padding**; MAC = `ASCII("ektel/<dominio>/v1") \|\| 0x00 \|\| header \|\| "." \|\| payload`; longitudes 32-bit big-endian; verificar MAC antes de decodificar header; HKDF prohibido en v1; todo cambio es envelope v2; dominio nuevo `ektel/termination/v1` para el token del handle | ADR-002 punto 2, ADR-003 punto 5 |
| C3 | C8/"head confiable" sin interfaz implementable | **C8 retirado de claims** (mismo precedente que C9): la cadena aporta diagnóstico de consistencia interna; `TrustedHeadStore`/`verify_chain` es propuesta v2 | ADR-007 punto 5; tabla C8 retirado, N7 |
| C4 | Los dos CAS evitan replay pero no definen recuperación | Claves CAS: `(issuer_id, nonce)` y `identity_digest`; estados `free→reserved` y `unspent→spent`; perdedor de `start` concurrente recibe `capability_rejected` (código cerrado); crash tras consumo y antes del spawn → `start_failed_indeterminate`, token permanentemente gastado, nueva admisión con nonce nuevo; reconciliación por `identity_digest` | ADR-004 punto 4, ADR-003 punto 7 |
| C5 | `ExecutionHandle` sin límites operativos | Local al proceso supervisor, opaco, no serializable, confidencial (redactado en logs/eventos), inválido tras reinicio del supervisor; no es capacidad bearer persistible | ADR-003 punto 8 (nuevo) |
| C6 | Deadline con gracia produce estados ambiguos | `soft_termination_at` (= deadline efectivo − gracia) y `hard_deadline_at`; clasificación por causa: salida natural antes de la escalación → `executed`; escalación iniciada por plazo → `deadline_exceeded`; terminación externa previa → `terminated` | ADR-005 punto 3, ADR-009 punto 3 |
| I1 | `policy_mode=optional` + `Indeterminate` sin declarar | Fail-open declarado con evento `policy_degraded` obligatorio cuando `audit_mode=required`; la degradación nunca es silenciosa | ADR-008 punto 2 |
| I2 | Timeout y `valid_until` sin reloj asignado | Timeout del puerto con reloj monotónico; `valid_until` con reloj de pared + tolerancia (regla de dos relojes de ADR-004 aplicada) | ADR-008 punto 1 |
| I3 | La especificación candidata afirmaba prevalecer sobre los ADR antes del consenso | Jerarquía corregida: la prevalencia rige **tras** el consenso; antes, mandan los ADR | Especificación v1.2 §0 |
| I4 | N14 atribuía la caída de C7 a la clave filtrada | Corregido: la clave filtrada anula C1 y C2; C7 sólo cae si además se compromete o evade el AuditSink | Tabla N14 |
| D1 | `durable` se desmiente a sí mismo (como `executed` y «firmada» antes) | Enum renombrado: `durable` → `flush_protocol_completed` | ADR-007 puntos 1/3/4; tabla C7/N5; spec |
| D2 | «No testeable» era falso en dos tercios | Testabilidad por niveles: 1 = SIGKILL del escritor (M3); 2 = dm-log-writes/dm-flakey en Linux (M3); 3 = corte físico real, no testeable sin hardware | ADR-007 punto 3; tabla C7/N5 |
| D3 | «Ausencia/fallo recuperable» con barra ambigua en vocabulario cerrado | Nombrado: `start_failed_indeterminate` (converge con C4) | ADR-004 punto 4 |
| D4 | N15 sin lápida en la tabla | Lápida añadida (numeración no se compacta; C8, C9 y N15 constan) | Tabla, nota tras N14 |
| D5 | El test de flush no registra el FS del volumen sondeado | El test registra dispositivo/montaje y declara que M3 debe re-sondear bajo el directorio real del sink; mensaje de fallo corregido («F_FULLFSYNC no disponible») | `tests/escape/test_host_characterization.py` |

## Efecto

La especificación se regenera como **v1.2** candidata. El ciclo de cierre
restante (propuesta de Codex, adoptada): revisión cruzada final de
ADR/tabla/especificación → consenso explícito del dueño sobre v1.2 → sólo
entonces autorización de M0.

## Aprobación

| Resolución | Dueño | Fecha |
|---|---|---|
| Aplicar C1–C6, I1–I4 y D1–D5; regenerar la especificación como v1.2 candidata | Kristhian Manuel Jimenez Sanchez | 2026-08-20 |
