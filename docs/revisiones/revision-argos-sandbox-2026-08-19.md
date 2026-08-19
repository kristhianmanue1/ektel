# Revisión de evidencia: `argos_epistemic/sandbox.py` contra E1–E3 (ektel)

**Fecha:** 2026-08-19.

**Origen:** ektel (revisión contribuible a Argos Epistemic `0.2.0rc2`).

**Objeto revisado:** `argos_epistemic/sandbox.py` (104 líneas) y su uso desde
`argos_epistemic/dynamic.py` (extractor L5).

**Evidencia aplicada:**
`docs/evidencia/caracterizacion-linux-2026-08-18.md` de ektel —
caracterización empírica de `RLIMIT_AS`, `cutime/cstime` y reparentado con
`PR_SET_CHILD_SUBREAPER` en Linux 6.11.11-linuxkit aarch64 (suite 7/7) y
Darwin arm64 (macOS 26.5.2), más la taxonomía de garantías de la propuesta
M0–M3 (`enforced` / `reactive` / `observed` / `unsupported`).

**Alcance:** revisión estática + contraste con evidencia empírica. No se
ejecutó código de Argos. Las afirmaciones sobre el comportamiento de Argos
son sobre el código leído en la revisión `0.2.0rc2`.

## Valoración general

El sandbox de Argos es una buena base honesta: la ejecución dinámica es
opt-in, la degradación de aislamiento se reporta (`degradation`), el
docstring declara explícitamente lo que no garantiza ("NO equivale a un
contenedor"), y los manifests se abren con `O_NOFOLLOW` en otra capa. La
revisión no cuestiona la arquitectura; aporta la clasificación de garantías
por plataforma y tres huecos concretos que la evidencia E1–E3 hace
visibles.

## Hallazgos

Severidad: impacto sobre la promesa que el propio componente hace.

### F1 · "No deja huérfanos" es falso ante escape de sesión (alta)

El docstring afirma: *"`start_new_session=True`: el subproceso lidera su
propio grupo, de modo que un timeout permite matar a toda su descendencia
(no deja huérfanos)"*.

La evidencia E2 de ektel (probada, no hipotética): un nieto cuyo padre
intermedio muere, o cualquier descendiente que llame `setsid`/double-fork,
**escapa al grupo** y `os.killpg` no lo alcanza. En Linux, sin
`prctl(PR_SET_CHILD_SUBREAPER)` en el supervisor, el CPU de ese huérfano es
irrecuperable (`test_orphaned_grandchild_cpu_is_lost_without_subreaper`);
con subreaper se recupera (`test_subreaper_recovers_orphaned_grandchild_cpu`).
`PR_SET_CHILD_SUBREAPER` es Linux-only, **sin mitigación conocida en Darwin**.

Clasificación ektel: la promesa actual es narrativa; la garantía real es
`reactive` sobre el grupo directo y `unsupported` para descendientes que
escapen a la sesión.

Recomendación: (a) corregir el docstring para declarar la clase de escape
(double-fork/`setsid` fuera del grupo) en lugar de "no deja huérfanos";
(b) si Argos llega a supervisar jerarquías de más de un nivel y le importa
la contabilidad, declararse subreaper en Linux antes de lanzar la
jerarquía, y declarar `unsupported` en Darwin.

### F2 · `RLIMIT_CPU` es garantía `reactive`, no respaldo uniforme del timeout (media)

`RLIMIT_CPU` mide **tiempo de CPU**, no tiempo de pared: un proceso que
bloquea en I/O o `sleep` nunca agota el límite y sólo lo mata el timeout de
`communicate()`. Además la semántica de rlimits no es portable: la evidencia
de ektel confirma que `RLIMIT_AS` es **rechazado en Darwin** y aceptado en
Linux; cada límite debe caracterizarse por plataforma antes de describirse
como respaldo.

Recomendación: documentar `cpu_seconds` como límite de CPU-time de clase
`reactive` (el kernel fuerza SIGXCPU, pero sólo sobre CPU consumida), no
como respaldo del plazo de pared.

### F3 · `proc.communicate()` tras el kill puede colgar indefinidamente (alta)

Secuencia actual en timeout (líneas 91–97): `killpg(SIGKILL)` →
`proc.communicate()` **sin timeout** → retorno. Si un descendiente escapó a
la sesión (F1) pero heredó los descriptores de stdout/stderr, el pipe no
llega a EOF hasta que ese descendiente termine, y el segundo
`communicate()` **bloquea para siempre**. El componente cuyo propósito es
acotar la ejecución tiene una ruta de hang ilimitado.

Recomendación: tras el kill, usar `proc.communicate(timeout=N)` con un
segundo plazo acotado; si expira, cerrar los pipes (`proc.stdout.close()`,
`proc.stderr.close()`) y reportar el truncamiento/cierre forzado en la
salida. Esto alinea el comportamiento con el criterio de ektel M2: "no hay
hangs en la suite acotada".

### F4 · El estado terminal tras timeout se descarta (media)

Tras matar y recoger al proceso, el retorno informa `returncode: None` y
`error: "TimeoutExpired"` aunque el proceso ya fue recogido y su estado
terminal real (señal 9) es conocido. Se pierde información que el propio
proceso ya entregó: el reporte mezcla "desconocido" con "terminado por el
supervisor".

Recomendación: capturar `proc.returncode` tras el `communicate()`
post-kill y distinguir en la salida `deadline_exceeded`/`terminated`
(estado terminal observado, p. ej. `-SIGKILL`) de `supervision_unknown`
(recogida no confirmada). Es la distinción que ektel tipa en
`ExecutionResult` y que hace los attestations más precisos.

### F5 · La degradación de aislamiento es informativa, no una compuerta (media)

Con `isolation="strict"` y sin firejail/bwrap, la ejecución **procede sin
aislamiento** y sólo lo delata el string `degradation`. El consumidor debe
recordar revisarlo. La regla equivalente de ektel: "no hay degradación
silenciosa de `enforced` a `observed`; solicitar una garantía obligatoria
no disponible rechaza la admisión".

Recomendación: añadir modo fail-closed opcional
(`isolation="strict_required"`) que rechace la ejecución cuando no haya
wrapper disponible, manteniendo el modo actual como degradación declarada.
El default honesto de Argos ya es mejor que la media; el modo estricto
completa la historia para código hostil (threat model:
"ejecución dinámica de terceros no debe habilitarse sin aislamiento
adicional").

### F6 · `scrub_env` por denylist heurística (baja)

Eliminar variables cuyo nombre contiene `TOKEN|SECRET|PASSWORD|...` tiene
falsos negativos (secretos con nombres propios: `MYAPP_SIGNING`,
`NPM_CONFIG_//registry...:_authToken` contiene "TOKEN" pero ilustra lo
frágil del patrón) y falsos positivos inocuos. La postura inversa —allowlist
de entorno, como `env_allowlist_values` en el descriptor de ektel— es la
que falla cerrada: lo no declarado no pasa.

Recomendación: para L5 sobre código de terceros, ofrecer
`env_allowlist: list[str]` que construya el entorno del hijo desde cero.

### F7 · Captura de salida sin límite (baja en Linux, media en Darwin)

`communicate()` acumula stdout/stderr completos en memoria del proceso
Argos. Un target que escribe sin tope agota la memoria del analista. En
Linux podría mitigarse con `RLIMIT_AS` sobre el propio analista (aceptado),
pero en Darwin `RLIMIT_AS` se rechaza (evidencia E1/E3): no hay red de
seguridad de plataforma.

Recomendación: captura acotada con truncamiento declarado
(`stdout_truncation`/`stderr_truncation` en ektel): leer hasta N bytes y
registrar el truncamiento en el artefacto L5.

## Tabla de clasificación (taxonomía ektel)

| Mecanismo en sandbox.py | Clase real | Nota |
|---|---|---|
| `killpg` en timeout | `reactive` | Sólo alcanza el grupo; escape por `setsid` fuera de alcance (F1) |
| `RLIMIT_CPU` | `reactive` | CPU-time, no wall-time (F2) |
| Recogida del proceso | `enforced` (hijo directo) | `communicate()` lo reapea; huérfanos escapados: `unsupported` (F1) |
| Aislamiento red/FS | `enforced` sólo si firejail/bwrap presente | Si no: `unsupported` con degradación declarada (F5) |
| `scrub_env` | `observed`-equivalente | Higiene sin garantía (F6) |
| Límite de salida | `unsupported` hoy | Sin mecanismo (F7) |
| Contabilidad CPU del hijo | no existe | `cutime/cstime` disponible vía `wait4`/`resource` si se quiere evidencia (E1) |

## Qué NO cambia

- La arquitectura opt-in de ejecución dinámica es correcta.
- El reporte explícito de degradación es mejor práctica que la media del
  ecosistema; esta revisión propone completarlo, no reemplazarlo.
- Nada aquí sugiere que Argos deba importar ektel: la relación propuesta es
  de contratos y evidencia compartida, no de código.

## Contribución sugerida a Argos

1. Issue con F1–F7 y esta tabla (texto reusable tal cual).
2. PR pequeño y separado para F3 (hang post-kill) y F4 (estado terminal),
   que son correcciones locales sin cambio de contrato.
3. Decisión de diseño propia de Argos para F5/F6 (compuerta fail-closed y
   allowlist de entorno), que sí tocan contrato público.

## Nota de ecosistema (Praxis)

El mantenedor indicó que Praxis Dev será parte del ecosistema en el futuro.
Esto no cambia ningún veredicto de esta revisión: Praxis sigue en
`0.1.0-draft.1` con autoridad `advisory`, por lo que no se adopta como norma
hoy. La única acción derivada es de formato: los artefactos de decisión de
ektel (ADR, registro de consenso) se mantienen mapeables a los contratos
ADRG de Praxis para que una conformidad futura sea barata. Sin dependencia
de runtime ni de plantilla duplicada.
