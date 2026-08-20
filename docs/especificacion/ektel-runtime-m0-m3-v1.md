# Especificación ektel — runtime mínimo M0–M3, v1.2

**Estado:** **adoptada** — consensuada por el dueño el 2026-08-20
(`docs/decisiones/consenso-especificacion-v1-2-2026-08-20.md`); M0 autorizado
por `docs/decisiones/autorizacion-m0-2026-08-20.md`. Toda enmienda posterior
requiere acta explícita.
**Versión del documento:** 1.2 (2026-08-20) — regenerada desde el acta
`docs/decisiones/enmienda-transversal-v3-2026-08-20.md`; v1.0 y v1.1 quedan
superadas antes de consenso.
**Versión de los contratos:** `schema_version` v1 en todos los wire types.

## 0. Autoridad y genealogía

Este documento funde en una sola fuente normativa:

- la propuesta `docs/propuestas/propuesta-runtime-minimo-m0-m3-2026-08-17.md`
  (en adelante «la propuesta»), que queda como antecedente histórico;
- los ADR-001 a ADR-009, aceptados por el dueño el 2026-08-19
  (`docs/decisiones/consenso-adr-001-009-2026-08-19.md`);
- las enmiendas abiertas de la ronda adversarial 2026-08-19: **R1**
  (autorización de `terminate`, reescrita tras F3), **R3** (absorbida por
  ADR-009) y **R5** (parser clean-room en M0);
- la tabla pública consensuada `docs/claims-y-no-claims.md`
  (`docs/decisiones/consenso-tabla-claims-2026-08-19.md`), que es el
  lenguaje público permitido y se incorpora por referencia;
- la ronda correctiva 2026-08-19 con sus tres actas:
  `enmienda-adr-007-durabilidad-2026-08-19.md` (regularización retroactiva
  y regla «enmienda = acta»), `divergencia-p0-p3-m0-m3-2026-08-19.md`
  (ektel no implementa P0–P3 literalmente) y
  `enmienda-transversal-b1-b8-2026-08-19.md` (B1–B8 de la revisión de
  Codex);
- la segunda ronda externa con su acta
  `enmienda-transversal-v3-2026-08-20.md` (C1–C6 de Codex y D1–D5 de
  Claude).

Ante conflicto, **desde el consenso del 2026-08-20**: manda este documento;
después los ADR; después la tabla pública para lenguaje externo; la propuesta
y los documentos anteriores son evidencia de evolución, no fuentes normativas.
La evidencia reproducible manda sobre cualquier promesa narrativa (propuesta
§2).

**M0 está autorizado** por acta separada
(`docs/decisiones/autorizacion-m0-2026-08-20.md`, propuesta §21.6); M1–M3 no.

## 1. Decisión adoptada

Ektel es un runtime local pequeño que gobierna únicamente su propia
frontera de ejecución: admite una acción, inicia y supervisa un grupo de
procesos, produce un resultado tipado y registra las transiciones que pudo
observar (ADR-001, D1 formalizada). «Local» significa: un solo host, un
solo usuario operador, procesos del mismo UID; cualquier despliegue
multiusuario o multitenant está fuera del modelo y requiere propuesta
nueva.

La gobernanza de negocio no vive en el núcleo: se conecta por el PolicyPort
(§9). CAGF sería una implementación posible de ese puerto, nunca una
dependencia, un modo especial ni una interpretación embebida (ADR-008).

El primer ciclo comprende los hitos M0–M3 y se detiene al cerrar M3
(**stop rule**, §13): memoria, routing, delegación, plugins, presupuestos
de proveedor, CAGF completo y aislamiento fuerte requieren propuesta y
autorización nuevas.

## 2. Objetivos y atributos de calidad

Objetivos funcionales (propuesta §3.1, sin cambios): rechazo fail-closed en
admisión; vínculo autorización–ejecución; supervisor separado; plazo y
terminación dirigida del grupo observado; resultados tipados que nunca
confunden terminación técnica con éxito de negocio; registro de
transiciones observadas; políticas externas sin acoplamiento.

Atributos de calidad en orden (propuesta §3.2, sin cambios): corrección y
fail-closed; honestidad sobre cobertura y fuerza de garantías; trazabilidad
causal; contratos pequeños y versionados; determinismo en validación;
portabilidad sólo donde la semántica sea realmente equivalente;
extensibilidad por adaptadores.

## 3. No-objetivos y frontera

Se mantienen íntegras las exclusiones de la propuesta §4 (D6 formalizada
por ADR-001): sin routing, sin selección de tareas, sin memoria, sin
plugins, sin interpretación CAGF, sin presupuestos de tokens, sin
delegación ni subacciones, sin revocación distribuida, sin multitenant, sin
aislamiento de filesystem/red, sin contención preventiva de CPU/RSS, sin
auditoría de acciones que eviten la frontera, sin recuperación garantizada
tras muerte del supervisor, sin reparación automática de estado externo.

Lenguaje público prohibido (ADR-001): «ejecución segura», «auditoría
completa», «límites duros» sin calificador. El lenguaje permitido es el de
la tabla `docs/claims-y-no-claims.md`.

## 4. Arquitectura

Hexagonal (propuesta §5–6, sin cambios de sustancia): dominio de contratos
puro en el centro; admisión con orden fijo de validación (§6.2 de la
propuesta); supervisor dueño del reloj monotónico, el grupo observado, la
salida acotada, las transiciones y la emisión de eventos; PolicyPort y
AuditSink como puertos estables; adaptadores reemplazables en el borde. El
dominio no importa adaptadores; el almacenamiento de auditoría es
reemplazable y no forma parte del modelo de autorización.

## 5. Wire format (ADR-002)

1. JSON UTF-8 estricto: se rechazan NaN/Infinity, claves duplicadas,
   campos desconocidos (salvo extensión versionada explícita), tipos
   coercionados y documentos que excedan los límites de tamaño declarados
   por tipo.
2. Sobre v1 de estructura fija `{protected_header_b64, payload_b64,
   signature}`. La firma y el `identity_digest` se computan sobre los bytes
   ASCII de `protected_header_b64 + "." + payload_b64` **tal como viajan**,
   estilo JWS — no sobre los bytes decodificados ni sobre el sobre
   completo. El protected header contiene `alg` y `schema_version`, de modo
   que **el algoritmo queda autenticado** (B5). El receptor verifica
   **antes** de decodificar y nunca re-serializa para verificar. El
   decodificado base64 estricto es defensa en profundidad, no pieza
   portante. Cambiar de familia criptográfica exige **envelope v2**, no
   sólo un `alg` nuevo. **Perfil byte-exacto v1 (C2):** `HS256` fijo;
   base64url **sin padding** para `protected_header_b64`, `payload_b64` y
   `signature`; entrada del MAC = `ASCII("ektel/<dominio>/v1") || 0x00 ||
   ASCII(protected_header_b64) || "." || ASCII(payload_b64)`; longitudes de
   32 bits big-endian donde apliquen; orden de verificación: localizar
   `signature` por parseo superficial, verificar el MAC y sólo después
   decodificar header y payload. No existe perfil alternativo
   «equivalente» en v1.
3. Ningún esquema de canonicalización JSON entra en v1.
4. Cada wire type v1 tiene vectores dorados (bytes + digest esperado +
   diagnóstico esperado) consumibles por todo parser de referencia.
5. Cada wire type lleva `schema_version`; el núcleo rechaza versiones
   mayores desconocidas.

## 6. Identidad y capacidad (ADR-003, formaliza D7a)

1. `ExecutionIdentity v1` incluye el campo firmado
   `artifact_identity_profile` con un único valor válido en v1:
   `route_mutable_unverified`. Forma parte del `identity_digest` y del
   `GuaranteePlan`; `ExecutionResult` lo repite. Solicitar otro perfil
   rechaza la admisión con código cerrado de garantía no soportada. Un
   perfil de alta integridad requiere versión de schema posterior con
   evidencia real por plataforma; no se reserva valor «pending».
2. Autenticación de la capacidad raíz: **HMAC-SHA256** sobre
   `protected_header_b64 + "." + payload_b64` (§5.2), con clave simétrica
   del operador. Razón primaria: el modelo de amenaza (un host, un
   operador) no tiene separación de roles que la asimetría compruebe.
   Razón secundaria (insuficiente por sí sola): stdlib-only (ADR-006).
3. Agilidad de algoritmo: `alg` viaja **dentro del protected header
   autenticado** (valor v1: `HS256`, cerrado); no existe downgrade por
   sustitución de `alg`. Cambiar de familia criptográfica exige envelope
   v2; ningún `alg` nuevo se acepta fuera de la lista cerrada del
   verificador.
4. **Separación de dominios (B5):** cada uso de HMAC lleva prefijo cerrado
   y codificación por longitudes (nunca concatenación ambigua):
   `ektel/capability/v1` (capacidad), `ektel/pop/v1` (`invocation_proof` =
   HMAC sobre `len(nonce) || nonce || payload_digest`), y
   `ektel/admission/v1` (token de admisión) y `ektel/termination/v1`
   (token de terminación del `ExecutionHandle`, B2). Construcción única en
   v1 (C2): prefijo de dominio ASCII terminado en `0x00` sobre la clave del
   operador; **HKDF prohibido en v1** — dos construcciones «equivalentes»
   producirían implementaciones incompatibles.
5. `identity_digest`: SHA-256 de la cadena autenticada
   `protected_header_b64 + "." + payload_b64`; incluye
   `artifact_identity_profile` y nonce. Dos serializaciones distintas son
   identidades distintas.
6. `admitted_action`: valor opaco = `identity_digest` + MAC interno de
   admisión + expiry; `start` re-verifica integridad, vigencia y consumo
   único. La reserva del nonce y el consumo del token son **dos registros
   CAS durable distintos** (§7.4): `nonce_reservation` en `admit` y
   `start_token_consumption` inmediatamente antes del spawn; un crash entre
   el CAS y el spawn deja el token permanentemente gastado y produce
   `start_failed_indeterminate` — nunca habilita replay (B3, C4).
7. Gestión de claves: archivo del operador con permisos `0600`, fuera del
   descriptor y de los eventos. Rotación = reemisión; sin jerarquía ni
   delegación (D2). Los eventos y resultados nunca registran la clave ni
   el HMAC completo: sólo `key_id` (digest truncado de la clave con sal de
   despliegue).
8. **`ExecutionHandle` (B2, C5):** lo emite `start` exitoso; porta un token
   opaco de terminación (MAC con dominio `ektel/termination/v1` sobre
   `action_id || identity_digest`). Es local al proceso supervisor, opaco,
   no serializable, confidencial (redactado en logs y eventos) e inválido
   tras reiniciar el supervisor; no es una capacidad bearer persistible.

El descriptor no contiene secretos (R2): los eventos registran el entorno
sólo por digest o forma redactada (§10).

## 7. Vigencia, reloj y nonce (ADR-004, formaliza D2/D3)

1. **Dos relojes con roles separados:** el reloj de pared valida
   `nbf`/`exp` en admisión; el reloj monotónico gobierna plazos de
   supervisión, duraciones y precedencia. Nunca se cruzan.
2. **Truncamiento impuesto (D3):** en admisión se computa `exp` como cota
   absoluta de pared y `deadline_eff = min(deadline_solicitado,
   exp - now_wall)`; si `exp <= now_wall`, rechazo por capacidad expirada.
   El supervisor aplica **ambas**: la duración monotónica desde el arranque
   *y* la cota absoluta de pared `exp`; gana la más temprana. Una
   capacidad que expira durante la ejecución no se revoca activamente
   (excluido por D6): la transición es `deadline_exceeded` con
   `cause_code` cerrado de vigencia agotada; el resultado registra la
   vigencia al admitir.
3. **Tolerancia de skew declarada:** fija de despliegue (propuesta
   inicial: 30 s), registrada en el evento de admisión. Supuesto: reloj de
   pared disciplinado (NTP); un administrador del host está fuera del
   modelo (§12).
4. **Replay store durable y obligatorio, con dos registros CAS distintos
   (B3, detalle C4/D3):** `nonce_reservation` durante `admit` — clave
   `(issuer_id, nonce)`, estados `free → reserved` — y
   `start_token_consumption` inmediatamente antes de crear el proceso —
   clave `identity_digest`, estados `unspent → spent`; el perdedor de un
   `start` concurrente recibe `capability_rejected` con código cerrado.
   **Recuperación:** un crash después del CAS de consumo y antes del spawn
   deja el token permanentemente gastado y produce
   `start_failed_indeterminate`; la operación se reintenta como nueva
   admisión con nonce nuevo, y la reconciliación consulta el store por
   `identity_digest` — nunca replay. Ambos registros usan el
   perfil `posix-fsync-dir/v1` con la corrección por plataforma de §11.3 y
   sobreviven reinicios; un nonce permanece reservado hasta
   `exp + tolerancia`. Sin store disponible, la admisión rechaza
   (fail-closed); el store en memoria sólo existe en pruebas.
5. **Ámbito del nonce:** único por `(emisor de capacidad, nonce)` dentro
   del despliegue.

## 8. Operaciones del núcleo y contratos públicos

```text
admit(ActionRequest) -> AdmissionOutcome
start(AdmittedAction) -> StartOutcome
terminate(ExecutionHandle, TerminationReason) -> TerminationOutcome
await_result(ExecutionHandle) -> ExecutionResult
verify_receipt(Receipt) -> VerificationResult
```

Los tipos de resultado son por operación (C1, §8.3): ninguno carga estados
que su interfaz no puede producir.

**Autorización de `terminate` (enmienda R1, reescrita tras F3; interfaz
corregida por B2):** `terminate` recibe el `ExecutionHandle` emitido por
`start`, que porta un **token opaco de terminación** ligado a la capacidad
**tal como fue admitida para ese `action_id`** y al evento de admisión
durable: el derecho de terminación nace de la admisión y no caduca con la
ejecución. La interfaz anterior `terminate(ActionId, …)` no transportaba
material para autenticar al llamador y queda descartada. Una terminación
sin handle válido se rechaza como `capability_rejected` y se registra como
evento. La terminación por deadline del propio supervisor no pasa por esta
compuerta (no es iniciada por el llamador).

No se exponen `before_action`/`after_action` como semántica principal; un
adaptador que los necesite traduce a `PolicyPort.evaluate` y al flujo de
eventos.

### 8.1 ActionRequest v1

Campos (propuesta §7.2, sin cambios): `schema_version`, `action_id`,
`command_absolute`, `args`, `cwd`, `env_allowlist_values`, `stdin_policy`,
`deadline`, `capability_envelope`, `invocation_proof`, `nonce`,
`repair_policy`, `output_limits`, `requested_guarantees`,
`metadata_opaque`. Restricciones de la propuesta §7.2 se mantienen,
incluida: `command_absolute` no implica identidad suficiente del artefacto
(ver §6.1 y no-claim N1).

### 8.2 AdmissionOutcome v1

```text
Admitted { admitted_action, identity_digest, policy_receipt?, guarantee_plan }
AdmissionRejected { reason_code, safe_detail, retryable, evidence_receipt? }
```

`policy_receipt` lo produce el PolicyPort cuando está configurado
(ADR-008, D7b absorbida por ADR-007). Códigos de rechazo cerrados y
versionados; `safe_detail` nunca filtra secretos, claves, entorno completo
ni material de firma.

### 8.3 Tipos de resultado por operación (ADR-005, formaliza D5; corregido por C1)

Cada operación tiene su tipo de resultado; ningún tipo carga estados que su
interfaz no puede producir:

```text
AdmissionOutcome  = Admitted | AdmissionRejected { reason_code, safe_detail, retryable, evidence_receipt? }
StartOutcome      = Started { handle } | StartFailed { reason_code }
TerminationOutcome = TerminationAccepted { receipt } | TerminationRejected { reason_code }
ExecutionResult   (sólo post-inicio) = executed | deadline_exceeded | terminated | supervision_failed
```

Vocabulario cerrado y versionado: los rechazos de admisión (descriptor mal
formado, capacidad inválida/expirada/reutilizada con `reason_code`
`capability_rejected`, política, auditoría) viven en `AdmissionRejected`;
`start_failed` y `start_failed_indeterminate` (crash tras el CAS de consumo
y antes del spawn, §7.4) son códigos de `StartFailed`; los estados de
ejecución son sólo los cuatro post-inicio. Una terminación sin handle
válido produce `TerminationRejected` (código `capability_rejected`), no un
estado de ejecución.

`budget_exceeded` **no existe en v1**; sólo podrá añadirse para una
magnitud cuyo mecanismo esté clasificado y probado en la plataforma
objetivo, nunca como comodín. Precedencia fija y **clasificación por causa**
(C6): el supervisor distingue `soft_termination_at` (deadline efectivo
menos gracia) y `hard_deadline_at`; salida natural antes de iniciada la
escalación → `executed`; escalación iniciada por agotamiento del plazo →
`deadline_exceeded`; terminación externa aceptada antes de la escalación →
`terminated`. **Ausencia honesta de resultado:** si el supervisor muere no
hay resultado y no se inventa estado. `executed` no significa éxito de
negocio. `guarantees_applied` refleja lo que realmente operó (con su
clase), no lo solicitado. Campos del resultado: los de la propuesta §7.5,
incluidos `stdout_truncation`, `stderr_truncation`, `discarded_bytes` y
`last_event_receipt`.

## 9. Clases de garantía y PolicyPort (ADR-008)

Clases de garantía (propuesta §8, sin cambios): `enforced`, `reactive`,
`observed`, `unsupported`; cada entrada de `GuaranteePlan` declara
`magnitude, class, platform, mechanism, assumptions, known_escapes,
failure_mode, evidence_ref`. Reglas 1–5 de la propuesta §8 se mantienen,
incluida: M0–M3 no usan CPU/RSS para producir `budget_exceeded`.

Contrato del puerto (propuesta §9.1 adoptado tal cual):
`PolicyPort.evaluate(PolicyEvaluationRequest) -> PolicyDecision` con
`Allow`/`Deny`/`Indeterminate`; `Indeterminate` se trata como rechazo
cuando la política es obligatoria. Ektel afirma la **presencia** de un
`Allow`, no la corrección de la política externa. La validación del
**sobre de respuesta** es del núcleo (B7): forma, `decision_id`, vigencia
(`valid_until` contra reloj de pared con la tolerancia declarada) y
recepción dentro del timeout — medido con **reloj monotónico** (los plazos
nunca usan reloj de pared; la vigencia sí); un `Allow` expirado o tardío se convierte en
`Indeterminate` — y en rechazo cuando el puerto sea requerido. Lo que el
núcleo no valida es que el adaptador decida bien (no-claim N16).

**Perfil de despliegue declarado:** el despliegue publica
`policy_mode ∈ {absent, optional, required}` y
`audit_mode ∈ {optional, required}`; el perfil viaja en
`deployment_claims` y se documenta. Con `policy_mode=required`, puerto
ausente, indisponible o `Indeterminate` rechaza la admisión. Con
`optional`, `Indeterminate` o puerto indisponible es **fail-open
declarado**: la admisión prosigue y emite el evento `policy_degraded`,
obligatorio si `audit_mode=required` — la degradación nunca es silenciosa
(I1). Los contract tests corren contra el puerto nulo y uno falso: el
núcleo se prueba completo sin CAGF.

**Frontera CAGF:** las conversiones prohibidas de la propuesta §9.2 son
norma (una capacidad local no es conformidad A9; un log local no es
auditoría constitucional; un proceso terminado no es satisfacción de A0;
una decisión individual no es verificación A2/A4; hooks no son gobernanza
A10). Ningún tipo, campo, código de error ni documento del núcleo nombra
axiomas CAGF.

## 10. Trazabilidad y eventos (propuesta §10 + ADR-007)

Cobertura honesta (§10.1 de la propuesta, sin cambios). `RuntimeEvent v1`
con los campos y tipos mínimos de la propuesta §10.2 más
`policy_degraded` (I1). Invariantes 1–6 de la propuesta §10.3, con la
invariante 5 corregida por C3: la cadena hash aporta en v1 **diagnóstico de
consistencia interna únicamente** — no prueba autoría, completitud, orden
global ni almacenamiento externo, y un atacante que reescribe todo el
almacén puede recalcularla; la verificación contra un head confiable
externo requeriría un puerto `TrustedHeadStore` que no existe en v1
(propuesta v2; el claim C8 se retiró de la tabla pública). Las demás
invariantes sin cambios: payloads sensibles por digest o forma redactada;
la brecha de auditoría es explícita y nunca se rellena retrospectivamente.

## 11. AuditSink (ADR-007, absorbe D7b)

1. Contrato: `AuditSink.append(RuntimeEvent) -> AppendOutcome` y
   `AuditSink.query(event_id) -> EventStatus`. `AppendOutcome` distingue
   exactamente cinco casos: **`flush_protocol_completed`** (antes
   `durable` — renombrado por D1: el nombre no debe prometer lo que la
   definición desmiente), `accepted_undemonstrated`,
   `rejected`, `unavailable`, `unknown_after_timeout`. Un `append()`
   exitoso no equivale a durabilidad. `query` es parte del contrato:
   la reconciliación tras `unknown_after_timeout` es por `event_id`, con
   respuestas `present`/`absent`/`unknown`; `query` sirve a la
   reconciliación operativa, no a la verificación (esa es
   `verify_receipt` contra digest y cadena).
2. Fail-closed: con `audit_mode=required`, un evento previo al inicio sin
   recibo `flush_protocol_completed` rechaza el inicio. La pérdida del sink después de
   iniciar produce brecha explícita (`audit_gap_detected` o ausencia
   declarada); nunca se rellena.
3. **Sink de referencia (M3):** append con fsync de archivo y
   directorio antes de emitir `flush_protocol_completed` (perfil
   `posix-fsync-dir/v1`), con corrección por plataforma: en Darwin
   `fsync()` no vacía la caché del disco y el sink usa
   `fcntl(F_FULLFSYNC)`; en Linux el fsync estándar basta (disponibilidad
   de la primitiva caracterizada en
   `tests/escape/test_host_characterization.py::test_flush_primitive_available`).
   `flush_protocol_completed` significa "protocolo de plataforma
   completado bajo supuestos declarados" (B8), con testabilidad por
   niveles (D2): nivel 1 — SIGKILL del escritor a mitad del protocolo
   (M3); nivel 2 — `dm-log-writes`/`dm-flakey` en Linux (M3); nivel 3 —
   corte físico real, no testeable sin hardware (supuesto declarado, N5).
   La sonda corre bajo el directorio real configurado del sink, no bajo el
   temporal del sistema (D5). Sinks sin protocolo demostrable sólo emiten
   `accepted_undemonstrated`.
4. **Recibo v1 (sin MAC — B1):** `{receipt_version, event_id,
   event_digest, previous_event_digest, sink_identity, received_at_wall,
   durability_class}` — acuse estructural del sink, no objeto autenticado.
   La cadena por digest aporta **diagnóstico de consistencia interna** en
   v1; no existe puerto de head confiable (C3; C8 retirado de la tabla
   pública, N7/N14). Un
   recibo autenticado (MAC con clave separada y dominio propio) es
   propuesta v2.

## 12. Mecánica de supervisión (ADR-009, absorbe R3)

1. **Salida acotada por bucle de lectura con drenado, no por rlimit:** al
   alcanzar `output_limits` el supervisor **sigue leyendo y descarta**
   (drenar-y-descartar, decidido por B6 — ni cerrar el pipe, que puede
   matar al proceso vía SIGPIPE, ni dejar de leer, que puede bloquearlo),
   lo declara en `stdout_truncation`/`stderr_truncation` con el conteo de
   bytes descartados, y el límite no mata al proceso. `RLIMIT_FSIZE` queda
   descartado como mecanismo primario (no caracterizado; actúa sobre
   archivos, no pipes).
2. **Sin hang post-kill:** tras `SIGKILL` al grupo, la espera de EOF tiene
   plazo propio; al expirar, el supervisor cierra los pipes y declara el
   cierre forzado en el resultado. Ningún descendiente con descriptores
   heredados puede colgar al supervisor.
3. **Terminación graduada:** `SIGTERM` al grupo, gracia fija de despliegue
   (propuesta inicial: 2 s), después `SIGKILL` al grupo. La gracia está
   presupuestada dentro del deadline efectivo: la secuencia de terminación
   inicia antes del vencimiento, **y el descuento es visible en el
   contrato** (B6): `GuaranteePlan` y resultado declaran la gracia aplicada
   y el tiempo útil resultante; gracia 0 (SIGKILL directo) es válida y
   declarada.
4. **Grupo de procesos como unidad de terminación** (`setpgid`); el escape
   por `setsid`/double-fork es declarado, no perseguido (§13, fuera del
   modelo).
5. **Subreaper opcional en Linux:** el supervisor se declara
   `PR_SET_CHILD_SUBREAPER` cuando el despliegue requiera contabilidad
   multi-nivel; se declara en el `GuaranteePlan` con su clase real
   (`observed`/`reactive`), nunca `enforced`. En Darwin la contabilidad
   CPU multi-nivel es `unsupported`, sin mitigación conocida (E2).
6. **Contabilidad de CPU: clase `observed`:** alimenta el resultado y
   ninguna decisión de control en v1.

## 13. Seguridad y modelo de amenaza (ADR-001)

Se adopta §12 de la propuesta como normativo. Dentro del modelo: descriptor
mal formado; capacidad ausente, inválida, expirada o reutilizada; replay
dentro del ámbito de nonce; comando que no termina; salida ilimitada;
fallos parciales del sink; errores de traducción en adaptadores; confusión
entre observación y garantía. Fuera del modelo: atacante con control del
host; kernel comprometido; escape de sandbox; `setsid`/double-fork;
D-state; exfiltración por red o filesystem no aislados; secretos ya
disponibles al proceso; efectos externos irreversibles; muerte simultánea
de supervisor y almacén sin watchdog.

Riesgos no mitigados incorporados (ADR-003): sustitución del contenido
resuelto por `command_absolute` entre admisión e inicio (perfil
`route_mutable_unverified`, no-claim N1), y efectos de modificación del
host que ektel no aísla ni detecta. Ektel no protege su almacén ni su clave
contra el proceso supervisado más allá de la separación de escritura por
diseño (N14): si la clave se filtra, C1, C2 y C7 caen en silencio
(capacidades fabricadas: caen C1 y C2); C7 sólo cae si además se
compromete o evade el AuditSink; y si el almacén es reescrito por completo,
la cadena deja de detectarlo (C8 está retirado: en v1 es diagnóstico de
consistencia interna).

## 14. Plataforma y lenguaje (ADR-006)

- **Lenguaje:** Python 3.12 (mínimo 3.12), stdlib-only para el núcleo de
  M0–M3; cero dependencias de terceros en dominio, puertos y supervisor.
- **Plataforma primaria M1–M3:** Linux aarch64, caracterizado únicamente
  en kernel 6.11.11-linuxkit (VM de Docker Desktop) con Python 3.12.14.
  Otro kernel, distro o entorno no hereda garantías sin re-ejecutar la
  suite pineada de `tests/escape/`.
- **Plataforma secundaria:** Darwin arm64 (macOS 26.5.2, Python 3.12.12)
  con tabla de garantías degradada y explícita; un cambio de versión mayor
  de macOS exige re-caracterización.
- **x86_64:** puerta de pre-producción, no de M1–M3 (N12).

Las garantías de clase `enforced` lo son sólo bajo el entorno declarado;
la portabilidad no se infiere por analogía.

## 15. Hitos y criterios de salida

### M0 — Contratos congelables

Entregables y criterio de la propuesta §13, con la enmienda **R5**: los
vectores deben ser consumibles por al menos dos parsers de referencia, y
**al menos uno se escribe desde el schema y los vectores, sin leer el
código del otro (clean-room)**; la independencia de lenguaje queda como
ideal, no como requisito de M0 (dado ADR-006). Además: D1–D7 resueltas
(cumplido), schemas validables sin runtime, y ninguna decisión abierta
puede cambiar la identidad firmada (cumplido con ADR-002/003).

### M1 — Admisión

Propuesta §13 M1 sin cambios: parser estricto, identidad determinista,
verificación de capacidad raíz, PoP, replay store con semántica de reinicio
(§7 puntos 4–5), PolicyPort nulo y adaptador de prueba. Criterio: ningún caso
inválido inicia proceso; vectores criptográficos negativos pasan; fallos
de dependencia requerida fail-closed; fuzzing sin aceptación ambigua.

### M2 — Supervisión

Propuesta §13 M2 más la mecánica de §12: sin hangs en la suite acotada;
precedencia deadline determinista; procesos observados recogidos; escapes
conocidos producen limitaciones declaradas, no tests falsamente verdes;
Linux y macOS se prueban por separado.

### M3 — Evidencia

Propuesta §13 M3 más el contrato AuditSink de §11: RuntimeEvent v1, sink en
memoria de pruebas y sink de referencia `flush_protocol_completed` (con `F_FULLFSYNC` en
Darwin), recibos y verificación, pruebas de pérdida/retry/reconciliación,
adaptador de política falso. Criterio de la propuesta §13 M3 sin cambios.

**Stop rule:** al cerrar M3 no se inicia M4 implícito (ADR-001).

## 16. Estrategia de pruebas, versionado y observabilidad

Se adoptan sin cambios de sustancia la propuesta §14 (pirámide y matriz
mínima; pruebas peligrosas fuera de CI general), §15 (versionado:
`schema_version` por wire type, rechazo de mayores desconocidas, códigos
no reutilizados, vectores dorados, SDK derivados, cambio incompatible =
versión mayor) y §16 (métricas mínimas sin contenido sensible; logs y
métricas no sustituyen `RuntimeEvent`). La API pública es estable sólo
después de M0 y de la prueba de implementación independiente (R5); antes
se etiqueta `experimental`.

## 17. Lenguaje público

La tabla `docs/claims-y-no-claims.md` (consensuada 2026-08-19) es parte
normativa de esta especificación: afirmar un no-claim como claim, o un
claim antes de que su criterio de salida esté probado, es un defecto que se
corrige antes de cualquier publicación. Todos los claims tienen hoy estado
de evidencia **P** (propuesta); la promoción a **V** es por claim, al
superar la suite de su hito.

## 18. Estructura de repositorio tras autorización de M0

Se adopta la propuesta §17: `contracts/`, `src/{domain,application,ports,
adapters}`, `tests/{contract,unit,integration,characterization,
adversarial}`, `docs/`. No se crea esta estructura antes de la autorización
de M0. La carpeta `tests/escape/` puede migrarse a
`tests/characterization/` en un cambio separado que preserve historia.

## 19. Riesgos y criterio de adopción

La tabla de riesgos de la propuesta §19 se mantiene, con «decidir
digest/handle estable en D7 y ADR-003» ya resuelto por §6.1 (perfil
`route_mutable_unverified` declarado, no mitigado).

Criterio de adopción (propuesta §21) a la fecha de esta v1.2:

1. D1–D7 con resolución y dueño — **cumplido** (2026-08-18).
2. Ronda adversarial — **cumplida** (R1–R12 + externa F1–F8 + externa
   Codex B1–B8, esta última aplicada en esta versión).
3. Objeciones incorporadas o refutadas — **cumplido**, con actas
   (`enmienda-transversal-b1-b8-2026-08-19.md`).
4. Tabla de claims/no-claims — **cumplida y enmendada con acta**
   (consensuada 2026-08-19; C2, C8, N8, N14, N16 corregidos por B1–B7).
5. ADR con responsable — **cumplido** (ADR-001 a ADR-009 aceptados;
   enmiendas posteriores con acta, por la regla nacida del defecto de
   gobernanza reconocido en `enmienda-adr-007-durabilidad-2026-08-19.md`).
6. Autorización separada de M0 y de cada hito — **cumplido para M0**
   (2026-08-20, `docs/decisiones/autorizacion-m0-2026-08-20.md`, tras la
   revisión cruzada final y el consenso explícito de esta v1.2); **M1, M2 y
   M3 siguen sin autorizar** y cada uno requiere su propio acto. Enmienda de
   estado con acta: `enmienda-adopcion-19-6-y-cita-tabla-2026-08-20.md`.
