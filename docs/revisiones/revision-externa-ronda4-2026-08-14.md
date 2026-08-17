# ektel — revisión externa adversarial (ronda 4)

**Estado:** ronda adversarial sobre la propuesta P1 de la ronda 2 y sobre la
elección de lenguaje del pre-proyecto. Contiene **una fe de erratas
vinculante** —P1 nombraba un mecanismo que no funciona— y una **reconciliación
con la ronda 3** (`revision-externa-r3-2026-08-14.md`, GLM 5.2), escrita en
paralelo y sin conocimiento mutuo.

**Nota de numeración:** esta ronda se escribió como «ronda 3» y se renumeró al
descubrir que ese lugar ya estaba ocupado por un documento firmado once
minutos antes. La colisión es en sí un hallazgo de proceso (§5.4).

**Fecha:** 2026-08-14 · **Entorno:** Darwin 25.5.0 (macOS, ARM), Go 1.26.6,
Python 3.9.6 del sistema, Rust 1.93.1 — dentro del sandbox de la herramienta
de ejecución (la ronda 3 corrió E1–E8 en el host; ver §5.2).

---

## 1. Fe de erratas — P1 nombra el mecanismo equivocado

### 1.1 Lo que decía

Ronda 2, §3, propuesta P1:

> En Nivel 0, CPU y memoria las vigila el **supervisor por muestreo**
> (`getrusage(RUSAGE_CHILDREN)` para CPU; RSS por `proc_pidinfo` en macOS y
> `/proc/<pid>/statm` en Linux), con `killpg` como brazo ejecutor.

### 1.2 Por qué es falso

`RUSAGE_CHILDREN` contabiliza únicamente hijos **ya recogidos**. Sobre un
proceso vivo devuelve cero.

Verificado dos veces, de forma independiente y con implementaciones distintas:

- **E14 (esta ronda, Go):** `0.000s` durante 2 s de quemado; `1.614s` tras
  `Kill` + `Wait`.
- **A1 (ronda 3, Python, en el host):** `0.000s` en vivo; `2.001s` tras
  `wait()`.

Una compuerta que conoce el consumo cuando el proceso ya murió no es una
compuerta: da ~0 mientras el hijo vive y el presupuesto no dispara nunca hasta
el reap, cuando ya es tarde. La propuesta que la ronda 2 presentó como *«la
única que la evidencia fuerza en vez de sugerir»* usaba una fuente post
mortem, y era la única propuesta del documento que no se había ejecutado.

No es defecto de un lenguaje: `resource.getrusage(RUSAGE_CHILDREN)` de Python
tiene la misma semántica que la de Go. **P1 estaba mal en cualquier
implementación.**

### 1.3 P1-bis — texto que sustituye a P1

Integra los cinco costos de N3 (ronda 3) y la cota de CPU de esta ronda.

**Compuerta (c) — sin cambios y sin muestreo.** El plazo no necesita nada de
esto: temporizador en el supervisor más `killpg` sobre el grupo de proceso
(E16, verificado). Es la única compuerta de Nivel 0 que se impone
mecánicamente en macOS sin condiciones.

**Unidad de medida: el grupo de proceso, no el PID raíz.** El presupuesto es
por acción completa (§5.1 del pre-proyecto), y una acción forkea. El muestreo
debe **caminar el árbol por pgid** y leer por proceso; leer sólo el PID raíz
deja fuera del presupuesto a todo descendiente. *(Hueco del borrador de esta
ronda, señalado por N3.1 de la ronda 3.)* En la vía `ps`, `ps -g <pgid>`
recupera el grupo entero en un solo spawn, de modo que el costo medido no
cambia de orden.

**Métrica de memoria: residente, nunca virtual.** La ronda 3 midió
`vsize ≈ 415 GiB` en un Python trivial, concordante entre `proc_pidinfo` y
`ps`. El espacio virtual es ruido en esta plataforma y produciría falsos
positivos también en Linux con binarios de gran reserva (Go, JVM) — que es
justamente el test P4.5, aún sin ejecutar.

**Sesgo de sobre-conteo, declarable en §7.** Sumar RSS por proceso cuenta N
veces las páginas compartidas (librerías mapeadas en N procesos). El sesgo es
conservador: mata antes una acción sana que deja pasar una hostil. Preserva la
propiedad de seguridad a costa de utilidad, y debe decirse. *(N3.3, ronda 3;
afirmado por conocimiento estándar, no medido por ninguna ronda.)*

**Fuentes de lectura por plataforma:**

- **Linux:** `/proc/<pid>/stat` campos 14–15 (`utime`, `stime` en ticks,
  dividir por `sysconf(_SC_CLK_TCK)`); RSS por `/proc/<pid>/statm` campo 2.
  Lectura de archivo: sin dependencias, sin spawn, stdlib de cualquier
  lenguaje. **No verificado por ninguna ronda** (§6).
- **macOS:** no hay `/proc`. Dos vías, ambas validadas:
  1. **`proc_pidinfo(PROC_PIDTASKINFO)`** — la ronda 3 verificó que funciona
     desde el padre, mismo uid, **sin root**, y que su RSS **coincide
     exactamente** con `ps` (58.4 MiB vs. 59792 KiB). Costo: exige **cgo** en
     Go o **ctypes** en Python; rompe la propiedad de stdlib puro y, en Go, la
     cross-compilación.
  2. **`/bin/ps -o time=,rss= -g <pgid>`** — medido en esta ronda: **2.7 ms
     por muestra** (E15), resolución de CPU 0.01 s. Viable con `T = 100 ms`.
     Evita cgo/ctypes al precio de un spawn por muestra. La ruta debe fijarse
     absoluta: resolver `ps` por `PATH` sería superficie de ataque dentro del
     lazo de imposición.

**Herencia de los límites ya declarados.** La caminata por pgid hereda el
límite de §5.4/§7 del pre-proyecto: un ejecutado que haga `setsid` escapa al
grupo y, por tanto, **también al muestreo**. P1-bis debe decirlo, no darlo por
obvio. *(N3.4, ronda 3.)*

### 1.4 Asimetría CPU / memoria — y hasta dónde llega

**CPU: el muestreo sirve, con cota calculable.** Es una magnitud acumulativa
de tasa acotada: un proceso no consume más de `C` segundos de CPU por segundo
de pared, con `C` los núcleos a su alcance. Un muestreo de periodo `T` acota
el sobreconsumo a `T × C` segundos de CPU — con `T = 100 ms` y `C = 8`, unos
0.8 s. Cota declarable en §7. *(Razonada, no medida; §6.)*

**Memoria: el muestreo sirve para el alcance declarado, no más.** Aquí el
borrador de esta ronda afirmaba que «el muestreo NO rescata la memoria,
punto», y eso sobrepasa. La memoria no es de tasa acotada —un `mmap` más un
recorrido de páginas añade gigabytes en mucho menos de 100 ms—, de modo que el
sobreconsumo entre muestras **no está acotado**, a diferencia del de CPU. Pero
el Nivel 0 declara su alcance como *contención de accidentes, no de
adversarios*: frente a una fuga accidental, el muestreo la detecta dentro de
un periodo y la máquina sobrevive, que es exactamente lo prometido. La
formulación correcta:

> El muestreo de RSS contiene fugas accidentales con retardo de un periodo. No
> acota el consumo frente a una asignación deliberada, y esa diferencia con la
> CPU —cuya cota es `T × C`— debe declararse en §7.

### 1.5 Estado real de la compuerta (a) en Nivel 0

| Magnitud | Linux | macOS |
|---|---|---|
| Tiempo de pared | Mecánico (supervisor + `killpg`) | Mecánico |
| CPU | `RLIMIT_CPU` + muestreo, cota `T × C` | **Sólo muestreo**, cota `T × C`, con costo por muestra |
| Memoria | `RLIMIT_AS` (matiz virtual ≠ RSS ya declarado) | **Sólo muestreo de RSS**: contiene accidentes, no acota adversarios |
| Tokens / costo | Sólo en la frontera del runtime (ya declarado en §1) | Ídem |

---

## 2. Evidencia de esta ronda

| # | Prueba | Resultado |
|---|---|---|
| E10 | `crypto/ed25519`, `crypto/sha256`, `encoding/binary` en Go; `go list -deps` | Sólo `std`. Cero dependencias externas |
| E11 | `otool -L` del binario Go en macOS | Enlaza `libSystem.B.dylib`, `libresolv.9.dylib` → **no estático** |
| E12 | `GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build` | ELF `statically linked`, 2.7 MB → estático **sólo en Linux** |
| E13 | Campos de `syscall.SysProcAttr` | Darwin: `Setsid`, `Setpgid`, `Credential`, `Chroot`. Linux añade `Cloneflags`, `Unshareflags`, `UidMappings`, `AmbientCaps`, `UseCgroupFD`/`CgroupFD`, `PidFD`, `Pdeathsig`. **Sin rlimits en ninguna** |
| E14 | `Getrusage(RUSAGE_CHILDREN)` sobre hijo vivo | `0.000s` durante 2 s; `1.614s` tras recogerlo. **Converge con A1 de la ronda 3** |
| E15 | `/bin/ps -o time=,rss=` sobre hijo vivo | CPU en vivo y RSS correcto (317 MB sobre 300 MB asignados). **2.7 ms por muestra** |
| E16 | `killpg(-pid, SIGKILL)` desde supervisor Go con `Setsid: true` | Mata el grupo. `signal: killed` |
| E17 | Landlock / seccomp en `syscall` de Go | **Ausentes**: `no symbol LANDLOCK_CREATE_RULESET` |
| E18 | Shim por auto-re-exec: `os.Executable()` → subcomando → `Setrlimit` → `Exec` | Funciona: el nieto ve `nofile=32`, el supervisor conserva 61440 |

---

## 3. La elección de lenguaje

### 3.1 H16 · M — El pre-proyecto no justifica su única decisión estructural

§4-O1 declara: *«La decisión de lenguaje queda cerrada para el MVP: Python»*,
y el anexo la registra como hallazgo menor aplicado. Cerrar una decisión no es
justificarla. En un documento que respalda con cita hasta la elección de
`killpg`, la única elección estructural sin un renglón de argumento es el
lenguaje.

**Propuesta:** escribir el párrafo, o devolver la decisión a §10 con §3.3
sobre la mesa. El riesgo concreto de dejarla «cerrada» sin argumento es que
una elección tomada para un MVP desechable se convierta en silencio en la
elección de Nivel 1.

### 3.2 Lo que sostiene a Python

- El MVP es un **supervisor**: lanza procesos, sostiene un reloj, mata grupos,
  valida tokens. Orquestación de syscalls, no cómputo. La velocidad del
  lenguaje es irrelevante para esa carga.
- La stdlib cubre el trabajo: `subprocess`, `signal`, `select`, `os.killpg`,
  `hashlib`.
- **La legibilidad de las compuertas es parte del producto.** Un proyecto cuya
  tesis es «compuertas mecánicas y verificables» necesita que un humano pueda
  leer las líneas que las imponen.
- Velocidad hacia un MVP falsable que, por diseño, se va a tirar.

### 3.3 Lo que no lo sostiene

**La excepción criptográfica la creó el lenguaje.** §2.3 dice: *«Única
excepción declarada: una librería criptográfica auditada para Ed25519 — la
stdlib de Python no ofrece firmas de clave pública»*, y O2 la califica de «la
más sensible del proyecto». E10 confirma que en Go esa excepción no existe:
`crypto/ed25519`, `crypto/sha256` y `encoding/binary` son stdlib, con cero
dependencias externas. El costo real en Python es mayor que «un import»:
`cryptography` arrastra cffi más wheels compilados; PyNaCl arrastra libsodium.

**El intérprete es superficie.** El supervisor impone compuertas sobre trabajo
no confiable y en Python carga código desde rutas influibles por entorno
(`PYTHONPATH`, `sitecustomize`). Mitigable con `python3 -I`, pero es una
mitigación que hay que recordar poner.

**Nivel 1 no es cuestión de que falte un binding.** Landlock y seccomp-bpf no
tienen stdlib en Python; se harían marshalando structs de syscall y
ensamblando BPF con `ctypes`, en la ventana fork-insegura de `preexec_fn`
(H13). Es código de frontera de seguridad hecho a mano.

**La ventaja específica de Python ya estaba degradada.** Su mejor baza era el
módulo `resource`: `setrlimit` en tres líneas donde Go necesita shim (E13,
E18). Pero E2 y E6 de la ronda 2 degradaron `setrlimit` a refuerzo opcional de
Linux. La ventaja se evaporó antes de esta discusión.

**Y un dato de política, no de lenguaje** (N5, ronda 3): el único Python de la
máquina objetivo es 3.9.6, **EOL desde 2025-10-31**; 3.10 muere en 2026-10.
Un runtime cuya única superficie es la stdlib debe declarar intérprete mínimo
sobre rama mantenida (≥3.11).

### 3.4 Ronda adversarial sobre mi propia recomendación de Go

Tras §3.3 recomendé que *«Go domina para el núcleo del supervisor»*. No
aguanta en esa forma.

**G2 — «Binario estático» es falso en macOS.** E11: enlaza `libSystem` y
`libresolv`; E12 confirma que sí lo es en Linux. El argumento de H8 —el
supervisor sobrevive mejor sin intérprete— vale **sólo en Linux**.

**G3 — La «cero excepciones» se rompe donde importa.** E10 la confirma en
Nivel 0; E17 la refuta en Nivel 1: Landlock y seccomp no están en la stdlib de
Go —la vía mantenida es `golang.org/x/sys/unix`, fuera de ella— y en macOS
Seatbelt es API de C, exige **cgo**, con lo que se pierde la cross-compilación
de E12. Vendí una propiedad que se sostiene en el nivel que contiene
accidentes y se cae en el que contiene adversarios.

**G4 — Usé un criterio que yo mismo había declarado inadecuado.** Sostuve que
el criterio de §2, formulado en imports, «subestima la cadena de suministro»,
y acto seguido apoyé la recomendación en un conteo de imports (1 → 0). La
comparación pertinente es de base de cómputo confiable —CPython y su cadena de
wheels frente al toolchain y runtime de Go— y **no la hice**.

**G5 — El mejor argumento a favor de Go no es el que di.** E13 muestra que en
Linux `SysProcAttr` expone declarativamente `Cloneflags`, `Unshareflags` y
`UidMappings` (namespaces: Nivel 1–2), `CgroupFD` (cgroups en el spawn:
Nivel 2) y `PidFD` (referencia sin carrera de reutilización de PID, útil para
que (c) mate al proceso correcto). Construí el caso sobre Ed25519, que es de
Nivel 0, cuando el caso real está en Niveles 1–2 y sólo en Linux. Matiz:
`Pdeathsig` —el campo que respondería parcialmente a H8— es el que la propia
documentación de Go marca como frágil, porque se entrega al morir el *hilo* y
el runtime mueve goroutines entre hilos (`go.dev/issue/27505`).

**G6 — El shim funciona y no es un costo de Go.** E18 confirma que Go no puede
ejecutar código entre `fork` y `exec` y que la vía es re-ejecutarse. Es la
misma arquitectura que la ronda 2 ya recomendaba para Python en H13. Añade una
superficie a declarar: el supervisor ejecuta una ruta resuelta en tiempo de
ejecución; en Linux `/proc/self/exe` es libre de carreras, en macOS
`os.Executable()` no ofrece la misma garantía.

**G7 — El hallazgo que anula la discusión.** El lenguaje **no toca H1 ni H2**.
En macOS el Nivel 0 impone mecánicamente el plazo; la CPU exige muestreo con
cgo/ctypes o con spawn por muestra, y la memoria queda con el alcance limitado
de §1.4 — idéntico en Python y en Go. Lo que Go mejora es la cadena de
suministro cripto en Nivel 0 y los Niveles 1–2 en Linux: ninguna de las dos
cosas es el problema que originó la pregunta. Dejé que la elección de lenguaje
absorbiera atención que pertenece a una decisión de plataforma.

### 3.5 Veredicto sobre el lenguaje

Retirado «Go domina».

| | A favor | En contra |
|---|---|---|
| **Python** | Legibilidad de las compuertas; velocidad hacia un MVP desechable; stdlib suficiente para Nivel 0 | Crea la excepción cripto; intérprete como superficie; Nivel 1 vía `ctypes` en ventana fork-insegura; intérprete de la máquina objetivo en EOL |
| **Go** | Cripto en stdlib (E10); Niveles 1–2 declarativos **en Linux** (E13); binario autocontenido **en Linux** (E12) | No estático en macOS (E11); Nivel 1 sale de stdlib (E17) y en macOS exige cgo; sin hook pre-`exec`, obliga a shim (E18) |
| **Rust** | La mejor historia de Nivel 1 en **ambas** plataformas (crates mantenidos, `pre_exec` disponible); ya instalado en la máquina objetivo | Reintroduce la dependencia cripto; peor legibilidad para auditoría; más lento de escribir |

Ninguno domina. La elección depende de qué se optimice, y eso no está decidido
porque la pregunta anterior sigue abierta (§4).

---

## 4. El orden correcto de decisiones

Hay una decisión de **plataforma** que precede al lenguaje y a la suite, y que
ninguna de las cuatro rondas había formulado:

> ¿El Nivel 0 en macOS declara que impone **sólo la compuerta (c)**, o se paga
> el costo del muestreo —`/bin/ps -g` a 2.7 ms por muestra, o `proc_pidinfo`
> vía cgo/ctypes fuera de la stdlib— aceptando la cota `T × C` en CPU y el
> alcance limitado de §1.4 en memoria?

Esa respuesta cambia qué hace el runtime, qué dice la fila de Nivel 0 de §6 y
qué se declara en §7. La del lenguaje no cambia nada de eso. Orden propuesto:

1. **Decidir la pregunta de plataforma.** Es la única que bloquea.
2. **Escribir la suite de escape.** Independiente del lenguaje —prueba el
   sistema operativo, no ektel—. Con las pruebas de las rondas 3 y 4 el
   conjunto mínimo sube de siete a diez: las siete de P4, más A1/E14
   (`RUSAGE_CHILDREN` post mortem), A2 (`proc_pidinfo` contra `ps`, que es
   donde se valida el mecanismo de muestreo) y la cota `T × C` verificada.
3. **Decidir el lenguaje** con lo que la suite devuelva, y escribir el párrafo
   que H16 reclama.

Se adopta además **R4 de la ronda 3** sobre H3: orden fijo de evaluación en
cada tick del supervisor —(c) antes que (a)—, toda doble violación produce
`deadline_exceeded`, y retirada de `max_wall_seconds` del descriptor. Con la
observación de su C2, que es correcta y contradice mi encuadre inicial: al
concentrar ambas decisiones de kill en el supervisor, P1 **vuelve determinista
una precedencia** que en el diseño original competía entre el kernel
(`SIGXCPU`) y el timer. El defecto de H3 preexiste a P1 y P1 lo mejora.

---

## 5. Reconciliación con la ronda 3

Las rondas 3 y 4 se escribieron en paralelo, sin conocimiento mutuo, por
modelos distintos (GLM 5.2 y Claude Opus 5) sobre el mismo documento base.

**5.1 Lo que converge — y por qué importa.** El hallazgo central es el mismo,
alcanzado con lenguajes e implementaciones distintas: A1 (Python, host) y E14
(Go, sandbox) coinciden en que `RUSAGE_CHILDREN` no ve hijos vivos. Es la
única afirmación de todo este ciclo con verificación independiente real, y por
eso es la que menos duda admite.

**5.2 Lo que la ronda 3 aporta y esta ronda no tenía.** Se incorpora a P1-bis
y se acredita: caminata por pgid (N3.1) —que era un hueco de mi texto—,
`proc_pidinfo` sin root validado contra `ps` (A2), métrica residente y no
virtual con `vsize ≈ 415 GiB` medido, sobre-conteo de RSS compartido (N3.3),
herencia del escape por `setsid` (N3.4), y la ejecución de E1–E8 **en el
host**, que rebaja la salvedad de sandbox que la ronda 2 declaró en su §6.

**5.3 Lo que esta ronda concede.** El borrador afirmaba que el muestreo «no
rescata la memoria, punto». Es demasiado fuerte: el Nivel 0 promete contención
de accidentes, y para eso el muestreo basta. Reformulado en §1.4. La asimetría
con la CPU se mantiene y se declara.

**5.4 Verificación de citas: un hallazgo que esta ronda no podía producir.**
Las rondas 2 y 4 declararon explícitamente no verificar ninguna cita del §9.
La ronda 3 verificó cuatro y encontró un error real en el pre-proyecto: **N8 —
`CVE-2026-4269` está mal atribuida**; corresponde a inyección en build por
verificación de propiedad de S3 en el Bedrock AgentCore Starter Toolkit, no al
bypass de DNS con el que §6 y §9 la emparejan. También N6: la glosa «cuyos
frameworks ofrecían esos mecanismos», base de D1, no es verificable desde el
abstract. Ambos se recogen aquí como **reportados por la ronda 3, no
verificados por esta**, y son la mejor demostración del ciclo: cada ronda
encuentra lo que su método permite ver, y ninguna ve lo que no mira.

**5.5 La colisión de numeración es un hallazgo de proceso.** Dos documentos se
titularon «ronda 3» con once minutos de diferencia sobre el mismo repositorio,
y `docs/` sigue untracked en `325beef` (N1, ronda 3). Con varios revisores en
paralelo, la numeración y el orden sólo existen si están en el historial. **La
reparación es la misma que recomienda R1 de la ronda 3: commitear `docs/`
completo antes de que se escriba una quinta ronda.**

---

## 6. Registro de correcciones

Continúa la numeración de la ronda 2 (R1–R8 contra su propia primera pasada).

**R9 — Error de hecho en documento firmado.** P1 nombraba
`getrusage(RUSAGE_CHILDREN)`. Es post mortem (E14, A1). Sustituida por P1-bis.

**R10 — Conclusión sobrepasada, en el borrador de esta ronda.** Afirmé que el
muestreo no rescata la memoria «punto». Corregido en §1.4: la contiene dentro
del alcance declarado del Nivel 0; lo que no hace es acotarla frente a
asignación deliberada.

**R11 — Severidad mal asignada en la ronda 2.** P1 se presentó como «la única
propuesta que la evidencia fuerza». Era la única propuesta del documento que
no se había ejecutado.

**R12 — P1-bis incompleta en su primer borrador:** leía el PID raíz en vez de
caminar el pgid. Corregido con N3.1 de la ronda 3.

**R13 — «Binario estático» sin verificar.** Falso en macOS (E11).

**R14 — «Cero excepciones» sobrevendida.** Cierta en Nivel 0, falsa en Nivel 1
(E17).

**R15 — Criterio incoherente.** Argumenté con conteo de imports tras declarar
ese criterio inadecuado.

**R16 — Argumento correcto por motivo equivocado.** El caso de Go está en
`SysProcAttr` de Linux (E13), no en Ed25519.

**R17 — «Go domina para el núcleo del supervisor», retirado.** Ver §3.5.

**R18 — Encuadre invertido en H3.** La ronda 2 trataba la precedencia como
defecto agravado; C2 de la ronda 3 muestra que P1 la mejora. Adoptado en §4.

---

## 7. Lo que esta ronda no verificó

- **Nada en Linux.** `/proc/<pid>/stat` y `/proc/<pid>/statm` —el mecanismo de
  lectura que P1-bis necesita allí—, `RLIMIT_AS`, `RLIMIT_CPU`, Landlock,
  `CgroupFD` y el binario estático de E12 **no se ejecutaron en Linux**: E12
  sólo comprueba que el binario se produce y qué dice `file` de él. Sigue
  siendo el mayor agujero de las cuatro rondas.
- **`Pdeathsig`**, el campo con consecuencia directa sobre H8: exclusivo de
  Linux, sin probar.
- **La cota `T × C`**: razonada, no medida.
- **El sobre-conteo de RSS compartido**: afirmado por ambas rondas, medido por
  ninguna.
- **Rust:** no se ejecutó una sola línea. Todo lo dicho sobre Rust en §3.5 es
  argumento, no evidencia — el mismo estatus que tenía Go antes de esta ronda,
  que es precisamente el estatus que esta ronda refutó dos veces.
- **Las citas del §9:** esta ronda no verificó ninguna. Las cuatro verificadas
  lo fueron por la ronda 3, y una resultó mal atribuida (§5.4). El bloque de
  capacidades —Biscuit, UCAN, Fly.io, zCAP-LD— sigue sin verificar por nadie.
- **La criptografía de §5.3:** sin análisis formal.
- Siguen sin evidencia, de la ronda 2: escape por `setsid`, D-state, fork
  bomb, y E9 (`preexec_fn` multihilo) que ninguna ronda ha reproducido.

---

## Anexo — reproducción

```go
// E14 · RUSAGE_CHILDREN es post mortem  (converge con A1 de la ronda 3)
cmd := exec.Command("python3", "-c", "x=0\nwhile True: x+=1")
cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
cmd.Start()
for i := 0; i < 5; i++ {
    time.Sleep(400 * time.Millisecond)
    var ru syscall.Rusage
    syscall.Getrusage(syscall.RUSAGE_CHILDREN, &ru) // 0.000s mientras vive
}
syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)     // E16: mata el grupo
cmd.Process.Wait()                                  // ahora si: ~1.6s
```

```go
// E15 · via sin cgo en macOS; -g <pgid> cubre el grupo en un solo spawn
exec.Command("/bin/ps", "-o", "time=,rss=", "-g", strconv.Itoa(pgid)).Output()
// ~2.7 ms por muestra; resolucion de CPU 0.01 s; ruta absoluta obligatoria
```

```go
// E18 · shim por auto-re-exec (unica via en Go para restringir antes de exec)
if len(os.Args) > 1 && os.Args[1] == "__shim" {
    syscall.Setrlimit(syscall.RLIMIT_NOFILE, &syscall.Rlimit{Cur: 32, Max: 32})
    // aqui irian Landlock / seccomp en Linux
    syscall.Exec(target, argv, env)
}
self, _ := os.Executable()
exec.Command(self, "__shim").CombinedOutput()  // nieto: 32; supervisor: 61440
```

```
# E11/E12/E17 · propiedades del binario y de la stdlib
otool -L probe                                        # macOS: libSystem, libresolv
GOOS=linux CGO_ENABLED=0 go build -o p . && file p    # ELF statically linked
GOOS=linux go doc syscall.LANDLOCK_CREATE_RULESET     # no symbol
```

---

## Firma

Revisión realizada por **Claude Opus 5** (`claude-opus-5`), Anthropic.
**Fecha:** 2026-08-14.
**Revisa:** `docs/revision-externa-2026-08-14.md` (ronda 2, mismo autor),
`docs/pre-proyecto.md` §4-O1, y una recomendación de lenguaje emitida en
conversación tras la ronda 2.
**Reconcilia con:** `docs/revision-externa-r3-2026-08-14.md` (ronda 3, GLM
5.2, Z.ai), escrita en paralelo y sin conocimiento mutuo.
**Sustituye:** la propuesta P1 de la ronda 2, por P1-bis (§1.3).
**Método:** ejecución en Darwin 25.5.0 con Go 1.26.6 y Python 3.9.6; nueve
pruebas (E10–E18) reproducibles en el anexo.

**Veredicto:** la ronda 2 acertó en el diagnóstico (H1, H2) y falló en la
reparación (R9). P1-bis queda especificada con los cinco costos que ninguna
ronda anterior tenía completos, y con la unidad de medida corregida —grupo de
proceso, memoria residente—. La elección de lenguaje, que ocupó el turno
siguiente, resultó ser una decisión de plataforma disfrazada: el orden está en
§4. Y la reconciliación de §5 deja el dato más útil de las cuatro rondas: el
único hallazgo con verificación independiente real es el que dos modelos
distintos produjeron por separado.

**Nota sobre el método, cuarta vez consecutiva:** cada ronda encontró su
hallazgo principal al ejecutar, y ninguna al leer. La ronda 1 fue documental y
falló. La ronda 2 ejecutó contra el pre-proyecto y acertó, pero no ejecutó sus
propias propuestas y una era falsa. Las rondas 3 y 4 ejecutaron contra esa
propuesta, por separado, y coincidieron. La ronda 3 además miró donde ninguna
otra miraba —las citas— y encontró allí un error que llevaba tres rondas
intacto. Nada garantiza que esta sea la última: **nada de todo esto se ha
ejecutado en Linux**, y esa afirmación está hoy en la misma posición en que
estaba P1 ayer.
