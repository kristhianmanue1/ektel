# BORRADOR — acta de autorización de M2 (supervisión)

> **ESTE DOCUMENTO NO ES UNA AUTORIZACIÓN.** Es un borrador redactado para
> revisión humana. No concede autoridad de construcción, no está firmado y no
> registra decisión alguna del dueño. Mientras no exista firma, la stop rule de
> ADR-012 §6 y del paquete de preparación M2 §9 permanece intacta y **no debe
> escribirse código M2**.

**Fecha de redacción:** 2026-09-09.
**Revisión:** 2 — incorpora la resolución humana de
`FIX-SCOPE-BEFORE-AUTHORIZATION` (2026-09-09).
**Estado:** borrador para revisión humana.
**Redacción:** asiento documental por agente, por instrucción de continuidad
del dueño (2026-09-09). El asiento transcribe y estructura; no crea ni amplía
autoridad.

## 0. Naturaleza del acto y qué falta para que exista

Conforme al criterio de adopción de la especificación v1.2 §19 punto 6, **cada
hito requiere su propia autorización**. M0 la obtuvo el 2026-08-20 y M1 el
2026-08-22; **M2 y M3 siguen sin autorizar**.

**Resuelto en la revisión 2.** La enumeración exacta de archivos, que la
revisión 1 dejaba abierta, está cerrada en §8.1 por referencia al documento de
alcance técnico, con inventario reconciliado y verificado. Las tres cuestiones
que motivaron `FIX-SCOPE-BEFORE-AUTHORIZATION` quedaron decididas por el dueño
el 2026-09-09 e incorporadas en §8.2 (`SpawnFrontier`: aislar, no retirar),
§8.3 (`admit.py`: aditivo, con regla `SCOPE VIOLATION`) y §8.4 (terminación
local y opaca, con condición de parada `BLOCKED-BY-NORMATIVE-GAP`).

Para que este borrador se convierta en acta vigente falta, como mínimo:

1. **decisión explícita del dueño** por canal, transcrita fielmente (patrón de
   `autorizacion-m1-2026-08-22.md`: orden + adendas, si las hubiera);
2. **asiento y firma** con fecha y referencia de canal.

Hasta entonces el estado correcto es: *M2 preparado, no autorizado*.

Las resoluciones de alcance del 2026-09-09 **no son autorización de
implementación**: fijan la frontera técnica revisable, no conceden autoridad de
construcción.

## 1. Objeto

Autorizar la implementación de **M2 (supervisión)** conforme a:

- la especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2,
  §12 mecánica de supervisión enmendada por ADR-012, §15 M2);
- **ADR-011** (handoff admisión → start), aceptada el 2026-08-28;
- **ADR-012** (contrato local y topología de supervisión M2), aceptada el
  2026-08-28, que resuelve D-M2-1(a), D-M2-2(a), D-M2-3, D-M2-4 y D-M2-5(a);
- el **paquete de preparación M2**
  (`docs/propuestas/paquete-preparacion-m2-2026-08-28.md`), del que se toman
  alcance, invariantes, gates y secuencia de incrementos;
- el estado **cerrado de M1**, incluidas M1-R1 y M1-R2
  (`cierre-m1-2026-08-22.md`, `cierre-m1-r1-2026-08-28.md`,
  `cierre-m1-r2-2026-08-28.md`).

Este acta **no introduce features nuevas**. Todo su contenido normativo deriva
de las fuentes anteriores.

### 1.1 Relación con la investigación AEC (F0-A)

La investigación Agent Execution Contract cerró F0-A el 2026-09-08 con
veredicto `F0-A-CLOSED`. **F0-B no pertenece al critical path de M2.** La
justificación es exclusivamente ésta:

> No existe actualmente una dependencia normativa demostrada entre F0-B y M2.

Este acta **no** afirma que `H-family` haya prevalecido. F0-A mantiene
`H-family` sólo como inclinación provisional y `H-profiles` como alternativa
abierta; esa decisión todavía no existe y no se anticipa aquí. F0-B tampoco se
cancela ni se declara innecesaria: conserva sus cuestiones (H-family vs
H-profiles, anti-trivialidad del núcleo, lifecycle mínimo común, binding entre
profile/admission/attempts/outcome) y requiere autorización humana propia.

## 2. Alcance autorizado

Dentro de M2, y sólo tras la firma de este acta:

1. tipo local `StartRequest` y **revalidación pura completa** según ADR-011;
2. plan de ejecución inmutable derivado de una **única instantánea validada**;
3. configuración local validada de capacidad, tiempos y `audit_mode` según
   D-M2-2/3/5;
4. actualización acotada de la ruta de admisión para declarar configuración y
   fórmula en `GuaranteePlan`, promover **sólo garantías M2 probadas** y
   conservar `audit_trail=unsupported`; toca M1 sin reabrir sus otros claims;
5. consumo y reconciliación de `start_token_consumption` **antes** del spawn;
6. supervisor POSIX separado por acción, grupo de procesos propio y handle
   local opaco;
7. `start` y `terminate` con outcomes wire v1 **ya congelados**, más el
   portador local de `await_result` decidido en D-M2-1(a);
8. reloj monotónico, cota absoluta `exp`, precedencia por causa y terminación
   graduada;
9. stdin acotado, stdout/stderr drenados continuamente, captura acotada y
   conteo de descarte;
10. recolección del proceso principal y de descendientes observados;
11. tabla honesta de garantías por Linux aarch64 y Darwin arm64;
12. tests unitarios, de integración, adversariales y de caracterización
    necesarios para los gates.

## 3. Fuera de alcance

M2 debe seguir siendo **la capa de supervisión prevista por la especificación
vigente**, no el runtime completo del ecosistema. Queda fuera, salvo
autorización normativa independiente:

**Diferido a M3:** `RuntimeEvent v1`, `AuditSink`, recibos de evento, cadena,
persistencia, retry y reconciliación de evidencia; cualquier activación
efectiva de `audit_mode=required`.

**Excluido de M0–M3:** cambios a schemas o vectores wire v1 (salvo nueva
autorización expresa tras incompatibilidad **demostrada**); identidad
byte-a-byte de `ActionRequest` o del binario; cierre del TOCTOU de
`command_absolute`; sandbox; aislamiento general de filesystem o de red;
sandboxing de kernel; multitenant; límites preventivos de CPU/RSS y
`budget_exceeded`; protección universal frente a `setsid`, double-fork,
D-state, muerte del supervisor o del administrador del host; x86_64, hardware
de producción no caracterizado y tests peligrosos (fork bomb, presión extrema);
CAGF dentro del núcleo; routing; memoria; plugins; delegación; orchestration
general; capability enforcement genérico; CI remoto, cambios de workflow, tag,
release o preparación de alfa.

**Excluido por frontera de ecosistema:** Agent Execution Contract universal e
integración específica con Ágora, Skopos o AN-KLA. La interoperabilidad se
obtiene por contratos y adaptadores externos, no acoplando el núcleo de M2.

**M4 / capability enforcement:** existe como hipótesis de investigación
**posterior a M3**, formulada como hipótesis nula —EKTEL no puede mediar
capabilities sobre efectos agénticos con garantías operacionalmente útiles sin
asumir responsabilidades de sandbox ni inflar su TCB hasta invalidar su diseño
de runtime mínimo—. Es un **Research Gate post-M3**. No se implementa ahora ni
se anticipa dentro de M2. La stop rule de la especificación §15 es explícita:
al cerrar M3 no se inicia M4 implícito (ADR-001).

## 4. Invariantes no negociables

Transcritos del paquete M2 §4. Una implementación que viole cualquiera de ellos
no es conforme:

1. Sólo un `StartRequest` **revalidado completamente** construye un plan
   inmutable.
2. La revalidación de `start` **no** llama `reserve_nonce`, **no** reevalúa
   `PolicyPort` y **no** emite otro token.
3. Ningún proceso se crea antes de un `ConsumeOutcome.CONSUMED`; valores
   desconocidos, excepciones y objetos truthy **no adquieren autoridad**.
4. La reconciliación CAS conserva exactamente ADR-011: `spent` y `unknown` son
   **indeterminados**; `unspent` permite otro CAS, nunca spawn directo.
5. Tras el CAS no existe dependencia externa entre consumo y spawn.
6. `now_wall < exp` es estricto en `start`; el skew de admisión no concede
   tiempo de ejecución.
7. El supervisor de acción drena ambos pipes aun después de truncar, transfiere
   buffers sin una segunda copia completa y acota su espera de EOF tras KILL.
8. El proceso ejecutado recibe sólo el entorno revalidado, cwd, argv e stdin
   autorizados; no hereda secretos ni descriptores ajenos.
9. `executed` significa **salida natural, no éxito**; la clasificación es por
   causa y **deadline gana en empate**.
10. El contenido en `command_absolute` continúa mutable entre validación y
    exec; N1 y N17 permanecen visibles.
11. Muerte del coordinador runtime o del supervisor de acción significa
    **ausencia honesta** según la fase; no se fabrica handle, resultado ni
    recuperación.
12. El núcleo M0–M3 sigue **stdlib-only**, con la excepción parcial y declarada
    de `ctypes` para `prctl` permitida por ADR-006; la API permanece
    experimental.

### 4.1 Preservación de `Indeterminate`

Cuando EKTEL no puede determinar un hecho, **la incertidumbre epistemológica se
conserva**. Un rechazo operacional fail-closed **no es prueba de failure**.

Con `policy_mode=required`, `PolicyPort → Indeterminate` produce rechazo de
admisión; ese rechazo es una decisión operacional, no una demostración de que
la acción habría fallado. La evidencia debe poder distinguir siempre tres
estados:

- sabemos que falló;
- sabemos que tuvo éxito;
- **no sabemos con suficiente certeza qué ocurrió**.

En M2 esta distinción se materializa, entre otros, en `spent`/`unknown` como
indeterminados de la reconciliación CAS (invariante 4),
`start_failed_indeterminate`, y la prohibición de fabricar tiempos o resultados
cuando la muestra final de reloj es inválida o regresiva (D-M2-3). **Ningún
`Indeterminate` puede convertirse en failure ni en success.**

### 4.2 Separación PDP / PEP

Se mantiene la separación ya establecida por ADR-008: el **Policy Decision
Point** decide política; el **Policy Enforcement Point** la aplica. EKTEL no
absorbe lógica de gobernanza de negocio en su núcleo. `PolicyPort` sigue siendo
la frontera correcta; CAGF u otros motores de gobernanza pueden ser
implementaciones **externas** del puerto, nunca dependencias internas del
runtime.

### 4.3 Evolución monotónica de M1 a M2

M2 debe constituir una **extensión monotónica** de las garantías cerradas en M1,
salvo que una decisión explícita autorice reabrir alguna de ellas.

**Agregar funcionalidad M2 no concede autoridad para invalidar evidencia M1.**
Este principio gobierna §8.2 (la frontera instrumental se preserva), §8.3 (la
modificación de `admit.py` es aditiva, con regla `SCOPE VIOLATION`) y el
tratamiento de las pruebas M1 existentes, que deben seguir pasando sin
modificación.

### 4.4 Las garantías declaran su fuerza

No se presenta una observación best-effort como límite duro. Cada garantía
declara explícitamente qué mecanismo la produce, sobre qué plataforma, qué
fuerza tiene, qué puede observar, qué **no** puede garantizar y qué failure
modes permanecen posibles.

Queda prohibido el lenguaje equivalente a «seguro», «aislado», «auditoría
completa» o «límite duro» cuando la evidencia disponible no lo demuestre. En
particular: el rango de `max_concurrent_actions` es **cota de capacidad, no
garantía de RSS baja**; el perfil de despliegue debe publicar ambos límites y
la caracterización de RSS.

## 5. Incrementos

Secuencia del paquete M2 §6. Los dos primeros ya están **completados** y
consumidos; se listan como antecedente, no como trabajo pendiente:

| Inc | Contenido | Estado |
|---|---|---|
| PRE-M2-R2 | corregir `failure_mode`, validación wire de `GuaranteePlan`, cerrar M1-R2 | **completado** (2026-08-28) |
| PRE-M2-ADR | aceptar D-M2-1..5, redactar ADR-012 y enmiendas normativas | **completado** (2026-08-28) |
| **INC-M2-1** | tipos locales, configuración validada y revalidación pura de `StartRequest`; proceso host falso, **cero spawn real** | pendiente |
| **INC-M2-2** | CAS, reconciliación, capacidad y handle/termination token con dobles deterministas | pendiente |
| **INC-M2-3** | supervisor POSIX real, IPC, grupo, stdin y salida acotada | pendiente |
| **INC-M2-4** | deadline, TERM→KILL, terminate/await y carreras | pendiente |
| **INC-M2-5** | caracterización por plataforma, suite integral, claims, manifest y cierre administrativo | pendiente |

**Cada incremento requiere tests locales y revisión adversarial sobre su propio
diff.** Un `PROCEED` de preparación o de un incremento anterior **no cubre el
diff final**.

## 6. Gates ejecutables G-M2-01..15

Transcritos del paquete M2 §5. Cada gate se acredita con la prueba mínima que
debe **falsificar** la promesa correspondiente.

| Gate | Prueba mínima |
|---|---|
| **G-M2-01** revalidación/configuración | Token/request malformados, MAC rota, campos cruzados, request ejecutable distinto, tipos hostiles, request >64 KiB y expiración: **cero CAS y cero procesos**. Matriz separada rechaza `bool`, floats, rangos/tipos inválidos de toda configuración y demuestra que `audit_mode=required` impide inicializar antes de solicitudes. |
| **G-M2-02** pureza | Spy demuestra cero `reserve_nonce`, cero `PolicyPort.evaluate` y cero emisión de token durante `start`. |
| **G-M2-03** linealización | Instrumentación prueba **reloj final → CAS → spawn**; sólo `CONSUMED` cruza. No hay dependencia inyectable entre CAS y spawn. |
| **G-M2-04** reconciliación | `ALREADY_SPENT`, `UNAVAILABLE`, excepción y tipo desconocido, combinados con status `spent/unspent/unknown`, producen exactamente los outcomes de ADR-011. |
| **G-M2-05** concurrencia/reinicio | Varios procesos compiten con el mismo token contra el store real: un solo CAS ganador; reinicio conserva `spent`; **nunca doble spawn**. |
| **G-M2-06** crash | Inyección antes/después de persistir CAS y alrededor de spawn: token gastado nunca se reabre y **no se inventa handle**. |
| **G-M2-07** salida | Flood independiente de stdout/stderr, límites 0/máximo y multibyte, coordinador lento/caído: prefijo exacto, flags y contadores correctos; frames ≤64 KiB, máximo uno no confirmado por stream, cota estable y pico de materialización bajo ambas fórmulas D-M2-1. Expiración del drenaje fija `post_kill_forced_pipe_close=1`. **RSS queda caracterizado, no declarado exacto.** |
| **G-M2-08** no-hang | Procesos que no leen stdin, ignoran TERM, mantienen pipes en descendientes, inundan salida o escapan con `setsid`: **toda prueba acotada termina**; escapes quedan declarados. |
| **G-M2-09** deadline | Relojes falsos ejercen duración, `exp`, gracia ≥ vida útil, plazo efectivo cero, muestra final inválida/regresiva, empate duración/vigencia y empate con terminate; clasificación determinista **sin afirmar detección de saltos entre muestras**. Recolección del principal fija tiempos; drenaje post-KILL sólo extiende la latencia de entrega dentro de su cota. |
| **G-M2-10** terminación | Handle válido/forjado/cruzado, repetición con el mismo objeto, solicitud post-resultado, destrucción del handle, reinicio del coordinador, pérdida del supervisor de acción y carrera con deadline respetan D-M2-4 y el vocabulario v1. **El evento de rechazo queda marcado pendiente M3, no verde ficticio.** |
| **G-M2-11** recolección/plan | Proceso principal y descendientes observados se recogen; `GuaranteePlan` declara configuración/fórmula/topología y `guarantees_applied` los valores efectivos; Linux declara el uso real de subreaper y Darwin multi-nivel `unsupported`. |
| **G-M2-12** capacidad | Carreras sobre `max_concurrent_actions` nunca exceden la cota ni gastan tokens por falta de slot; el handoff terminal libera el slot, un handle abandonado no deja registro global y un handle retenido conserva su propia memoria. Tests con límites máximos confirman **8 GiB + 8 MiB estables y pico de 16 GiB + 8 MiB** de payload para 64 acciones, más overhead y **sin claim exacto de RSS**. |
| **G-M2-13** plataforma | Suite completa **separada** en Darwin arm64 y Linux aarch64 pineado; skips y degradaciones explícitos, **nunca convertidos en verde equivalente**. |
| **G-M2-14** regresión | M1-R2 cerrado con `GuaranteePlan` válido contra schema; todos los gates M0/M1, `mypy --strict`, regeneración diff-cero y fuzzers permanecen verdes. |
| **G-M2-15** frontera | Diff final **sin** schemas, workflows, dependencias runtime, M3, x86_64, tag ni release; revisión adversarial fresca `PROCEED`. |

## 7. Plataformas

- **Linux aarch64** en contenedor, **imagen fijada por digest** — clase V.
- **Darwin arm64** — clase L.

Ambas se prueban **por separado** (G-M2-13); un skip o una degradación no se
convierte en verde equivalente. Es el mismo perfil de dos plataformas con el
que se cerró M1.

**x86_64 real permanece fuera**: es puerta de **pre-producción** (ADR-006/N12),
no puerta de M1–M3. Rosetta no es sustituto válido para la caracterización de
`RLIMIT_AS`.

## 8. Capas que la implementación puede tocar

| Capa | Alcance permitido |
|---|---|
| `src/domain/` | tipos locales de start/handle/terminación/salida y máquina de estados pura; **sin eventos M3**. |
| `src/application/` | `AdmissionService` sólo para configuración `audit_mode`, plan/promoción de garantías M2 y fórmula/topología; orquestación `start`, `terminate`, `await_result`, slots y orden ADR-011. **No reabre otras semánticas M1.** |
| `src/ports/` | puerto de proceso/IPC estrictamente local, **en paralelo** a la frontera instrumental M1, que se preserva intacta (§8.2). **No AuditSink sustituto.** |
| `src/adapters/` | supervisor POSIX por acción y helpers de plataforma; el adaptador instrumental M1 se **preserva intacto** (§8.2). |
| `tests/{unit,integration,adversarial,escape}/` | G-M2-01..15; procesos siempre acotados, identificables y recogidos. |
| `scripts/`, `docs/evidencia/` | runner local reproducible, manifests y caracterización saneada; **sin secretos ni salida bruta sensible**. |

### 8.1 Enumeración exacta de archivos

El hueco que este borrador dejaba abierto queda **resuelto**. La enumeración
concreta y revisable vive en
`docs/propuestas/alcance-tecnico-m2-2026-09-09.md` (revisión 2), que forma
parte de este acta por referencia:

- **45 rutas inventariadas**: 32 nuevas propuestas y 13 existentes;
- **38** modificables o nuevas — el alcance real de M2;
- **5** preservadas, **no modificables** (§8.2);
- **2** consumidas sin cambios (`replay_store` puerto y adaptador: las
  primitivas CAS que M2 necesita ya existen y M1 las ejercitó).

Cada ruta aparece exactamente una vez, con capa, motivo, incremento
`INC-M2-1..5`, gates asociados, si toca M1 y riesgo.

### 8.2 `SpawnFrontier` — aislar, no retirar

**Decisión del dueño (2026-09-09): AISLAR, NO RETIRAR.** Durante M2 no se
retira `SpawnFrontier` ni se elimina la evidencia M1 asociada. La frontera M2 se
implementa **en paralelo** mediante `src/ports/process_host.py`.

Motivo: forma parte de la evidencia existente de M1; hay pruebas adversariales
que acreditan claims ya cerrados; eliminarla dentro de M2 produciría
**discontinuidad de evidencia**; **M2 debe ser extensión del runtime, no
reescritura retroactiva de M1**.

Quedan **intactas** y deben seguir pasando sin modificación:
`src/ports/spawn_frontier.py`, `src/adapters/spawn_frontier_counter.py`,
`tests/unit/helpers_m1.py`, `tests/adversarial/test_fuzz_admision.py` y
`tests/adversarial/test_policy_spawn_frontier.py` — este último con **20
pruebas** que acreditan que M1 no crea procesos.

`src/ports/__init__.py` y `src/adapters/__init__.py` se tocan **sólo para
añadir** los símbolos M2; retirar un símbolo M1 de sus re-exports es
`SCOPE VIOLATION` (§8.3).

Una eliminación futura de `SpawnFrontier` exigirá evidencia sustitutiva
equivalente o superior, demostración de que los claims M1 siguen válidos y
decisión documental independiente. **Esa migración no ocurre dentro de M2.**

### 8.3 `admit.py` — extensión aditiva y regla SCOPE VIOLATION

Es la **única** modificación de código M1 autorizada, y **sólo** para
transportar o declarar información que exigen los contratos M2 ya adoptados:
configuración `audit_mode`; entradas ASCII `clave=valor` congeladas por D-M2-3
en `GuaranteePlan.mechanism`/`assumptions`; promoción de garantías M2 probadas;
`audit_trail=unsupported` conservado.

**M2 no debe alterar el comportamiento observable previamente validado de la
ruta M1.** Se preservan: semántica existente · decisiones de admisión M1 ·
diagnósticos y su orden · comportamiento fail-closed · `PolicyPort` ·
contratos wire · regresión M1 completa.

**Regla de parada.** Si una prueba M1 existente cambia de resultado, se trata
**inicialmente como `SCOPE VIOLATION`** y se **detiene ese incremento** hasta
demostrar documentalmente que el cambio estaba autorizado. **Prohibido
reinterpretar una regresión como adaptación implícita de M1 a M2.**

### 8.4 Terminación — local y opaca

El mecanismo de terminación permanece dentro del contrato local ya previsto:
handle/capability local conforme a ADR-012, receipt opaco, local, no durable y
sin MAC, con `capability_rejected` como único reason code de rechazo.

**Prohibido crear:** nuevo wire schema · `termination-token-payload` firmado ·
nuevo envelope · protocolo remoto · capability distribuida · mecanismo
cross-host. El schema `termination-token-payload` permanece congelado **sin capa
productora**, exactamente igual que hoy.

**Condición de parada:** si durante INC-M2-2 se demuestra que M2 requiere
necesariamente un nuevo payload wire o modificar contratos congelados,
**DETENER EL INCREMENTO**, declarar `BLOCKED-BY-NORMATIVE-GAP` y volver al dueño
con evidencia. **No inventar el contrato durante la implementación.**

### 8.5 Ubicación de la revalidación

**La decisión de archivo concreto pertenece al desarrollador. La semántica no.**
Puede resolverse durante el incremento respetando arquitectura hexagonal,
dominio sin dependencia de adaptadores, la pureza exigida por los gates, y
**cero** llamadas nuevas a `PolicyPort`, **cero** `reserve_nonce` y **cero**
emisión de token nuevo. Si resolver la ubicación exigiese cambiar alguna
semántica normativa: **detener y escalar.**

## 9. Definition of Done y evidencia requerida

**Criterio de salida M2** (paquete §5): todos los gates G-M2-01..15 verdes;
ninguna prueba acotada cuelga; manifest saneado y reproducible.

**Promoción de claims:** `C2-handoff`, `C3`, `C4` y la parte de inicio de `C6`
se promueven **sólo con prueba citada**. `C5`, `C7` y `audit_trail` permanecen
**P (pendientes) hasta M3**. M2 no puede reclamar conformidad completa de
trazabilidad: `audit_mode=optional` evita el bloqueo por durabilidad pero **no
elimina la obligación del evento**, incluido el `capability_rejected` de un
`terminate` inválido.

**Evidencia exigida antes del cierre:**

1. los quince gates acreditados con prueba citada, no con afirmación;
2. pruebas ejecutadas y registradas **por plataforma** (Darwin arm64 y Linux
   aarch64 pineado por digest), con skips y degradaciones explícitos;
3. **regresión completa de M1** verde, incluida M1-R2, `mypy --strict`,
   regeneración de vectores con diff cero y fuzzers;
4. caracterización de RSS y de las cotas de capacidad publicada como
   caracterización, no como garantía exacta;
5. evidencia **reproducible** con manifest saneado;
6. **revisión adversarial externa sobre el código real**;
7. resolución explícita de todos los findings;
8. acta de cierre.

### 9.1 La revisión de diseño no aprueba el código

ADR-012 §5 lo dice expresamente: **«un `PROCEED` documental no cubre ese futuro
diff»**. Queda explícitamente rechazado como razonamiento de cierre:

> «El diseño ya recibió PROCEED, por tanto el código está aprobado.»

Eso es **inválido**. El diff real de M2 debe ganar su propia evidencia.

## 10. Límites de autoridad

**Autorizado** (sólo tras firma):

- registrar el acto de autorización M2 con las condiciones de este documento;
- implementar únicamente M2 en las capas enumeradas en §8;
- pruebas unit/integration/adversarial/escape, fuzz y scripts necesarios;
- CI **local** y configuración de desarrollo necesarias para `mypy --strict`;
- documentación de implementación, rondas de revisión y cierre M2;
- commits locales por avance y cierre.

**No autorizado:**

- **push, PR, tag, release** y preparación de alfa (la orden del dueño del
  2026-08-22 difiere toda publicación hasta el cierre de M3);
- **M3**: `RuntimeEvent`/`AuditSink` durable, recibos, cadena, persistencia;
- activar `audit_mode=required`;
- cambios a schemas o vectores wire v1, workflows o CI remoto;
- dependencias runtime nuevas (M0–M3 permanece stdlib-only, salvo `ctypes`
  para `prctl` por ADR-006);
- x86_64, crash-consistency de dispositivo o RSS por muestreo como claim;
- ampliar el modelo de amenaza;
- cambios normativos silenciosos en spec, ADR o wire contracts;
- usar memoria o relaciones del ecosistema como autoridad.

## 11. Stop rule

Vigente hasta que exista firma, y de nuevo al cerrar M2:

- no implementar M2, no crear procesos ni fronteras IPC, no iniciar M3, no
  cambiar schemas ni workflows, no activar GitHub Actions, no preparar
  tag/alfa/release y no ampliar el modelo de amenaza;
- **al cerrar M3 no se inicia M4 implícito** (ADR-001, especificación §15);
- M4 / capability enforcement es Research Gate post-M3 y requiere su propio
  acto.

## 12. Condiciones de cierre de M2

M2 se declara cerrado únicamente cuando concurren:

1. gates G-M2-01..15 verdes con evidencia citada;
2. suites por plataforma ejecutadas y registradas por separado;
3. regresión M0/M1 completa verde;
4. revisión adversarial externa **sobre el código real** con `PROCEED`;
5. findings resueltos explícitamente, cada uno con su corrección o su refutación
   registrada;
6. manifest de evidencia reproducible y saneado;
7. **acta de cierre** propia, con actualización de
   `docs/gobernanza/INDEX.md` y del estado §19.6 de la especificación.

El cierre de M2 **no** abre por sí mismo un ciclo de publicación ni autoriza
M3: cada hito requiere su propio acto.

## 13. Secuencia posterior prevista

```text
M2 authorization → M2 implementation → M2 code-level adversarial review
  → M2 closure → M3 → cierre del runtime mínimo
  → Research Gate M4 (capability enforcement)
```

Desacoplado y en paralelo, **sin bloquear M2**: Execution Boundary Contract
mínimo → profiles/adapters → Ágora, Skopos, AN-KLA, cada consumidor con puerto
propio y adaptador sustituible (anti-corruption layer), de modo que su dominio
no se acople a las clases internas de EKTEL. F0-B queda fuera del critical path
y requiere autorización propia.

## 14. Firma y asiento

- **Decisión del dueño:** *pendiente* — sin firma, este documento no es acta.
- **Transcripción de canal:** *pendiente*.
- **Resoluciones de alcance:** dueño, por canal (2026-09-09) — `SpawnFrontier`
  aislar y no retirar; `admit.py` aditivo con regla `SCOPE VIOLATION`;
  terminación local y opaca con condición de parada. **Fijan frontera técnica;
  no conceden autoridad de construcción.**
- **Asiento documental:** borrador redactado el 2026-09-09 por instrucción de
  continuidad del dueño; revisión 2 el mismo día. El asiento no crea ni amplía
  autoridad.

## 15. Evidencia de soporte

- Paquete de preparación M2:
  `docs/propuestas/paquete-preparacion-m2-2026-08-28.md`.
- ADR-011: `docs/adr/adr-011-handoff-admision-start.md` (aceptada,
  `docs/decisiones/aceptacion-adr-011-handoff-2026-08-28.md`).
- ADR-012: `docs/adr/adr-012-supervision-local-m2.md` (aceptada,
  `docs/decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md`;
  revisión adversarial `docs/revisiones/revision-adversarial-adr-012-2026-08-28.md`).
- Especificación v1.2: §12 (supervisión, enmendada por ADR-012), §15 (M2),
  §19 punto 6 (autorización separada por hito).
- Cierre de M1: `docs/decisiones/cierre-m1-2026-08-22.md`,
  `cierre-m1-r1-2026-08-28.md`, `cierre-m1-r2-2026-08-28.md`.
- Patrón documental: `docs/decisiones/autorizacion-m1-2026-08-22.md`.
- Alcance técnico §8 (inventario de 45 rutas, revisión 2):
  `docs/propuestas/alcance-tecnico-m2-2026-09-09.md`.
- Contexto AEC (no dependencia normativa):
  `docs/propuestas/aec-fase-0/f0-a/f0-a-verdict.md`.
