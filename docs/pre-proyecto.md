# ektel — documento de pre-proyecto

**Estado:** pre-proyecto, revisado adversarialmente (1 ronda, 14 hallazgos,
todos aplicados tras verificación contra la investigación de base). Objetivos
y especificaciones antes de la primera línea de código. Este documento no es
evidencia verificada de nada que exista: describe lo que se va a construir y
por qué, con las decisiones tomadas y las que quedan abiertas.

**Fecha:** 2026-08-14 · **Base:** investigación de estado del arte en tres
frentes (aislamiento y límites de recursos, autorización expirable y
delegable, runtimes de agentes y patrones de control), con fuentes citadas en
cada sección.

## 1. Qué es ektel

El runtime de ejecución: el componente que corre acciones —incluidas acciones
de agentes de IA— bajo **compuertas mecánicas, no bajo confianza declarativa**.

Un runtime necesita imponer, en el momento de la ejecución —no antes, no
después— tres cosas:

- **(a) Presupuesto acotado** — CPU, memoria, tiempo, tokens, costo; por
  acción o por tarea.
- **(b) Capacidad expirable** — la autorización para actuar tiene ventana de
  validez y profundidad de delegación, validada en el punto de entrada.
- **(c) Plazo de resolución** — toda acción termina, ejecutada o descartada,
  dentro de un tiempo declarado. Nada queda en el aire indefinidamente.

**Precisión de alcance (añadida en ronda adversarial):** no toda magnitud de
(a) es imponible sin cooperación en todo despliegue. CPU, memoria y tiempo de
pared los impone el OS sobre **cualquier** comando. Tokens y costo sólo son
gobernables cuando la llamada al modelo **pasa por una frontera del runtime**
—lo que exige que ninguna credencial del proveedor entre al perímetro de
ejecución—, condición que el Nivel 0 no impone mecánicamente (§5.1, §7). Lo
que sí es imponible siempre: (b) y (c), y la parte de (a) que el OS ve.

Todo lo demás —qué puede hacer una acción, con qué evidencia se acepta su
resultado— es gobernanza de negocio y **no es de ektel**.

## 2. Principio de independencia

ektel nace dentro del ecosistema Aria pero **no es un componente de Aria**. Es
una herramienta independiente, útil para cualquiera que necesite ejecutar
trabajo potencialmente no confiable bajo límites duros. Consecuencias de
diseño, no aspiracionales:

1. **El núcleo no importa nada de Aria.** Ni task-cards de Epistates, ni
   manifiestos de Pinax, ni contratos de Praxis. La entrada del núcleo es un
   *descriptor de acción* propio de ektel (§5.2), genérico.
2. **La relación con Aria es por adaptador.** Consumir `task-card/v1` de
   Epistates será un adaptador opcional que traduce task-card → descriptor de
   acción. ektel funciona igual sin él; el adaptador es quien depende, nunca
   el núcleo. Misma regla de dependencia unidireccional que usa Pinax.
3. **Sin infraestructura obligatoria.** El MVP corre como proceso único local,
   sin red, sin servidor de autorización, sin base de datos. Quien lo adopte
   fuera de Aria no hereda nada del ecosistema. Única excepción declarada: una
   librería criptográfica auditada para Ed25519 (§4, O2) — la stdlib de Python
   no ofrece firmas de clave pública.
4. **Los límites se declaran en el propio proyecto** (§7), no por referencia a
   otros documentos del ecosistema.

El criterio de independencia es mecánico y comprobable en CI: **el núcleo no
importa nada fuera de la stdlib de Python (excepción: la librería
criptográfica declarada) ni referencia ningún identificador de Aria**
(nombres de proyecto, rutas, contratos). El ejemplo fuera-de-ecosistema de
O5 es una demostración de uso, no la prueba de ausencia de acoplamiento.

## 3. Decisiones de diseño que la evidencia respalda

La investigación previa (fuentes en §9) converge en tres decisiones que
estructuran todo lo demás:

**D1. El reloj y el freno viven fuera del código gobernado.**
Casi todos los controles que traen los frameworks de agentes (OpenAI Agents
SDK `max_turns`, LangGraph `recursion_limit`, CrewAI `max_iter`) son contadores
que lanzan una excepción *dentro* del proceso gobernado: se resetean por
invocación, dependen de un llamador vivo, y no cubren los caminos de
retroalimentación entre invocaciones. El paper "When Agents Do Not Stop"
(arXiv 2607.01641) documenta 68 fallos reales de bucles infinitos en 47
proyectos **cuyos frameworks ofrecían esos mecanismos** — la causa dominante
no es que el mecanismo falle, sino que los desarrolladores lo omiten, lo
malconfiguran o lo colocan fuera del camino de retroalimentación real (un
tope interno de un sub-agente no cubre el ciclo externo). La excepción
estructural es Temporal: los timers los mantiene el servidor, no el código de
la actividad, y disparan aunque el worker muera. ektel hereda esa separación
de autoridad: el supervisor posee reloj, presupuesto y terminación; el
ejecutado no puede influir en sus propios límites.

**D2. Toda acción cara pasa por una frontera con identidad, validada
pre-vuelo.**
El metering de la industria (LiteLLM, Helicone, OpenRouter) es post-facto:
el costo exacto se conoce cuando la respuesta vuelve. Lo preventivo real es
rechazo en la frontera de la *siguiente* llamada — OpenRouter llega al chequeo
de affordability pre-vuelo contra el `max_tokens` **declarado** del request.
Consecuencia: el presupuesto de tokens/costo se implementa como *reserva
antes de ejecutar, liberación después* (reserve/commit), con contabilidad
hecha por el runtime, nunca reportada por el agente, y con el alcance
limitado que declara §1: sólo lo que cruza la frontera.

**D3. Los límites cubren el camino de retroalimentación completo, no la
invocación individual.**
Un tope por invocación no domina reintentos, delegación ni ciclos
multi-agente. Las compuertas de ektel se definen sobre la **acción completa**
—con su árbol de sub-acciones delegadas— y la profundidad de delegación es
parte del formato de capacidad (§5.3), no de la política.

Y una asimetría que se declara, no se promete: **no existe freno no
cooperativo con limpieza garantizada.** Cancelar (SIGTERM, cancel de
Temporal) es cooperativo; terminar (SIGKILL, terminate de Temporal) es
mecánico pero no corre limpieza. Por tanto el descriptor de acción exige
declarar **cómo se repara el estado externo** (idempotente | compensación |
irreversible-declarada). Precisión importante: ektel exige la *presencia* del
campo y valida su forma; su **veracidad** es responsabilidad de quien despacha
la acción —"idempotente" es una autoatastación que ektel no puede comprobar.
Es la misma asimetría que Pinax declara para los manifiestos: validar forma,
nunca verdad.

## 4. Objetivos

**Estados terminales canónicos** (lista única, referenciada por O1 y O4):
`executed` · `budget_exceeded` · `capability_rejected` · `deadline_exceeded`
(el plazo venció; incluye la terminación forzosa del proceso como su mecanismo)
· `terminated` (parada externa vía la interfaz de terminación, sin plazo
vencido). Toda acción termina en exactamente uno.

**O1 — MVP local verificable.** Un ejecutor de proceso único, multiplataforma
(macOS y Linux), sin root, escrito en Python sobre su stdlib —con la excepción
declarada de O2—, que ejecute una acción real bajo las tres compuertas activas
simultáneamente. Criterio: una acción que excede presupuesto, una con
capacidad expirada y una que excede su plazo terminan en los estados
terminales correspondientes de la lista canónica, nunca en un hang. (La
decisión de lenguaje queda **cerrada** para el MVP: Python. Si el Nivel 1
exige bindings que Python no tenga, se reevalúa entonces, con decisión
registrada.)

**O2 — Capacidades con profundidad de delegación acotada.** Formato de token
propio, minimalista: cadena de bloques firmados Ed25519 (modelo Biscuit),
ventana temporal efectiva como intersección de la cadena (modelo UCAN/zCAP),
campo `depth` explícito y decreciente (que **ningún** formato existente trae
de serie), e invocación firmada por el portador (proof-of-possession:
un token robado no es ejecutable sin la clave). Verificación **completamente
offline y local en el MVP**; la ruta de revocación distribuida (§5.3)
reintroduce estado compartido y conectividad con comportamiento fail-closed,
y se declara así. Dependencia criptográfica: una librería Ed25519 auditada
(`cryptography` o PyNaCl; elección concreta al implementar) — la única fuera
de la stdlib, y la más sensible del proyecto; implementar las firmas a mano
está descartado.

**O3 — Aislamiento honesto por niveles.** Nivel 0 (stdlib, sin root) activo
desde el MVP, documentado como *contención de accidentes, no de adversarios*.
Niveles superiores (§6) como ruta declarada, no como promesa implícita.

**O4 — Resultado siempre terminal y tipado.** Toda acción termina en un
estado de la lista canónica. El patrón de referencia es el error tipado
`execution_time_exceeded` documentado por Anthropic: un estado, no un cuelgue.
Con la acotación de §5.4: la garantía cubre el proceso raíz y su grupo, no
sesiones que hayan escapado con `setsid` ni procesos bloqueados en D-state.

**O5 — Utilidad fuera de Aria demostrada.** El MVP incluye un ejemplo que
ejecuta una acción sin relación con el ecosistema (un script arbitrario con
presupuesto, capacidad y plazo), como demostración de uso del §2.

### No-objetivos (explícitos)

- **No es el mecanismo de parada completo.** Alojar la recepción de señales
  de parada en un proceso independiente corresponde a un gateway de ingreso
  separado (en Aria: propylon). ektel expone la *interfaz* de terminación;
  la vía de interrupción fuera de proceso es composición del despliegue, no
  parte del núcleo. Recibir una señal no es tener potestad de detener: eso
  exige además independencia energética del dominio gobernado.
- **No es gobernanza de negocio.** Qué está permitido lo declara quien emite
  la capacidad; qué evidencia acepta un resultado lo declara quien despacha.
- **No es orquestación.** No selecciona objetivos, tareas ni prioridades;
  ejecuta lo que recibe, bajo las tres compuertas.
- **No es un sandbox de seguridad fuerte en el MVP.** El Nivel 0 contiene
  accidentes. El aislamiento de adversarios es Nivel 1+ y se dice así.
- **No gestiona secretos.** Regla sacada de los incidentes documentados:
  las credenciales nunca entran al perímetro de ejecución; si una acción
  necesita un recurso autenticado, lo media un proxy externo al perímetro
  (patrón Anthropic/Claude Code). En Nivel 0 esta regla es **contrato del
  despliegue, no mecanismo** — nada impide mecánicamente que un comando
  arbitrario traiga su propia credencial (ver §7).

## 5. Especificaciones

### 5.1 Compuerta (a) — presupuesto acotado

- El presupuesto se declara en el descriptor de acción: `max_cpu_seconds`,
  `max_memory_bytes`, `max_wall_seconds` (redundante con (c),
  deliberadamente), `max_tokens`, `max_cost_units`, `max_iterations`.
- **Imposición mecánica, lo que el OS ve:** `RLIMIT_CPU` para CPU,
  `RLIMIT_AS` para memoria (con el matiz declarado: limita memoria *virtual*,
  no RSS — un límite bajo rompe procesos sanos y uno alto no frena al
  atacante), timeout de pared con `killpg`. Esto aplica a **cualquier**
  comando.
- **Gobernanza en frontera, lo que el OS no ve:** tokens y costo. La llamada
  al modelo pasa por una **frontera del runtime** que hace chequeo pre-vuelo
  contra el máximo declarado (patrón OpenRouter) y reserva/commit de
  presupuesto. Alcance declarado: sólo las llamadas que cruzan la frontera;
  una acción con credencial propia gasta invisible para ektel (§1, §7).
- **Sobregiro:** acotado a las llamadas concurrentes en vuelo (N, no 1, si hay
  concurrencia), y **condicionado a que el enforcement de la frontera
  funcione** — es software con bugs, como demuestra litellm#26672.
- La contabilidad la hace el runtime desde las respuestas del proveedor;
  ningún número reportado por el agente alimenta una compuerta.
- Los contadores son por acción completa (con sus sub-acciones delegadas),
  no por invocación (D3).

### 5.2 Descriptor de acción (la entrada del núcleo)

Documento autocontenido (JSON o YAML plano) con: comando/entrypoint,
argumentos, presupuesto (a), referencia a la capacidad (b), plazo (c),
política de reparación del estado externo (idempotente | compensación |
irreversible-declarada). El último campo es obligatorio en forma; su veracidad
la garantiza quien despacha, no ektel (§3). Es el único formato que el núcleo
entiende. Los adaptadores (task-card de Epistates, CLI, otros) traducen a él.

### 5.3 Compuerta (b) — capacidad expirable y delegable

Formato: `Token := Bloque⁰ (raíz) · Bloque¹…ⁿ (delegaciones)`.

- **Bloque:** `{ versión, acciones permitidas (lista o prefijo jerárquico),
  prefijo de recurso, nbf, exp, depth restante, clave pública del siguiente,
  nonce }`, firmado con la clave efímera cuya pública va embebida en el bloque
  anterior. La raíz se firma con la clave Ed25519 del emisor.
- **Validación en el punto de entrada**, en orden, todo local y determinista:
  estructura → cadena de firmas → ventana temporal (intersección:
  `exp = min`, `nbf = max` de la cadena; tolerancia de reloj ±60 s) →
  `depth > 0` para delegar, `≥ 0` para ejecutar → monotonía (cada bloque ⊆
  padre) → denylist local → sólo entonces compuertas (a) y (c).
  Rechazo = descarte con causa tipificada.
- **Invocación firmada:** la acción se presenta con firma del portador actual
  sobre (comando, argumentos, nonce de invocación).
- **Denylist como interfaz:** tabla en memoria en el MVP; sustituible por un
  feed distribuido sin cambiar el formato (patrón validado en producción por
  Fly.io), con el costo declarado: la revocación distribuida destruye la
  verificación offline pura y exige comportamiento fail-closed al perder
  contacto (Fly.io invalida toda su caché). La expiración corta es el
  mecanismo primario; la revocación es kill-switch operativo con costo de
  estado explícito.
- **Límite estructural declarado:** ningún formato da confinamiento —un
  delegante no puede conocer todas las sub-delegaciones existentes (UCAN lo
  admite, Fly.io lo demuestra)—. La mitigación es la tríada expiración corta
  + profundidad acotada + proof-of-possession, no la revocación.
- **Fuera del MVP:** Datalog (Biscuit completo), JSON-LD (zCAP-LD),
  DAG-CBOR/DIDs (UCAN completo). Ed25519 + SHA-256 + serialización
  determinista bastan; las restricciones son campos tipados comparables
  mecánicamente.

### 5.4 Compuerta (c) — plazo de resolución

- Todo descriptor declara `deadline_seconds`. Sin plazo declarado no hay
  ejecución —deny-by-default, igual que sin capacidad.
- El timer vive en el supervisor, no en el ejecutado (D1). Al vencer:
  cancelación cooperativa breve (grace configurable, por defecto corto) y
  **terminación forzosa como backstop** (`killpg` con `SIGKILL` al grupo de
  proceso). La dualidad cancel/terminate es la de Temporal, traducida a
  procesos POSIX.
- **Alcance de la garantía de terminación (declarado):** cubre el proceso
  raíz y su grupo de proceso. Un ejecutado que haga double-fork + `setsid`
  escapa al grupo y sobrevive al `SIGKILL`; un proceso en D-state
  (syscall de kernel ininterrumpible) no muere hasta retornar de la syscall.
  Ambos casos son límites de §7.
- Las pausas para aprobación humana —si alguna vez entran— llevan su propio
  plazo: el hueco documentado de LangGraph (interrupts que esperan
  indefinidamente) no se reproduce aquí.

### 5.5 Supervisión y vía de interrupción

- El supervisor es un proceso distinto del ejecutado (D1). Un watchdog del
  supervisor mismo (dead man's switch: el silencio es señal) es nivel de
  despliegue, no de núcleo.
- `terminate` no corre limpieza (asimetría estructural, §3): el descriptor
  declara cómo se repara el estado externo (idempotencia o compensación),
  bajo la asimetría forma/verdad de §3.
- Todo evento de compuerta (admisión, rechazo, consumo, terminación) se
  registra en un log append-only del supervisor — la auditabilidad es
  consecuencia del rechazo tipificado, no un subsistema aparte.

## 6. Niveles de aislamiento (ruta declarada)

Cada nivel es funcionalmente completo —las tres compuertas activas— antes de
subir al siguiente.

| Nivel | Mecanismo | Contiene | Requiere |
|---|---|---|---|
| **0 (MVP)** | stdlib: `setrlimit` (CPU, memoria virtual, archivos, PIDs), `subprocess` + `killpg`, validación de capacidad en proceso | Accidentes: bucles infinitos, consumo desbordado de CPU/memoria involuntario. **Sin aislamiento de red ni fs; sin contención de adversarios. Documentado como tal.** | nada (macOS + Linux, sin root) |
| **1** | Linux: Landlock (fs por rutas + TCP por puerto) y seccomp-bpf —ambos autofiltros sin privilegio y **sin** user namespaces—, o bubblewrap (fs vía mount namespace; **éste sí** requiere user namespaces). macOS: Seatbelt con perfil en archivo (no argv — bug documentado claude-code#73468), como defensa en profundidad, no frontera dura | Errores y abusos simples; alcance de fs y red | Linux sin root (userns sólo para bwrap); macOS sin root |
| **2** | nsjail (rlimits + seccomp Kafel + cgroups + namespaces en un binario), o cgroups v2 delegados vía systemd + nftables para egress **incluida DNS** | Código no confiable sin instalación arbitraria de paquetes | un host Linux dedicado |
| **3** | Firecracker (KVM) o gVisor si no hay KVM; E2B open source como referencia de orquestación | Multitenancy hostil, `pip install` arbitrario | infraestructura |

Reglas aplicables **a partir del Nivel 1** (en Nivel 0 no hay mecanismo de
red que las haga cumplibles), sacadas de incidentes reales (AgentCore: egreso
que olvidó DNS; ExploitGym→Hugging Face: el proxy de paquetes *era* la
superficie; Anthropic/Irregular: el prompt decía "sin internet" y la red
salía; ClaudyDay: exfiltración por un host del propio allowlist):

1. La red es **default-deny con opt-in por capacidad**, y el control cubre
   DNS, no sólo TCP/HTTP.
2. Toda excepción de red se trata como superficie de ataque del propio
   sandbox; el allowlist sólo contiene destinos controlados.
3. Lo que el prompt le diga al agente sobre su entorno es irrelevante: sólo
   cuentan los mecanismos.
4. Las credenciales nunca entran al perímetro; la mediación es por proxy
   externo. (En Nivel 0: contrato del despliegue, no mecanismo.)
5. Se asume que el mecanismo de aislamiento tendrá bugs (los parches llegan
   después del despliegue) y se minimiza el daño post-escape.

## 7. Límites de ektel (declarados, no descubribles)

- Nivel 0 no es frontera de seguridad contra adversarios.
- **Tokens y costo sólo son gobernables para llamadas que cruzan la frontera
  del runtime.** En Nivel 0 nada impide mecánicamente que una acción use una
  credencial propia y gaste fuera de la vista de ektel; la compuerta (a) para
  tokens/costo exige que las credenciales del proveedor no entren al
  perímetro, y esa condición es contrato del despliegue hasta Nivel 1+.
- El sobregiro de presupuesto existe y está acotado a las llamadas
  concurrentes en vuelo, condicionado a que el enforcement funcione.
- La terminación forzosa cubre el proceso raíz y su grupo: un ejecutado que
  haga `setsid` escapa, y un proceso en D-state puede retrasar su muerte. El
  estado terminal `deadline_exceeded` se garantiza para la *acción registrada*
  —la supervisión deja de esperar y reporta—, no necesariamente para cada
  proceso huérfano que la acción haya dejado.
- La terminación forzosa no limpia; la reparación es por idempotencia o
  compensación declarada, cuya veracidad valida quien despacha, no ektel.
- Nada en el formato de capacidad da confinamiento de sub-delegaciones.
- La vía de interrupción independiente del proceso es composición del
  despliegue (en Aria: propylon), no parte del núcleo.
- El supervisor mismo puede caer: sin un watchdog externo, su freno muere con
  él (lección del caso gunicorn: el que alimenta el watchdog no puede vivir
  en el proceso gobernado).

## 8. Relación con Aria (opcional, por adaptador)

- Un adaptador traducirá `epistates/task-card/v1` → descriptor de acción.
  Vive fuera del núcleo; quien no usa Aria no lo instala.
- Cuando exista propylon, la validación de capacidad de ektel es la misma
  función que el gateway necesita en el punto de entrada — el formato de §5.3
  está diseñado para ser verificable por cualquier proceso con la clave
  pública, sin cambios.
- ektel declarará su `project-manifest.yaml` de Pinax en el mismo commit que
  su primera línea de código, con estas relaciones en `consume` (opcionales)
  y estos límites en `no_ofrece`.

## 9. Fuentes principales de la investigación

**Aislamiento y límites:** cgroups(7) y setrlimit(2) (man7.org) · Docker
seccomp docs · Landlock (docs.kernel.org) · nsjail (github.com/google/nsjail)
· comparativa académica de sandboxes (arXiv 2404.04127) · Anthropic,
"Claude Code sandboxing" (bubblewrap/Seatbelt + proxy por socket unix) ·
gVisor systrap (gvisor.dev) · Firecracker (NSDI 2020, Agache et al.) ·
wasmtime security docs · incidentes: Unit 42 sobre AWS AgentCore (bypass DNS,
CVE-2026-4269), OpenAI ExploitGym→Hugging Face (InfoQ 2026-08), Anthropic/
Irregular (3 incidentes de evaluación, 2026-07-30), OASIS "ClaudyDay",
claude-code#73468, GHSA-62r4-hw23-cc8v (n8n/Pyodide).

**Capacidades:** Capsicum (man.freebsd.org; USENIX Security 2010) · Macaroons
(NDSS 2014) y Fly.io "Operationalizing Macaroons" (online-stateful, denylist,
>98% caché) · Biscuit (eclipse-biscuit/biscuit; FAQ: sin auditoría formal) ·
UCAN v1.0.0 (ucan-wg/spec; ventana por intersección; invocación firmada;
revocación opcional; sin confinamiento) · zCAP-LD (W3C CCG draft: `expires`
obligatoria **en zcaps delegadas** —la raíz es implícita—; longitud de cadena
≤ 10 como **SHOULD de política del verificador**, no norma del formato;
almacenar revocaciones hasta expiración) · OAuth 2.0: RFC 8705 (mTLS),
RFC 9449 (DPoP), RFC 8693 (token exchange) · draft IETF de tokens atenuantes
para agentes (draft-niyikiza-oauth-attenuating-agent-tokens-00) · estrategias
de revocación JWT (Drozd; IDPro BoK).

**Runtimes de agentes y control:** OpenAI Agents SDK (max_turns; guardrails
paralelos vs. bloqueantes) · LangGraph (recursion_limit; interrupts sin TTL) ·
CrewAI (max_iter, max_execution_time) · AutoGen v0.4 (TimeoutTermination,
ExternalTermination) · "When Agents Do Not Stop" (arXiv 2607.01641: 68 bucles
infinitos reales en proyectos cuyos frameworks ofrecían topes; causas:
omisión, mala configuración, tope fuera del camino de retroalimentación) ·
Temporal (timeouts de actividad mantenidos por el servidor; cancel vs.
terminate; exactly-once de observación, no de ejecución) · systemd watchdog y
/dev/watchdog; gunicorn#2726 · OpenAI Operator System Card (mitigaciones en
capas, watch mode, tope de 400 pasos) · LiteLLM (budgets por clave/sesión;
bug #26672 de enforcement) · Helicone (429 preventivo) · OpenRouter (402;
chequeo pre-vuelo contra max_tokens) · OWASP LLM Top 10 (LLM06, LLM10) ·
OWASP Agentic Top 10 (ASI03, ASI08) · CISA/CSA guía de IA agéntica (kill
switches diseñados, no asumidos) · catálogo de sobregiros (arXiv 2606.04056).

## 10. Decisiones abiertas

1. **Serialización del token:** CBOR canónico vs. binario propio determinista.
2. **Librería Ed25519 concreta:** `cryptography` vs. PyNaCl (la decisión de
   *que habrá exactamente una* está cerrada, §4 O2).
3. **Quién emite la raíz de confianza** en un despliegue multi-proceso (en el
   MVP es la clave del propio runtime; en Aria está abierta la pregunta del
   emisor de capacidades, registrada como hueco del ecosistema, no de ektel).
4. **Watchdog del supervisor:** patrón elegido (systemd vs. proceso par) como
   documento de despliegue, no de núcleo.

---

## Anexo — registro de la ronda adversarial (2026-08-14)

1 ronda, 14 hallazgos, todos aplicados tras verificación contra la
investigación de base. Resumen por severidad:

- **Crítico (1):** la compuerta (a) para tokens/costo no es imponible sin
  cooperación cuando un comando arbitrario porta su propia credencial en
  Nivel 0. Corregido: §1 reformulado con la precisión de alcance, §5.1
  descompone imposición (OS) vs. gobernanza (frontera), §7 lo declara.
- **Mayores (3):** memoria ausente del presupuesto pese a figurar en Nivel 0
  (añadido `max_memory_bytes` con el matiz virtual≠RSS); "estado terminal
  garantizado" sobreafirmado (acotado: escapes `setsid`, D-state); la
  política de reparación era confianza declarativa vestida de propiedad
  exigida (reformulada: forma obligatoria, verdad de quien despacha).
- **Menores (10):** lista canónica de estados terminales; decisión de lenguaje
  cerrada (Python) y retirada de decisiones abiertas; excepción criptográfica
  Ed25519 declarada; cita del paper de bucles infinitos precisada; alcance
  offline de O2 acotado a MVP con ruta fail-closed declarada; reglas de red
  marcadas "a partir del Nivel 1"; requisitos de Nivel 1 separados por
  mecanismo (Landlock/seccomp sin userns, bwrap con userns); sobregiro acotado
  a N concurrente y condicionado al enforcement; atribuciones de citas
  corregidas (Anthropic para `execution_time_exceeded`; zCAP-LD SHOULD y
  "delegadas"); criterio de independencia convertido en mecánico
  (imports/stdlib + CI) en vez de "clonar en máquina sin Aria".

**Veredicto del adversario:** adoptable tras correcciones; sin defecto
estructural.
