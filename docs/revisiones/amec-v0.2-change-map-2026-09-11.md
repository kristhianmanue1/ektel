# AMeC v0.2 — Change Map

**Fecha:** 2026-09-11. **Objeto:** trazabilidad de cambios de
`AMeC v0.1` (revisada adversarialmente) a
`docs/propuestas/Agent Memory Enforcement Contract v0.2 Candidate.md`.

**Base:** commit `b21e916bd8684bb81864569a81650ece95df1891` (contrato v0.1 +
revisión adversarial incorporados). **Naturaleza:** propuesta documental, no
vinculante; no autoriza implementación, no selecciona MECs para EKTEL M3, no
modifica el cierre de EKTEL M2.

Formato: `finding → modificación normativa → criterio falsable`.

## Tabla principal (P1 + P2 estructurales)

| Finding v0.1 | Cambio v0.2 | MEC afectado | Criterio falsable | Estado |
|---|---|---|---|---|
| **P1-1** Procedencia e integridad de policy: MEC-01/02 ordenan la carga pero nadie impide que el agente modifique el policy source antes del boot | Nuevo MEC-34 (§21): distinción content/identity/digest/provenance/root/runtime; propiedad `policy_effective` bound a `trusted_policy_root` externa al modelo; verificación en BOOT antes de crear agentes (enmienda MEC-01); mismatch → FAIL-CLOSED/RESTRICTED-DIAGNOSTIC sin capabilities materiales; sin mandato tecnológico (TPM/firma/Git opcionales) | MEC-01 (enmendado), MEC-02 (referencia a root), **MEC-34 (nuevo)** | Ataque de 4 pasos del mandato: agente con escritura modifica policy/perfil → reinicio → carga del archivo modificado. PASS sólo si la policy modificada no adquiere autoridad por sí misma (inline §21.4; hipótesis E-MEC-8) | Resuelto en v0.2 |
| **P1-2** Digests de MEC-19/20 sin serialización canónica; campos desconocidos y evolución de schema pueden introducir autoridad o romper bindings | Nuevo MEC-35 (§22): canonical representation obligatoria antes de hashing (schema/version, encoding, orden determinista, rechazo de duplicadas, unicode definido, numéricos, rechazo de campos desconocidos, domain separation); MEC-14/19/20 enmendados a digest canónico; MEC-34 usa digest canónico; principio nuevo `HASH WITHOUT CANONICALIZATION ≠ STABLE BINDING`; ADR-002/010 citados como precedente local, no dependencia | MEC-14, MEC-19, MEC-20 (enmendados), **MEC-35 (nuevo)** | Dos implementaciones conformes producen el mismo digest para el mismo objeto lógico; representaciones ambiguas y campos desconocidos se rechazan con reason code, sin reinterpretación silenciosa (inline §22.4; hipótesis E-MEC-9) | Resuelto en v0.2 |
| **P1-3** Paradoja de bootstrap: `material effect requires recovered memory` pero crear la primera memoria es un efecto material; v0.1 no distingue store ausente de store no disponible | Nuevo MEC-36 (§23) + estado `UNINITIALIZED` en el grafo §7.2: transición T3 gobernada por EXPLICIT BOOTSTRAP AUTHORITY (no del modelo, ligada a scope, single-purpose, no se convierte en autoridad normal, deja receipt, replay-resistant); genesis receipt **fuera del store** para distinguir UNINITIALIZED legítimo de STORE_LOSS (→DEGRADED, sin reabrir génesis); principio `STORE ABSENT ≠ STORE UNAVAILABLE`; prohibido `missing store == degraded store` | **MEC-36 (nuevo)**, MEC-03 (grafo T1/T3), MEC-28 (coherencia) | F1: agente sin bootstrap authority no puede crear el store. F2: la authority consumida no concede nada post-génesis. F3: borrar el store no regenera UNINITIALIZED (receipt presente → STORE_LOSS → DEGRADED) (inline §23.5; hipótesis E-MEC-10) | Resuelto en v0.2 |
| **P1-4** Autoridad humana sin binding de alcance: `human said yes` reutilizable como blanket o entre targets/revisiones | Nuevo MEC-37 (§17) + MEC-18 enmendado: binding mínimo a subject/action/scope/target/base revision/validity (ventana o consumo)/provenance/replay semantics (single-use por defecto); prohibiciones explícitas: blanket indefinido, consent de texto del modelo, A→B, R0→R1 silencioso; sin mandato de UI ni canal; exige binding verificable | MEC-18 (enmendado), **MEC-37 (nuevo)** | Reutilizar una aprobación fuera de su binding (otro target, otra revisión, ventana expirada) → DENY con reason code; un tercero verifica que los campos de binding no satisfacen la transición intentada (inline §17; hipótesis E-MEC-11) | Resuelto en v0.2 |
| **P1-5** Downgrade de perfil: la garantía se liga al inventario (MEC-33) pero no al perfil; runtime puede anunciar P4 y ejecutar P1 | Nuevo MEC-38 (§24): binding `profile_declared ↔ profile_effective ↔ policy generation ↔ capability inventory ↔ runtime identity/version`; propiedad `profile_claimed == profile_effectively_enforced`; perfil efectivo parte de la evidencia externa §27.3; cambios de perfil/plugin/inventory/generación invalidan conformidad previa | **MEC-38 (nuevo)**, MEC-33 (complementario) | Runtime declara P4 y ejecuta una capability material sin PEP → detectable por divergencia entre declarado y efectivo en evidencia externa → NON-CONFORMING (inline §24; hipótesis E-MEC-12) | Resuelto en v0.2 |
| **P2-1** MEC-03 sin grafo de transiciones legales (lista de estados ambigua) | Nuevo §7.2 normativo: 9 estados (incluye `UNINITIALIZED` nuevo), 14 transiciones con precondición/evento/destino/capabilities/evidencia/recovery/terminalidad; tabla de capabilities por estado; transiciones prohibidas enumeradas (p. ej. `DEGRADED → WORKING`, `DIRTY → CLOSED_SUCCESS`); ninguna transición por afirmación del modelo | MEC-03 (ampliado normativamente) | `DEGRADED → CONTEXT_VALID` exige recovery host-side con evidencia; ninguna transición ocurre por assertion del modelo (hipótesis E-MEC-13) | Resuelto en v0.2 |
| **P2-2** Sin matriz MEC×perfil: §44 no aplicable mecánicamente; riesgo de conformidad arbitraria | Nuevo §27: matriz cerrada REQUIRED/CONDITIONAL/NOT-CLAIMED para 38 MECs × P0..P5 con condiciones C1/C2/C3 definidas; respuesta mecánica a «¿qué exige conformidad P3?»; binding de toda declaración de conformidad (AMeC version, profile, runtime, policy generation, inventory, plugin set, profile_effective) | Todos (matriz normativa); **P2-2 estructural** | La pregunta «¿qué debe demostrar un runtime para conformidad Pn?» se responde mecánicamente con la matriz; selección arbitraria de MECs imposible (hipótesis E-MEC-14) | Resuelto en v0.2 |

## P2 restantes (decisión individual — §32 del candidato)

| Finding v0.1 | Cambio v0.2 | MEC afectado | Criterio falsable | Estado |
|---|---|---|---|---|
| MEC-02 sin clase de mecanismo de revocación | Identificación + rollout obligatorio quedan normativos; mecanismo (pull/lease/push) diferido | MEC-02 | Falsabilidad de identificación conservada; el mecanismo tendrá suite propia | `DEFER-WITH-RATIONALE` → v0.3 (D1) |
| MEC-06 «retry acotado» sin techo | Techo `recovery_max_attempts` y backoff declarados en policy; agotamiento = transición T6 a DEGRADED; tradeoff de liveness declarado | MEC-06 | Sin techo declarado, DEGRADED es arbitrario → no conforme; T6 falsable con ledger de retries (hipótesis E-MEC-13) | `INCLUDE-IN-v0.2` (D2, promovido por dependencia del grafo §7.2) |
| MEC-09 observabilidad de efectos remotos/ambiguos | Default conservador `UNKNOWN_EFFECT → DIRTY` elevado a norma; reconciliación por-capability diferida | MEC-09 | DIRTY falsable por observación host-side; timeout con efecto desconocido → DIRTY (conservador) | `DEFER-WITH-RATIONALE` → v0.3 (D3) |
| MEC-16 «reducir» sin rastro | Reason code obligatorio en las tres ramas (rechazar/reducir/reason code) | MEC-16 | Reducción silenciosa sin reason code → no conforme | `INCLUDE-IN-v0.2` (D4) |
| MEC-24 «cuando sea viable» sin criterio | Criterio mínimo de viabilidad: (a) frontera de confianza inalcanzable o (b) presupuesto agotado; omisión siempre con reason code y estado AMBIGUOUS hasta reconciliar | MEC-24 | Omisión sin reason code → no conforme; read-back omitido dejando SUCCESS → no conforme | `INCLUDE-IN-v0.2` (D5, promovido por dependencia de MEC-23) |
| MEC-32 «no debe crear normalmente» | «Normalmente» eliminado; requisito incondicional; restricted diagnostic mode sin capabilities materiales | MEC-32 | Policy ausente/rota + agente con capabilities materiales creados → no conforme (E-MEC-4) | `INCLUDE-IN-v0.2` (D6) |
| MEC-30 log sin tamper-evidence ni binding decisión→regla | `policy_rule_reference` + superficie de log fuera del alcance de escritura del modelo: INCLUDE; cadena hash/append-only: diferida | MEC-30, MEC-29 | DENY sin referencia correlacionable a regla → no satisface MEC-29 | Dividido: `INCLUDE-IN-v0.2` (propiedades) + `DEFER-WITH-RATIONALE` → v0.3 (cadena) (D7) |

## P3 (disposición)

Los siete P3 de la revisión adversarial quedan como `OPEN QUESTIONS /
NON-BLOCKING` en §33 del candidato (Q-1..Q-7), con las aclaraciones no
normativas que no costaban nada: identidad de subagente (Q-1, con clarificación
de MEC-12: el hijo deriva autoridad de sus propias observaciones mediadas) y
tradeoff de liveness del fail-closed registrado como declarado-aceptado (Q-7,
en §8). Ningún P3 bloquea v0.2.

## Trazabilidad de principios

| Principio nuevo | Finding |
|---|---|
| `HASH WITHOUT CANONICALIZATION ≠ STABLE BINDING` | P1-2 |
| `STORE ABSENT ≠ STORE UNAVAILABLE` | P1-3 |
| `BOOTSTRAP AUTHORITY ≠ NORMAL AUTHORITY` | P1-3 |
| `PROFILE CLAIMED ≠ PROFILE ENFORCED` | P1-5 |

## Índice de MEC en v0.2

MEC-01…MEC-33 heredados de v0.1 (enmendados: 01, 02, 03, 06, 14, 16, 18, 19,
20, 24, 30, 32 — ver tablas). MEC-34 (policy root), MEC-35 (canonicalización),
MEC-36 (bootstrap/genesis), MEC-37 (binding de autoridad humana), MEC-38
(profile effective binding): nuevos.

## Verificación de conservación (regla §2 del mandato)

- Contrato v0.1: conservado sin modificaciones (`docs/propuestas/Agent Memory Enforcement Contract v0.1.md`).
- Revisión adversarial v0.1: conservada (`../revisiones/revision-adversarial-amec-v0.1-2026-09-11.md`).
- Findings P1/P2/P3: todos trazados arriba o en §32/§33 del candidato.
- Procedencia experimental Prime Agent × AN-KLA y DSH × AN-KLA: conservada en
  §34 del candidato (lecciones y limitación de extrapolación).
