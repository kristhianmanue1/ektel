# ektel — consolidación corregida para consenso

**Estado:** candidato no vinculante para consenso. Recopila el preproyecto,
las revisiones externas de rondas 2, 3 y 4, y una ronda adversarial específica
sobre esta consolidación. Las correcciones de esa última ronda ya están
integradas. No describe una implementación existente ni sustituye por sí solo
los documentos históricos.

**Fecha:** 2026-08-14 · **Versión documental:** 0.3 · **Siguiente acto:**
consenso explícito sobre las decisiones de §11.

**Autoría:** consolidación realizada por **Codex (OpenAI)**. La ronda
adversarial asociada fue realizada por el mismo agente y, por tanto, es
**autorrevisión, no verificación independiente**. Dos análisis externos
posteriores fueron contrastados para la versión 0.3; sus observaciones se
registran en el documento adversarial. Método: lectura cruzada del corpus,
reproducciones locales declaradas y comprobación de consistencia interna.

## 1. Propósito y autoridad

Este documento tiene cuatro funciones:

1. reunir en un solo lugar lo que sobrevivió las revisiones;
2. separar propiedades demostradas, hipótesis y decisiones de producto;
3. proponer un alcance realizable para el primer incremento;
4. exponer las preguntas que necesitan consenso, sin cerrarlas por redacción.

Hasta que exista ese consenso, prevalecen los hechos reproducibles sobre las
afirmaciones incompatibles del preproyecto, pero ninguna propuesta nueva se
considera todavía contrato del proyecto.

### 1.1 Genealogía documental

- `README.md`: intención pública; declara correctamente que no hay código.
- `pre-proyecto.md`: especificación original, aún no actualizada con las
  rondas posteriores.
- `revision-externa-2026-08-14.md`: ronda 2; primera refutación empírica de
  los mecanismos de CPU y memoria en Darwin.
- `revision-externa-r3-2026-08-14.md`: ronda 3; reproduce E1–E8, demuestra que
  `RUSAGE_CHILDREN` es post mortem y verifica una parte de las citas.
- `revision-externa-ronda4-2026-08-14.md`: ronda 4; reconcilia la colisión de
  numeración, propone P1-bis y somete a crítica la elección de lenguaje.
- `revision-adversarial-consolidacion-2026-08-14.md`: revisión de este texto;
  sus correcciones aceptadas se enumeran en §13.

Antes de preparar esta versión, todo `docs/` permanecía fuera del historial
Git. La precondición documental es que el commit y tag que contengan la versión
0.3 fijen esta genealogía antes del consenso (§11.1).

## 2. Vocabulario de garantías

La palabra *compuerta* sólo es útil si declara su fuerza. Se adoptan estas
categorías para la discusión:

| Clase | Significado |
|---|---|
| **G0 · admisión** | Rechaza antes de iniciar cuando un descriptor o una capacidad no cumplen una condición verificable. |
| **G1 · límite preventivo** | La plataforma impide superar el límite en la frontera del recurso, sujeto a los límites documentados del mecanismo. |
| **G2 · límite reactivo con sobreconsumo acotado** | El supervisor observa y termina; existe una cota demostrada del exceso entre observaciones completas. |
| **G3a · transición eventual** | Si el supervisor sigue vivo y vuelve a ser planificado, produce una transición; la latencia no tiene cota dura. |
| **G3b · observación best-effort** | Puede detectar un exceso después de ocurrido, pero puede perder eventos y no garantiza máximo ni supervivencia del host. |
| **G4 · servicio mediado** | Sólo gobierna operaciones que atraviesan una frontera controlada por ektel. |
| **G5 · declaración** | Valida forma o registra intención; no demuestra la verdad de lo declarado. |

Ninguna garantía G2 se considerará tal hasta probar que la contabilidad cubre
procesos vivos y efímeros del alcance declarado. Mientras eso no exista, el
muestreo de CPU se clasifica provisionalmente como G3b.

La clase se acompaña con un eje independiente de **modo de fallo**:

- **F-R · ruidoso:** el mecanismo señala que perdió la propiedad o rechaza;
- **F-S · silencioso:** produce un valor plausible o ausencia de alarma aunque
  la propiedad haya fallado;
- **F-M · mixto:** tiene caminos ruidosos y silenciosos.

Una medición G3b/F-S no se presenta como compuerta ni entra en decisiones de
terminación hasta que la suite delimite su cobertura.

### 2.1 Estados de evidencia

- **V:** verificado mediante ejecución conservada como prueba reproducible.
- **L:** ejecución local única o en una sola ronda, aún no independiente.
- **R:** reproducido en más de una implementación o ronda, pero todavía no
  conservado en la suite del repositorio.
- **D:** respaldado sólo por documentación o fuente externa.
- **I:** inferencia técnica razonada, aún no ejecutada.
- **P:** propuesta de diseño o producto.
- **N:** no verificado.

Las ejecuciones narradas cuentan como L, o R cuando convergen realmente entre
rondas/implementaciones; nunca como V hasta convertirse en pruebas versionadas
con expectativas automáticas.

## 3. Tesis que sobrevive

ektel pretende ejecutar acciones potencialmente no cooperativas bajo control
de un supervisor separado. El proceso ejecutado no debe poseer el reloj, la
decisión de admisión ni el brazo de terminación que lo gobiernan.

La tesis se descompone en tres responsabilidades, evitando presentarlas como
si tuvieran la misma fuerza:

1. **Admisión autorizada:** validar descriptor, capacidad y vigencia antes de
   iniciar (G0).
2. **Ejecución restringida:** aplicar los límites que la plataforma realmente
   pueda imponer o medir, identificados individualmente como G1–G3.
3. **Resolución observada:** cuando vuelve a ser planificado después del plazo,
   el supervisor deja de esperar y emite un resultado tipado; un OS de propósito
   general no ofrece por sí solo una latencia máxima de despertar. Esto tampoco
   implica que todo descendiente haya muerto ni que el estado externo se haya
   reparado.

Tokens y costo no forman parte de la ejecución local: son una responsabilidad
G4 opcional de una frontera de proveedor posterior.

Las rondas 2–4 refutaron mecanismos G1–G3, no la posibilidad estructural de
G0. Validar localmente estructura, firma, vigencia, PoP y nonce no depende del
scheduler ni del árbol de procesos. Eso vuelve G0 el núcleo más estable y la
novedad prioritaria de MVP-0, **pero no lo vuelve evidencia**: el protocolo
sigue en P/N hasta implementarse, probar vectores negativos y recibir revisión
criptográfica.

## 4. Alcance y modelo de amenaza propuestos

### 4.1 MVP-0

El primer incremento es un supervisor local G0-first, sin root y de un solo
nodo, para **admisión autorizada y resolución observada**. No es frontera contra
código hostil y no promete proteger al host frente a asignaciones explosivas,
escapes de grupo, explotación del kernel o credenciales accesibles por el
sistema de archivos.

El término *accidental* describe intención, no velocidad ni daño. Por tanto,
ningún mecanismo de muestreo garantiza que el host sobreviva a una fuga rápida,
aunque esa fuga no haya sido deliberada.

### 4.2 Fuera de MVP-0

- aislamiento de red o filesystem;
- ejecución adversarial o multitenant;
- cgroups, namespaces, Landlock, seccomp, Seatbelt, VM o sandbox fuerte;
- delegación emitida por ektel y árboles de subacciones;
- presupuesto preventivo de tokens o costo;
- revocación distribuida;
- garantía de recuperación tras muerte del supervisor.

## 5. Estado consolidado por mecanismo

| Magnitud o propiedad | macOS / Darwin | Linux | Clase | Modo de fallo | Evidencia |
|---|---|---|---|---|---|
| Admisión por descriptor | Implementable en proceso | Ídem | G0 | F-R por diseño | P |
| Capacidad firmada raíz | Dependencia Ed25519 en Python | Ídem | G0 | F-R previsto; protocolo aún no probado | P/N cripto |
| Alcance de “recurso” | Verificable contra descriptor; no confina fs/red del hijo | Ídem | G0 para identidad; G5 si se interpreta como confinamiento | F-S por sobreinterpretación | P |
| Plazo del registro | Timer propuesto; OS no-RT | Ídem | G3a | F-M: despierta tarde o desaparece con supervisor | I/N; no se ejecutó integración de timer |
| Muerte del grupo | `killpg`; no cubre `setsid`, D-state ni supervisor muerto | Ídem | Brazo de terminación | F-M | V Darwin para grupo observado; N Linux |
| CPU por `RLIMIT_CPU` | Evaluable por el hijo e ignorable | Esperado como refuerzo | No G1 en macOS | F-S en Darwin | V Darwin con CPU por `wait4`; D/N Linux |
| `RUSAGE_CHILDREN` | Cero mientras hijo vive; acumula tras `wait` | Semántica esperada igual | No fuente de vivo | F-S si se usa para muestreo | V Darwin; N Linux en suite |
| CPU por muestreo | `proc_pidinfo` o `/bin/ps` | Candidato `/proc` | G3b | F-S: procesos efímeros/churn | R del hueco; L de lecturas; N Linux |
| Memoria por `RLIMIT_AS` | Rechazado en entorno probado | Esperado sobre espacio virtual | No disponible macOS; candidato G1 imperfecto Linux | F-R al configurar en macOS; falsos positivos Linux | V Darwin; D/N Linux |
| RSS por muestreo | Lectura de vivos demostrada; picos pueden perderse | Candidato `/proc` | G3b | F-M: subcuenta picos y sobrecuenta compartido | R lectura Darwin; N como contención/Linux |
| PIDs por `RLIMIT_NPROC` | Por UID, no por acción | Ídem; no es `pids.max` | No compuerta por acción | F-S si se atribuye al árbol | D |
| Aplicación pre-`exec` | Shim por auto-reexec probado en Go | Ídem; alternativas por lenguaje | Mecanismo auxiliar | F-M según resolución de ruta | L: E18 |
| Tokens y costo | Sólo llamadas mediadas | Ídem | G4 | F-S para llamadas que evitan frontera | P |
| `max_iterations` | Invisible para comando arbitrario | Ídem | Sin garantía | F-S | P/N |
| Reparación externa | Declaración del despachador | Ídem | G5 | F-S | P |
| Log local | Reescribible; hash-chain parcial | Ídem | Registro, no auditoría fuerte | F-S | P |

### 5.1 Sobre la CPU muestreada

La cota teórica `T × C` sólo aplica al consumo ocurrido entre dos observaciones
**completas** del mismo conjunto de procesos. El mecanismo descrito todavía no
demuestra que incorpore procesos que nazcan y terminen entre muestras, churn de
descendientes ni CPU perdida al cambiar de grupo. No se adopta la cota como
propiedad del producto hasta cerrar esos casos.

### 5.2 Sobre la memoria muestreada

El muestreo de RSS puede disparar una terminación después de observar un
umbral, pero no impide el pico, no acota el exceso y no garantiza que el host
sobreviva hasta la siguiente muestra. Se presenta como telemetría reactiva,
no como límite de memoria.

### 5.3 Sobre el plazo

El plazo solicita una transición del **registro observado por un supervisor
vivo** a `deadline_exceeded` cuando el supervisor vuelve a ejecutarse. Sin un
scheduler de tiempo real o watchdog con cota demostrada, no garantiza una
latencia máxima exacta desde el instante nominal del deadline. Tampoco
garantiza:

- muerte de procesos que escaparon con `setsid`;
- terminación de procesos en estado ininterrumpible;
- reparación del estado externo;
- emisión de resultado si el supervisor muere sin un registrador externo.

No existe una graduación general de G3a a G2 mediante benchmarks en un OS no
RT: una caracterización sólo produce una distribución del entorno probado, no
una cota universal.

### 5.4 P1-bis como mecanismo candidato, no propiedad adoptada

La especificación extensa permanece en la ronda 4 §1.3. Para que esta
consolidación sea autosuficiente, el candidato se resume así:

- la unidad contable es el grupo de proceso, no sólo el PID raíz;
- en macOS se lee CPU/RSS con `proc_pidinfo` o `/bin/ps -g <pgid>` mediante
  ruta absoluta; la ronda 4 reportó aproximadamente 2.7 ms por muestra;
- en Linux se proponen `/proc/<pid>/stat` para CPU y
  `/proc/<pid>/statm` para RSS;
- para memoria se observa RSS, nunca espacio virtual;
- sumar RSS sobrecuenta páginas compartidas;
- `setsid` escapa tanto de `killpg` como del muestreo por pgid;
- la cota `T × C` no se acepta mientras procesos efímeros queden fuera.

Mecanismo Linux a probar: sumar `utime + stime + cutime + cstime` del padre
superviviente puede recuperar CPU de hijos ya recogidos. No cubre por sí solo
subárboles cuyo padre también terminó ni procesos reparentados. La suite debe
comparar un padre que crea y recoge N hijos breves contra una medición de
referencia. Hasta entonces es I, no una reparación.

## 6. Descriptor mínimo propuesto

MVP-0 acepta un documento JSON con versión explícita y, al menos:

- `action_id`;
- `command` como ruta absoluta;
- `args` como lista de bytes o cadenas con codificación definida;
- `cwd` explícito;
- `env` construido por allowlist;
- política explícita para stdin;
- `deadline_seconds`;
- presupuesto opcional por magnitud, acompañado de la clase de garantía que
  la plataforma ofrece;
- referencia a capacidad raíz e invocación firmada;
- política de reparación declarada;
- versión de esquema.

La identidad de ejecución debe vincular comando, argumentos, cwd, entorno,
stdin relevante, presupuesto, plazo, identificador de acción y nonce. Queda
abierto si además se vincula el digest del ejecutable y de archivos auxiliares;
sin ello, una ruta estable puede resolver contenido distinto entre firma y
ejecución.

No se admite YAML en MVP-0: una única codificación reduce ambigüedad de tipos y
superficie de canonicalización.

## 7. Capacidad mínima propuesta

MVP-0 consume una capacidad raíz firmada, expirable y no delegable. No emite
subdelegaciones. La validación mínima incluye:

1. versión y estructura;
2. bytes firmados transportados sin reserialización para verificar;
3. cadena de confianza configurada localmente;
4. `nbf` y `exp` con regla explícita de reloj;
5. acción y recurso autorizados con semántica cerrada;
6. proof-of-possession sobre la identidad completa de ejecución;
7. nonce con alcance, retención y comportamiento tras reinicio definidos.

La semántica propuesta para MVP-0 es **validez en admisión**: una capacidad
válida al iniciar autoriza esa ejecución hasta su plazo propio. La alternativa
de truncar el plazo a `exp` permanece como pregunta de consenso (§11).

Delegación, profundidad, denylist distribuida y canal de subacciones pasan a
un incremento posterior y requieren revisión criptográfica específica. La
capacidad raíz de MVP-0 también requiere vectores negativos; “usar Ed25519” no
demuestra que el protocolo sea seguro.

## 8. Resultado y estados propuestos

Se separa la fase de admisión de la ejecución:

### 8.1 Resultados antes de iniciar

- `admission_rejected`: esquema, versión, comando o parámetro inválido;
- `capability_rejected`: firma, vigencia, permiso, PoP o nonce inválido;
- `start_failed`: no fue posible crear o ejecutar el proceso.

### 8.2 Resultados después de iniciar

- `executed`: el proceso terminó sin que una compuerta observada lo detuviera;
- `budget_exceeded`: una magnitud presupuestada disparó el mecanismo declarado;
- `deadline_exceeded`: el supervisor dejó de esperar al vencer el plazo;
- `terminated`: orden externa aceptada antes del plazo;
- `supervision_failed`: el supervisor detectó que perdió una capacidad de
  medición o control y pudo emitir resultado.

Cada resultado incluye, cuando exista: `exit_code`, señal, timestamps,
mediciones, garantía aplicada, causa tipada y truncamiento explícito de salida.
`executed` no significa éxito de negocio.

Si el supervisor muere sin observador o almacenamiento externo, no existe un
estado terminal emitido. Esa situación es una ausencia de resultado, no un
estado que el proceso muerto pueda producir. La reconciliación pertenece a un
nivel de despliegue posterior.

`max_wall_seconds` se retira: el reloj de pared tiene un único dueño,
`deadline_seconds`. Si plazo y presupuesto se observan violados en el mismo
ciclo, se evalúa primero el plazo y el resultado es `deadline_exceeded`.

## 9. Incrementos propuestos

### 9.1 Caracterización ejecutable

Antes de afirmar garantías, convertir los anexos en una suite versionada para
macOS y Linux:

1. disponibilidad y semántica de rlimits;
2. hijo que ignora `SIGXCPU`;
3. CPU de proceso vivo y proceso efímero;
4. churn y árboles de descendientes;
5. double-fork + `setsid`;
6. gran reserva virtual y pico rápido de RSS;
7. muerte del supervisor con hijo vivo;
8. credenciales heredadas por entorno y filesystem;
9. precedencia simultánea de plazo y presupuesto;
10. carga y costo del mecanismo de muestreo.

Los casos peligrosos —fork bomb y D-state— necesitan entorno aislado o una
simulación justificada; no deben ejecutarse indiscriminadamente en CI.

**Primera ejecución conservada:** Darwin 25.5.0 ARM, Python 3.9.6,
2026-08-14. Comando: `python3 -m unittest discover -s tests/escape -v`.
Resultado: 4 éxitos, 1 omitida por ser exclusiva de Linux. Quedaron verificadas
en este entorno la indisponibilidad de `RLIMIT_AS`, la supervivencia con
`SIGXCPU` ignorado midiendo CPU real mediante `wait4`, la semántica post mortem
de `RUSAGE_CHILDREN` y la terminación del grupo observado por `killpg`. El caso
Linux de `cutime/cstime` no se ejecutó y permanece N.

### 9.2 MVP-0

- descriptor mínimo;
- capacidad raíz no delegable;
- identidad de ejecución completa;
- entorno por allowlist;
- grupo de proceso;
- plazo y terminación;
- estados tipados;
- ejemplo ajeno a Aria.

CPU/RSS no alimentan decisiones de MVP-0. Su instrumentación vive primero en
la suite: una medición G3b/F-S dentro del runtime invitaría a tratar un número
incompleto como compuerta.

### 9.3 MVP-1

- mecanismos preventivos Linux verificados;
- presupuesto CPU/memoria con garantías por plataforma;
- persistencia operativa y watchdog opcional;
- endurecimiento de filesystem y red.

### 9.4 Incrementos posteriores

- delegación y subacciones;
- frontera de tokens/costo con reserva de input y output;
- revocación distribuida;
- aislamiento adversarial y multitenancy.

## 10. Lenguaje

No hay evidencia suficiente para declarar un ganador universal. La decisión se
separa por horizonte:

- la suite de caracterización puede escribirse en Python sin comprometer el
  lenguaje del runtime;
- Python favorece legibilidad y velocidad, pero necesita dependencia Ed25519,
  versión mantenida y endurecimiento del intérprete;
- Go ofrece cripto en stdlib y mejores primitivas declarativas en Linux, pero
  no elimina dependencias de sistema ni resuelve los límites de Darwin;
- Rust permanece como hipótesis no ejecutada en las revisiones.

La elección del runtime se toma después de fijar plataforma y alcance. Si se
elige Python, el mínimo propuesto para consenso debe ser una rama mantenida;
la versión 3.9.6 usada en las pruebas es entorno legado, no objetivo sugerido.

### 10.1 Cobertura de hallazgos anteriores

Esta tabla evita que la síntesis pierda observaciones al abandonar la
numeración de las rondas:

| Hallazgo previo | Disposición en este candidato |
|---|---|
| H1 · memoria macOS | Confirmado para el mecanismo probado; `RLIMIT_AS` no disponible y RSS queda G3b (§5). |
| H2 · CPU macOS | Confirmado; `RLIMIT_CPU` no es G1 y el muestreo permanece G3b (§5.1). |
| H3 · dos relojes | Se retira `max_wall_seconds` y se fija precedencia (§8). |
| H4 · `RLIMIT_NPROC` | No se presenta como límite por acción (§5). |
| H5 · log append-only | Rebajado a registro operativo; auditoría fuerte fuera de alcance (§5). |
| H6 · reserva de tokens | Frontera diferida; deberá reservar input y output, con modelo de precios/versiones definido (§9.4). |
| H7 · estados incompletos | Estados de admisión, arranque y ejecución separados (§8). |
| H8 · muerte del supervisor | Produce ausencia de resultado sin observador externo (§5.3, §8). |
| H9 · expiración durante ejecución | Dos semánticas expuestas; decisión normativa D3 (§7, §11.2). |
| H10 · tolerancia de reloj | Debe fijarse regla y fuente de tiempo; no se hereda ±60 s automáticamente (§7). |
| H11 · delegación sin canal | MVP-0 consume sólo raíz y no emite delegaciones (§7). |
| H12 · retención de nonces | Alcance, retención y reinicio son obligatorios (§7). |
| H13 · `preexec_fn` multihilo | Deuda de prueba; la arquitectura de spawn/shim queda abierta hasta elegir lenguaje (§9.1, §12). |
| H14 · interrupción por terminal | `terminated` exige orden dirigida al supervisor; la UX concreta queda por especificar (§8). |
| H15 · canonicalización | Verificación sobre bytes transportados, parser versionado e identidad completa (§6–§7). |
| H16 · lenguaje sin justificación | Elección reabierta y condicionada por plataforma/evidencia (§10). |
| N1 · corpus sin commit | Convertido en precondición del consenso (§1.1, §11.1). |
| N2 · orden divergente | Resuelto como caracterización ejecutable seguida de promesas (§9). |
| N3 · costos del muestreo | Integrados, pero sin promover sus inferencias a garantía (§5.1–§5.2). |
| N5 · Python EOL | 3.9.6 queda sólo como entorno legado (§10). |
| N6 · glosa del paper | Registrada como deuda de cita (§12). |
| N7 · E9 no reproducida | Incorporada a la caracterización pendiente (§9.1, §12). |
| N8 · CVE mal atribuida | Registrada para corrección normativa (§12). |

## 11. Entrada al consenso

El consenso decide producto y política; no vota hechos del sistema operativo.

### 11.1 Precondiciones, no preguntas

1. Consolidación y autorrevisión firmadas, con independencia declarada.
2. Corpus completo fijado en commit y tag anterior al acto de consenso.
3. README alineado con las garantías actualmente demostradas.
4. Suite segura de caracterización versionada; ejecución Darwin registrada.

Si alguna falta, el consenso se pospone: no se “acepta” la falta por votación.

### 11.2 Decisiones normativas resolubles ahora

Cada una se resuelve como **aceptada**, **rechazada** o **aplazada con dueño y
fecha**, no con evidencia empírica inventada:

- **D1 · alcance:** MVP-0 es admisión G0 y resolución local; no frontera de
  seguridad ni contención de recursos.
- **D2 · capacidad:** MVP-0 consume sólo capacidad raíz no delegable.
- **D3 · vigencia:** validez sólo en admisión o truncamiento del plazo a `exp`.
- **D4 · descriptor:** JSON versionado y exclusión de YAML en MVP-0.
- **D5 · resultados:** estados de §8 y precedencia plazo → presupuesto.
- **D6 · exclusiones:** tokens, costo, iteraciones, subacciones y telemetría
  accionable quedan fuera de MVP-0.
- **D7 · identidad:** decidir si, además de comando/args/cwd/env/stdin y
  límites, se vinculan digest del ejecutable y archivos auxiliares.

### 11.3 Cuestiones empíricas: no sometidas a voto

- **E1 · plataforma:** Linux-first para límites preventivos se decide después
  de ejecutar la suite Linux. Hasta entonces no hay plataforma prometida para
  CPU/memoria G1.
- **E2 · CPU:** permanece G3b/F-S hasta cubrir procesos efímeros, padres
  terminados y reparentado. La salida es una prueba de extremo a extremo, no
  acuerdo verbal.
- **E3 · memoria:** RSS macOS permanece G3b; caracterizar Linux decide sólo
  qué promete `RLIMIT_AS`, sin convertir espacio virtual en RSS.
- **E4 · lenguaje:** permanece abierto hasta fijar plataforma y ejecutar la
  caracterización Linux. La suite puede seguir en Python.

## 12. Deuda de evidencia

- No se ha ejecutado la caracterización en Linux.
- Existe una suite segura autorizada: 4 pruebas pasan en Darwin y 1 caso Linux
  queda omitido por plataforma; falta CI macOS/Linux y ampliar cobertura.
- La cobertura de procesos efímeros en el muestreo está abierta.
- No se ha medido la supuesta cota CPU de extremo a extremo.
- No se ha probado supervivencia del host ante presión rápida de memoria.
- `setsid`, D-state, fork bomb y muerte del supervisor siguen sin prueba segura
  conservada.
- El protocolo de capacidades no tiene análisis formal ni vectores completos.
- El bloque de fuentes sobre capacidades no ha sido verificado.
- La atribución de `CVE-2026-4269` señalada por la ronda 3 sigue sin corregirse
  en el preproyecto.
- La afirmación sobre el paper de bucles infinitos excede lo verificado desde
  el abstract y debe precisarse.

## 13. Correcciones incorporadas tras la ronda adversarial

La revisión adversarial de esta consolidación produjo y se aplicaron estas
correcciones:

1. se retiró la pretensión de que el muestreo CPU ya es G2;
2. se distinguió plazo del registro observado de muerte universal de procesos;
3. se retiró cualquier garantía de supervivencia del host ante fuga accidental;
4. se añadió `supervision_failed`, sin fingir un resultado cuando muere el
   propio supervisor;
5. se amplió la identidad firmada más allá de comando y argumentos;
6. se rebajó la autoridad de los experimentos narrados de V a R;
7. se separó la suite de caracterización del lenguaje del runtime;
8. se añadió riesgo y tratamiento especial para pruebas destructivas;
9. se convirtió la plataforma inicial en cuestión empírica con criterio de
   salida, no decisión por consenso;
10. se explicitó que este documento no sustituye el historial antes del
    consenso;
11. se retiró la clasificación G1 del deadline y de `killpg`: el primero no
    tiene cota de planificación demostrada y el segundo es un brazo de
    terminación, no un límite preventivo;
12. se añadieron G3a/G3b y el eje de fallo ruidoso/silencioso;
13. se corrigió la tabla a L/R/D/N coherentes y se añadieron alcance de
    recurso y shim pre-`exec`;
14. se reordenó MVP-0 alrededor de G0 y se sacó telemetría accionable;
15. se partió §11 entre precondiciones, decisiones y preguntas empíricas;
16. se incorporó P1-bis como candidato, incluido `cutime/cstime` por probar.

## 14. Criterio de salida del consenso

El consenso termina cuando D1–D7 tienen resolución y dueño. E1–E4 conservan
su clasificación por defecto hasta que la suite entregue evidencia. El
resultado deberá producir:

- una especificación normativa nueva que sustituya al preproyecto;
- ADR de plataforma, lenguaje, capacidad y estados;
- backlog de pruebas con matriz macOS/Linux;
- una tabla pública de garantías y no-garantías;
- una regla de proceso: no se abre otra ronda narrativa antes de tener CI de
  caracterización en macOS y Linux, salvo autorización expresa para trabajo
  documental que no pretenda aumentar el grado de evidencia.

Hasta entonces, este texto es una base de discusión corregida, no una promesa
de producto.
