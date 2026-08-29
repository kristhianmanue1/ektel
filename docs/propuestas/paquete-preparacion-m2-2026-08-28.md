# Paquete de preparación para la decisión sobre M2

**Fecha:** 2026-08-28.

**Estado:** **propuesta para decisión del dueño — NO es autorización de
M2**. Este documento no permite crear procesos, implementar `start`, modificar
schemas, activar CI remoto, crear tags ni publicar releases.

**Base vigente:** M0 y M1, incluida M1-R1, están cerrados. ADR-011 está
aceptada y gobierna el handoff `admit` → `start`; M2 y M3 siguen requiriendo
actos separados. La CI autorizada continúa siendo exclusivamente local.

## 1. Resultado del análisis previo

La especificación, ADR-003/004/005/006/007/008/009/010/011, los once schemas v1
y el runtime M1 son una base suficiente para **preparar** M2, pero no todavía
para autorizar su implementación. Permanecen cinco decisiones locales que no
deben improvisarse dentro del código:

1. el wire `ExecutionResult v1` informa truncamiento y bytes descartados, pero
   no contiene stdout/stderr ni existe otro portador normativo de esos bytes;
2. `TerminationReason` y la semántica del `receipt` de
   `TerminationAccepted` no están definidos;
3. ADR-009 deja para M2 la topología exacta del supervisor, el alcance del
   subreaper y los parámetros concretos de gracia y salida post-kill;
4. M2 precede a M3, pero `audit_mode=required` exige un evento durable previo
   al inicio y `RuntimeEvent`/`AuditSink` son entregables M3; y
5. no hay límite de concurrencia de acciones: los límites de salida son por
   acción y alcanzan 64 MiB por stream, por lo que concurrencia sin cota haría
   falsa la afirmación de memoria acotada del supervisor.

**Recomendación de gobierno:** resolver D-M2-1 a D-M2-5 mediante ADR-012 y su
acta antes de autorizar código M2. La futura autorización M2 debe ser un acto
posterior y separado. No reutilizar este paquete como autorización implícita.

**Prerrequisito nuevo verificado:** el emisor M1 de `GuaranteePlan` usa hoy
`failure_mode=""`, mientras el schema v1 exige una cadena no vacía; la suite M1
comprueba magnitudes/clases, pero no valida ese resultado emitido contra el
schema. Es deuda preexistente, no causada por esta propuesta, y no invalida por
sí sola los CAS, fuzzers o replay durable ya cerrados. Sí bloquea promover C3 o
usar ese plan como base de M2. Requiere una corrección gobernada **M1-R2**,
acotada al valor honesto no vacío y a una prueba de conformidad wire, antes de
autorizar implementación M2. La hipótesis adicional de que `policy_mode` no se
validaba fue refutada al comprobar `AdmissionService.__init__`.

## 2. Alcance propuesto para M2

### 2.1 Dentro de M2, sólo después de autorización expresa

- tipo local `StartRequest` y revalidación pura completa según ADR-011;
- plan de ejecución inmutable derivado de una única instantánea validada;
- configuración local validada de capacidad, tiempos y `audit_mode` según
  D-M2-2/3/5;
- actualización acotada de la ruta de admisión para declarar configuración y
  fórmula en `GuaranteePlan`, promover sólo garantías M2 probadas y conservar
  `audit_trail=unsupported`; esto toca M1 sin reabrir sus otros claims;
- consumo y reconciliación de `start_token_consumption` antes del spawn;
- supervisor POSIX separado por acción, grupo de procesos propio y handle
  local opaco;
- `start` y `terminate` con outcomes wire v1 ya congelados, más la decisión
  explícita sobre el portador local de `await_result` de D-M2-1;
- reloj monotónico, cota absoluta `exp`, precedencia por causa y terminación
  graduada;
- stdin acotado, stdout/stderr drenados continuamente, captura acotada y
  conteo de descarte;
- recolección del proceso principal y de descendientes observados;
- tabla honesta de garantías por Linux aarch64 y Darwin arm64; y
- tests unitarios, de integración, adversariales y de caracterización
  necesarios para los gates de este paquete.

### 2.2 Fuera de M2

- `RuntimeEvent v1`, `AuditSink`, recibos de evento, cadena, persistencia,
  retry y reconciliación de evidencia: **M3**;
- cualquier activación efectiva de `audit_mode=required` antes de M3;
- cambios a schemas o vectores wire v1, salvo nueva autorización expresa tras
  una incompatibilidad demostrada;
- identidad byte-a-byte del `ActionRequest` o del binario, cierre del TOCTOU de
  `command_absolute`, sandbox, aislamiento filesystem/red o multitenant;
- límites preventivos de CPU/RSS y `budget_exceeded`;
- protección universal frente a `setsid`, double-fork, D-state, muerte del
  supervisor o administrador del host;
- x86_64, hardware de producción no caracterizado y tests peligrosos como fork
  bomb o presión extrema;
- CAGF dentro del núcleo, routing, memoria, plugins o delegación; y
- CI remoto, cambios de workflow, tag, release o preparación de alfa.

## 3. Decisiones D-M2 pendientes del dueño

### D-M2-1 — Portador local de salida capturada

**Defecto contractual:** `ExecutionResult v1` es cerrado y no tiene campos de
stdout/stderr. Implementar una captura que el llamador no puede obtener sería
un cumplimiento aparente de `output_limits`, no una API útil.

**Alternativa recomendada (a):** mantener intacto el wire
`ExecutionResult v1` y enmendar sólo la API local experimental:

```text
AwaitedExecution {
  result: ExecutionResult,
  stdout: bytes,
  stderr: bytes
}

await_result(ExecutionHandle) -> AwaitedExecution
```

La captura conserva exactamente los primeros `max_stdout_bytes` y
`max_stderr_bytes`; después sigue drenando y descarta. `stdout_truncation` y
`stderr_truncation` indican descarte en su stream; `discarded_bytes` es la suma
exacta de ambos contadores. Los buffers son locales, inmutables al entregarse,
no se escriben en replay store, logs, recibos ni disco. Tras el handoff terminal
desde el supervisor de acción, el payload queda ligado al `ExecutionHandle` del
llamador; `await_result` transfiere su propiedad a `AwaitedExecution` y el handle conserva
sólo metadatos acotados de ciclo de vida. En ambas fases es memoria atribuida al
llamador y ektel no afirma gobernarla.

El supervisor de acción transfiere la salida al coordinador runtime en frames
ordenados de máximo 64 KiB por stream, con crédito y confirmación para permitir
a un solo frame no confirmado por stream. Libera cada frame confirmado y nunca
conserva una segunda copia completa. Si el coordinador deja de consumir, el
supervisor sigue drenando al hijo hasta los límites ya retenidos, descarta el
exceso y, al cerrarse el canal, aplica la terminación best-effort de D-M2-2. La
cota estable combinada de payload retenido entre supervisor, canal y
coordinador antes de materializar los `bytes` de entrega es:

```text
max_stdout_bytes + max_stderr_bytes + 2 * 65536
```

por acción. La materialización inmutable puede crear una segunda copia
transitoria; por ello el pico de payload durante el handoff se publica como:

```text
2 * (max_stdout_bytes + max_stderr_bytes) + 2 * 65536
```

por acción, más overhead de objetos, pipes y kernel que se caracteriza pero no
se publica como cota exacta de RSS. Al completar el handoff, el resultado queda
propiedad del `ExecutionHandle` que conserva el llamador y el slot se libera;
`await_result` mueve esa propiedad a `AwaitedExecution` sin prometer cero copias
adicionales fuera del runtime. Esta regla de propiedad, framing, pico y
backpressure es parte de D-M2-1(a), no un detalle que el código pueda elegir.

Alternativas no recomendadas:

- **(b) `ExecutionResult v2` con salida:** contrato wire nuevo, migración,
  schemas, vectores y doble gate M0; coste desproporcionado antes de demostrar
  necesidad de transporte.
- **(c) descartar toda salida y entregar sólo contadores:** preserva memoria,
  pero contradice la expectativa normativa de captura acotada y hace irrelevante
  el presupuesto de bytes retenidos.

**Decisión solicitada:** aceptar (a), elegir (b)/(c) o pedir otra forma. La
opción (a) requiere ADR-012 y enmienda de la firma local, no cambio wire.

### D-M2-2 — Topología del supervisor y capacidad

**Alternativa recomendada (a):** un proceso supervisor dedicado por acción.
El **coordinador runtime** (proceso padre y dueño de handles) conserva el
`ExecutionHandle` y un canal IPC local; el **supervisor de acción** queda fuera
del grupo del proceso ejecutado y crea para éste un grupo propio mediante una
primitiva POSIX equivalente a
`subprocess.Popen(..., process_group=0)`, sin `preexec_fn`.

En Linux, sólo ese supervisor de acción puede activar
`PR_SET_CHILD_SUBREAPER`; en Darwin la contabilidad multi-nivel permanece
`unsupported`. El EOF del canal del coordinador solicita terminación
best-effort del grupo, pero no se transforma en promesa de recuperación o
muerte universal.

Para acotar memoria y procesos se añade configuración local exacta
`max_concurrent_actions: int`, con `bool` rechazado, rango `1..64` y default
`1`. El runtime reserva un slot local antes de cualquier efecto irreversible;
si no hay capacidad devuelve `StartFailed(reason_code=start_failed)` sin
consumir el token. El slot se libera ante un fallo pre-spawn o cuando el
resultado terminal y su salida pasan a ser propiedad del handle; hasta ese
handoff limita también resultados terminados todavía alojados por el runtime.
Retener un handle ya terminal puede retener su resultado, pero esa memoria es
propiedad del llamador; abandonar el último referente al handle libera resultado
y metadatos sin mantener un slot o registro global.
El vocabulario wire no distingue este backpressure de otros `start_failed` y
no contiene `retryable`: M2 no afirma esa distinción como machine-readable.
El llamador puede reintentar explícitamente el mismo token no consumido.

`max_concurrent_actions` es una cota de capacidad, no un presupuesto pequeño de
memoria. Con límites wire máximos, el default `1` permite 128 MiB + 128 KiB
estables y un pico transitorio de hasta 256 MiB + 128 KiB de payload; el máximo
`64` permite 8 GiB + 8 MiB estables y un pico transitorio de hasta 16 GiB +
8 MiB. A esas cifras se suma overhead de objetos, pipes y kernel. El perfil de
despliegue debe publicar ambos límites y la caracterización de RSS; no se
permite presentar el rango como garantía de RSS baja.

Alternativa (b), no recomendada: threads dentro de un supervisor global. Hace
global el efecto de subreaper, introduce carreras de `waitpid` entre acciones y
amplía el blast radius de un fallo.

**Decisión solicitada:** aceptar (a) y sus cotas, o definir otra topología
antes de autorizar M2.

### D-M2-3 — Configuración temporal y mediciones

**Alternativa recomendada:** configuración local, no wire, con tipos exactos:

| Parámetro | Default | Rango | Semántica |
|---|---:|---:|---|
| `termination_grace_ms` | 2000 | 0..60000 | TERM→KILL; 0 significa KILL directo. |
| `post_kill_drain_ms` | 1000 | 1..10000 | cota propia para esperar EOF tras KILL. |

`bool`, floats, valores fuera de rango y tipos hostiles impiden inicializar el
servicio. Para cada inicio:

```text
applied_grace_ms = min(termination_grace_ms, deadline_eff_ms)
useful_runtime_ms = deadline_eff_ms - applied_grace_ms
soft_termination_at = start_mono + useful_runtime_ms
hard_deadline_at = start_mono + deadline_eff_ms
```

Si `deadline_eff_ms == 0`, `start` devuelve
`StartFailed(reason_code=capability_rejected)` antes del CAS y sin spawn: el
único origen posible es que la vigencia restante redondeada sea cero, no un
fallo de dependencia. No gasta un token para crear un proceso sin vida útil;
`safe_detail` permanece saneado.

El `GuaranteePlan` de admisión declara en `mechanism`/`assumptions` la gracia
configurada, la fórmula anterior, el alcance por proceso del supervisor de
acción y si se solicita subreaper; todavía no puede declarar un valor aplicado porque
`deadline_eff_ms` sólo existe en `start`. `guarantees_applied` del resultado
declara la gracia aplicada y el tiempo útil efectivos, además del uso real de
subreaper. ADR-012 debe enmendar expresamente ADR-009 y la especificación:
plan configurado en admisión y valores aplicados en el resultado. Si el dueño
exige ambos valores aplicados dentro del `GuaranteePlan` ya emitido, la opción
(a) es incompatible con el schema v1 y debe detenerse para versionar contrato.
Para evitar texto interpretado libremente, ADR-012 debe congelar en
`assumptions` entradas ASCII `clave=valor` para
`termination_grace_ms_configured`, `useful_runtime_formula`,
`supervisor_scope` y `subreaper_requested`; el resultado usa el mismo formato
para `termination_grace_ms_applied`, `useful_runtime_ms` y
`subreaper_applied`. Valores, orden y ausencia se cubren con vectores locales.

El resultado registra, bajo claves congeladas localmente por ADR-012 —el schema
wire mantiene el mapa abierto—,
`deadline_effective_ms`, `termination_grace_ms`, `useful_runtime_ms`,
`soft_termination_after_start_ms`, `hard_deadline_after_start_ms`,
`post_kill_drain_elapsed_ms`, `post_kill_forced_pipe_close` (entero `0|1`),
`stdout_discarded_bytes` y `stderr_discarded_bytes`; `discarded_bytes` conserva
la suma. Los offsets son relativos al inicio: no se exportan instantes
monotónicos sin significado fuera del proceso.

El plazo post-KILL no amplía el deadline de ejecución. `finished_at_wall` y
`duration_monotonic_ms` miden hasta la recolección del proceso principal,
instante que fija ADR-009; `post_kill_drain_ms` sólo acota la latencia adicional
de recolección de pipes antes de entregar el resultado. Al expirar, se cierran
los pipes y se declara el cierre forzado. D-state y una imposibilidad real de
recoger el principal permanecen fuera del modelo, no se convierten en un
resultado fabricado.

La última muestra de pared validada previa al CAS fija el tiempo restante hasta
`exp`, que se proyecta conservadoramente sobre el reloj monotónico. Después del
spawn ninguna nueva muestra de pared puede extender ni reclasificar ese plazo;
M2 no promete detectar saltos de pared entre muestras. La muestra final sólo
alimenta `finished_at_wall`: si no es un número finito válido o regresa respecto
de la inicial, el supervisor de acción produce, si puede,
`supervision_failed/supervision_failure` sin fabricar tiempos. La causa
`deadline_validity_exhausted` se fija cuando `remaining_validity_ms`, derivado de
`exp` en el cálculo final pre-CAS, fue menor o igual que `deadline_ms`; por tanto,
en empate entre ambas duraciones gana explícitamente vigencia. Esta regla nueva
debe congelarse en ADR-012; no se atribuye a la precedencia de ADR-005, que sólo
cubre otras causas.

**Decisión solicitada:** aceptar defaults, rangos, claves y tratamiento del
reloj, o corregirlos antes de ADR-012.

### D-M2-4 — `TerminationReason`, recibo e idempotencia

**Alternativa recomendada:** v1 local admite únicamente
`TerminationReason.OPERATOR_REQUESTED`; no transporta detalle arbitrario. El
`receipt` de `TerminationAccepted` es un identificador opaco local de la
solicitud, no un recibo AuditSink, no lleva claim de durabilidad ni MAC y nunca
se registra completo.

El primer `terminate` autenticado se linealiza en el supervisor de acción y el
coordinador runtime guarda el receipt en el propio objeto local
`ExecutionHandle`. Repetir la misma operación con ese objeto, dentro de la misma
instancia del coordinador, devuelve el mismo receipt. Si el coordinador ya
observó y almacenó el resultado terminal, el handle válido permanece como
metadato local acotado, la solicitud se acepta como no-op idempotente y no
reclasifica el resultado. No existe registro global de receipts: al dejar de
existir el handle termina también esa retención.

Esto conserva el derecho de terminación después de la ejecución sin prometer
persistencia. ADR-012 denomina **coordinador runtime** al proceso supervisor
dueño del handle de ADR-003: reiniciarlo invalida todos sus handles. Reiniciar o
perder sólo un supervisor de acción produce el estado honesto de supervisión,
pero no redefine la identidad de la instancia. Un handle forjado, de otra
instancia o discordante produce
`TerminationRejected(capability_rejected)`; ningún otro reason code se inventa.

En carrera con deadline, el supervisor de acción clasifica por el primer hecho
que observa; si ambos son observables en el mismo paso, gana deadline conforme
a ADR-005.

**Decisión solicitada:** aceptar esta semántica o exigir otro contrato antes de
M2. Si se requiere receipt durable o razón wire extensible, pertenece a una
versión posterior y no puede ocultarse en un string libre.

### D-M2-5 — Frontera M2/M3 para auditoría

**Alternativa recomendada (a):** M2 opera únicamente con
`audit_mode=optional`; `audit_trail` permanece `unsupported`. Configurar
`audit_mode=required` sin el M3 autorizado impide inicializar el servicio, antes
de recibir solicitudes y sin consumir tokens. M2 no crea `RuntimeEvent`,
`AuditSink`, recibos ni un puerto sustituto con semántica inventada.

M2 introduce y valida esa configuración local porque hoy no existe en `src/`;
acepta sólo `optional` y reconoce `required` para rechazar la inicialización.
Esto no satisface todavía la obligación normativa de emitir eventos, incluido
el `capability_rejected` de un `terminate` inválido: `audit_mode=optional`
evita el bloqueo por durabilidad, pero no elimina el evento. Esa obligación y
su prueba quedan explícitamente pendientes de M3; M2 no puede reclamar C5, C7
ni conformidad completa de trazabilidad.

Esto no relaja ADR-007/011: cuando M3 active el perfil `required`, el orden será
evento `flush_protocol_completed` → nueva muestra de reloj → CAS → spawn. M2
conserva esa inserción como frontera arquitectónica sin fingir que hoy existe.

Alternativa (b), no recomendada: coautorizar una rebanada de M3 para probar la
matriz completa. Mezcla hitos, exige schema `RuntimeEvent v1` y vuelve ambiguo
qué claims se promueven.

**Decisión solicitada:** aceptar (a) o emitir una autorización explícita que
redefina el alcance de hitos; este paquete no hace lo segundo.

## 4. Invariantes no negociables de una futura implementación

1. Sólo un `StartRequest` revalidado completamente construye un plan inmutable.
2. La revalidación de `start` no llama `reserve_nonce`, no reevalúa
   `PolicyPort` y no emite otro token.
3. Ningún proceso se crea antes de un `ConsumeOutcome.CONSUMED`; valores
   desconocidos, excepciones y objetos truthy no adquieren autoridad.
4. La reconciliación CAS conserva exactamente ADR-011: `spent` y `unknown`
   son indeterminados; `unspent` permite otro CAS, nunca spawn directo.
5. Tras el CAS no existe dependencia externa entre consumo y spawn.
6. `now_wall < exp` es estricto en `start`; el skew de admisión no concede
   tiempo de ejecución.
7. El supervisor de acción drena ambos pipes aun después de truncar, transfiere
   buffers sin una segunda copia completa y acota su espera de EOF tras KILL.
8. El proceso ejecutado recibe sólo el entorno revalidado, cwd, argv e stdin
   autorizados; no hereda secretos ni descriptores ajenos.
9. `executed` significa salida natural, no éxito; la clasificación es por causa
   y deadline gana en empate.
10. El contenido en `command_absolute` continúa mutable entre validación y
    exec; N1 y N17 permanecen visibles.
11. Muerte del coordinador runtime o del supervisor de acción significa
    ausencia honesta según la fase; no se fabrica handle, resultado ni
    recuperación.
12. El núcleo M0–M3 sigue stdlib-only, con la excepción parcial y declarada de
    `ctypes` para `prctl` permitida por ADR-006; la API permanece experimental.

## 5. DoD y gates ejecutables

| Gate | Prueba mínima que debe falsificar la promesa |
|---|---|
| G-M2-01 · revalidación/configuración | Token/request malformados, MAC rota, campos cruzados, request ejecutable distinto, tipos hostiles, request >64 KiB y expiración: cero CAS y cero procesos. Matriz separada rechaza `bool`, floats, rangos/tipos inválidos de toda configuración y demuestra que `audit_mode=required` impide inicializar antes de solicitudes. |
| G-M2-02 · pureza | Spy demuestra cero `reserve_nonce`, cero `PolicyPort.evaluate` y cero emisión de token durante `start`. |
| G-M2-03 · linealización | Instrumentación prueba reloj final → CAS → spawn; sólo `CONSUMED` cruza. No hay dependencia inyectable entre CAS y spawn. |
| G-M2-04 · reconciliación | `ALREADY_SPENT`, `UNAVAILABLE`, excepción y tipo desconocido, combinados con status `spent/unspent/unknown`, producen exactamente los outcomes de ADR-011. |
| G-M2-05 · concurrencia/reinicio | Varios procesos compiten con el mismo token contra el store real: un solo CAS ganador; reinicio conserva spent; nunca doble spawn. |
| G-M2-06 · crash | Inyección antes/después de persistir CAS y alrededor de spawn: token gastado nunca se reabre y no se inventa handle. |
| G-M2-07 · salida | Flood independiente de stdout/stderr, límites 0/máximo y multibyte, además de coordinador lento/caído: prefijo exacto, flags y contadores correctos; frames ≤64 KiB, máximo uno no confirmado por stream, cota estable y pico de materialización bajo ambas fórmulas D-M2-1. Expiración del drenaje fija `post_kill_forced_pipe_close=1`. RSS queda caracterizado, no declarado exacto. |
| G-M2-08 · no-hang | Procesos que no leen stdin, ignoran TERM, mantienen pipes en descendientes, inundan salida o escapan con `setsid`: toda prueba acotada termina; escapes quedan declarados. |
| G-M2-09 · deadline | Relojes falsos ejercen duración, `exp`, gracia mayor que vida útil, plazo efectivo cero, muestra final inválida/regresiva, empate duración/vigencia y empate con terminate; clasificación determinista sin afirmar detección de saltos entre muestras. Recolección del principal fija tiempos; drenaje post-KILL sólo extiende la latencia de entrega dentro de su cota. |
| G-M2-10 · terminación | Handle válido/forjado/cruzado, repetición con el mismo objeto, solicitud post-resultado, destrucción del handle, reinicio del coordinador, pérdida del supervisor de acción y carrera con deadline respetan D-M2-4 y el vocabulario v1. El evento de rechazo queda marcado pendiente M3, no verde ficticio. |
| G-M2-11 · recolección/plan | Proceso principal y descendientes observados se recogen; `GuaranteePlan` declara configuración/fórmula/topología y `guarantees_applied` los valores efectivos; Linux declara el uso real de subreaper y Darwin multi-nivel `unsupported`. La enmienda de ADR-009 está aceptada en ADR-012. |
| G-M2-12 · capacidad | Carreras sobre `max_concurrent_actions` nunca exceden la cota ni gastan tokens por falta de slot; el handoff terminal libera el slot, un handle abandonado no deja registro global y un handle retenido conserva su propia memoria. Tests con límites máximos confirman 8 GiB + 8 MiB estables y pico de 16 GiB + 8 MiB de payload para 64 acciones, más overhead y sin claim exacto de RSS. |
| G-M2-13 · plataforma | Suite completa separada en Darwin arm64 y Linux aarch64 pineado; skips y degradaciones explícitos, nunca convertidos en verde equivalente. |
| G-M2-14 · regresión | M1-R2 está cerrado con `GuaranteePlan` válido contra schema; todos los gates M0/M1, mypy strict, regeneración diff-cero y fuzzers permanecen verdes. |
| G-M2-15 · frontera | Diff final sin schemas, workflows, dependencias runtime, M3, x86_64, tag ni release; revisión adversarial fresca `PROCEED`. |

**Criterio de salida M2:** todos los gates G-M2-01..15 verdes; ninguna prueba
acotada cuelga; manifest saneado y reproducible; C2-handoff, C3, C4 y la parte
de inicio de C6 se promueven sólo con prueba citada. C5/C7 y `audit_trail`
permanecen P hasta M3.

## 6. Secuencia propuesta de construcción, si después se autoriza

1. **PRE-M2-R2:** con autoridad separada, corregir `failure_mode` en el emisor
   M1, añadir validación wire del `GuaranteePlan`, obtener `PROCEED` y cerrar
   M1-R2; todavía sin código M2.
2. **PRE-M2-ADR:** aceptar/corregir D-M2-1..5, redactar ADR-012 y enmendar
   expresamente la firma local de `await_result`, ADR-009 y las secciones
   normativas afectadas; obtener `PROCEED`, todavía sin código M2.
3. **INC-M2-1:** tipos locales, configuración validada y revalidación pura de
   `StartRequest`; proceso host falso, cero spawn real.
4. **INC-M2-2:** CAS, reconciliación, capacidad y handle/termination token con
   dobles deterministas.
5. **INC-M2-3:** supervisor POSIX real, IPC, grupo, stdin y salida acotada.
6. **INC-M2-4:** deadline, TERM→KILL, terminate/await y carreras.
7. **INC-M2-5:** caracterización por plataforma, suite integral, claims,
   manifest y cierre administrativo.

Cada incremento requiere tests locales y revisión adversarial sobre su propio
diff. Un `PROCEED` de preparación o de un incremento anterior no cubre el diff
final.

## 7. Capas que una implementación autorizada podría tocar

| Capa | Alcance futuro permitido por una eventual autorización M2 |
|---|---|
| `src/domain/` | tipos locales de start/handle/terminación/salida y máquina de estados pura; sin eventos M3. |
| `src/application/` | `AdmissionService` sólo para configuración `audit_mode`, plan/promoción de garantías M2 y fórmula/topología; además orquestación `start`, `terminate`, `await_result`, slots y orden ADR-011. No reabre otras semánticas M1. |
| `src/ports/` | puerto de proceso/IPC estrictamente local; retirar o aislar también `spawn_frontier.py`, cuya firma pre-ADR-011 no es el nuevo handoff; no AuditSink sustituto. |
| `src/adapters/` | supervisor POSIX por acción y helpers de plataforma; retirar o aislar el adaptador instrumental M1 sin perder sus pruebas. |
| `tests/unit/`, `tests/integration/`, `tests/adversarial/`, `tests/escape/` | G-M2-01..15; procesos siempre acotados, identificables y recogidos. |
| `scripts/`, `docs/evidencia/` | runner local reproducible, manifests y caracterización saneada; sin secretos ni salida bruta sensible. |

El acto futuro debe enumerar archivos o capas exactas y resolver cualquier
solapamiento con cambios ajenos antes de escribir.

## 8. Forma de la siguiente decisión

Hay dos autoridades independientes que el dueño puede emitir juntas o por
separado, pero que deben conservar actas y commits distintos. Para cerrar el
prerrequisito M1:

> Autorizo una corrección M1-R2 acotada a sustituir el `failure_mode` vacío por
> una declaración honesta no vacía, añadir la prueba wire del `GuaranteePlan` y
> actualizar su evidencia; no autorizo otros cambios M1 ni implementar M2.

Para fijar el diseño previo a M2:

> Acepto D-M2-1(a), D-M2-2(a), D-M2-3, D-M2-4 y D-M2-5(a), y autorizo
> redactar ADR-012 y las enmiendas normativas previas. Todavía no autorizo
> implementar M2.

El dueño puede corregir cualquier punto. Sólo después de cerrar M1-R2 y publicar
ADR-012 con revisión final, otra decisión podrá autorizar o rechazar la
implementación M2 con estos gates. No convertir ninguna de las dos autoridades
anteriores en autorización implícita de M2.

## 9. Stop rule

Hasta recibir la autoridad correspondiente de §8, no implementar M1-R2, no
crear ADR-012 y no modificar la especificación, código, schemas, tests, scripts,
CI ni fronteras de proceso. Autorizar M1-R2 o ADR-012 tampoco autoriza M2. No
iniciar M3, no activar GitHub Actions, no preparar tag/alfa/release y no ampliar
el modelo de amenaza por efecto de este paquete.
