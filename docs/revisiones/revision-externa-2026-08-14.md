# ektel — revisión externa adversarial (ronda 2)

**Estado:** revisión externa del documento de pre-proyecto (`pre-proyecto.md`,
2026-08-14). Dos pasadas: una documental y una empírica que corrigió a la
primera. Este documento **no es evidencia verificada del comportamiento de
ektel** —ektel no existe todavía—; sí es evidencia verificada del
comportamiento de los mecanismos del sistema operativo sobre los que el
pre-proyecto apoya su compuerta (a), en la plataforma y versión declaradas
en §2.

**Alcance:** hallazgos contra el pre-proyecto, propuestas, y registro de las
afirmaciones que esta misma revisión retiró o rebajó.

---

## 1. Método, y por qué la primera pasada fue insuficiente

La primera pasada fue documental: lectura crítica del pre-proyecto contra sí
mismo y contra el estado del arte. Produjo 14 observaciones.

La segunda pasada ejecutó los cuatro puntos que la primera había declarado
verificables. El resultado corrige a la primera en siete lugares y produce el
único hallazgo crítico de ambas: **una afirmación central del §1 del
pre-proyecto es falsa en macOS**.

La lección es simétrica a la que el propio pre-proyecto se aplica. Su anexo
registra una ronda adversarial «verificada contra la investigación de base»,
es decir, contra fuentes secundarias. Ninguna ronda de ese tipo —ni la del
pre-proyecto ni mi primera pasada— encontró H1 ni H2. Veinte minutos de
`python3` sí.

---

## 2. Evidencia empírica

**Entorno:** Darwin 25.5.0 (macOS, ARM), Python 3.9.6 del sistema.
Reproducción en el anexo A.

| # | Prueba | Resultado |
|---|---|---|
| E1 | Constantes `RLIMIT_AS` / `RLIMIT_RSS` en Darwin | Ambas = `5`. Header del SDK: `#define RLIMIT_RSS RLIMIT_AS /* source compatibility alias */`, comentario de `RLIMIT_AS`: *"address space (resident set size)"* |
| E2 | `setrlimit(RLIMIT_AS, 128 MiB)` | **`EINVAL`** — no se puede fijar |
| E3 | `setrlimit(RLIMIT_DATA, 128 MiB)` | **`EINVAL`** |
| E4 | Control: bajar `NOFILE`, `CPU`, `NPROC`, `FSIZE` | Todos aceptados → el fallo de E2/E3 es específico de esos recursos, no del entorno de ejecución |
| E5 | `RLIMIT_CPU` (soft=1 s, hard=5 s), hijo cooperativo | Muere a ~0.7 s de CPU, `exit=152` (128+`SIGXCPU`) |
| E6 | `RLIMIT_CPU` (soft=1 s, hard=5 s), hijo con `SIGXCPU` ignorado | **Sobrevive con 15.1 s de CPU consumida**; el límite duro no entrega `SIGKILL` |
| E7 | `RLIMIT_CPU` con **soft == hard == 2 s**, `SIGXCPU` ignorado | **Sobrevive con 10.5 s de CPU** |
| E8 | `man 2 setrlimit`, `RLIMIT_NPROC` | *"The maximum number of simultaneous processes for this **user id**"* |
| E9 | `preexec_fn` desde proceso con hilo vivo | Se ejecuta sin emitir ningún aviso |

Medición de CPU en E5–E7 por `getrusage(RUSAGE_SELF).ru_utime + ru_stime`, no
por reloj de pared: un primer intento con reloj de pared habría sido
impugnable y fue descartado.

---

## 3. Hallazgos

Severidad: **C** crítico (invalida una afirmación del documento o un criterio
de aceptación) · **M** mayor (hueco de especificación con consecuencia
mecánica) · **m** menor (precisión, ambigüedad o trampa de implementación).

### H1 · C — La compuerta (a) de memoria no existe en macOS

§1 afirma: «CPU, memoria y tiempo de pared los impone el OS sobre
**cualquier** comando». §5.1 especifica `RLIMIT_AS` para memoria. §6 lo lista
en la fila de Nivel 0.

En Darwin, `RLIMIT_AS` es alias de `RLIMIT_RSS` (E1) y **`setrlimit` sobre él
devuelve `EINVAL`** (E2): no es que el límite se imponga mal, es que no se
puede fijar. `RLIMIT_DATA` tampoco (E3). El control E4 descarta que sea una
restricción del entorno.

Consecuencia: `max_memory_bytes` es inejecutable en una de las dos plataformas
que O1 declara. El matiz ya declarado en el pre-proyecto («limita memoria
virtual, no RSS») es correcto para Linux e irrelevante para macOS, donde no
hay límite alguno.

### H2 · C — La compuerta (a) de CPU es cooperativa en macOS

§3/D1 funda el proyecto en que «el reloj y el freno viven fuera del código
gobernado» y en que «el ejecutado no puede influir en sus propios límites».

En Darwin, `RLIMIT_CPU` mata al hijo cooperativo (E5) pero **no al que ignora
`SIGXCPU`**: sobrevive 15 s de CPU con límite duro de 5 s (E6). Y sobrevive
también con `soft == hard` (E7), que es la mitigación estándar y la que yo
mismo había propuesto.

Dos líneas —`signal.signal(signal.SIGXCPU, signal.SIG_IGN)`— anulan la
compuerta. Es exactamente la categoría de control que el pre-proyecto rechaza
en su primera línea: mecanismo que depende de que el gobernado coopere.

### H1+H2 · Consecuencia conjunta sobre O1

Estado real de «lo que el OS ve» en Nivel 0, macOS:

| Magnitud | Estado real |
|---|---|
| Memoria | **No disponible** (`EINVAL`) |
| CPU | **Sólo cooperativa** (evadible en dos líneas) |
| Tiempo de pared | Sí — supervisor + `killpg`. El único mecánico. |
| Procesos (`NPROC`) | Existe, pero por-uid, no por árbol (H4) |

El criterio de aceptación de O1 —«una acción que excede presupuesto […]
termina en el estado terminal correspondiente, nunca en un hang»— **no se
cumpliría hoy en macOS** frente a un ejecutado no cooperativo. O1 combina
«multiplataforma (macOS y Linux), sin root» con «las tres compuertas activas
simultáneamente»; con la especificación actual, esas dos cláusulas son
incompatibles.

**Propuesta P1 (§6).** En Nivel 0, CPU y memoria las vigila el **supervisor
por muestreo** (`getrusage(RUSAGE_CHILDREN)` para CPU; RSS por `proc_pidinfo`
en macOS y `/proc/<pid>/statm` en Linux), con `killpg` como brazo ejecutor.
`setrlimit` pasa a **refuerzo opcional en Linux**, no a mecanismo primario.
Esto es *más* fiel a D1 que el diseño actual —el freno queda entero fuera del
proceso gobernado— y su costo es declarable en §7: **la granularidad del
muestreo; un pico entre dos muestras escapa**. Es un límite honesto y acotado,
a diferencia de "dos líneas lo anulan".

### H3 · M — `max_wall_seconds` y `deadline_seconds` sin regla de precedencia

§5.1 declara `max_wall_seconds` «redundante con (c), deliberadamente». §4 exige
que toda acción termine en **exactamente un** estado terminal. Si el tiempo de
pared vence, no está definido si el estado es `budget_exceeded` o
`deadline_exceeded`, y el criterio de aceptación de O1 distingue ambos casos.

**Propuesta:** retirar `max_wall_seconds` del presupuesto —el tiempo de pared
ya tiene dueño en la compuerta (c)— o, si se conserva, declarar que toda
violación de reloj de pared produce `deadline_exceeded`.

### H4 · M — `RLIMIT_NPROC` no acota el árbol de la acción

La fila de Nivel 0 en §6 lista «PIDs» junto a CPU y memoria. `RLIMIT_NPROC`
es **por user id** (E8): no acota los descendientes de la acción, y un valor
bajo puede dejar al operador sin capacidad de lanzar procesos en toda su
sesión. No es equivalente a `pids.max` de cgroups.

**Propuesta:** retirar «PIDs» de Nivel 0, o marcarlo con el mismo matiz
explícito que se dio a la memoria. El control real de PIDs es Nivel 2.

### H5 · M — El log append-only lo es por convención, y no está en §7

§5.5 registra todo evento de compuerta en «un log append-only del supervisor»
y presenta la auditabilidad como consecuencia gratuita. Un archivo local es
truncable y reescribible por cualquiera con permiso de escritura: es
confianza declarativa presentada como propiedad, que es precisamente lo que
el documento persigue en otros lugares. Además, §7 no lo lista entre los
límites.

**Propuesta:** encadenar por hash cada entrada (`sha256(entrada ‖ hash_previo)`,
stdlib, ~10 líneas) → **manipulación detectable**; y declarar en §7 lo que eso
*no* cubre: **el truncamiento de cola no es detectable sin números de
secuencia más un ancla externa**. Alternativa igualmente aceptable: declararlo
en §7 como no resistente a manipulación y no hacer nada más. Lo que no es
aceptable es el silencio actual.

### H6 · M — La reserva de presupuesto de tokens está mal dimensionada

D2 y §5.1 modelan el chequeo pre-vuelo «contra el `max_tokens` declarado»
(patrón OpenRouter). En bucles de agente el costo lo domina el **input**: un
contexto de 200k tokens con `max_tokens = 1024` reservaría una fracción
mínima del gasto real, y la compuerta preventiva —que es el objeto de D2—
quedaría desactivada en la práctica aunque la contabilidad posterior corrija.

**Propuesta:** reservar `coste(input) + coste(max_tokens)`. Con una
advertencia sobre el costo de esta propuesta: contar el input con exactitud
exige un tokenizador, es decir **una segunda dependencia fuera de stdlib**,
lo que rozaría el criterio de independencia de §2. La versión compatible con
ese criterio es una cota superior heurística (bytes/4 con factor de
seguridad) declarada como tal, o reservar contra un tope de contexto
declarado en el descriptor.

### H7 · m — Faltan estados de admisión; `executed` es ambiguo

Un descriptor malformado o un binario inexistente hoy sólo pueden colapsar en
`capability_rejected`, que sería falso. §5.4 refuerza la confusión al decir
que sin plazo declarado el rechazo es «igual que sin capacidad». Y no está
dicho si un comando que sale con código 1 termina en `executed`.

**Propuesta:** añadir `admission_rejected` a la lista canónica; declarar que
`executed` significa «terminó sin violar compuerta», con el código de salida
como **dato del resultado, no como estado** — coherente con el no-objetivo de
gobernanza de negocio.

### H8 · m — §5.4 omite la muerte del supervisor

§5.4 acota la garantía de terminación a los escapes por `setsid` y a D-state.
§7 sí registra que el supervisor puede caer y llevarse su freno. La acotación
de §5.4 —a la que O4 remite explícitamente— debería enumerar también ese caso,
que es el más probable de los tres.

*Sin propuesta de estado terminal nuevo:* ver R3.

### H9 · m — La semántica de expiración de la capacidad no está declarada

§5.3 valida la ventana temporal «en el punto de entrada». Con eso, una acción
de horas admitida con una capacidad que expira en un minuto corre hasta el
final. Es la semántica estándar de OAuth (el token válido al momento de la
petición autoriza esa petición) y es defendible; la alternativa —acotar el
plazo por la expiración— también lo es. El defecto no es la elección, es que
no está dicha.

**Propuesta:** declarar cuál rige. Si se elige acotar, la forma mecánica es
`deadline_efectivo = min(deadline_seconds, exp_cadena − ahora − tolerancia)`,
y `capability_rejected` si el resultado es ≤ 0.

### H10 · m — Tolerancia de reloj contra expiración corta

§5.3 fija tolerancia de ±60 s y §5.3 declara la expiración corta como
mecanismo primario de mitigación. Un token con `exp` de 60 s sigue siendo
aceptable hasta 120 s después de su emisión —el doble de su vida prevista—
frente a un verificador con el reloj atrasado dentro de la tolerancia.

**Propuesta:** declarar un invariante validado en admisión, del tipo
`exp − nbf ≥ k · tolerancia` con `k` explícito, o reducir la tolerancia y
exigir sincronía. La cifra concreta importa menos que el que la relación
quede declarada.

### H11 · m — `depth`: no está dicho si ektel emite delegaciones o sólo las consume

D3 define las compuertas sobre «la acción completa con su árbol de
sub-acciones delegadas», pero O1 es un ejecutor de proceso único y no hay
canal especificado por el cual el ejecutado solicite una sub-acción. Validar
`depth` al admitir —rechazar una cadena demasiado profunda— sí es
implementable en el MVP y no es vacío. Lo que no tiene mecanismo es el árbol
de D3.

**Propuesta:** declarar en §7 que en el MVP ektel **consume** cadenas
delegadas pero no las **emite**, y que por tanto D3 se ejerce sobre acciones
sin árbol. Si se quiere el árbol, especificar el canal mínimo (socket unix del
supervisor; el supervisor descuenta del presupuesto y del plazo restantes del
padre) como incremento posterior.

### H12 · m — Ventana de retención de nonces no declarada

La protección contra repetición de §5.3 exige que el supervisor recuerde
nonces vistos, lo que es estado con una retención que nadie fijó.

**Propuesta:** añadir expiración propia a la invocación (segundos) y acotar la
retención de nonces a esa ventana.

### H13 · m — `preexec_fn` y el supervisor con reloj

Si el supervisor implementa el reloj de D1 como hilo y aplica límites vía
`preexec_fn` de `subprocess`, cae en un peligro documentado de CPython (fork
desde proceso multihilo) que **no emite ningún aviso** (E9).

**Propuesta:** supervisor de un solo hilo con `select`/`signal` para el reloj,
o un binario intermedio `ektel-exec` que aplique los límites en su propio
`main` antes de `execve`.

### H14 · m — El canal de interrupción no puede ser una señal del terminal

Para que `killpg` funcione, el ejecutado debe estar en su propio grupo de
proceso; las señales que el terminal envía a su grupo en primer plano no lo
alcanzan. La vía de interrupción del MVP tiene que ser una orden dirigida al
supervisor, no una señal tecleada en la terminal. El README describe el canal
A0 como «manual — la terminal de quien lo opera», formulación compatible con
ambas lecturas: conviene precisarla.

### H15 · m — Canonicalización: firmar los bytes que se transportan

La decisión abierta #1 (CBOR canónico vs. binario propio determinista) es el
punto criptográficamente más frágil del diseño. Una discrepancia de
canonicalización entre firmante y verificador es una de las formas clásicas
de romper un esquema de firma, y escribir un serializador canónico a mano en
un proyecto que presume de stdlib maximiza esa exposición.

**Propuesta:** firmar sobre **los bytes tal como se transportan**, de modo que
el verificador nunca re-serialice para verificar. Elimina la clase entera de
fallos, y vuelve la decisión #1 una cuestión de conveniencia y no de
seguridad.

---

## 4. Registro de correcciones a esta misma revisión

Se listan porque el criterio que el pre-proyecto aplica a sí mismo —declarar
los límites antes de que los descubra otro— debe aplicarse también a quien lo
revisa. Todo lo siguiente estuvo en la primera pasada y fue retirado o
rebajado en la segunda.

**R1 — Retirado por falso.** Sostuve que la firma de invocación de §5.3, al no
cubrir la cadena de token, permitía recombinar una firma válida con un token
más amplio. Es falso: la cadena debe terminar en la clave pública del
invocador, de modo que cualquier token que un invocador pueda emparejar con
su firma es uno que le fue legítimamente delegado. No hay escalada de
privilegio. Sobrevive únicamente H12. Ligar la firma a `H(cadena_token)` sigue
siendo higiene y claridad de auditoría, pero **no corrige ninguna
vulnerabilidad, porque no la había**. Es el error más grave de esta revisión:
una vulnerabilidad inexistente afirmada sobre un documento de seguridad.

**R2 — Refutado empíricamente.** Propuse `soft == hard` como mitigación del
`SIGXCPU` ignorable. E7 la refuta en macOS. El hallazgo H2 es mayor de lo que
la primera pasada estimó, y la solución que ofrecía no funciona.

**R3 — Severidad rebajada, propuesta retirada.** Presenté como contradicción
bloqueante que O4 («toda acción termina en un estado canónico») chocara con
§7 (el supervisor puede caer). No es contradicción: O4 remite explícitamente
a la acotación de §5.4. El defecto real es sólo que §5.4 no enumera ese caso
(H8). Además, mi propuesta de añadir un estado `unknown` era **peor que el
documento**: exige reconciliación al reiniciar, es decir estado persistente y
protocolo de recuperación, que §2.3 excluye del MVP deliberadamente.

**R4 — Aritmética corregida.** Afirmé que la tolerancia de ±60 s podía triplicar
la vida de un token de 60 s (180 s). El número correcto es el doble (120 s);
los 180 s cuentan la ventana `nbf − 60 → exp + 60`, que no es la vida útil de
un token concreto. Ver H10.

**R5 — Propuesta incompleta.** Ofrecí el hash-chain del log como solución. Sólo
detecta modificación; el truncamiento de cola deja una cadena consistente.
Corregido dentro de H5.

**R6 — Costo omitido.** Propuse contar tokens de input antes de enviar sin
señalar que exige un tokenizador, es decir una segunda dependencia fuera de
stdlib, contra el criterio de §2 que yo estaba defendiendo. Corregido dentro
de H6.

**R7 — Inferencia no verificada.** Deduje que «la terminal de quien lo opera»
del README significaba Ctrl-C, y presenté como contradicción lo que era una
lectura mía de una intención ajena. La conclusión técnica sobrevive por otra
vía; el encuadre no. Ver H14.

**R8 — Subestimación.** Escribí que `RLIMIT_AS` en macOS «probablemente no
hace nada». No se puede ni fijar (E2).

Recuento: de 14 observaciones iniciales, **1 retirada por falsa**, **1 con la
propuesta refutada**, **3 con severidad rebajada**, **3 con propuestas
defectuosas o más caras de lo declarado**, **5 confirmadas** (dos de ellas
agravadas por la evidencia).

---

## 5. Propuestas de alcance

**P1 — Supervisión por muestreo en Nivel 0.** Detallada en H1+H2. Es la única
propuesta de este documento que la evidencia fuerza en vez de sugerir.

**P2 — Convertir media regla de contrato en mecanismo.** §4 y §6 declaran «las
credenciales nunca entran al perímetro» como contrato del despliegue hasta
Nivel 1+. Eso es más pesimista de lo necesario: el supervisor construye el
entorno del hijo, y un `env` por **allowlist** (no denylist) es imposición
mecánica disponible ya en Nivel 0. Elimina la vía dominante de fuga —variables
heredadas del shell— y deja como residual sólo el sistema de archivos
(`~/.aws/credentials`, `~/.netrc`, etc.), que sí es Nivel 1. Convierte una
promesa en compuerta, que es la tesis del proyecto.

**P3 — Cortar el alcance de O1.** Formato de token con cadenas Ed25519, `depth`,
denylist, prueba de posesión, nonces, frontera de tokens, límites de recursos,
grupos de proceso, log y adaptador no es «un esqueleto mínimo». Corte
sugerido:

- **MVP-0:** compuerta (c) completa; compuerta (a) por muestreo del supervisor;
  capacidad de **un solo bloque raíz firmado** con `depth` validado pero sin
  emisión de delegaciones (H11); entorno por allowlist (P2); log encadenado
  por hash (H5). Sin frontera de tokens. Satisface el criterio de aceptación
  de O1 y es falsable.
- **MVP-1:** cadena de delegación, canal de sub-acciones, frontera de tokens.

**P4 — Escribir la suite de escape antes que el runtime.** Es la única
propuesta que ambas pasadas confirman por vías independientes, y la que
habría producido H1 y H2 el primer día. Cada test que falla es una línea del
§7 ganada con evidencia en vez de con prosa. Conjunto mínimo:

1. `setrlimit(RLIMIT_AS)` sobre la plataforma objetivo → **falla hoy en macOS**
2. Hijo que ignora `SIGXCPU` bajo `RLIMIT_CPU` → **falla hoy en macOS**
3. Hijo que hace double-fork + `setsid` y sobrevive a `killpg`
4. Proceso en D-state y su efecto sobre el plazo
5. Binario con gran reserva de espacio virtual (Go, JVM) bajo límite de
   memoria en Linux → mide el falso positivo de `RLIMIT_AS`
6. Hijo que lee una credencial del sistema de archivos → delimita P2
7. Supervisor muerto con hijo vivo → delimita H8

**P5 — Firmar los bytes transportados.** Detallada en H15. Cierra la decisión
abierta #1 por la vía que elimina una clase de fallo en vez de gestionarla.

---

## 6. Lo que esta revisión no verificó

- **Nada en Linux.** H1 y H2 son hallazgos de macOS. En Linux `RLIMIT_AS` y
  `RLIMIT_CPU` se comportan como el pre-proyecto asume, según su
  documentación, pero eso tampoco lo verifiqué aquí.
- **Una sola máquina**, un solo `uname`, una sola versión de Python (3.9.6 del
  sistema), y dentro del sandbox de la herramienta de ejecución. El control
  E4 aísla la causa de E2/E3 a esos recursos concretos, pero una interacción
  con el sandbox no puede excluirse al 100 %.
- **Escape por `setsid` y D-state** (P4.3, P4.4): no probados. Los mantiene el
  pre-proyecto como límites declarados y siguen sin evidencia en ninguna
  dirección.
- **Fork bomb / `RLIMIT_NPROC` bajo carga:** deliberadamente no ejecutado; el
  riesgo es justamente el que denuncia H4.
- **Las fuentes del §9 del pre-proyecto.** No verifiqué ninguna cita, ningún
  identificador de arXiv, CVE ni número de incidente. Todo lo que este
  documento afirma sobre el estado del arte lo hereda del pre-proyecto sin
  comprobar.
- **La criptografía.** Ni el formato de §5.3 ni sus propiedades fueron
  analizados formalmente. H15 es una observación de ingeniería sobre una clase
  conocida de fallo, no un análisis criptográfico.

---

## Anexo A — Reproducción de la evidencia

```python
# E1–E4 · disponibilidad de los límites de memoria
import ctypes, ctypes.util, os, resource
libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
class RL(ctypes.Structure):
    _fields_ = [('cur', ctypes.c_uint64), ('max', ctypes.c_uint64)]
for res, name in [(5, 'RLIMIT_AS'), (2, 'RLIMIT_DATA')]:
    r = RL(128*1024*1024, 128*1024*1024); ctypes.set_errno(0)
    rc = libc.setrlimit(ctypes.c_int(res), ctypes.byref(r))
    e = ctypes.get_errno()
    print(f'{name}: rc={rc} errno={e} {os.strerror(e) if e else "ok"}')
# control: estos deben poder bajarse
for n in ['RLIMIT_NOFILE', 'RLIMIT_CPU', 'RLIMIT_NPROC']:
    resource.setrlimit(getattr(resource, n), (64, 64))
    print(n, 'bajado ok')
```

```python
# E5–E7 · RLIMIT_CPU frente a un hijo no cooperativo
# uso: python3 este.py {ignorar|normal}   (E7: cambiar a setrlimit(..., (2, 2)))
import resource, signal, sys
resource.setrlimit(resource.RLIMIT_CPU, (1, 5))
if sys.argv[1] == 'ignorar':
    signal.signal(signal.SIGXCPU, signal.SIG_IGN)
def cpu():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime      # CPU real, no reloj de pared
x = 0
while True:
    x += 1
    if x % 5_000_000 == 0:
        c = cpu()
        if c > 15:
            print(f'SOBREVIVIO con {c:.1f}s de CPU (soft=1 hard=5)'); sys.exit(0)
```

Resultado esperado en Darwin 25.5.0: `EINVAL` en ambos límites de memoria;
`exit=152` con `normal`; supervivencia indefinida con `ignorar`, también si
`soft == hard`.

---

## Firma

Revisión realizada por **Claude Opus 5** (`claude-opus-5`), Anthropic.
**Fecha:** 2026-08-14.
**Documento revisado:** `docs/pre-proyecto.md`, revisión del 2026-08-14, y
`README.md`, commit `325beef`.
**Método:** dos pasadas, una documental y una empírica; la segunda corrigió a
la primera en los ocho puntos del §4.

**Veredicto:** el pre-proyecto no tiene defecto estructural, y su §7 es su
mejor activo. Tiene una afirmación central falsa en una de sus dos plataformas
declaradas (H1, H2), que invalida el criterio de aceptación de O1 en macOS y
es reparable con P1 sin tocar ninguna de las tres compuertas ni el principio
de independencia. Lo que la evidencia recomienda no es corregir el documento:
es que el próximo commit sea la suite de P4, y que el documento se corrija con
lo que esa suite devuelva.
