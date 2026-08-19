# ADR-003: Identidad firmada y digests de artefactos

**Estado:** borrador para consenso. No adoptado. No autoriza implementación.

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Contexto normativo:** propuesta §7.3 (ExecutionIdentity), §7.4
(`admitted_action` opaco y de un solo uso), §18. Decisiones vigentes: **D7a**
(`artifact_identity_profile` = `route_mutable_unverified` en M0, con riesgos
reconocidos no mitigados que este ADR debe incorporar a §12 — mandato
explícito del registro de consenso), D2 (capacidad raíz) y ADR-002 (firma
sobre bytes transportados). ADR-002 difirió a este ADR: algoritmo de firma,
gestión de claves y confianza.

## 1. Decisión propuesta

1. **D7a se formaliza sin cambios de sustancia:** `ExecutionIdentity v1`
   incluye el campo firmado `artifact_identity_profile` con un único valor
   válido en v1: `route_mutable_unverified`. El perfil forma parte del
   `identity_digest` y del `GuaranteePlan`; `ExecutionResult` lo repite.
   Solicitar otro perfil rechaza la admisión con código cerrado de garantía
   no soportada. Un perfil de alta integridad llega en una versión de schema
   posterior con evidencia real por plataforma; no se reserva valor
   "pending".
2. **Riesgos no mitigados se incorporan a §12** (cumpliendo el mandato del
   registro D1–D7): sustitución del contenido resuelto por
   `command_absolute` entre admisión e inicio, y efectos de modificación del
   host que ektel no aísla ni detecta.
3. **Algoritmo de autenticación de la capacidad raíz: HMAC-SHA256** sobre
   los bytes transportados (ADR-002), con clave simétrica del operador.
   Razón: ADR-006 fija stdlib-only y la stdlib de Python no incluye firma
   asimétrica (Ed25519). La capacidad raíz es emitida y verificada por el
   mismo operador local (modelo de amenaza ADR-001: un host, un operador),
   donde la asimetría no compra separación real de roles.
4. **`invocation_proof` (PoP):** con HMAC, la posesión de la clave *es* la
   prueba; `invocation_proof` = HMAC independiente sobre
   `nonce + payload_digest`, de modo que el nonce quede ligado al descriptor
   concreto y no sea reusable con otro payload bajo la misma capacidad.
5. **`identity_digest`:** `sha256` de los bytes transportados del descriptor
   (incluye `artifact_identity_profile` y nonce). Dos serializaciones
   distintas son identidades distintas (ADR-002, A4).
6. **`admitted_action`:** valor opaco = `identity_digest + mac interno de
   admisión + expiry`, verificado de nuevo en `start` (integridad, vigencia,
   consumo único). El consumo se registra de forma durable junto al nonce
   (ADR-004), cerrando el intervalo admisión→inicio también tras reinicio.
7. **Gestión de claves:** la clave raíz vive en un archivo del operador con
   permisos `0600`, fuera del descriptor y de los eventos. Rotación =
   reemisión de capacidades; no hay jerarquía ni delegación (D2). Los
   eventos y resultados nunca registran la clave ni el HMAC completo: sólo
   un identificador de clave (`key_id` = digest truncado de la clave
   pública derivada… en modo simétrico, digest truncado de la clave con
   sal de despliegue).

## 2. Motivación

D7a decidió *qué* se firma (perfil de identidad del artefacto); este ADR
decide *cómo* se firma y con qué se verifica, y cierra la tensión entre
stdlib-only (ADR-006) y la necesidad de autenticación criptográfica real en
M1 (criterio de salida: "vectores criptográficos negativos pasan").

## 3. Alternativas consideradas

### A. HMAC-SHA256 simétrico (propuesta)

A favor: stdlib puro (`hmac`, `hashlib`); suficiente bajo el modelo de un
operador (ADR-001); vectores negativos triviales de generar; verificación
de tiempo constante incluida (`hmac.compare_digest`).
En contra: no ofrece verificación por terceros ni no-repudio; la
compromisión de la clave compromete emisor y verificador a la vez.
**Declarado como no-claim:** "los recibos y capacidades de ektel v1 no son
verificables por terceros ni aportan no-repudio".

### B. Ed25519 vía dependencia (`cryptography` o `PyNaCl`)

A favor: firma asimétrica real; habilita `verify_receipt` por terceros.
En contra: rompe stdlib-only (ADR-006) por una capacidad que el modelo de
amenaza de M0–M3 no necesita (un operador, un host). **Rechazada para v1**;
criterio de revisión §6 contempla su llegada como v2 cuando exista un
consumidor externo de recibos (p. ej. integración CAGF vía ADR-008).

### C. Sin criptografía: token opaco local

En contra: un token sin MAC no liga el descriptor a la capacidad y no
supera vectores negativos de mutación; incumple el espíritu de D2.
Rechazada.

## 4. Consecuencias

- El enum de perfiles de artefacto nace cerrado con un solo valor; añadir
  `digest_verified` exige schema v2 + evidencia por plataforma (D7a).
- La verificación de `admitted_action` en `start` requiere el replay store
  durable de ADR-004; ambos ADR son co-dependientes y deben consensuarse
  juntos.
- `env_allowlist_values` queda dentro de la identidad firmada: los valores
  del entorno admitido viajan en el descriptor. **Consecuencia declarada:**
  el descriptor no debe contener secretos; los eventos registran el
  entorno sólo por digest o forma redactada (propuesta §10.3.4).
- La documentación pública hereda el no-claim de verificación por terceros.

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | HMAC simétrico significa que quien verifica también puede emitir: un proceso que lea la clave del operador puede fabricar capacidades. | **Incorporada:** la clave vive fuera del entorno del proceso supervisado (scrub/allowlist de entorno, ADR-001 §1.5) y el no-claim correspondiente se declara; la protección de la clave es del despliegue (permisos `0600`), no de ektel. |
| A2 | `key_id` derivado de la clave, aun con sal, permite correlacionar despliegues. | **Refutada parcialmente:** la sal de despliegue rompe la correlación cruzada; la correlación intra-despliegue es una feature (rotación auditable), no una fuga. |
| A3 | Re-verificar `admitted_action` en `start` no cierra TOCTOU del artefacto (D7a lo reconoce), así que el consumo único durable es teatro. | **Refutada:** el consumo único no pretende cerrar TOCTOU del artefacto sino replay de la *admisión*; son dos ataques distintos y el primero ya está declarado como riesgo no mitigado. |
| A4 | HMAC-SHA256 truncado vs completo: truncar ahorra bytes pero reduce seguridad. | **Incorporada:** HMAC completo (32 bytes) en capacidad y PoP; el truncamiento sólo aplica a `key_id`, que no es autenticador. |

## 6. Criterio de revisión

Reabrir si:

1. aparece un consumidor externo de recibos (CAGF u otro) que exija
   verificación por terceros → evaluar Ed25519 como schema v2 y excepción
   declarada a stdlib-only;
2. D7a se reabre hacia un perfil de alta integridad;
3. D2 se reabre hacia delegación (requeriría jerarquía de claves).

## 7. Decisiones que este ADR no toma

- Formato de sobre y bytes firmados → ADR-002.
- Vigencia, reloj y persistencia del nonce/consumo → ADR-004.
- Recibo del AuditSink y firma del operador → ADR-007.
