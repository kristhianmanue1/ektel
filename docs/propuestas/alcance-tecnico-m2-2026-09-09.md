# Propuesta de alcance técnico M2 — enumeración §8

> **NO AUTORIZA M2.** Este documento es una **propuesta del agente** que
> traduce el alcance arquitectónico ya fijado por ADR-011, ADR-012 y el
> paquete de preparación M2 a una enumeración concreta de archivos revisable.
> No es acta, no está firmado y no concede autoridad de construcción. El
> agente propone; el dueño autoriza.

**Fecha:** 2026-09-09.
**Resuelve:** el hueco de §8 del borrador
`docs/propuestas/borrador-autorizacion-m2-2026-09-09.md`.
**Deriva exclusivamente de:** especificación M0–M3 v1.2, ADR-011, ADR-012,
`paquete-preparacion-m2-2026-08-28.md`, gates G-M2-01..15, arquitectura actual
del repositorio (inspección read-only) y estado cerrado de M1.

## 1. Principio aplicado

**Mínimo alcance.** Ninguna ruta se incluye «por si acaso»: cada una tiene
justificación concreta y gate asociado. Permanecen **fuera** `contracts/`,
schemas wire, ADR existentes, `.github/workflows/`, e integración con Ágora,
Skopos, AN-KLA, AEC, capability enforcement y sandboxing.

Regla de diseño derivada del principio: **cuando una capacidad M2 puede
implementarse en un módulo nuevo en vez de modificar uno de M1, se propone el
módulo nuevo.** Modificar código M1 cerrado es el riesgo más caro de este hito
y se reduce a los casos donde es inevitable (§4).

`mypy.ini` aplica `strict = True` global sin enumerar módulos: los archivos
nuevos quedan cubiertos sin tocar configuración.

## 2. Enumeración propuesta

Estado: **E** existe · **N** nuevo propuesto. Riesgo: **B** bajo · **M** medio
· **A** alto.

### INC-M2-1 — tipos locales, configuración y revalidación pura (cero spawn real)

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/domain/start_request.py` | N | domain | `StartRequest{admitted_action, action_request_wire}` de ADR-011 §2.1 y plan de ejecución inmutable de §2.3.7, derivado de una única instantánea validada | 01, 02 | no | B |
| `src/domain/revalidation.py` | N | domain | Ruta de revalidación pura de ADR-011 §2.3 pasos 1–7, **separada de la admisión**. Reutiliza en sólo-lectura `contract_layer`, `capability`, `pop`, `representability`, `stdin_policy`, `crypto` sin modificarlos | 01, 02 | no | M |
| `src/domain/start_outcomes.py` | N | domain | `StartOutcome` con el vocabulario v1 ya congelado: `started` \| `start_failed`, reason codes `start_failed`, `start_failed_indeterminate`, `capability_rejected`, `safe_detail` saneado | 01, 04, 09 | no | B |
| `src/application/config.py` | N | application | Configuración local validada de D-M2-2/3/5: `max_concurrent_actions` (1..64, default 1, `bool` rechazado), `termination_grace_ms` (2000, 0..60000), `post_kill_drain_ms` (1000, 1..10000), `audit_mode` (sólo `optional`; `required` impide inicializar) | 01 | no | B |
| `src/application/admit.py` | **E** | application | **Única modificación inevitable de M1.** Aceptar configuración `audit_mode`; declarar en `GuaranteePlan.mechanism`/`assumptions` las entradas ASCII `clave=valor` congeladas por D-M2-3 (`termination_grace_ms_configured`, `useful_runtime_formula`, `supervisor_scope`, `subreaper_requested`); promover **sólo** garantías M2 probadas; conservar `audit_trail=unsupported` | 01, 11, 14 | **sí** | **A** |

### INC-M2-2 — CAS, reconciliación, capacidad, handle y terminación

| Ruta | Est | Capa | Motivo | Gates | ¿Toca M1? | Riesgo |
|---|---|---|---|---|---|---|
| `src/application/start_service.py` | N | application | Orquestación de `start`, `terminate`, `await_result`; orden ADR-011 **reloj final → CAS → spawn**; reserva y liberación de slots; reconciliación exacta de ADR-011 (`spent`/`unknown` indeterminados, `unspent` permite otro CAS y nunca spawn directo) | 03, 04, 05, 06, 12 | no | M |
| `src/domain/execution_handle.py` | N | domain | `ExecutionHandle` local opaco: porta el token opaco de terminación ligado a la capacidad para ese `action_id`, aloja el receipt tras el primer `terminate` y la propiedad del resultado terminal tras el handoff. Ligado a la instancia del coordinador; reiniciarlo invalida sus handles; sin registro global | 10, 12 | no | M |
| `src/domain/termination.py` | N | domain | D-M2-4: `TerminationReason.OPERATOR_REQUESTED` como único valor v1; `TerminationAccepted(receipt opaco, local, no durable, sin MAC)`; `TerminationRejected(capability_rejected)` como único reason code | 10 | no | B |
| `src/ports/process_host.py` | N | port | Puerto de proceso/IPC **estrictamente local**: spawn bajo plan inmutable, transporte de frames, handoff terminal y terminación del grupo. Permite dobles deterministas en INC-M2-2 antes del supervisor real | 07, 08 | no | B |
| `src/ports/spawn_frontier.py` | **E** | port | **Retirar o aislar** (paquete §7): su firma pre-ADR-011 `submit(Admitted)` no es el nuevo handoff | 14, 15 | **sí** | **A** |
| `src/adapters/spawn_frontier_counter.py` | **E** | adapter | **Retirar o aislar** el adaptador instrumental M1 (D-P4-α) **sin perder sus pruebas** | 14, 15 | **sí** | **A** |
| `src/ports/__init__.py` | **E** | port | Consecuencia mecánica de retirar/aislar `SpawnFrontier` del re-export | 14 | **sí** | M |
| `src/adapters/__init__.py` | **E** | adapter | Consecuencia mecánica de retirar/aislar `SpawnFrontierCounter`/`SpawnCrossing` del re-export | 14 | **sí** | M |
| `src/ports/replay_store.py` | E | port | **Sin cambios previstos.** Ya declara `consume_start_token` y `start_token_status`: las primitivas CAS que M2 necesita existen y M1 las ejercitó | 04, 05 | no | B |
| `src/adapters/replay_store_file.py` | E | adapter | **Sin cambios previstos.** Implementa los dos CAS con fsync; M2 lo consume tal cual | 05, 06 | no | B |

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
| `tests/unit/helpers_m2.py` | N | test | Fixtures y constructores deterministas de M2, espejo de `helpers_m1.py` | todos | no | B |
| `tests/unit/test_start_revalidation.py` | N | test | Token/request malformados, MAC rota, campos cruzados, ejecutable distinto, tipos hostiles, >64 KiB, expirado: cero CAS y cero procesos. Spy: cero `reserve_nonce`, cero `PolicyPort.evaluate`, cero emisión de token | 01, 02 | no | B |
| `tests/unit/test_m2_config.py` | N | test | Matriz de configuración: `bool`, floats, rangos y tipos inválidos; `audit_mode=required` impide inicializar antes de recibir solicitudes | 01 | no | B |
| `tests/unit/test_deadline_math.py` | N | test | Relojes falsos: duración, `exp`, gracia ≥ vida útil, plazo efectivo cero, muestra final inválida o regresiva, ambos empates | 09 | no | B |
| `tests/unit/test_termination_semantics.py` | N | test | Handle válido/forjado/cruzado, repetición con el mismo objeto, post-resultado, destrucción, reinicio del coordinador, pérdida del supervisor, carrera con deadline | 10 | no | B |
| `tests/integration/test_start_linearization.py` | N | test | Instrumentación de reloj final → CAS → spawn; sólo `CONSUMED` cruza; matriz de reconciliación de ADR-011; inyección de crash antes/después del CAS y alrededor del spawn | 03, 04, 06 | no | M |
| `tests/integration/test_start_concurrency.py` | N | test | Varios procesos con el mismo token contra el store real: un solo ganador; reinicio conserva `spent`; nunca doble spawn | 05 | no | M |
| `tests/integration/test_capacity_slots.py` | N | test | Carreras sobre `max_concurrent_actions`; el handoff terminal libera slot; handle abandonado no deja registro global; handle retenido conserva su memoria | 12 | no | M |
| `tests/integration/test_output_framing.py` | N | test | Flood independiente de stdout/stderr, límites 0/máximo, multibyte, coordinador lento y caído; frames ≤64 KiB, uno no confirmado; cota estable y pico bajo ambas fórmulas D-M2-1; `post_kill_forced_pipe_close=1` al expirar el drenaje | 07 | no | **A** |
| `tests/adversarial/test_no_hang.py` | N | test | Procesos que no leen stdin, ignoran TERM, mantienen pipes en descendientes, inundan salida o escapan con `setsid`: toda prueba acotada termina; escapes declarados, no mitigados | 08 | no | **A** |
| `tests/escape/test_supervisor_characterization.py` | N | test | Recolección del principal y de descendientes observados; uso real de subreaper en Linux; `unsupported` multi-nivel en Darwin; RSS **caracterizado, no declarado exacto** | 11, 13 | no | M |
| `tests/unit/helpers_m1.py` | **E** | test | Importa `SpawnFrontier`; se ajusta si el puerto se retira | 14 | **sí** | **A** |
| `tests/adversarial/test_fuzz_admision.py` | **E** | test | Usa `SpawnFrontierCounter` como spy; se ajusta si el adaptador se retira | 14 | **sí** | **A** |
| `tests/adversarial/test_policy_spawn_frontier.py` | **E** | test | **20 pruebas** sobre la frontera instrumental; es la evidencia M1 que el paquete §7 manda **no perder** | 14 | **sí** | **A** |
| `scripts/fuzz_start_revalidation.py` | N | doc/evid | Fuzz con oráculo de la ruta de revalidación, simétrico a `fuzz_admision.py` de M1, exigido por la matriz de tipos hostiles de G-M2-01 | 01 | no | B |
| `scripts/characterize-m2.sh` | N | doc/evid | Runner local reproducible de la suite M2 por plataforma; complementa `characterize-linux.sh` sin sustituirlo | 13 | no | B |
| `docs/evidencia/caracterizacion-m2-darwin-<fecha>.md` | N | doc/evid | Evidencia clase L, Darwin arm64, **separada** | 13 | no | B |
| `docs/evidencia/caracterizacion-m2-linux-<fecha>.md` | N | doc/evid | Evidencia clase V, Linux aarch64 con imagen fijada por digest, **separada** | 13 | no | B |
| `docs/evidencia/estado-evidencia-m2-<fecha>.md` | N | doc/evid | Estado consolidado de los quince gates con prueba citada | todos | no | B |
| `docs/evidencia/manifest-m2-sha256.txt` | N | doc/evid | Manifest saneado y reproducible | todos | no | B |
| `docs/revisiones/revision-adversarial-m2-<fecha>.md` | N | doc/evid | Revisión adversarial externa **sobre el código real** | 15 | no | B |
| `docs/decisiones/autorizacion-m2-<fecha>.md` | N | doc/evid | Acta firmada (la produce el dueño, no el agente) | — | no | B |
| `docs/decisiones/cierre-m2-<fecha>.md` | N | doc/evid | Acta de cierre | todos | no | B |
| `docs/gobernanza/INDEX.md` | E | doc/evid | Registro de apertura y cierre de M2 | — | no | B |
| `README.md`, `project-manifest.yaml` | E | doc/evid | **Sólo al cierre**: mover supervisión de `no_ofrece` a `ofrece` con el alcance exacto probado | — | no | M |

**Consolidables:** la contabilidad pura de prefijo retenido, banderas de
truncamiento y `discarded_bytes` puede vivir en `posix_supervisor.py` o en un
módulo de dominio propio. Es decisión de implementación, no una ruta adicional
obligatoria; no se lista por separado para no inflar el alcance.

## 3. Puntos marcados PENDIENTE

No se fabrica respuesta donde no la hay.

### PENDIENTE-1 — mecanismo del token opaco de terminación · INC-M2-2

La especificación §8.0 dice que el `ExecutionHandle` «porta un **token opaco de
terminación** ligado a la capacidad tal como fue admitida para ese
`action_id`». D-M2-4 fija que el **receipt** es opaco, local, sin MAC y sin
durabilidad, y que un handle forjado, cruzado o de otra instancia produce
`TerminationRejected(capability_rejected)`. Lo que **no** está fijado es el
mecanismo del **token**: MAC sobre el dominio `DOMAIN_TERMINATION` —que
`src/domain/crypto.py` ya define— o identidad en proceso comparada dentro de la
instancia del coordinador.

- **Por qué no puede resolverse antes:** ambas satisfacen el comportamiento
  observable exigido por D-M2-4 y por G-M2-10; distinguirlas requiere el modelo
  de handle ya construido.
- **Qué lo resolverá:** la implementación de `execution_handle.py` en INC-M2-2,
  al fijar qué material identifica una instancia del coordinador.
- **Límite que impide ampliar el alcance:** ninguna de las dos opciones puede
  producir el documento wire `termination-token-payload`. Ese schema permanece
  congelado **sin capa productora**, igual que hoy. Si la implementación
  concluyera que hace falta emitirlo, eso es un cambio de contrato: **detenerse
  y volver al dueño**, no resolverlo en código.

### PENDIENTE-2 — frontera domain/application de la revalidación · INC-M2-1

ADR-011 §2.3 exige que la revalidación sea una ruta **separada** de la admisión
y prohíbe reutilizar `AdmissionService.admit()`, pero no fija en qué capa vive.
Se propone dominio para los pasos puros y aplicación para la orquestación.

- **Por qué no puede resolverse antes:** es una elección de diseño interno, no
  una decisión normativa; ADR-011 y ADR-012 son deliberadamente agnósticas.
- **Qué lo resolverá:** INC-M2-1, al escribir los pasos 1–7 y comprobar cuáles
  necesitan dependencias inyectadas.
- **Límite:** la elección **no puede** relajar el invariante 2 (cero
  `reserve_nonce`, cero `PolicyPort.evaluate`, cero emisión de token durante
  `start`), acreditado por G-M2-02.

### PENDIENTE-3 — retirar frente a aislar la frontera instrumental · INC-M2-2

El paquete §7 dice «retirar o aislar» y exige «sin perder sus pruebas». Es una
disyuntiva con consecuencias distintas sobre evidencia M1 cerrada (§4.2). **No
la resuelve el agente**: requiere decisión del dueño.

## 4. Riesgos

### 4.1 Reabrir M1 — `src/application/admit.py` · riesgo alto

Es la **única** modificación inevitable de código M1. El paquete §2.1 la acota
a configuración `audit_mode`, plan/promoción de garantías M2 y fórmula ⁄
topología, y prohíbe expresamente reabrir otras semánticas M1.

**Contención propuesta:** cambio aditivo, sin alterar rutas de rechazo, orden
de diagnósticos ni vocabulario M1; `audit_trail` permanece `unsupported`;
G-M2-14 exige regresión M0/M1 verde, `mypy --strict`, regeneración de vectores
con diff cero y fuzzers. Cualquier cambio de comportamiento observable en una
ruta M1 existente es señal de haber excedido el alcance.

### 4.2 Pérdida de evidencia M1 — retirada de la frontera instrumental · riesgo alto

`SpawnFrontier` y `SpawnFrontierCounter` fueron la compuerta D-P4-α que demostró
que M1 **no** creaba procesos. Retirarlos toca **cinco archivos**, tres de ellos
de pruebas M1: `src/ports/spawn_frontier.py`,
`src/adapters/spawn_frontier_counter.py`, `src/ports/__init__.py`,
`src/adapters/__init__.py`, `tests/unit/helpers_m1.py`,
`tests/adversarial/test_fuzz_admision.py` y
`tests/adversarial/test_policy_spawn_frontier.py` — este último con **20
pruebas**.

Retirar sin preservar convierte evidencia de cierre M1 en un hueco silencioso.
Recomendación: **aislar antes que retirar**, o migrar las pruebas al nuevo
`process_host` conservando su intención original. Decisión del dueño
(PENDIENTE-3).

### 4.3 Modificar wire contracts · riesgo controlado

Ninguna ruta propuesta entra en `contracts/`. `execution_result.py` y
`start_outcomes.py` **consumen** el vocabulario v1 congelado sin redefinirlo, y
D-M2-1(a) mantiene el wire `ExecutionResult v1` intacto enmendando sólo la API
local. G-M2-15 exige diff final sin schemas.

### 4.4 Absorber M3 · riesgo controlado

Ningún archivo propuesto crea `RuntimeEvent`, `AuditSink`, recibos, cadena ni
persistencia de evidencia. `config.py` sólo **reconoce** `audit_mode=required`
para rechazar la inicialización. Riesgo residual: `audit_mode=optional` evita
el bloqueo por durabilidad pero **no elimina la obligación del evento**; esa
deuda queda marcada pendiente M3 en G-M2-10, **no verde ficticio**.

### 4.5 Coupling con AEC · riesgo bajo

Ninguna ruta menciona AEC, perfiles ni Core común. El vocabulario propuesto es
el wire v1 de EKTEL, anterior a F0-A.

### 4.6 Ampliar la TCB · riesgo medio

`platform_caps.py` introduce `ctypes` para `prctl`, **única excepción parcial
permitida por ADR-006** al núcleo stdlib-only, ya declarada. `posix_supervisor.py`
añade un proceso supervisor por acción: amplía la superficie de fallo pero es
exactamente la topología que ADR-012 fija, elegida frente a la alternativa (b)
de threads en supervisor global precisamente por acotar el blast radius. No se
añade ninguna dependencia runtime nueva.

### 4.7 Introducir sandboxing · riesgo bajo

Ningún archivo propuesto aísla filesystem ni red. El grupo de procesos propio
es **contención de terminación, no aislamiento**: los escapes por `setsid`,
double-fork y D-state se **declaran** en G-M2-08, no se mitigan. El invariante
10 mantiene visible el TOCTOU de `command_absolute` (N1, N17).

## 5. Recomendación

**FIX-SCOPE-BEFORE-AUTHORIZATION.**

El alcance arquitectónico está completo y es implementable; la enumeración
técnica no encontró ningún vacío normativo que impida trabajar —no hay
`BLOCKED-BY-NORMATIVE-GAP`—. Pero **no** es `READY-FOR-HUMAN-AUTHORIZATION`
todavía, porque el acta debe resolver antes tres cosas que un agente no puede
decidir por su cuenta:

1. **PENDIENTE-3 · retirar o aislar la frontera instrumental.** Afecta 20
   pruebas adversariales que acreditan un claim de cierre M1. Es una decisión
   sobre evidencia ya firmada.
2. **Alcance exacto del cambio en `admit.py`.** El acta debería registrar que
   la modificación es aditiva y que cualquier cambio de comportamiento
   observable en una ruta M1 existente detiene el trabajo.
3. **Reconocimiento de PENDIENTE-1 y PENDIENTE-2** como puntos a resolver
   dentro de su incremento, con la condición de parada de PENDIENTE-1: si la
   implementación concluyera que debe emitirse `termination-token-payload`, se
   detiene y vuelve al dueño.

Resueltos esos tres puntos en el acta, el alcance queda listo para firma.

Esta recomendación **no es un PROCEED** y no autoriza código.

## 6. Fuentes

Especificación v1.2 (§8.0 handoff y autorización de `terminate`, §12
supervisión enmendada por ADR-012, §15 M2, §19.6) ·
`docs/adr/adr-011-handoff-admision-start.md` ·
`docs/adr/adr-012-supervision-local-m2.md` ·
`docs/propuestas/paquete-preparacion-m2-2026-08-28.md` (§2 alcance, §4
invariantes, §5 gates, §6 incrementos, §7 capas) · cierre de M1, M1-R1 y M1-R2
· inspección read-only de `src/`, `tests/`, `scripts/`, `mypy.ini` y
`contracts/schemas/v1/` al commit `8686fdc`.
