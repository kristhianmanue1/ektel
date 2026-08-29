# ADR-011: Handoff de admisión hacia `start`

**Estado:** **propuesto para decisión del dueño** — no aceptado ni normativo.
No autoriza M2, cambios de schemas, proceso real, supervisión, tag ni release.

**Fecha:** 2026-08-28.

**Origen:** cierre administrativo M1-R1 y
`docs/propuestas/propuesta-handoff-admision-m2-2026-08-28.md`. Resuelve el
bloqueo contractual entre el token emitido por M1 y el descriptor que M2
necesitaría para crear un proceso. Debe recibir aceptación explícita separada
antes de modificar la especificación normativa o construir M2.

**Contexto normativo relacionado:** ADR-003 (identidad y token de admisión),
ADR-004 (vigencia y dos CAS), ADR-005 (resultados de `start`), ADR-007
(evento previo cuando la auditoría es obligatoria), ADR-008 (PolicyPort) y
ADR-009 (mecánica de supervisión).

## 1. Problema

La API vigente declara `start(AdmittedAction)`, pero el `admitted_action` v1
sólo autentica `{identity_digest, action_id, exp, issuer_id}`. No contiene
`command_absolute`, argumentos, entorno, cwd, stdin, límites de salida ni
`deadline_ms`. Por tanto, el token no basta para construir la ejecución y no
autoriza recuperar esos datos desde una fuente mutable implícita.

`identity_digest` identifica la cadena autenticada del sobre de capacidad, no
los bytes completos del `ActionRequest`. Dos documentos exteriores diferentes
pueden reutilizar la misma capacidad y producir el mismo token si conservan las
invariantes ligadas por `action_binding`. El diseño v1 no puede demostrar que
los bytes presentados a `start` sean los mismos que observó `admit`.

## 2. Decisión propuesta

### 2.1 Tipo local compuesto

Sustituir conceptualmente la firma incompleta por:

```text
StartRequest {
  admitted_action: str,
  action_request_wire: bytes
}

start(StartRequest) -> StartOutcome
```

`StartRequest` es un tipo local experimental del núcleo, no un nuevo documento
JSON ni una capacidad. El llamador conserva y reenvía el `ActionRequest` bajo
el techo global vigente de 64 KiB. Ektel no persiste una copia adicional del
comando, entorno o stdin para resolver el handoff.

Si en el futuro este tipo cruza un límite de proceso o red, deberá obtener un
wire contract versionado con sus propios vectores, límites y tratamiento de
bytes. Esta ADR no reserva esa forma.

### 2.2 Garantía exacta: equivalencia revalidada, no identidad de bytes

El llamador **debe** reenviar los bytes que recibió `admit`, pero el token v1 no
permite a ektel probar ese hecho. La garantía implementable es más estrecha:
`start` sólo puede usar un descriptor que vuelva a superar todas las
validaciones determinantes y que sea coherente con la capacidad autenticada y
con los campos del token.

Esto demuestra equivalencia del material ejecutable ligado por el contrato; no
demuestra igualdad byte-a-byte del documento exterior. En particular,
serialización JSON y `metadata_opaque` no quedan autenticados por
`identity_digest`. Ningún claim puede llamarlos “bytes originales”.

Una futura garantía byte-a-byte requiere una versión nueva del token que firme
un digest del `ActionRequest` completo. No se añade silenciosamente al token v1.

### 2.3 Revalidación pura antes de cualquier efecto

`start` debe aplicar, en este orden, una ruta separada de la admisión:

1. exigir tipos exactos para ambos campos y el techo de 64 KiB antes del parseo;
2. verificar forma, canonicalidad base64url, MAC y payload cerrado del token de
   admisión con la clave activa;
3. parsear de nuevo `action_request_wire` con el parser v1 congelado;
4. repetir representabilidad de `command_absolute`, cwd, args, entorno y stdin;
5. verificar la capacidad y PoP, incluido reloj de pared, nonce, digest efectivo
   de stdin y coherencia completa descriptor ↔ `action_binding`;
6. exigir igualdad exacta entre token y material revalidado para
   `identity_digest`, `action_id`, `exp` e `issuer_id`; y
7. construir en memoria un plan de ejecución inmutable a partir de esa única
   instantánea validada.

Esta ruta no llama `reserve_nonce`, no evalúa de nuevo `PolicyPort` y no emite
otro token. Reutilizar `AdmissionService.admit()` sería incorrecto: confundiría
la reserva previa esperada con replay y repetiría efectos y dependencias no
deterministas.

Todo fallo de forma, cripto, vigencia o coherencia produce `StartFailed` con
`reason_code=capability_rejected` y `safe_detail` saneado. Un fallo de una
dependencia pre-inicio requerida produce `start_failed`. En ambos casos no se
crea proceso y, mientras no se haya intentado el CAS, el token permanece sin
gastar.

### 2.4 Semántica de política

El token firmado prueba que M1 terminó una admisión, incluida la política que
correspondía al perfil de despliegue en ese instante. `start` no vuelve a
consultar `PolicyPort`: hacerlo abriría una segunda decisión con otra identidad,
otra vigencia y carreras difíciles de reconciliar.

En v1, `PolicyReceipt.valid_until_wall` valida la frescura del `Allow` cuando se
recibe; **no es una lease de lanzamiento** porque su valor no está atestado por
el token de admisión. Por tanto, ektel no afirma autorización de política
continua entre `admit` y `start`. Un despliegue que la requiera necesita token
v2 —o un contexto local autenticado— que ligue esa cota; no puede inferirla del
recibo opcional.

### 2.5 Vigencia y deadline

`start` toma una nueva muestra finita de reloj de pared y exige
`now_wall < token.exp` sin usar el skew de admisión para crear tiempo de
ejecución después de `exp`. Calcula:

```text
exp_ms = token.exp * 1000
now_ms = ceil_exact_ms(now_wall)
remaining_validity_ms = exp_ms - now_ms
deadline_eff_ms = min(action_request.deadline_ms, remaining_validity_ms)
```

`ceil_exact_ms` multiplica por 1000 el valor racional exacto del `float`
validado —por ejemplo, mediante `as_integer_ratio()`— y redondea hacia arriba
con división entera; nunca redondea hacia abajo ni gana una fracción de
milisegundo. Si la conversión no es representable o el resultado no es
positivo, rechaza antes de consumir. La duración se transforma una sola vez a
una cota monotónica del supervisor; la cota absoluta `exp` sigue aplicándose
conforme a ADR-004.

Esta regla hace `start` deliberadamente más restrictivo que `admit`: no aplica
`skew_tolerance_s` y rechaza cuando `now_wall >= token.exp`, aunque la admisión
hubiera aceptado dentro de su tolerancia post-exp. El skew permite interpretar
claims entre relojes; no concede ejecución local después de la cota atestada.

Después de cualquier dependencia previa potencialmente lenta —en particular el
evento pre-inicio cuando `audit_mode=required`— `start` vuelve a muestrear el
reloj y recalcula la cota justo antes del CAS. Nunca reutiliza una duración que
ya pudo vencer.

### 2.6 Linealización de efectos

Una vez construido el plan inmutable, el orden es:

1. cuando `audit_mode=required`, lograr para el evento pre-inicio el recibo
   `flush_protocol_completed` exigido por ADR-007; cualquier otro resultado de
   `AuditSink.append` rechaza fail-closed;
2. inmediatamente después de las dependencias previas y antes del CAS, volver a
   muestrear el reloj, revalidar vigencia y fijar las cotas de supervisión;
3. ejecutar el CAS durable
   `start_token_consumption(identity_digest): unspent → spent`; y
4. invocar inmediatamente la primitiva de spawn con el plan ya validado, sin
   otra dependencia externa intermedia.

Sólo `ConsumeOutcome.CONSUMED` cruza la frontera de proceso.
`ALREADY_SPENT` produce `capability_rejected`. `UNAVAILABLE`, una excepción o
un tipo desconocido obligan a reconciliar con
`start_token_status(identity_digest)` antes de permitir otro intento:

- `spent` → `start_failed_indeterminate`, sin spawn ni reintento;
- `unspent` → `start_failed`, sin spawn; un nuevo intento del mismo token es
  admisible; y
- `unknown` → `start_failed_indeterminate`, sin spawn ni reintento ciego.

Ningún valor truthy o subtipo no reconocido adquiere autoridad. Si la
reconciliación no está disponible, prevalece el resultado indeterminado. La
consulta es un snapshot posterior, no atómico con el CAS: `unspent` sólo
autoriza intentar un CAS nuevo; nunca autoriza spawn directamente y el estado
puede cambiar antes de ese intento.

El CAS linealiza el derecho de inicio, no garantiza que el spawn sucedió. Si el
CAS queda durable y el supervisor cae antes de conocer el resultado del spawn,
el token permanece gastado. Sin un handle confirmado, la reconciliación por
`identity_digest` sólo puede afirmar `start_failed_indeterminate`; no fabrica
un handle ni reintenta. El llamador debe obtener una admisión nueva con nonce
nuevo.

Un fallo explícito y síncrono de la primitiva antes de crear proceso produce
`start_failed`. Un spawn confirmado produce `Started` y desde ese punto rigen
ADR-005 y ADR-009. La muerte del supervisor continúa siendo ausencia honesta de
resultado; esta ADR no promete recuperación de procesos huérfanos.

### 2.7 Retención y confidencialidad

El llamador es responsable de conservar `action_request_wire` hasta `start`.
Ektel:

- no lo escribe en el replay store ni en logs o recibos;
- trata el stdin inline y el entorno como material sensible aunque el descriptor
  no sea una capacidad secreta;
- conserva sólo la instantánea inmutable necesaria durante start/supervisión; y
- aplica a diagnósticos la misma regla de saneamiento de M1.

La ausencia de un almacén durable del descriptor significa que, después de un
reinicio, sólo puede iniciarse si el llamador todavía posee token y request. No
se promete recuperación autónoma.

## 3. Alternativas rechazadas o aplazadas

### A. Objeto local emitido por `admit`

Aplazado. Es simple dentro de un proceso, pero hace el token innecesario como
handoff, pierde reinicio y oculta la retención de stdin/entorno en memoria del
supervisor.

### B. Store durable del descriptor

Rechazado para M2. Añade retención y borrado de comando, entorno y stdin,
cifrado en reposo, cuotas y reconciliación; duplica material sensible que el
llamador ya puede reenviar.

### C. Token v2 con digest del request completo

Aplazado. Es la opción correcta si se exige identidad byte-a-byte, pero cambia
el contrato criptográfico y requiere migración, compatibilidad y nuevos
vectores. M2 no necesita esa garantía para ejecutar el material semánticamente
ligado por la capacidad v1.

### D. Recuperar por `action_id` desde una base externa

Rechazado. `action_id` es correlación, no contenido autenticado ni clave de un
registro autorizado. Introduciría una fuente mutable implícita entre admisión y
spawn.

## 4. Consecuencias y no-claims

- Se evita un segundo almacén durable con comando, entorno y stdin.
- El costo es repetir parseo, cripto y representabilidad en `start`; no se
  repiten política ni reserva de nonce.
- El token v1 conserva compatibilidad; cambia la firma conceptual de la API
  local, por lo que especificación y tarjetas M2 deberán enmendarse sólo después
  de aceptar esta ADR.
- No se cierra el TOCTOU del ejecutable por ruta: continúa
  `route_mutable_unverified` (D7a).
- No se demuestra que el request reenviado sea byte-a-byte el original.
- No se promete política continua hasta el spawn ni recuperación autónoma tras
  reinicio.
- El CAS evita dos inicios autorizados con la misma identidad; no vuelve
  transaccionales el store y el kernel.

## 5. Criterios de aceptación de la futura implementación M2

Esta ADR sólo podría promoverse a construcción M2 con una tarjeta separada que
exija, como mínimo:

1. vectores y pruebas negativas para token malformado, MAC, campos cruzados,
   request distinto, expiración y tipos hostiles;
2. prueba de que ninguna ruta previa al CAS crea proceso y sólo `CONSUMED`
   cruza la frontera;
3. carrera multiproceso: un único ganador y perdedores
   `capability_rejected`, incluido reinicio;
4. crash injection alrededor de persistencia, CAS y spawn, sin replay ni handle
   inventado;
5. deadline recomputado después de dependencias lentas y supervisado por reloj
   monotónico más cota absoluta;
6. cero persistencia o logging de request, entorno e stdin fuera de los
   artefactos expresamente autorizados;
7. pruebas separadas Linux aarch64 y Darwin arm64 para la frontera real; y
8. revisión adversarial fresca del diff final, con M3/AuditSink todavía fuera de
   alcance salvo las interfaces previas exigidas por ADR-007.

## 6. Stop rule

Mientras el dueño no marque esta ADR como aceptada, no modificar schemas,
especificación normativa, token, API productiva, replay store ni frontera de
spawn. Aceptar la ADR tampoco autoriza M2: la implementación requiere una
tarjeta, DoD, alcance y autorización propios. No iniciar M3, tag ni release por
efecto de esta propuesta.
