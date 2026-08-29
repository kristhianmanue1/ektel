# Especificación ektel — runtime mínimo M0–M3, v1.2

**Estado:** **adoptada** — consensuada por el dueño el 2026-08-20
(`docs/decisiones/consenso-especificacion-v1-2-2026-08-20.md`); M0 autorizado
por `docs/decisiones/autorizacion-m0-2026-08-20.md`. Toda enmienda posterior
requiere acta explícita.
**Versión del documento:** 1.2 (2026-08-20) — regenerada desde el acta
`docs/decisiones/enmienda-transversal-v3-2026-08-20.md`; v1.0 y v1.1 quedan
superadas antes de consenso. Enmendada tras la doble NO-GO externa de M0 por
`docs/decisiones/enmienda-correccion-m0-2026-08-20.md` (canonicalidad
base64url ADR-010, precedencia de diagnósticos, vocabularios y asientos), y el
2026-08-28 por
`docs/decisiones/aceptacion-adr-011-handoff-2026-08-28.md` (handoff local
`StartRequest`; no cambia `schema_version` v1 ni autoriza M2), y por
`docs/decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md` (contrato
local, topología y parámetros previos a M2; tampoco autoriza implementarlo).
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
  Claude); y
- ADR-010, incorporada por
  `docs/decisiones/enmienda-correccion-m0-2026-08-20.md`, y ADR-011,
  aceptada por
  `docs/decisiones/aceptacion-adr-011-handoff-2026-08-28.md`, y ADR-012,
  aceptada por
  `docs/decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md`.

Ante conflicto, **desde el consenso del 2026-08-20**: manda este documento;
después los ADR; después la tabla pública para lenguaje externo; la propuesta
y los documentos anteriores son evidencia de evolución, no fuentes normativas.
La evidencia reproducible manda sobre cualquier promesa narrativa (propuesta
§2).

**M0 y M1 están autorizados, implementados y cerrados** por sus actas
separadas, incluida la corrección M1-R2; ADR-011/012 fijan diseño previo pero
M2 y M3 siguen sin autorizar (§19.6).

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
   coercionados (bool no es int) y documentos que excedan el **techo global
   de 64 KiB por documento** (enmienda corrección M0 2026-08-20: no hay
   límites por tipo; el techo global ES la regla, sin ambigüedad). Un
   documento cuya **profundidad de anidamiento** exceda la capacidad del
   decodificador JSON —aunque su tamaño quede dentro del techo— se
   rechaza **fail-closed como `malformed_json`** (asiento
   M0-FAR-CLAUDE-01): ningún parser de referencia debe propagar
   excepción alguna por anidamiento.
2. Sobre v1 de estructura fija `{protected_header_b64, payload_b64,
   signature}`. La firma y el `identity_digest` se computan sobre los bytes
   ASCII de `protected_header_b64 + "." + payload_b64` **tal como viajan**,
   estilo JWS — no sobre los bytes decodificados ni sobre el sobre
    completo. El protected header contiene `alg` y `schema_version`, de modo
    que **el algoritmo queda autenticado** (B5). **Orden de verificación
    del receptor (corrección H1, cuatro pasos congelados):**
    (1) localizar y validar la **estructura exterior** del sobre (JSON
    estricto, campos exactos, tipos);
    (2) comprobar **alfabeto, padding y canonicalidad base64url** de
    `protected_header_b64`, `payload_b64` y `signature` — decodificando y
    re-encodificando como **test de pertenencia al conjunto canónico**,
    SIN interpretar el JSON que transportan. La canonicalidad es
    **precondición de admisión**, no defensa en profundidad: un alias no
    canónico de los mismos bytes se rechaza con `bad_base64` AUNQUE su
    MAC sea válida para esa cadena (ADR-010);
    (3) verificar el **MAC sobre las cadenas ASCII originales** tal como
    viajan (`bad_base64` precede inequívocamente a `bad_signature`,
    punto 6);
    (4) sólo después **interpretar y validar semánticamente** header y
    payload. En ningún paso se re-serializa para verificar.
    Cambiar de familia criptográfica exige **envelope v2**, no
    sólo un `alg` nuevo. **Perfil byte-exacto v1 (C2):** `HS256` fijo;
    base64url **sin padding y canónico** para `protected_header_b64`,
    `payload_b64` y `signature` — los bits residuales deben ser cero y el
    receptor lo comprueba re-codificando (**ADR-010**, cierra la
    maleabilidad de firma y la inestabilidad de `identity_digest` frente a
    re-encoding); entrada del MAC = `ASCII("ektel/<dominio>/v1") || 0x00 ||
    ASCII(protected_header_b64) || "." || ASCII(payload_b64)`; longitudes de
    32 bits big-endian donde apliquen. No existe perfil alternativo
    «equivalente» en v1. La regla de canonicalidad aplica a **todo** campo
    base64url de los schemas (p. ej. `stdin_policy.data_b64`).
3. Ningún esquema de canonicalización JSON entra en v1.
4. Cada wire type v1 tiene vectores dorados (bytes + digest esperado +
   diagnóstico esperado) consumibles por todo parser de referencia.
5. Cada wire type lleva `schema_version`; regla uniforme (corrección
   FIX-AND-RETRY 2, B8): entero **mayor que 1** →
   `schema_version_unsupported` (versión mayor desconocida; aplica al
   documento, al invocation-proof y a header/payload firmados); entero
   **<= 0** → `invalid_value` (valor inválido, no versión desconocida;
   cae en la validación de valor respetando la precedencia del punto 6);
   **booleano** → `invalid_value` (bool no es int, §5.1).
6. **Precedencia de diagnósticos de parser (fija, corrección M0):**
   `size_exceeded` → `malformed_json` → `duplicate_key` →
   `schema_version_unsupported` (documento) → `unknown_field` →
    `missing_field` → `invalid_type` → `invalid_value`. En sobres firmados
    los tres campos se validan **por campo, en el orden declarado por el
    schema** (`protected_header_b64` → `payload_b64` → `signature`),
    aplicando en cada uno sus chequeos propios — patrón/longitud →
    `invalid_value` (p. ej. `signature` ≠ 43 chars, acta §12) y
    alfabeto/canonicalidad → `bad_base64` (paso 2 de §5.2) — todo antes
    del MAC; en el caso compuesto gana el primer campo ofensivo del
    orden del schema — luego → `bad_signature` (MAC; paso 3) → header
    (`alg_unsupported`,
    `schema_version_unsupported`, `typ` discordante → `invalid_value`) →
    validación del payload (paso 4). La validación semántica de header y
    payload ocurre SIEMPRE después de una MAC válida (§5.2): una mutación de
    payload con MAC rota produce `bad_signature`, no un error de campo; y
    un alias no canónico con MAC válida produce `bad_base64`, no
    `bad_signature`. Dentro de
    un documento, los valores de campo se comprueban en el orden declarado
    por el schema, no en el orden del documento recibido.
7. **Semántica de `pattern` y `format` en los schemas (corrección
    FIX-AND-RETRY 2026-08-20):** `pattern` conserva la semántica de JSON
    Schema Draft 2020-12 — regex ECMA-262, coincidencia NO anclada. Ningún
    parser o documento del proyecto la redefine como fullmatch. Los
    patrones de `contracts/schemas/v1` van **auto-anclados** (`^` al
    inicio, `(?![\s\S])` como fin absoluto de cadena), de modo que cada
    schema rechaza por sí mismo prefijos, sufijos y salto de línea final —
    incluido ante validadores cuyo motor ancle `$` antes de un `\n` final
    (p. ej. `re.search` de Python). **Saltos de línea, semántica
    independiente del motor (corrección H5 del gate Claude, 2026-08-21):**
    donde un campo prohíba saltos de línea, el patrón lo expresa con una
    **clase de caracteres negada explícita** que excluye `CR`, `LF`,
    `U+2028` y `U+2029` (p. ej. `^/[^\r\n\u2028\u2029]*$`-con-fin-absoluto
    en `command_absolute`/`cwd`) — **nunca** confiando en la semántica de
    `.` de ningún motor (ECMA-262 excluye los cuatro; Python `re` sólo
    `LF`): los parsers ektel y un validador Draft 2020-12 conforme deben
    coincidir en esas cuatro clases de carácter. Los patrones existentes
    de alfabeto cerrado (base64url, hex) ya son inmunes por construcción.
    `format: ektel-b64u-canonical` es un
    formato **privado**: en JSON Schema, `format` es anotación salvo
    aserción explícita del consumidor; un validador genérico NO comprueba
    la canonicalidad (ADR-010) si no registra ese formato — los parsers de
    referencia ektel sí lo asertan (`bad_base64`). Los outcomes cierran
    campos desconocidos por el schema mismo con `unevaluatedProperties:
    false` (Draft 2020-12), compatible con la unión discriminada `oneOf`
    de §8.3: una propiedad sólo es válida si la evalúa la raíz o la
    alternativa elegida. Para validar con un consumidor genérico: registrar
    TODOS los schemas locales por su `$id` (`https://ektel.local/…`),
    NO resolver ese host por red (dominio privado declarativo) y registrar
    y asertar el formato `ektel-b64u-canonical` — prueba de referencia:
    `scripts/validate_with_jsonschema.py`.
8. **Semántica de `accept` (corrección H2, congelada):** el veredicto
    `accept` de un parser de referencia significa **aceptación del parser
    para el wire type solicitado** — el documento es sintáctica y
    estructuralmente válido contra el contrato v1 — y **nada más**: no
    significa autorización, admisión, aprobación de política ni permiso
    de ejecución. Precisión por wire type:
    - Al parsear un **capability envelope, admission-token,
      termination-token o invocation-proof como objeto superior**, el
      parser aplica TODAS sus verificaciones criptográficas (MAC, PoP):
      un `accept` ahí sí implica autenticidad de ese objeto.
    - Al parsear un **action-request**, M0 valida **sólo la estructura
      del documento exterior** (incluida la forma base64url canónica de
      los campos anidados): la firma del sobre anidado, la PoP anidada,
      el replay y la coherencia semántica entre objetos anidados y el
      descriptor (p. ej. `command_absolute` del descriptor vs
      `action_binding.command_absolute` de la capacidad) **pertenecen a
      la admisión M1**, no al parser de contrato M0. Un action-request
      con firma anidada inválida o con incoherencia de comando es
      `accept/ok` en M0 por diseño — la frontera está congelada por
      vectores (`areq-valid-nested-*`) y su violación es defecto M0.
    Ningún campo de metadatos se añade a los schemas actuales para
    transportar esta semántica: es regla del parser, no del wire.

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
   identidades distintas. **Precisión de alcance (FIX-AND-RETRY
   2026-08-20, ADR-010 §6):** la canonicalidad base64url cierra los
   aliases no canónicos *de los mismos bytes decodificados*; no afirma
   identidad estable entre serializaciones JSON semánticamente
   equivalentes — claves reordenadas o espacios distintos son bytes
   distintos y digests distintos, por diseño. v1 identifica el wire
   autenticado, no una forma normalizada del documento.
6. `admitted_action`: valor opaco = `identity_digest` + MAC interno de
   admisión + expiry; `start` re-verifica integridad, vigencia y consumo
   único. **Forma de cable (corrección M0 2026-08-20, la implementación es
   mejor que la letra anterior):** el token de admisión es un **sobre firmado
   estándar** (§5.2, dominio `ektel/admission/v1`) cuyo payload v1 es
   `{schema_version, identity_digest, action_id, exp, issuer_id}` — la
   construcción sobre-JWS elimina la ambigüedad de concatenación de la
   redacción anterior. El token por sí solo no contiene el descriptor
   ejecutable ni autentica los bytes completos del `ActionRequest`: `start`
   recibe el tipo local `StartRequest` y revalida la equivalencia ejecutable
   definida en §8.0; no se afirma identidad byte-a-byte del request exterior
   (ADR-011, N17). La reserva del nonce y el consumo del token son
   **dos registros CAS durable distintos** (§7.4): `nonce_reservation` en
   `admit` y `start_token_consumption` inmediatamente antes del spawn; un
   crash entre el CAS y el spawn deja el token permanentemente gastado y
   produce `start_failed_indeterminate` — nunca habilita replay (B3, C4).
7. Gestión de claves: archivo del operador con permisos `0600`, fuera del
   descriptor y de los eventos. Rotación = reemisión; sin jerarquía ni
   delegación (D2). Los eventos y resultados nunca registran la clave ni
   el HMAC completo: sólo `key_id` (digest truncado de la clave con sal de
   despliegue).
8. **`ExecutionHandle` (B2, C5; terminología enmendada por ADR-012):** lo
   emite `start` exitoso; porta un token
   opaco de terminación con forma de **sobre firmado estándar** (§5.2,
   dominio `ektel/termination/v1`; payload v1 `{schema_version, action_id,
   identity_digest}` — corrección M0 2026-08-20, misma razón que §6.6). Es
   local al coordinador runtime dueño de handles, opaco,
   no serializable, confidencial (redactado en logs y eventos; en el cable
   sólo circula su `handle_ref` para correlación) e inválido
   tras reiniciar el coordinador; no es una capacidad bearer persistible. El
   supervisor dedicado de una acción es otro proceso y su pérdida no redefine
   la identidad del handle.
9. **Ventana de vigencia no vacía (corrección M0):** todo payload de
   capacidad exige `exp > nbf`; `exp <= nbf` se rechaza como
   `invalid_value` en el parser de contrato, antes de cualquier lógica de
   admisión.

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
start(StartRequest) -> StartOutcome
terminate(ExecutionHandle, TerminationReason) -> TerminationOutcome
await_result(ExecutionHandle) -> AwaitedExecution
verify_receipt(Receipt) -> VerificationResult
```

Los tipos de resultado son por operación (C1, §8.3): ninguno carga estados
que su interfaz no puede producir.

### 8.0 `StartRequest` y handoff `admit` → `start` (ADR-011)

`StartRequest { admitted_action: str, action_request_wire: bytes }` es un tipo
local experimental del núcleo, no un documento JSON ni una capacidad. El
llamador debe reenviar los bytes entregados a `admit`, bajo el techo global de
64 KiB, pero el token v1 no permite demostrar identidad byte-a-byte del
documento exterior. La garantía implementable es equivalencia del material
ejecutable revalidado (N17).

Antes de cualquier efecto, `start` valida tipos y tamaño, verifica MAC y
payload cerrado del token, parsea de nuevo el request, repite
representabilidad, capacidad, PoP y binding, exige igualdad de
`identity_digest`, `action_id`, `exp` e `issuer_id`, y construye desde esa única
instantánea un plan de ejecución inmutable. Esta ruta es pura: no reserva de
nuevo el nonce, no reevalúa `PolicyPort` y no emite otro token. El `Allow` es
válido en el instante de admisión; no constituye una lease continua hasta el
spawn.

`start` exige `now_wall < exp`, sin reutilizar la tolerancia de skew de
admisión. Calcula conservadoramente en milisegundos enteros
`now_ms = ceil_exact_ms(now_wall)`,
`remaining_validity_ms = exp * 1000 - now_ms` y
`deadline_eff_ms = min(deadline_ms, remaining_validity_ms)`, mediante
aritmética racional exacta que nunca gana una fracción. Cuando la auditoría
sea obligatoria, obtiene primero el recibo `flush_protocol_completed`; luego
toma una nueva muestra de reloj y recalcula el plazo; después consume por CAS
`identity_digest`; y sólo un resultado `CONSUMED` puede cruzar la frontera de
proceso. Un resultado ambiguo se reconcilia conservadoramente: `spent` implica
`start_failed_indeterminate`; `unspent`, fallo sin spawn y reintento explícito;
`unknown`, `start_failed_indeterminate`. Nunca se habilita replay.

Ektel no persiste por este handoff una copia adicional del comando, entorno o
stdin y no promete recuperación autónoma del descriptor tras reinicio. Esta
decisión tampoco cierra el TOCTOU de una ruta mutable ni liga el contenido del
binario ejecutado (N1). Si `StartRequest` cruza en el futuro un límite de
proceso o red, requiere un wire contract versionado propio.

`AwaitedExecution { result: ExecutionResult, stdout: bytes, stderr: bytes }`
es también un tipo local experimental (ADR-012), no un wire type. Conserva
intacto `ExecutionResult v1`; propiedad, cotas y framing se fijan en §12.

### Autorización de `terminate`

**Enmienda R1, reescrita tras F3; interfaz
corregida por B2):** `terminate` recibe el `ExecutionHandle` emitido por
`start`, que porta un **token opaco de terminación** ligado a la capacidad
**tal como fue admitida para ese `action_id`**. Cuando M3 y
`audit_mode=required` operen, el evento durable previo será una condición del
inicio, no material añadido al token. El derecho de terminación nace del
`start` autorizado y no caduca con la ejecución mientras viva el handle en la
misma instancia del coordinador; no es durable frente a reinicio (ADR-003/012).
La interfaz anterior
`terminate(ActionId, …)` no transportaba
material para autenticar al llamador y queda descartada. Una terminación
sin handle válido se rechaza como `capability_rejected` y se registra como
evento cuando M3 opere la frontera; en M2 esa obligación permanece pendiente,
no satisfecha ficticiamente. La terminación por deadline del propio supervisor no pasa por esta
compuerta (no es iniciada por el llamador).

ADR-012 cierra la semántica local: v1 sólo acepta
`TerminationReason.OPERATOR_REQUESTED`; el receipt aceptado es opaco, local,
no durable y no autenticado. La repetición con el mismo handle y coordinador
devuelve el mismo receipt. Si el primer `terminate` llega después de almacenado
el resultado, el coordinador genera y guarda atómicamente el receipt en el
handle, devuelve `TerminationAccepted` y no contacta al supervisor; es un no-op
que no reclasifica el estado. Reiniciar el coordinador invalida sus handles. Un
handle forjado,
cruzado o de otra instancia produce `TerminationRejected(capability_rejected)`.

No se exponen `before_action`/`after_action` como semántica principal; un
adaptador que los necesite traduce a `PolicyPort.evaluate` y al flujo de
eventos.

### 8.1 ActionRequest v1

Campos (propuesta §7.2, sin cambios): `schema_version`, `action_id`,
`command_absolute`, `args`, `cwd`, `env_allowlist_values`, `stdin_policy`,
`deadline_ms`, `capability_envelope`, `invocation_proof`, `nonce`,
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
AwaitedExecution  (sólo local) = { result: ExecutionResult, stdout: bytes, stderr: bytes }
```

Vocabulario cerrado y versionado: los rechazos de admisión (descriptor mal
formado, capacidad inválida/expirada/reutilizada con `reason_code`
`capability_rejected`, política, auditoría) viven en `AdmissionRejected`;
`start_failed`, `start_failed_indeterminate` (crash tras el CAS de consumo
y antes del spawn, §7.4) **y `capability_rejected`** (perdedor de un `start`
concurrente, §7.4 — enmienda corrección M0 2026-08-20: resuelve el conflicto
interno entre §7.4, que lo exige, y la redacción anterior de esta sección,
que lo negaba; posición verificada por Pinax en la ronda externa) son
códigos de `StartFailed`; los estados de ejecución son sólo los cuatro
post-inicio. Una terminación sin handle
válido produce `TerminationRejected` (código `capability_rejected`), no un
estado de ejecución.

Asientos añadidos por la corrección M0 (2026-08-20), que faltaban en la
letra:

- **Códigos cerrados de `AdmissionRejected`:** `malformed_descriptor`,
  `capability_rejected`, `policy_denied`, `policy_unavailable`,
  `audit_unavailable`, `guarantee_unsupported` (este último con causa en
  §6.1: perfil de garantía no soportado). Los códigos `capability_invalid`,
  `capability_expired` y `capability_reused` **no existen**: la distinción
  inválida/expirada/reutilizada se colapsa en `capability_rejected`.
- **Uniones discriminadas:** los outcomes se validan por alternativa —
  los campos de una alternativa son obligatorios en ella y prohibidos en
  las demás (`started` exige `handle_ref` y prohíbe `reason_code`, etc.).
- **`cause_code` cerrado:** `natural_exit`, `deadline_duration`,
  `deadline_validity_exhausted`, `external_termination`,
  `supervision_failure`.
- **Enums de `ActionRequest` con asiento aquí:** `stdin_policy.kind` ∈
  {`empty`, `inline_b64`}; `repair_policy` ∈ {`none`};
  `requested_guarantees` ⊆ {`runtime_supervision`, `output_bounds`,
  `audit_trail`}.

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

Enmienda ADR-012: el `GuaranteePlan` de admisión declara configuración,
fórmula y topología conocidas entonces; `guarantees_applied` declara valores
efectivos observados durante la ejecución. El plan no se muta ni anticipa
`deadline_eff_ms`. Las entradas ASCII ordenadas de `assumptions` para ambos
objetos y las claves locales de `measurements` son las de ADR-012 §2.3.

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

Frontera por hito (ADR-012): mientras sólo M2 esté implementado, el servicio
acepta exclusivamente `audit_mode=optional`; configurar `required` impide
inicializar antes de solicitudes. Esto no satisface ni elimina los eventos de
C5/C7: permanecen pendientes de M3. Cuando M3 exista, `required` conserva el
orden de ADR-007/011.

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

## 12. Mecánica de supervisión (ADR-009, enmendada por ADR-012)

1. **Salida acotada por bucle de lectura con drenado, no por rlimit:** al
   alcanzar `output_limits` el supervisor **sigue leyendo y descarta**
   (drenar-y-descartar, decidido por B6 — ni cerrar el pipe, que puede
   matar al proceso vía SIGPIPE, ni dejar de leer, que puede bloquearlo),
   lo declara en `stdout_truncation`/`stderr_truncation` con el conteo de
   bytes descartados, y el límite no mata al proceso. `RLIMIT_FSIZE` queda
   descartado como mecanismo primario (no caracterizado; actúa sobre
   archivos, no pipes).
2. **Portador y framing local:** `await_result` devuelve `AwaitedExecution`.
   El supervisor de acción envía frames ordenados de máximo 65 536 bytes por
   stream, con máximo uno no confirmado por stream. La cota estable es
   `max_stdout_bytes + max_stderr_bytes + 2 * 65536`; el pico de
   materialización es
   `2 * (max_stdout_bytes + max_stderr_bytes) + 2 * 65536`, más overhead
   caracterizado pero sin cota exacta de RSS. El wire v1 no cambia.
3. **Sin hang post-kill:** `post_kill_drain_ms` es entero exacto, default
   1000 y rango 1..10000. Tras `SIGKILL`, acota sólo la entrega de pipes, no
   el deadline. Al expirar se cierran y
   `post_kill_forced_pipe_close=1`; ningún descendiente con descriptores
   heredados puede colgar el resultado.
4. **Terminación graduada:** `termination_grace_ms` es entero exacto, default
   2000 y rango 0..60000; 0 implica KILL directo. Se calculan
   `applied_grace_ms`, `useful_runtime_ms`, `soft_termination_at` y
   `hard_deadline_at` conforme a ADR-012 §2.3. El plan declara configuración
   y fórmula; el resultado declara los valores aplicados. Deadline efectivo
   cero rechaza `start` como `capability_rejected` antes del CAS.
5. **Topología:** un coordinador runtime crea un proceso supervisor dedicado
   por acción. Éste queda fuera del grupo ejecutado y crea para la acción un
   grupo propio sin `preexec_fn`. `max_concurrent_actions` es entero exacto,
   default 1 y rango 1..64; se reserva antes de efectos irreversibles y falta
   de slot produce `start_failed` sin consumir token.
6. **Propiedad y capacidad:** el slot se libera al transferir resultado y
   salida al handle. La memoria de handles terminados es del llamador y no
   queda acotada globalmente por los slots. Con máximos wire, 1 acción permite
   128 MiB + 128 KiB estables y pico de 256 MiB + 128 KiB; 64 permiten 8 GiB
   + 8 MiB y pico de 16 GiB + 8 MiB, más overhead.
7. **Grupo y subreaper:** `setsid`/double-fork permanece escape. Sólo el
   supervisor dedicado puede activar `PR_SET_CHILD_SUBREAPER` en Linux; el
   plan declara solicitud y el resultado uso real. Darwin multi-nivel es
   `unsupported`.
8. **Reloj y clasificación:** la vigencia restante pre-CAS se proyecta una
   vez a monotónico y nunca se extiende con reloj de pared. En empate entre
   vigencia y duración gana `deadline_validity_exhausted`. Un reloj final no
   finito o regresivo produce, si es posible,
   `supervision_failed/supervision_failure` sin tiempos fabricados.
9. **Contabilidad de CPU: clase `observed`:** alimenta el resultado y ninguna
   decisión de control en v1.

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

Propuesta §13 M2 más ADR-011/012 y los gates G-M2-01..15: revalidación pura,
CAS y reconciliación, supervisor dedicado, framing/backpressure, memoria y
capacidad publicadas, tiempos/terminación deterministas, procesos observados
recogidos y escapes declarados. Linux y macOS se prueban por separado.
`audit_mode=optional` es el único perfil M2; C5/C7 y `audit_trail` permanecen
pendientes de M3.

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
5. ADR con responsable — **cumplido** (ADR-001 a ADR-012 aceptados; ADR-010,
   ADR-011 y ADR-012 por actas propias, y toda enmienda posterior con acta, conforme a
   la regla nacida del defecto de gobernanza reconocido en
   `enmienda-adr-007-durabilidad-2026-08-19.md`).
6. Autorización separada de M0 y de cada hito — **cumplido para M0**
   (2026-08-20, `docs/decisiones/autorizacion-m0-2026-08-20.md`, tras la
   revisión cruzada final y el consenso explícito de esta v1.2) y **para
   M1** (2026-08-22, `docs/decisiones/autorizacion-m1-2026-08-22.md` con
   adendas; implementado y cerrado con evidencia en dos plataformas —
   ver `docs/decisiones/enmienda-estado-19-6-m1-2026-08-22.md` y
   `docs/decisiones/cierre-m1-2026-08-22.md`); **M2 y M3 siguen sin
   autorizar** y cada uno requiere su propio acto. Enmienda de estado con
   acta: `enmienda-adopcion-19-6-y-cita-tabla-2026-08-20.md` (M0) y
   `enmienda-estado-19-6-m1-2026-08-22.md` (M1).
