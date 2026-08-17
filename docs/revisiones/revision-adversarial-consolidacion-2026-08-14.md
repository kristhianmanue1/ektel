# ektel — ronda adversarial de la consolidación para consenso

**Estado:** revisión adversarial cerrada sobre la versión 0.1 de
`consolidacion-para-consenso-2026-08-14.md`. Sus correcciones aceptadas fueron
incorporadas primero en 0.2; una segunda pasada con dos análisis aportados por
el operador produjo la versión 0.3. Este documento conserva la traza crítica;
no es una especificación alternativa.

**Fecha:** 2026-08-14 · **Objeto:** detectar sobreafirmaciones, decisiones
disfrazadas de hechos, garantías sin mecanismo y criterios de aceptación que
puedan satisfacerse de forma trivial.

**Autoría:** revisión realizada por **Codex (OpenAI)**, el mismo agente que
redactó la consolidación. Es una **autorrevisión y no una validación
independiente**. La versión 0.3 incorpora además dos análisis críticos
aportados posteriormente por el operador; se adjudican en §7.

## 1. Método

Se intentó refutar cada familia de afirmaciones mediante cinco preguntas:

1. ¿Qué observación exacta la sostiene?
2. ¿La evidencia está versionada y es reproducible?
3. ¿La conclusión es más amplia que la plataforma o amenaza probada?
4. ¿Un implementador podría satisfacer la letra sin cumplir la intención?
5. ¿Qué ocurre si falla el supervisor, la medición o la identidad del proceso?

No se verificaron fuentes web ni se ejecutó Linux. Se reprodujeron localmente
dos hechos ya narrados por rondas anteriores en Darwin 25.5.0/Python 3.9.6:

- fijar `RLIMIT_AS` a 128 MiB fue rechazado;
- `RUSAGE_CHILDREN` reportó cero durante la vida del hijo y CPU acumulada sólo
  después de `kill` + `wait`.

También se observó que un hijo con `RLIMIT_CPU=(1,1)` e `SIGXCPU` ignorado
sobrevivía tres segundos de pared, pero ese intento **no midió CPU consumida**
y no cuenta como reproducción de E6/E7. La conclusión sobre CPU Darwin se
apoya en las mediciones de `getrusage` de las rondas 2–3, no en ese intento.

Estas reproducciones aumentan confianza local, pero no son pruebas del
repositorio y no generalizan a Linux.

## 2. Hallazgos

Severidad: **C** invalida el contrato propuesto; **M** deja una garantía
materialmente ambigua; **m** afecta precisión o proceso.

### A1 · C — La CPU muestreada fue clasificada demasiado pronto como acotada

El borrador adoptaba la cota `T × C` como propiedad G2. Esa cota sólo vale si
cada intervalo compara observaciones completas del mismo conjunto contable.
El mecanismo por `ps` o caminata de pgid no ha probado que conserve CPU de:

- procesos que nacen y mueren entre dos muestras;
- nietos recogidos por otro proceso;
- churn continuo de descendientes breves;
- procesos que cambian de sesión o grupo.

Una sucesión de consumos no observados puede repetir el error; no basta con
acotarlo una vez por periodo.

**Corrección:** clasificar CPU muestreada como G3 hasta demostrar contabilidad
completa. Mantener `T × C` como hipótesis a probar.

### A2 · C — “Plazo mecánico” confundía resultado con muerte

Un supervisor puede dejar de esperar y emitir `deadline_exceeded`, pero
`killpg` no domina `setsid`, D-state ni la muerte del propio supervisor. Decir
que “la acción termina” permite interpretar que todos sus efectos cesaron.

**Corrección:** garantizar sólo la transición del registro observado por un
supervisor vivo. Declarar por separado el intento de matar el grupo.

### A3 · C — Contención de fuga accidental no implica supervivencia

El borrador heredaba de la ronda 4 que una fuga accidental sería detectada en
un periodo y que el host sobreviviría. La intención no limita la tasa de
asignación. Un bug puede agotar memoria antes de la siguiente muestra.

**Corrección:** RSS muestreado es G3; detecta algunos excesos después de
ocurridos y no garantiza máximo ni supervivencia.

### A4 · M — Los experimentos narrados no alcanzan el estado V

Los anexos contienen comandos y resultados, pero no archivos ejecutables,
expectativas automáticas, hashes de entorno ni CI. Llamarlos “verificados” en
una tabla consolidada vuelve a confundir relato con artefacto reproducible.

**Corrección:** clasificarlos como R o evidencia local. Reservar V para la
suite versionada.

### A5 · M — Un estado de fallo interno puede prometer lo imposible

El borrador proponía un resultado de error interno sin distinguir entre fallo
detectado y muerte total del supervisor. Un proceso muerto no puede emitir su
propio estado terminal sin observador o almacenamiento externo.

**Corrección:** `supervision_failed` sólo cuando el supervisor sigue vivo y
detecta pérdida de medición/control. La muerte sin observador produce ausencia
de resultado y queda fuera de MVP-0.

### A6 · M — La identidad firmada seguía siendo incompleta

Vincular sólo comando y argumentos no impide cambiar significado mediante
cwd, entorno, stdin, resolución de ruta o sustitución del ejecutable entre
firma y `exec`.

**Corrección:** incluir esos campos en la identidad de ejecución y elevar el
digest del artefacto a decisión explícita de consenso.

### A7 · M — La plataforma inicial aparecía como conclusión

La evidencia sólo caracteriza Darwin. Recomendar Linux para límites
preventivos es razonable, pero presentarlo como decisión cerrada antes de
ejecutar Linux repite el patrón criticado en las rondas anteriores.

**Corrección:** llevar Linux-first a §11 como decisión de consenso condicionada
a caracterización.

### A8 · M — La suite podía contener pruebas peligrosas sin política

Fork bomb y D-state no son casos ordinarios de CI. Enumerarlos sin aislamiento
podría convertir una recomendación de calidad en riesgo operativo.

**Corrección:** exigir entorno aislado o simulación justificada para esos
casos.

### A9 · m — La decisión de lenguaje y el lenguaje de la suite se mezclaban

Escribir la caracterización en Python no compromete el runtime. Esperar la
decisión final de lenguaje para probar el OS sería una dependencia artificial.

**Corrección:** separar explícitamente ambos lenguajes.

### A10 · m — El consolidado podía parecer sustitución automática

Una síntesis escrita por un revisor no adquiere autoridad normativa por
recopilar más material. El usuario indicó que se llevará después a consenso.

**Corrección:** estado “candidato no vinculante”; la sustitución del
preproyecto es un producto posterior del consenso.

### A11 · C — El deadline seguía sobreclasificado como G1

La comprobación final encontró una repetición del defecto central: el borrador
corregido llamaba G1 al plazo porque el timer vive fuera del hijo. Eso prueba
separación de autoridad, no una cota temporal estricta. En macOS y Linux de
propósito general, el callback puede ejecutarse después del instante nominal
por presión del scheduler. Además, `killpg` es un brazo de terminación y no
impide que el consumo previo cruce una frontera.

**Corrección:** clasificar el deadline como G3 hasta caracterizar su latencia y
declararlo no-RT; describir `killpg` fuera de G1 como mecanismo de terminación.

## 3. Intentos de refutación que no prosperaron

### S1 — “El MVP está sobredimensionado”

La crítica sobrevive. Aun recortando delegación y frontera de modelos, un
supervisor más protocolo criptográfico sigue teniendo dos núcleos sensibles.
No obstante, esto es riesgo de entrega, no imposibilidad. La mitigación
adoptada —capacidad raíz no delegable— es proporcionada.

### S2 — “Faltan estados terminales”

Sobrevive con precisión adicional. Separar admisión, arranque y ejecución
evita colapsar errores falsamente en `capability_rejected`. La corrección A5
impide prometer un estado tras muerte total del supervisor.

### S3 — “Tokens y costo son otra frontera”

Sobrevive. No hay mecanismo local que observe consumo externo de un proceso
con credenciales propias. Clasificarlo como G4 y sacarlo de MVP-0 es coherente
con la tesis mecánica.

### S4 — “Firmar bytes transportados reduce riesgo de canonicalización”

Sobrevive, pero no basta por sí solo. El contenido transportado debe cubrir
toda la identidad de ejecución y la semántica del parser debe estar versionada.

### S5 — “El corpus necesita versionado”

Sobrevive como hecho de proceso: `docs/` está untracked y hubo colisión de
numeración. No se infiere pérdida ni manipulación; sólo falta de orden
persistente y autoridad explícita.

## 4. Nuevas preguntas producidas por la ronda

1. ¿La identidad autorizada apunta a una ruta o a un artefacto inmutable?
2. ¿Qué reloj y qué fuente de tiempo usa la vigencia de capacidades?
3. ¿Qué ocurre si se pierde una fuente de medición durante la ejecución?
4. ¿La acción se considera iniciada antes o después de `exec` exitoso?
5. ¿Qué tamaño máximo tienen stdout/stderr y quién paga ese almacenamiento?
6. ¿Cómo se evita que el propio log o captura de salida agote recursos?
7. ¿Qué significa “recurso” en la capacidad cuando no hay aislamiento de fs o
   red que haga cumplir ese alcance dentro del hijo?

Las preguntas 1 y 3 se reflejaron directamente en el consolidado. Las demás
deben convertirse en detalle normativo o backlog antes de cerrar MVP-0.

## 5. Registro de correcciones aplicadas

| Hallazgo | Disposición | Lugar incorporado inicialmente en 0.2 |
|---|---|---|
| A1 | Aceptado | §2, §5.1, §11.3 |
| A2 | Aceptado | §3, §5.3, §8 |
| A3 | Aceptado | §4.1, §5.2 |
| A4 | Aceptado | §2.1, tabla §5 |
| A5 | Aceptado | §8.2 |
| A6 | Aceptado | §6, §7, §11.11 |
| A7 | Aceptado | §10, §11.2 |
| A8 | Aceptado | §9.1 |
| A9 | Aceptado | §10 |
| A10 | Aceptado | cabecera, §1, §14 |
| A11 | Aceptado | §3, tabla §5, §5.3, §13 |

## 6. Veredicto

La versión 0.1 repetía en menor escala el defecto que pretende corregir:
convertía mecanismos plausibles en garantías antes de cerrar su observación.
Tras aplicar A1–A11, la versión 0.2 quedó apta como base provisional. Los
hallazgos K1–K7 de §7 producen la versión 0.3, que es la candidata actual para
consenso, no una especificación de implementación.

Su principal mejora no es elegir mecanismo, plataforma o lenguaje, sino
obligar a que cada promesa declare fuerza y evidencia. El mayor riesgo que
permanece es social: que el consenso acepte palabras como “reactivo” o
“experimental” y después el README siga vendiendo “límites duros” sin la
misma tabla de alcance.

Antes de declarar consenso debe comprobarse que las decisiones de §11 se
reflejarán también en README, especificación normativa y criterios de
aceptación, no sólo en este documento.

## 7. Segunda pasada: adjudicación de los análisis aportados

Dos análisis críticos posteriores convergieron en siete observaciones. No son
una ronda independiente firmada dentro del repositorio; se tratan como insumo
externo y se verifican contra los archivos.

### K1 · evidencia incoherente — aceptado

La tabla usaba R para un timer no integrado, E16 de una sola ronda y una
lectura de manual. Se añadió L, se reclasificó el timer a I/N, `killpg` a L y
`RLIMIT_NPROC` a D. Después se creó una suite versionada: en Darwin pasan
`RLIMIT_AS`, CPU ignorando `SIGXCPU` medida por `wait4`, semántica post mortem
de `RUSAGE_CHILDREN` y cierre del grupo observado por `killpg`; esas cuatro
filas ascienden a V sólo para Darwin. Linux permanece N/D.

### K2 · documentos sin firma — aceptado

Ambos documentos declaran ahora Codex (OpenAI) y que la adversarial fue
autorrevisión del mismo agente. No se le atribuye independencia inexistente.

### K3 · P1-bis ausente — aceptado con límite

§5.4 del consolidado resume el mecanismo candidato y conserva la ronda 4 como
fuente histórica. Se añade `cutime/cstime` como hipótesis Linux con caso de
prueba, no como mecanismo confirmado.

### K4 · consenso legislando física — aceptado

§11 separa precondiciones, D1–D7 normativas y E1–E4 empíricas. CPU, memoria,
plataforma y lenguaje no cambian de clasificación mediante voto.

### K5 · G3 empastaba fallos distintos — aceptado

G3 se divide en G3a (transición eventual) y G3b (observación que puede perder
eventos). Se añade el eje F-R/F-S/F-M. La caracterización del plazo produce
percentiles, nunca una promoción general a G2 en un OS no RT.

### K6 · filas omitidas — aceptado

La tabla incorpora alcance de `resource`, que sólo es G0 contra el descriptor,
y el shim pre-`exec` de E18 como evidencia L.

### K7 · el proceso sustituyó al proyecto — aceptado y accionado

El README ya no promete tres límites duros uniformes. Con autorización expresa
del operador se creó `tests/escape/`; la ejecución local Darwin produjo cuatro
éxitos y un skip Linux. El corpus se fijará en commit y tag antes del consenso.
No se crea otro documento de ronda para estas correcciones.

### Propuestas no adoptadas literalmente

- No se convierte G0 en “probado”: sobrevivió a las refutaciones del OS, pero
  el protocolo aún es P/N y necesita vectores y revisión criptográfica.
- No se afirma que `cutime/cstime` cierre A1: sólo cubre hijos recogidos mientras
  sobrevive el padre contable.
- No se hace del CI Linux una condición para discutir D1–D7; sí lo es para
  cambiar E1–E4 o prometer límites de recursos.
