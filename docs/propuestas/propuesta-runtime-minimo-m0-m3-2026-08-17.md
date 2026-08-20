# Propuesta de arquitectura: runtime mínimo M0–M3

**Estado:** fusionada en `docs/especificacion/ektel-runtime-m0-m3-v1.md`
(2026-08-19). Este documento queda como antecedente histórico; la fuente
normativa es la especificación.

**Fecha:** 2026-08-17.

**Alcance de este acto:** diseño y arquitectura; no autoriza implementación.

**Repositorio de producto:** ektel.

**Referencia de alineación opcional:** CAGF, consumido por contrato y sin
dependencia del núcleo.

## 1. Decisión propuesta

Construir ektel como un runtime local pequeño que gobierna únicamente su
propia frontera de ejecución. El núcleo admite una acción, inicia y supervisa
un grupo de procesos, produce un resultado tipado y registra las transiciones
que pudo observar.

La gobernanza de negocio no vive en el núcleo. Se conecta mediante un puerto
opcional que cualquier política puede implementar después. CAGF sería una
implementación posible de ese puerto, no una dependencia, un modo especial ni
una interpretación embebida en ektel.

El primer ciclo se divide en cuatro hitos, `M0` a `M3`, y se detiene
deliberadamente al cerrar `M3`. No se usa la nomenclatura `P0`–`P3`, porque
`P0` y `P1`–`P8` ya tienen significados propios en CAGF.

## 2. Autoridad y relación con documentos anteriores

Esta propuesta desarrolla, pero no resuelve automáticamente, las decisiones
`D1`–`D7` de la consolidación para consenso. Ante conflicto:

1. manda la evidencia reproducible sobre cualquier promesa narrativa;
2. la consolidación conserva su estado de candidato no vinculante;
3. esta propuesta no convierte una opción en contrato hasta que el consenso
   la acepte explícitamente;
4. los documentos históricos continúan siendo evidencia de evolución, no
   fuentes normativas acumulativas.

Antes de autorizar código deben resolverse al menos:

- alcance exacto de MVP-0;
- semántica de vigencia de la capacidad;
- identidad firmada y uso de digests;
- estados y precedencias;
- plataforma y lenguaje iniciales;
- formato de los contratos de transporte.

## 3. Objetivos

### 3.1 Objetivos funcionales

1. Rechazar antes del inicio acciones mal formadas o no autorizadas.
2. Vincular autorización e identidad a la ejecución concreta.
3. Ejecutar un comando bajo un supervisor separado.
4. Dejar de esperar cuando vence el plazo y dirigir la terminación del grupo
   observado.
5. Emitir resultados tipados sin confundir terminación técnica con éxito de
   negocio.
6. Registrar las transiciones observadas dentro de la frontera declarada.
7. Permitir políticas externas sin acoplar el núcleo a CAGF, Aria u otro
   sistema.

### 3.2 Atributos de calidad prioritarios

En orden:

1. corrección y comportamiento fail-closed en admisión;
2. honestidad sobre cobertura y fuerza de garantías;
3. trazabilidad causal;
4. contratos pequeños, versionados y compatibles;
5. determinismo en validación;
6. portabilidad donde la semántica sea realmente equivalente;
7. extensibilidad por adaptadores, no por condicionales en el núcleo.

## 4. No-objetivos y frontera

Quedan fuera de M0–M3:

- enrutamiento de conversaciones, mensajes o agentes;
- selección de objetivos, tareas o prioridades;
- memoria conversacional o semántica;
- marketplace y carga dinámica de plugins;
- interpretación de axiomas o políticas CAGF;
- presupuesto de tokens o costo de proveedor;
- delegación y subacciones;
- revocación distribuida;
- ejecución multitenant o contra código hostil;
- aislamiento de filesystem o red;
- contención preventiva de CPU/RSS no demostrada;
- auditoría de acciones que eviten la frontera de ektel;
- recuperación garantizada tras muerte del supervisor;
- reparación automática del estado externo.

El routing pertenece a un gateway o despachador. El contexto de conversación
pertenece al sistema llamador. Ektel recibe solamente un descriptor de acción
autocontenido.

## 5. Modelo de contexto y contenedores

```text
Sistema llamador
  |
  | ActionRequest v1
  v
+----------------------- ektel ------------------------+
| API / adaptador de entrada                            |
|          |                                            |
|          v                                            |
| Admisión -> PolicyPort opcional -> Supervisor         |
|                                      |                |
|                                      v                |
|                              Proceso / grupo observado|
|                                                       |
| RuntimeEvent --------------------------> AuditSink     |
+-------------------------------------------------------+
           ^                                  |
           |                                  v
   adaptador CAGF futuro              almacén del operador
   u otra gobernanza                  fuera del núcleo
```

Reglas de dependencia:

1. El dominio no importa adaptadores.
2. El supervisor depende de puertos definidos por el dominio.
3. Los adaptadores implementan puertos y traducen protocolos externos.
4. CAGF, Epistates o un CLI pueden depender del contrato público de ektel;
   ektel no depende de ellos.
5. El almacenamiento de auditoría es reemplazable y no forma parte del modelo
   de autorización.

Esta es una arquitectura hexagonal: dominio en el centro, puertos estables y
adaptadores reemplazables en el borde.

## 6. Componentes

### 6.1 Dominio de contratos

Define tipos, estados, invariantes y errores. No crea procesos, no accede a
red, no lee configuración global y no conoce CAGF.

### 6.2 Servicio de admisión

Valida, en orden fijo:

1. versión y forma del descriptor;
2. valores y tamaños permitidos;
3. identidad completa de ejecución;
4. firma, confianza, vigencia y proof-of-possession;
5. nonce y prevención de replay;
6. decisión del `PolicyPort`, si está configurado;
7. disponibilidad de la evidencia obligatoria previa al inicio.

No debe ejecutar efectos parciales antes de terminar la admisión.

### 6.3 Supervisor

Es dueño de:

- reloj monotónico;
- creación del proceso y grupo observado;
- captura acotada de salida;
- transición de estados;
- terminación dirigida;
- resultado técnico;
- emisión de eventos.

El proceso ejecutado no puede decidir sus propios límites, falsificar el
resultado del supervisor ni escribir directamente el registro autoritativo.

### 6.4 PolicyPort

Puerto opcional y fail-closed cuando el despliegue declare política
obligatoria. Evalúa una solicitud inmutable y devuelve una decisión tipada.

No puede:

- mutar silenciosamente la solicitud;
- iniciar procesos;
- emitir por sí mismo un resultado de ejecución;
- declarar éxito de negocio;
- convertir una observación en garantía de plataforma.

### 6.5 AuditSink

Persiste eventos del runtime y devuelve un acuse verificable. Su contrato
distingue entre:

- evento aceptado y durable;
- evento aceptado sin durabilidad demostrada;
- rechazo explícito;
- indisponibilidad;
- resultado desconocido tras timeout.

Un simple `append()` exitoso no equivale por sí solo a durabilidad.

## 7. Contratos públicos

Los contratos públicos se definen primero como wire schemas neutrales. Cada
SDK de lenguaje es una proyección derivada y debe demostrar compatibilidad con
vectores canónicos.

### 7.1 Operaciones del núcleo

```text
admit(ActionRequest) -> AdmissionDecision
start(AdmittedAction) -> ExecutionHandle
terminate(ActionId, TerminationReason) -> TerminationReceipt
await_result(ExecutionHandle) -> ExecutionResult
verify_receipt(Receipt) -> VerificationResult
```

No se exponen `before_action` y `after_action` como semántica principal:
parecen callbacks, no contratos de estado. Si un adaptador necesita esos
nombres, los implementa traduciendo a `PolicyPort.evaluate` y al flujo de
eventos, sin alterar el dominio.

### 7.2 ActionRequest v1

Campos mínimos propuestos:

```text
schema_version
action_id
command_absolute
args
cwd
env_allowlist_values
stdin_policy
deadline
capability_envelope
invocation_proof
nonce
repair_policy
output_limits
requested_guarantees
metadata_opaque
```

Restricciones:

- `action_id` es único dentro del ámbito declarado;
- no se hereda el entorno completo del padre;
- `command_absolute` no implica identidad suficiente del artefacto;
- `metadata_opaque` no alimenta decisiones del núcleo;
- no se aceptan campos desconocidos salvo extensión versionada explícita;
- el descriptor transportado conserva los bytes necesarios para verificar la
  firma sin reserialización ambigua.

### 7.3 ExecutionIdentity v1

La identidad vincula como mínimo:

- versión de esquema;
- `action_id`;
- comando y argumentos;
- cwd;
- entorno admitido;
- política y digest de stdin cuando corresponda;
- plazo;
- límites de salida;
- garantías solicitadas;
- nonce.

La inclusión del digest del ejecutable y de archivos auxiliares permanece
como decisión normativa explícita. Si no se incluyen, el resultado debe
declarar que la ruta pudo resolver contenido diferente entre admisión e inicio.

### 7.4 AdmissionDecision v1

```text
Admitted {
  admitted_action,
  identity_digest,
  policy_receipt?,
  guarantee_plan
}

Rejected {
  reason_code,
  safe_detail,
  retryable,
  evidence_receipt?
}
```

`admitted_action` es un valor opaco, íntegro y de un solo uso. `start` vuelve a
comprobar su integridad, vigencia y consumo para cerrar el intervalo entre
admisión y ejecución. El llamador no puede construirlo ni modificarlo mediante
los campos públicos de `ActionRequest`.

Los códigos de rechazo son cerrados y versionados. El detalle no puede filtrar
secretos, claves, entorno completo ni material de firmas.

### 7.5 ExecutionResult v1

Estados antes de iniciar:

- `admission_rejected`;
- `capability_rejected`;
- `start_failed`.

Estados después de iniciar:

- `executed`;
- `deadline_exceeded`;
- `terminated`;
- `supervision_failed`.

`budget_exceeded` sólo se habilita para una magnitud cuyo mecanismo pueda
clasificarse y probarse en la plataforma objetivo. No existe como comodín para
una observación incompleta.

Todo resultado incluye, cuando exista:

```text
action_id
identity_digest
state
started_at_wall
finished_at_wall
duration_monotonic
exit_code_or_signal
cause_code
guarantees_applied
measurements
stdout_truncation
stderr_truncation
last_event_receipt
```

`executed` significa que el proceso observado terminó sin que una compuerta de
ektel produjera otro estado. No significa éxito de negocio ni ausencia de
efectos externos.

## 8. Clases de garantía

Cada magnitud devuelve una clase independiente:

| Clase | Significado |
|---|---|
| `enforced` | La plataforma impide o fuerza una transición bajo supuestos declarados. |
| `reactive` | Ektel puede actuar después de observar una condición. |
| `observed` | Existe medición, pero no alimenta decisiones de control. |
| `unsupported` | No existe mecanismo aceptado en esta plataforma o despliegue. |

Cada entrada de `GuaranteePlan` incluye:

```text
magnitude
class
platform
mechanism
assumptions
known_escapes
failure_mode
evidence_ref
```

Reglas:

1. No hay degradación silenciosa de `enforced` a `observed`.
2. Solicitar una garantía obligatoria no disponible rechaza la admisión.
3. Una medición incompleta nunca se presenta como límite preventivo.
4. El plazo describe la transición del registro por un supervisor vivo; no
   promete scheduler de tiempo real ni muerte universal de descendientes.
5. M0–M3 no usan CPU/RSS para producir `budget_exceeded`.

## 9. Política externa y futura integración CAGF

### 9.1 Contrato del puerto

```text
PolicyPort.evaluate(PolicyEvaluationRequest) -> PolicyDecision

PolicyEvaluationRequest {
  contract_version,
  action_identity,
  requested_guarantees,
  capability_summary,
  deployment_claims,
  opaque_policy_context_ref?
}

PolicyDecision =
  Allow { decision_id, valid_until?, claims, receipt }
  | Deny { decision_id, reason_code, receipt }
  | Indeterminate { decision_id, reason_code, retryable, receipt? }
```

`Indeterminate` se trata como rechazo cuando la política sea obligatoria. El
runtime no reinterpreta axiomas ni completa información faltante.

### 9.2 Adaptador CAGF posterior

Un adaptador CAGF puede:

- traducir hechos de ejecución al contrato que CAGF haya ratificado;
- evaluar únicamente los predicados para los que tenga evidencia;
- devolver claims tipados y acotados;
- producir una atestación verificable.

No puede convertir por nombre:

- una capacidad local en conformidad A9 completa;
- un log local en auditoría constitucional completa;
- un proceso terminado en satisfacción de A0;
- una decisión individual en verificación A2/A4;
- la existencia de hooks en gobernanza end-to-end A10.

La conformidad CAGF pertenece al adaptador y a su contrato, no al núcleo de
ektel.

## 10. Trazabilidad y eventos

### 10.1 Cobertura honesta

M3 exige trazabilidad de toda transición que ektel observe dentro de su
frontera. No afirma observar acciones que:

- no atraviesen ektel;
- utilicen canales externos directos;
- escapen del grupo observado;
- ocurran después de perder al supervisor;
- dependan de estado externo no mediado.

### 10.2 RuntimeEvent v1

```text
event_version
event_id
action_id
sequence
event_type
occurred_at_wall
observed_at_monotonic
causal_parent_ids
identity_digest
payload_digest
safe_payload
producer_identity
previous_event_digest?
```

Tipos mínimos:

- `admission_requested`;
- `admission_rejected`;
- `admission_granted`;
- `start_attempted`;
- `started`;
- `start_failed`;
- `termination_requested`;
- `termination_signal_sent`;
- `process_observed_exited`;
- `deadline_observed`;
- `supervision_degraded`;
- `result_emitted`;
- `audit_gap_detected`.

### 10.3 Invariantes de eventos

1. `sequence` es monotónica por acción, no necesariamente global.
2. Cada evento posterior a admisión referencia causalmente un evento previo.
3. Un evento durable previo al inicio es requisito cuando auditoría sea
   obligatoria.
4. Los payloads sensibles se registran por digest o forma redactada.
5. Una cadena hash detecta modificación; no prueba por sí sola autoría,
   completitud, orden global ni almacenamiento externo.
6. La pérdida del sink después de iniciar genera una brecha explícita; no se
   rellena retrospectivamente con eventos inventados. La brecha se incluye en
   el resultado local o en el siguiente evento durable si alguno llega a
   existir; si también se pierde el supervisor, permanece como ausencia de
   evidencia, no como evento presumido.

## 11. Semántica de fallos

| Fallo | Comportamiento mínimo |
|---|---|
| Descriptor inválido | Rechazo sin iniciar proceso. |
| Capacidad inválida o expirada | `capability_rejected`. |
| PolicyPort requerido e indisponible | Rechazo fail-closed. |
| AuditSink requerido falla antes de iniciar | Rechazo fail-closed. |
| `exec` falla | `start_failed`, con recibo si el sink sigue disponible. |
| Deadline observado | Precedencia sobre presupuesto; transición a `deadline_exceeded`. |
| Orden externa aceptada | `terminated` si precede al deadline observado. |
| Se pierde medición o control | `supervision_failed` si el supervisor puede emitirlo. |
| Muere el supervisor | Ausencia de resultado salvo observador externo; no se inventa estado. |
| Respuesta desconocida del AuditSink | No reintentar sin clave idempotente; reconciliar por `event_id`. |

Las operaciones externas usan claves idempotentes. Un timeout nunca autoriza a
suponer que el efecto no ocurrió.

## 12. Seguridad y modelo de amenaza M0–M3

### 12.1 Dentro del modelo

- descriptor mal formado;
- capacidad ausente, inválida, expirada o reutilizada;
- replay dentro del ámbito de nonce;
- comando que no termina voluntariamente;
- salida ilimitada;
- fallos parciales del sink de evidencia;
- errores de traducción en adaptadores;
- confusión entre observación y garantía.

### 12.2 Fuera del modelo

- atacante con control del host;
- kernel comprometido;
- escape de sandbox;
- double-fork/`setsid` fuera del grupo observado;
- D-state;
- exfiltración por red o filesystem no aislados;
- secretos ya disponibles al proceso;
- efectos externos irreversibles;
- muerte simultánea de supervisor y almacén sin watchdog.

La documentación pública debe incluir esta frontera sin expresiones como
“ejecución segura”, “auditoría completa” o “límites duros” sin calificador.

## 13. Hitos y criterios de salida

### M0 — Contratos congelables

Entregables:

- wire schemas v1;
- vocabularios cerrados de estados y errores;
- invariantes;
- vectores válidos e inválidos;
- política de compatibilidad;
- ADR de serialización, lenguaje y plataforma inicial.

Criterio de salida:

- D1–D7 resueltas;
- schemas validables sin runtime;
- vectores consumibles por al menos dos implementaciones independientes o dos
  parsers de referencia;
- ninguna decisión abierta puede cambiar la identidad firmada.

### M1 — Admisión

Entregables:

- parser estricto;
- identidad determinista;
- verificación de capacidad raíz;
- PoP;
- nonce/replay store con semántica de reinicio;
- PolicyPort nulo y adaptador de prueba.

Criterio de salida:

- ningún caso inválido inicia proceso;
- vectores criptográficos negativos pasan;
- fallos de dependencia requerida son fail-closed;
- fuzzing del parser no produce aceptación ambigua.

### M2 — Supervisión

Entregables:

- inicio del grupo observado;
- reloj monotónico;
- plazo y terminación;
- salida acotada;
- estados terminales;
- tabla de garantías por plataforma.

Criterio de salida:

- no hay hangs en la suite acotada;
- precedencia deadline/presupuesto es determinista;
- procesos observados son recogidos;
- escapes conocidos producen limitaciones declaradas, no tests falsamente
  verdes;
- Linux y macOS se prueban por separado.

### M3 — Evidencia

Entregables:

- RuntimeEvent v1;
- AuditSink en memoria para pruebas;
- sink durable de referencia;
- recibos y verificación;
- pruebas de pérdida, retry y reconciliación;
- adaptador de política falso para pruebas contractuales.

Criterio de salida:

- toda transición observada intenta emitir un evento y todo fallo reconocido
  queda como brecha explícita en el resultado o en el siguiente evento durable;
- el inicio falla cerrado si no puede persistirse el evento previo requerido;
- reintentos idempotentes no duplican secuencia lógica;
- una cadena alterada es detectada;
- el resultado referencia su último recibo conocido;
- la cobertura declarada coincide con lo probado.

**Stop rule:** al cerrar M3 no se inicia M4 implícito. Memoria, routing,
delegación, plugins, presupuestos de proveedor, CAGF completo y aislamiento
fuerte requieren propuesta y autorización nuevas.

## 14. Estrategia de pruebas

### 14.1 Pirámide

1. Pruebas de contrato: schemas, serialización y compatibilidad.
2. Pruebas de dominio: transiciones e invariantes sin procesos reales.
3. Pruebas de adaptador: PolicyPort y AuditSink mediante contract tests.
4. Integración: procesos acotados y recuperables.
5. Caracterización por plataforma: primitivas del OS sin promover automáticamente
   resultados a garantías de producto.
6. Pruebas adversariales: replay, mutación de identidad, corrupción de eventos,
   timeouts y carreras.

### 14.2 Matriz mínima

| Área | Caso positivo | Caso negativo |
|---|---|---|
| Descriptor | solicitud canónica | campos desconocidos, tipos y tamaños inválidos |
| Capacidad | firma y vigencia válidas | firma, PoP, nonce, `nbf` y `exp` inválidos |
| Política | allow | deny, indeterminate y timeout |
| Inicio | comando válido | ruta inexistente y permiso denegado |
| Deadline | salida antes del plazo | proceso no cooperativo |
| Eventos | secuencia válida | duplicado, hueco, padre desconocido y hash alterado |
| Sink | ack durable | rechazo, timeout y resultado desconocido |
| Compatibilidad | lector v1 | versión futura no soportada |

Las pruebas peligrosas —fork bomb, D-state y presión extrema— no se ejecutan
en CI general. Requieren entorno desechable y autorización específica.

## 15. Versionado y compatibilidad

1. Cada wire type lleva `schema_version`.
2. El núcleo rechaza versiones mayores desconocidas.
3. Añadir campos sólo es compatible si el contrato declara su opcionalidad y
   semántica de firma.
4. Códigos de estado y error no se reutilizan.
5. La canonicalización tiene vectores dorados independientes del lenguaje.
6. Los SDK no son fuente de verdad; se generan o verifican contra schemas.
7. Un cambio incompatible crea versión mayor y plan de migración.

La API pública se considera estable únicamente después de M0 y de una prueba
de implementación independiente. Antes se etiqueta `experimental`.

## 16. Observabilidad operativa

Métricas mínimas, sin contenido sensible:

- admisiones aceptadas y rechazadas por código;
- latencia de admisión;
- acciones iniciadas y terminadas por estado;
- desviación observada del deadline;
- eventos rechazados o desconocidos por sink;
- brechas de auditoría;
- bytes de salida truncados;
- garantías solicitadas frente a aplicadas.

Logs y métricas no sustituyen `RuntimeEvent`. Las métricas agregadas no son
evidencia causal individual.

## 17. Estructura de repositorio propuesta tras autorización

La estructura concreta depende del lenguaje, pero deben preservarse estas
fronteras:

```text
ektel/
  contracts/          wire schemas y vectores canónicos
  src/
    domain/           tipos, estados e invariantes puros
    application/      admisión y coordinación de casos de uso
    ports/            PolicyPort, AuditSink, Clock, ProcessHost
    adapters/
      cli/
      process_host/
      audit/
  tests/
    contract/
    unit/
    integration/
    characterization/
    adversarial/
  docs/
    adr/
    architecture/
    proposals/
```

No debe crearse esta estructura hasta elegir lenguaje y aceptar el diseño. La
carpeta actual `tests/escape/` puede migrarse después a
`tests/characterization/` mediante un cambio separado que preserve historia.

## 18. ADR requeridos

Antes de M1:

1. ADR-001: alcance y modelo de amenaza M0–M3.
2. ADR-002: wire format y canonicalización.
3. ADR-003: identidad firmada y digests de artefactos.
4. ADR-004: semántica de vigencia, reloj y nonce.
5. ADR-005: estados, precedencia y ausencia de resultado.
6. ADR-006: plataforma y lenguaje iniciales.
7. ADR-007: durabilidad, recibos y fail-closed del AuditSink.
8. ADR-008: frontera del PolicyPort y adaptador CAGF.

Cada ADR registra decisión, alternativas, consecuencias, evidencia y criterio
de revisión. Un ADR no convierte una hipótesis del OS en hecho.

## 19. Riesgos principales

| Riesgo | Mitigación propuesta |
|---|---|
| Contratos “estables” prematuros | M0 separado y vectores multilenguaje. |
| Política acoplada al runtime | Puerto hexagonal y adaptador externo. |
| Auditoría presentada como completa | Frontera y `audit_gap_detected` explícitos. |
| Límite observado presentado como duro | `GuaranteeClass` obligatorio. |
| Callback posterior que nunca corre | Estados del supervisor y ausencia honesta de resultado. |
| Retry duplica efectos | Idempotency keys y reconciliación por identificador. |
| Descriptor válido cambia antes de `exec` | Decidir digest/handle estable en D7 y ADR-003. |
| Scope creep hacia routing/memoria | No-objetivos y stop rule M3. |
| CAGF se vuelve dependencia de producto | Contract tests con PolicyPort nulo. |

## 20. Decisiones solicitadas al consenso

La propuesta recomienda resolver así, pero no adopta por redacción:

| Decisión | Recomendación |
|---|---|
| D1 alcance | Admitir G0 + resolución local; no prometer contención de recursos. |
| D2 capacidad | Raíz no delegable en M1. |
| D3 vigencia | Truncar el plazo efectivo a `exp`, salvo justificación operativa contraria. |
| D4 descriptor | JSON versionado, estricto y sin YAML. |
| D5 resultados | Estados de §7.5; deadline precede a presupuesto. |
| D6 exclusiones | Mantener todas las exclusiones de §4 hasta nuevo acto. |
| D7 identidad | Vincular digest del ejecutable; auxiliares mediante manifiesto explícito. |

También debe decidirse:

- lenguaje y versión mínima;
- plataforma primaria de M1–M3;
- alcance y persistencia del replay store;
- garantía mínima exigida al AuditSink;
- si PolicyPort es omitible o requerido por perfil de despliegue;
- formato de recibo y firma del operador.

## 21. Criterio de adopción

Esta propuesta puede pasar a arquitectura adoptada cuando:

1. D1–D7 tengan resolución y dueño;
2. una ronda adversarial intente romper fronteras, contratos e invariantes;
3. las objeciones se incorporen o refuten explícitamente;
4. exista una tabla de claims y no-claims;
5. los ADR requeridos tengan responsable;
6. se emita autorización separada para M0 y, después, para cada hito.

Hasta entonces, este documento sirve para consenso y planificación. No es una
especificación implementada, una afirmación de conformidad CAGF ni permiso para
crear el runtime.

## 22. Fuentes de diseño y genealogía

Fuentes internas de ektel:

- [Consolidación corregida para consenso](../consolidacion-para-consenso-2026-08-14.md).
- [Documento de preproyecto](../pre-proyecto.md), tratado como antecedente
  histórico cuando contradiga la consolidación.
- [Revisión adversarial de la consolidación](../revisiones/revision-adversarial-consolidacion-2026-08-14.md).
- [Ronda externa 2](../revisiones/revision-externa-2026-08-14.md),
  [ronda 3](../revisiones/revision-externa-r3-2026-08-14.md) y
  [ronda 4](../revisiones/revision-externa-ronda4-2026-08-14.md).
- [Suite segura de caracterización](../../tests/escape/README.md).

Fuentes CAGF consultadas en su repositorio canónico, sin copiarlas ni crear
dependencia de runtime:

- `AGENTS.md` y su frontera para tooling externo;
- `README.md`, superficie tipada vigente;
- `MANIFIESTO-DEL-ORIGEN.md`, significado de P0;
- `docs/N22-P1P8-DISPOSITION-SCOPING-v0.1.md`, disposición histórica P1–P8;
- `docs/CLOSEOUT-N31-v0.1.md`, regla de frontera gobernanza/tooling;
- `docs/N14-CLOSEOUT-v0.1.md`, límites de autorización del runtime A10.

Estas referencias explican alineación y límites. No transfieren autoridad
constitucional a esta propuesta ni convierten ektel en una implementación de
CAGF.
