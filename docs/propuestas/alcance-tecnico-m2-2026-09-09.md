# Propuesta de alcance técnico M2 — enumeración §8

> **NO AUTORIZA M2.** Propuesta del agente que traduce el alcance
> arquitectónico ya fijado por ADR-011, ADR-012 y el paquete de preparación M2
> a una enumeración concreta de archivos revisable. No es acta, no está firmada
> y no concede autoridad de construcción. El agente propone; el dueño autoriza.

**Fecha:** 2026-09-09.
**Revisión:** 2 — incorpora la resolución humana de
`FIX-SCOPE-BEFORE-AUTHORIZATION` (2026-09-09).
**Resuelve:** el hueco de §8 del borrador
`docs/propuestas/borrador-autorizacion-m2-2026-09-09.md`.
**Deriva exclusivamente de:** especificación M0–M3 v1.2, ADR-011, ADR-012,
`paquete-preparacion-m2-2026-08-28.md`, gates G-M2-01..15, arquitectura actual
del repositorio (inspección read-only) y estado cerrado de M1.

## 1. Principios aplicados

**Mínimo alcance.** Ninguna ruta se incluye «por si acaso»: cada una tiene
justificación concreta y gate asociado. Permanecen **fuera** `contracts/`,
schemas wire, ADR existentes, `.github/workflows/`, e integración con Ágora,
Skopos, AN-KLA, AEC, capability enforcement y sandboxing.

**Evolución monotónica (resolución §6).** M2 es una **extensión monotónica** de
las garantías cerradas en M1. Agregar funcionalidad M2 **no concede autoridad
para invalidar evidencia M1**. Reabrir cualquier garantía M1 exige decisión
explícita separada.

**Derivada de las dos anteriores:** cuando una capacidad M2 cabe en un módulo
nuevo, se propone el módulo nuevo en vez de modificar uno de M1.

`mypy.ini` aplica `strict = True` global sin enumerar módulos: los archivos
nuevos quedan cubiertos sin tocar configuración.

## 2. Inventario reconciliado

Contabilidad única y verificable, contada desde las tablas de §3, §4 y §5. Cada
ruta aparece **exactamente una vez** en todo el documento.

| Concepto | Rutas |
|---|---:|
| **TOTAL inventariado** | **45** |
| — de las cuales **nuevas propuestas** | 32 |
| — de las cuales **existentes** | 13 |

Verificación: `32 + 13 = 45`. ✔

### 2.1 Por tratamiento

| Tabla | Tratamiento | Rutas | Nuevas | Existentes |
|---|---|---:|---:|---:|
| §3 | **Modificables o nuevas** — el alcance real de M2 | 38 | 32 | 6 |
| §4 | **Preservadas** — NO modificables en M2 | 5 | 0 | 5 |
| §5 | **Consumidas sin cambios** | 2 | 0 | 2 |
| | **Total** | **45** | **32** | **13** |

Verificación: `38 + 5 + 2 = 45` y `32 + 0 + 0 = 32`, `6 + 5 + 2 = 13`. ✔

### 2.2 Por naturaleza

| Naturaleza | Rutas | Nuevas | Existentes |
|---|---:|---:|---:|
| **Código** (`src/`: domain, application, port, adapter) | 19 | 12 | 7 |
| **Tests** (`tests/`) | 14 | 11 | 3 |
| **Herramienta** (`scripts/`) | 2 | 2 | 0 |
| **Documentación y evidencia** (`docs/`, raíz) | 10 | 7 | 3 |
| **Total** | **45** | **32** | **13** |

Verificación: `19 + 14 + 2 + 10 = 45`; nuevas `12 + 11 + 2 + 7 = 32`;
existentes `7 + 3 + 0 + 3 = 13`. ✔

Desglose del código por capa: domain 7 · application 3 · port 4 · adapter 5.

## 3. Rutas modificables o nuevas (38)

Estado: **E** existe · **N** nueva. Riesgo: **B** bajo · **M** medio · **A** alto.

### INC-M2-1 — tipos locales, configuración y revalidación pura (cero spawn real)

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/domain/start_request.py` | N | domain | `StartRequest{admitted_action, action_request_wire}` de ADR-011 §2.1 y plan de ejecución inmutable de §2.3.7, derivado de una única instantánea validada | 01, 02 | no | B |
| `src/domain/revalidation.py` | N | domain | Ruta de revalidación pura de ADR-011 §2.3 pasos 1–7, **separada de la admisión**. Reutiliza en sólo-lectura `contract_layer`, `capability`, `pop`, `representability`, `stdin_policy`, `crypto` sin modificarlos | 01, 02 | no | M |
| `src/domain/start_outcomes.py` | N | domain | `StartOutcome` con el vocabulario v1 ya congelado: `started` \| `start_failed`; reason codes `start_failed`, `start_failed_indeterminate`, `capability_rejected`; `safe_detail` saneado | 01, 04, 09 | no | B |
| `src/application/config.py` | N | application | Configuración local validada de D-M2-2/3/5: `max_concurrent_actions` (1..64, default 1, `bool` rechazado), `termination_grace_ms` (2000, 0..60000), `post_kill_drain_ms` (1000, 1..10000), `audit_mode` (sólo `optional`; `required` impide inicializar) | 01 | no | B |
| `src/application/admit.py` | **E** | application | **Única modificación de código M1**, estrictamente aditiva y acotada por §6.2 | 01, 11, 14 | **sí** | **A** |

### INC-M2-2 — CAS, reconciliación, capacidad, handle y terminación

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/application/start_service.py` | N | application | Orquestación de `start`, `terminate`, `await_result`; orden ADR-011 **reloj final → CAS → spawn**; reserva y liberación de slots; reconciliación exacta de ADR-011 (`spent`/`unknown` indeterminados, `unspent` permite otro CAS y nunca spawn directo) | 03, 04, 05, 06, 12 | no | M |
| `src/domain/execution_handle.py` | N | domain | `ExecutionHandle` local opaco: porta el token opaco de terminación ligado a la capacidad para ese `action_id`, aloja el receipt tras el primer `terminate` y la propiedad del resultado terminal tras el handoff. Ligado a la instancia del coordinador; reiniciarlo invalida sus handles; **sin registro global** | 10, 12 | no | M |
| `src/domain/termination.py` | N | domain | D-M2-4: `TerminationReason.OPERATOR_REQUESTED` como único valor v1; `TerminationAccepted(receipt opaco, local, no durable, sin MAC)`; `TerminationRejected(capability_rejected)` como único reason code | 10 | no | B |
| `src/ports/process_host.py` | N | port | Puerto de proceso/IPC **estrictamente local** y **paralelo** a la frontera instrumental M1 (§4): spawn bajo plan inmutable, transporte de frames, handoff terminal y terminación del grupo. Permite dobles deterministas antes del supervisor real | 07, 08 | no | B |
| `src/ports/__init__.py` | **E** | port | **Sólo añadir** el re-export de `ProcessHost`. **Prohibido retirar** `SpawnFrontier` del re-export (§4) | 14 | **sí** | M |
| `src/adapters/__init__.py` | **E** | adapter | **Sólo añadir** los re-exports de los adaptadores M2. **Prohibido retirar** `SpawnFrontierCounter` ni `SpawnCrossing` (§4) | 14 | **sí** | M |

### INC-M2-3 — supervisor POSIX real, IPC, grupo, stdin y salida acotada

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/adapters/posix_supervisor.py` | N | adapter | Supervisor dedicado **por acción** (D-M2-2(a)): fuera del grupo del proceso ejecutado, le crea grupo propio con `process_group=0` y **sin `preexec_fn`**; drena ambos pipes aun tras truncar; frames ordenados ≤64 KiB por stream con crédito y máximo uno no confirmado; descarta el exceso con contadores exactos; acota su espera de EOF tras KILL | 07, 08, 11 | no | **A** |
| `src/adapters/platform_caps.py` | N | adapter | Capacidades por plataforma: en Linux **sólo el supervisor de acción** activa `PR_SET_CHILD_SUBREAPER` vía `ctypes` (excepción parcial declarada de ADR-006); en Darwin la contabilidad multi-nivel es `unsupported` | 11, 13 | no | M |

### INC-M2-4 — deadline, TERM→KILL, terminate/await y carreras

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/domain/deadline.py` | N | domain | Fórmulas puras de D-M2-3: `applied_grace_ms = min(termination_grace_ms, deadline_eff_ms)`, `useful_runtime_ms`, `soft_termination_at`, `hard_deadline_at`; `deadline_eff_ms == 0` → `StartFailed(capability_rejected)` **antes del CAS y sin spawn**; empate duración/vigencia → gana vigencia (`deadline_validity_exhausted`); empate con terminate → gana deadline (ADR-005) | 09 | no | M |
| `src/domain/execution_result.py` | N | domain | Clasificación terminal con el vocabulario wire v1 ya congelado (`executed`, `deadline_exceeded`, `terminated`, `supervision_failed`; causas `natural_exit`, `deadline_duration`, `deadline_validity_exhausted`, `external_termination`, `supervision_failure`); tipo local `AwaitedExecution{result, stdout, stderr}` de D-M2-1(a); claves congeladas de `guarantees_applied`. **No modifica el wire** | 07, 09, 11 | no | M |

### INC-M2-5 — pruebas, caracterización, evidencia y cierre

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `tests/unit/helpers_m2.py` | N | test | Fixtures y constructores deterministas M2, espejo de `helpers_m1.py`, **sin modificarlo** | todos | no | B |
| `tests/unit/test_start_revalidation.py` | N | test | Token/request malformados, MAC rota, campos cruzados, ejecutable distinto, tipos hostiles, >64 KiB, expirado: cero CAS y cero procesos. Spy: cero `reserve_nonce`, cero `PolicyPort.evaluate`, cero emisión de token | 01, 02 | no | B |
| `tests/unit/test_m2_config.py` | N | test | Matriz de configuración: `bool`, floats, rangos y tipos inválidos; `audit_mode=required` impide inicializar antes de recibir solicitudes | 01 | no | B |
| `tests/unit/test_deadline_math.py` | N | test | Relojes falsos: duración, `exp`, gracia ≥ vida útil, plazo efectivo cero, muestra final inválida o regresiva, ambos empates | 09 | no | B |
| `tests/unit/test_termination_semantics.py` | N | test | Handle válido/forjado/cruzado, repetición con el mismo objeto, post-resultado, destrucción, reinicio del coordinador, pérdida del supervisor, carrera con deadline | 10 | no | B |
| `tests/integration/test_start_linearization.py` | N | test | Instrumentación de reloj final → CAS → spawn; sólo `CONSUMED` cruza; matriz de reconciliación de ADR-011; inyección de crash antes/después del CAS y alrededor del spawn | 03, 04, 06 | no | M |
| `tests/integration/test_start_concurrency.py` | N | test | Varios procesos con el mismo token contra el store real: un solo ganador; reinicio conserva `spent`; nunca doble spawn | 05 | no | M |
| `tests/integration/test_capacity_slots.py` | N | test | Carreras sobre `max_concurrent_actions`; el handoff terminal libera slot; handle abandonado no deja registro global; handle retenido conserva su memoria | 12 | no | M |
| `tests/integration/test_output_framing.py` | N | test | Flood independiente de stdout/stderr, límites 0/máximo, multibyte, coordinador lento y caído; frames ≤64 KiB, uno no confirmado; cota estable y pico bajo ambas fórmulas D-M2-1; `post_kill_forced_pipe_close=1` al expirar el drenaje | 07 | no | **A** |
| `tests/adversarial/test_no_hang.py` | N | test | Procesos que no leen stdin, ignoran TERM, mantienen pipes en descendientes, inundan salida o escapan con `setsid`: toda prueba acotada termina; escapes **declarados, no mitigados** | 08 | no | **A** |
| `tests/escape/test_supervisor_characterization.py` | N | test | Recolección del principal y de descendientes observados; uso real de subreaper en Linux; `unsupported` multi-nivel en Darwin; RSS **caracterizado, no declarado exacto** | 11, 13 | no | M |
| `scripts/fuzz_start_revalidation.py` | N | script | Fuzz con oráculo de la ruta de revalidación, simétrico a `fuzz_admision.py` de M1 (que no se modifica), exigido por la matriz de tipos hostiles de G-M2-01 | 01 | no | B |
| `scripts/characterize-m2.sh` | N | script | Runner local reproducible de la suite M2 por plataforma; complementa `characterize-linux.sh` **sin sustituirlo** | 13 | no | B |
| `docs/evidencia/caracterizacion-m2-darwin-<fecha>.md` | N | doc/evid | Evidencia clase L, Darwin arm64, **separada** | 13 | no | B |
| `docs/evidencia/caracterizacion-m2-linux-<fecha>.md` | N | doc/evid | Evidencia clase V, Linux aarch64 con imagen fijada por digest, **separada** | 13 | no | B |
| `docs/evidencia/estado-evidencia-m2-<fecha>.md` | N | doc/evid | Estado consolidado de los quince gates con prueba citada | todos | no | B |
| `docs/evidencia/manifest-m2-sha256.txt` | N | doc/evid | Manifest saneado y reproducible | todos | no | B |
| `docs/revisiones/revision-adversarial-m2-<fecha>.md` | N | doc/evid | Revisión adversarial externa **sobre el código real** | 15 | no | B |
| `docs/decisiones/autorizacion-m2-<fecha>.md` | N | doc/evid | Acta firmada (la produce el dueño, no el agente) | — | no | B |
| `docs/decisiones/cierre-m2-<fecha>.md` | N | doc/evid | Acta de cierre | todos | no | B |
| `docs/gobernanza/INDEX.md` | **E** | doc/evid | Registro de apertura y cierre de M2 | — | no | B |
| `README.md` | **E** | doc/evid | **Sólo al cierre**: estado del ciclo con el alcance exacto probado | — | no | M |
| `project-manifest.yaml` | **E** | doc/evid | **Sólo al cierre**: mover supervisión de `no_ofrece` a `ofrece` con el alcance exacto probado | — | no | M |

**Consolidables:** la contabilidad pura de prefijo retenido, banderas de
truncamiento y `discarded_bytes` puede vivir en `posix_supervisor.py` o en un
módulo de dominio propio. Es decisión de implementación, no una ruta adicional;
no se inventaría por separado para no inflar el alcance.

## 4. Rutas preservadas — NO modificables en M2 (5)

**Resolución humana §1: AISLAR, NO RETIRAR.** Durante M2 no se retira
`SpawnFrontier` ni se elimina la evidencia M1 asociada. La frontera M2 se
implementa **en paralelo** mediante `src/ports/process_host.py`. Las pruebas M1
existentes **deben seguir pasando sin modificación**.

Motivo registrado: forma parte de la evidencia existente de M1; hay pruebas
adversariales que acreditan claims ya cerrados; eliminarla dentro de M2
produciría **discontinuidad de evidencia**; M2 debe ser extensión del runtime,
**no reescritura retroactiva de M1**.

| Ruta | Capa | Qué acredita | Tratamiento |
|---|---|---|---|
| `src/ports/spawn_frontier.py` | port | Puerto instrumental D-P4-α | **Intacto.** No retirar, no reescribir |
| `src/adapters/spawn_frontier_counter.py` | adapter | Contador de cruces de frontera | **Intacto.** No retirar, no reescribir |
| `tests/unit/helpers_m1.py` | test | Fixtures M1 que importan `SpawnFrontier` | **Intacto.** M2 usa `helpers_m2.py` |
| `tests/adversarial/test_fuzz_admision.py` | test | Fuzz M1 con spy de frontera | **Intacto** |
| `tests/adversarial/test_policy_spawn_frontier.py` | test | **20 pruebas** que acreditan que M1 no crea procesos | **Intacto** |

Una eliminación futura de `SpawnFrontier` exigirá: (1) evidencia sustitutiva
equivalente o superior; (2) demostración de que los claims M1 siguen válidos;
(3) decisión documental independiente. **Esa migración no ocurre dentro de M2.**

## 5. Rutas consumidas sin cambios (2)

| Ruta | Capa | Por qué no se modifica |
|---|---|---|
| `src/ports/replay_store.py` | port | Ya declara `consume_start_token` y `start_token_status`: las primitivas CAS que M2 necesita **ya existen** y M1 las ejercitó |
| `src/adapters/replay_store_file.py` | adapter | Implementa ambos CAS con fsync; M2 lo consume tal cual |

Si durante INC-M2-2 se demostrase que la reconciliación de ADR-011 exige una
distinción no representable por el puerto actual, eso amplía alcance sobre
código M1: **detenerse y volver al dueño**.

## 6. Fronteras exactas resueltas

### 6.1 Terminación — local y opaca (resolución §3)

El mecanismo de terminación permanece **dentro del contrato local ya previsto**.
Se implementa con handle/capability local conforme a ADR-012:
`ExecutionHandle` porta un token opaco ligado a la capacidad para ese
`action_id`; el receipt es opaco, local, no durable y sin MAC; el vocabulario de
rechazo es exclusivamente `capability_rejected`.

**Prohibido crear:** nuevo wire schema · `termination-token-payload` firmado ·
nuevo envelope · protocolo remoto · capability distribuida · mecanismo
cross-host. El schema `contracts/schemas/v1/termination-token-payload.json`
permanece congelado **sin capa productora**, exactamente igual que hoy.

**Condición de parada:** si durante INC-M2-2 se demuestra que M2 requiere
necesariamente un nuevo payload wire o modificar contratos congelados,
**DETENER EL INCREMENTO**, declarar `BLOCKED-BY-NORMATIVE-GAP` y volver al
dueño con evidencia. **No inventar el contrato durante la implementación.**

### 6.2 `admit.py` — extensión aditiva (resolución §2)

Modificación permitida **únicamente** para transportar o declarar información
que exigen los contratos M2 ya adoptados: aceptar configuración `audit_mode`;
declarar en `GuaranteePlan.mechanism`/`assumptions` las entradas ASCII
`clave=valor` congeladas por D-M2-3 (`termination_grace_ms_configured`,
`useful_runtime_formula`, `supervisor_scope`, `subreaper_requested`); promover
**sólo** garantías M2 probadas; conservar `audit_trail=unsupported`.

**M2 no debe alterar el comportamiento observable previamente validado de la
ruta M1.** Se preservan: semántica existente · decisiones de admisión M1 ·
diagnósticos y su orden · comportamiento fail-closed · `PolicyPort` ·
contratos wire · regresión M1 completa.

**Regla de parada — SCOPE VIOLATION.** Si una prueba M1 existente cambia de
resultado, se trata **inicialmente como `SCOPE VIOLATION`** y se **detiene ese
incremento** hasta demostrar documentalmente que el cambio estaba autorizado.
**Prohibido reinterpretar una regresión como adaptación implícita de M1 a M2.**

### 6.3 Frontera domain/application de la revalidación (resolución §4)

**La decisión de archivo concreto pertenece al desarrollador. La semántica no.**
La ubicación puede resolverse durante el incremento siempre que se respeten:
arquitectura hexagonal · dominio sin dependencia de adaptadores · pureza
exigida por los gates · **cero** llamadas nuevas a `PolicyPort` · **cero**
`reserve_nonce` · **cero** emisión de token nuevo · determinismo de la
revalidación.

Si resolver la ubicación exigiese cambiar alguna semántica normativa:
**detener y escalar.**

## 7. PENDIENTES residuales

**Ninguno de alcance.** Los tres puntos abiertos de la revisión 1 quedaron
resueltos: §4 (aislar, no retirar), §6.1 (terminación local con condición de
parada) y §6.3 (ubicación al desarrollador, semántica no).

Subsisten dos decisiones **de implementación**, dentro del alcance y sin
autoridad adicional, cada una con su límite ya fijado:

| Punto | Incremento | Límite que no puede cruzar |
|---|---|---|
| Material exacto que identifica una instancia del coordinador en `ExecutionHandle` | INC-M2-2 | No puede producir documento wire ni registro global; si lo exigiera → `BLOCKED-BY-NORMATIVE-GAP` (§6.1) |
| Reparto exacto domain/application de los pasos 1–7 de ADR-011 | INC-M2-1 | No puede relajar el invariante 2, acreditado por G-M2-02 (§6.3) |

## 8. Riesgos

### 8.1 Reabrir M1 · riesgo alto, contenido

`src/application/admit.py` es la **única** modificación de código M1. Contención
en §6.2: cambio aditivo, regla `SCOPE VIOLATION` y G-M2-14 exigiendo regresión
M0/M1 verde, `mypy --strict`, regeneración de vectores con diff cero y fuzzers.

### 8.2 Discontinuidad de evidencia M1 · riesgo **eliminado**

Era el riesgo alto de la revisión 1. La resolución §1 lo cierra: las cinco rutas
de §4 quedan **intactas** y sus 20 pruebas adversariales siguen acreditando el
claim D-P4-α sin modificación. `src/ports/__init__.py` y
`src/adapters/__init__.py` se tocan **sólo para añadir**; retirar un símbolo M1
de sus re-exports es `SCOPE VIOLATION`.

### 8.3 Modificar wire contracts · riesgo controlado

Ninguna ruta entra en `contracts/`. `execution_result.py` y `start_outcomes.py`
**consumen** el vocabulario v1 congelado sin redefinirlo; D-M2-1(a) mantiene el
wire `ExecutionResult v1` intacto enmendando sólo la API local. §6.1 prohíbe
explícitamente producir `termination-token-payload`. G-M2-15 exige diff final
sin schemas.

### 8.4 Absorber M3 · riesgo controlado

Ninguna ruta crea `RuntimeEvent`, `AuditSink`, recibos, cadena ni persistencia.
`config.py` sólo **reconoce** `audit_mode=required` para rechazar la
inicialización. Riesgo residual: `audit_mode=optional` evita el bloqueo por
durabilidad pero **no elimina la obligación del evento**; queda marcada
pendiente M3 en G-M2-10, **no verde ficticio**.

### 8.5 Coupling con AEC · riesgo bajo

Ninguna ruta menciona AEC, perfiles ni Core común. El vocabulario propuesto es
el wire v1 de EKTEL, anterior a F0-A.

### 8.6 Ampliar la TCB · riesgo medio

`platform_caps.py` introduce `ctypes` para `prctl`, **única excepción parcial
permitida por ADR-006** al núcleo stdlib-only, ya declarada.
`posix_supervisor.py` añade un supervisor por acción: amplía la superficie de
fallo, pero es exactamente la topología que ADR-012 fija, elegida frente a la
alternativa (b) de threads en supervisor global precisamente por acotar el blast
radius. **Cero dependencias runtime nuevas.**

### 8.7 Introducir sandboxing · riesgo bajo

Ninguna ruta aísla filesystem ni red. El grupo de procesos propio es
**contención de terminación, no aislamiento**: los escapes por `setsid`,
double-fork y D-state se **declaran** en G-M2-08, no se mitigan. El invariante
10 mantiene visible el TOCTOU de `command_absolute` (N1, N17).

## 9. Recomendación

**READY-FOR-HUMAN-AUTHORIZATION.**

Los tres puntos que motivaron `FIX-SCOPE-BEFORE-AUTHORIZATION` están resueltos
por la revisión humana e incorporados: tratamiento de `SpawnFrontier` (§4),
frontera de `admit.py` con regla `SCOPE VIOLATION` (§6.2) y terminación
local/opaca con condición de parada (§6.1). El inventario está reconciliado y
verificado (§2): `32 + 13 = 45`, sin duplicados, cada ruta una sola vez. No
subsiste ningún PENDIENTE de alcance (§7).

Esta recomendación **no es un PROCEED ni una autorización**. El alcance está
listo para que el dueño lo firme; la implementación no comienza hasta ese acto
humano explícito.

## 10. Fuentes

Especificación v1.2 (§8.0 handoff y autorización de `terminate`, §12
supervisión enmendada por ADR-012, §15 M2, §19.6) ·
`docs/adr/adr-011-handoff-admision-start.md` ·
`docs/adr/adr-012-supervision-local-m2.md` ·
`docs/propuestas/paquete-preparacion-m2-2026-08-28.md` (§2 alcance, §4
invariantes, §5 gates, §6 incrementos, §7 capas) · cierre de M1, M1-R1 y M1-R2
· resolución humana de `FIX-SCOPE-BEFORE-AUTHORIZATION` (2026-09-09) ·
inspección read-only de `src/`, `tests/`, `scripts/`, `mypy.ini` y
`contracts/schemas/v1/` al commit `f56f770`.
