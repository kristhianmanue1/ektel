# ektel — ronda 3: verificación de la ronda 2 y auditoría adversarial de la propia verificación

**Estado:** este documento no es evidencia verificada del comportamiento de
ektel —ektel sigue sin existir—. Sí es evidencia verificada de tres cosas:
(i) que las pruebas E1–E8 de la ronda 2 se reproducen hoy, en el host y fuera
del sandbox de la herramienta de ejecución; (ii) de dos propiedades mecánicas
del mecanismo que la propuesta P1 de la ronda 2 necesita y que nadie había
probado (A1, A2); (iii) del estado real de cuatro citas que la ronda 2 dejó
declaradas sin verificar —una de ellas resulta mal atribuida en el
pre-proyecto—.

**Fecha:** 2026-08-14 · **Entorno:** Darwin 25.5.0 (ARM), Python 3.9.6 del
sistema —la misma máquina que declaró la ronda 2; ver C3 por lo que eso
certifica y lo que no—.

## 1. Método

Dos pasadas, como la ronda 2, con una diferencia: el objeto de la segunda es
la primera.

1. **Pasada de verificación.** Reproducción de E1–E8, del estado del corpus
   git (commit `325beef`, `docs/` untracked) y de una cita (arXiv
   2607.01641). Produjo cinco hallazgos (N1–N5).
2. **Pasada adversarial (esta).** Cada frase afirmativa de la pasada 1
   contra lo que realmente se ejecutó; ejecución de las dos afirmaciones
   técnicas que la pasada 1 dejó sin probar (N3); y aplicación a sí misma de
   su propia recomendación pendiente —verificar las citas D2-críticas antes
   de escribir código—.

Resultado: seis correcciones a la pasada 1 (§4), dos hallazgos nuevos (N6,
N8), un hallazgo disuelto en corrección (N4 → C2), y una propuesta de la
ronda 2 (P1) que queda especificada con evidencia que no tenía (§5, §6).

## 2. Evidencia empírica

| # | Prueba | Resultado |
|---|---|---|
| E1–E8 | Reproducción de la ronda 2, en el host, sin sandbox de herramienta | Idénticas: `RLIMIT_AS` ≡ `RLIMIT_RSS` (=5) con el texto literal del header del SDK (`sys/resource.h:448-450`); `EINVAL` en AS y DATA; control (NOFILE/CPU/NPROC) aceptado; hijo cooperativo `exit=152`; hijo que ignora `SIGXCPU` sobrevive 15.1 s (lim 1/5) y 15.3 s (`soft==hard==2`); `RLIMIT_NPROC` *"for this **user id**"* literal en `man 2 setrlimit` |
| **A1** | `getrusage(RUSAGE_CHILDREN)` con hijo **vivo** que quema 2 s de CPU | **Vivo: 0.000 s · tras `wait()`: 2.001 s.** La acumulación sólo cuenta hijos terminados y reapeados; es inservible para muestrear un vivo |
| **A2** | `proc_pidinfo(PROC_PIDTASKINFO)` desde el padre, mismo uid, **sin root**, contra `ps` | `rc=96`, datos devueltos; `rss = 58.4 MiB` **coincide exactamente** con `ps -o rss` (59792 KiB); `vsize ≈ 415 GiB` según **ambas** herramientas |

Nota sobre A2: la coincidencia exacta con `ps` valida el mecanismo de
lectura que P1 necesita en macOS. El `vsize` gigantesco en ambas
herramientas descarta el espacio virtual como métrica de compuerta en esta
plataforma: P1 debe muestrear **memoria residente, nunca virtual** —lo que,
dicho sea de paso, también blinda a Linux del falso positivo de binarios con
gran reserva virtual (P4.5 de la ronda 2, aún sin probar).

## 3. Verificación de citas

| Cita (dónde) | Resultado |
|---|---|
| `litellm#26672` (§5.1, contexto de D2) | **Confirmada.** Issue abierto, etiquetado `bug`: *"Budget enforcement bypassed in v1.82.3 for key/user max_budget despite spend exceeding max_budget"* (abierto 2026-04-28). La glosa del pre-proyecto es fiel: el spend se rastrea, el enforcement no dispara. |
| `CVE-2026-4269` (§6 y §9: «Unit 42 sobre AWS AgentCore (bypass DNS, CVE-2026-4269)») | **Existe, pero mal atribuida.** NVD (CNA: AMZN): *"missing S3 ownership verification in the Bedrock AgentCore Starter Toolkit before v0.1.13… inject code during the build process"*. Es inyección en build por propiedad de S3, **no** un bypass de DNS. El bypass de DNS de la investigación de Unit 42 es otro hallazgo; emparejarlo con este número es un error de atribución → **N8**. |
| arXiv 2607.01641 (base de D1) | **Números confirmados** desde el abstract: 74 reportes, 68 fallos confirmados por revisión manual en 47 proyectos. La glosa «cuyos frameworks ofrecían esos mecanismos» **no es verificable desde el abstract** → **N6**. |
| Python 3.9.6 EOL (N5) | **Confirmado.** devguide: 3.9 EOL 2025-10-31; 3.10 EOL 2026-10 (a dos meses de hoy); 3.11 en fase *security* hasta 2027-10. |

## 4. Correcciones a la pasada 1 de esta misma ronda

Se listan por el mismo criterio que la ronda 2 aplicó a sí misma: declarar
los propios errores antes de que los encuentre otro.

**C1 — Sobreafirmación de reproducción.** Escribí «sus 9 pruebas se
reproducen exactamente» habiendo reproducido 8: E9 (`preexec_fn` desde
proceso con hilo vivo, sin aviso) no fue ejecutado por la pasada 1 ni lo es
por esta. Lo correcto: 8 de 9. E9 queda como deuda explícita (N7).

**C2 — N4 mal enmarcado, y en dirección inversa.** Dije que P1 «agrava» H3.
Es al revés: en el diseño original el `SIGXCPU` lo entrega el kernel —un
segundo actor— compitiendo con el timer del supervisor; P1 concentra ambas
decisiones de kill en un único proceso, lo que vuelve la precedencia
trivialmente determinista (orden fijo de chequeo). El defecto real —falta de
regla de precedencia— preexiste a P1 y P1 lo resuelve mejor, no peor. El
núcleo de N4 sobrevive como recomendación (R4), no como hallazgo contra P1.

**C3 — Reproducir no es validar de forma independiente.** La ronda 2 y esta
ronda corren en la misma máquina (mismo `uname`, mismo Python). Mi
«confirmado» certifica reproducibilidad en el entorno declarado, no
generalidad a otro hardware u otra versión de macOS. Lo que sí gana la
evidencia al ejecutarse en el host: la salvedad de la ronda 2 (§6, «dentro
del sandbox de la herramienta de ejecución») queda rebajada para E1–E8 y A1–A2.

**C4 — Retórica inflada en N1.** «Sin cadena de custodia» sobre trabajo del
mismo día sin commitear es exceso. El hallazgo real es de proceso: dos
documentos fechados hoy describen estados del corpus git distintos (la ronda
2 cita un commit que no contiene a la ronda 2). Se repara con un commit y un
tag. Severidad final: m.

**C5 — N2 no es contradicción.** El README exige «antes que cualquier
documento de diseño adicional»; una suite de tests no es un documento de
diseño, y recomendar suite-primero (P4) es compatible con la letra del
README. Lo que subsiste es la divergencia no registrada: dos textos de la
misma fecha ordenan pasos siguientes distintos sin cruzarse. Severidad
final: m.

**C6 — «El Anexo A ya es la suite».** Cubre 2 de los 7 tests de P4 (P4.1,
P4.2). Es el germen, no la suite.

## 5. Hallazgos consolidados (tras la pasada adversarial)

Severidades según la convención de la ronda 2 (C/M/m).

- **N3 · M — P1 estaba sub-costeada, y le faltaba evidencia.** La propuesta
  de supervisión por muestreo de la ronda 2 declaraba un solo costo (la
  granularidad). Con la evidencia de esta ronda, la especificación completa
  exige:
  1. **A1:** `getrusage(RUSAGE_CHILDREN)` no ve hijos vivos. La herramienta
     stdlib obvia para un implementador produce una compuerta **muerta** (da
     ~0 mientras el hijo vive; el presupuesto nunca dispara hasta el reap,
     cuando ya es tarde). El muestreo debe caminar el árbol de procesos por
     pgid y leer por proceso.
  2. **A2:** el mecanismo de lectura existe sin root en macOS
     (`proc_pidinfo`) y coincide con `ps` al byte; en Linux, `/proc/<pid>/statm`
     —pendiente de verificación (§7)—. La métrica es **RSS, nunca vsize**
     (415 GiB de espacio virtual en un python trivial lo vuelven ruido).
  3. **Sobre-conteo de compartido:** sumar RSS por proceso cuenta N veces
     las páginas compartidas (librerías mapeadas en N procesos). El sesgo es
     conservador —mata antes una acción sana que deja pasar a una hostil—,
     lo que preserva la propiedad de seguridad a costa de utilidad. Debe
     declararse en §7. No medido aquí: conocimiento estándar, declarado como
     tal.
  4. **Invisibilidad post-escape:** la caminata por pgid hereda el límite ya
     declarado en §5.4/§7 de pre-proyecto —un `setsid` escapa al grupo y
     también al muestreo—. La herencia debe decirse explícitamente en P1,
     no darse por obvia.
  5. **Granularidad:** la ya declarada por la ronda 2 (un pico entre dos
     muestras escapa).
- **N1 · m — corpus sin commitear.** `docs/` es untracked en `325beef`;
  las rondas 2 y 3 no existen en el historial que ellas mismas citan.
- **N2 · m — divergencia de secuenciación no registrada** entre README
  («esqueleto mínimo») y ronda 2 (P4-primero). Compatible con la letra (C5),
  pero la decisión debe quedar registrada.
- **N5 · m — política de versión de Python ausente.** El entorno verificado
  (3.9.6) lleva EOL desde 2025-10; 3.10 muere en 2026-10. Un runtime cuya
  única superficie es la stdlib debería declarar mínimo soportado sobre
  intérprete mantenido.
- **N6 · m — glosa no verificable del paper IAL.** Los números 68/47 se
  verifican; la caracterización «cuyos frameworks ofrecían esos mecanismos»
  exige el full-text y hoy es glosa. Misma clase que la corrección de
  atribuciones de la ronda 1 del pre-proyecto.
- **N7 · m — E9 sin reproducir por ninguna ronda** (`preexec_fn` desde
  proceso multihilo, sin aviso). Deuda de la suite.
- **N8 · m — CVE mal atribuida en el pre-proyecto.** §6 y §9 emparejan
  «bypass DNS» con `CVE-2026-4269`, que es otro defecto (propiedad S3 en el
  Starter Toolkit, inyección en build). El incidente de DNS existe como
  hallazgo de Unit 42 pero no bajo ese número. Corregir la atribución o
  separar las dos citas.

## 6. Recomendaciones y cambios propuestos

**R1 — Commit y tag del corpus doc.** Commitear `docs/` completo (incluido
este documento) y etiquetar. Actualizar «Siguiente paso» del README
registrando la decisión P4-primero, que es compatible con su letra (C5).
Nota de estado: este documento queda escrito pero sin commitear —commitear
es decisión del operador; N1 se aplica también a quien la formula.

**R2 — La suite antes que el runtime (refuerza P4).** `tests/escape/` a
partir del Anexo A (E1–E7) más A1/A2 como tests de mecanismo del
supervisor, parametrizados por plataforma, rojo/verde en CI macOS+Linux, e
incluyendo E9 y P4.3–P4.7. P4.1 y P4.2 ya están reproducidos en host por
esta ronda. La suite es también el lugar donde se valida el mecanismo de
muestreo mismo —A2 sólo se fiable después de contrastarse con `ps`, y ese
contraste pertenece a CI, no a prosa—.

**R3 — Especificar P1 con sus cinco costos** (los de N3) en el pre-proyecto
como §5.1bis, con la regla de métrica: residente, nunca virtual, leída por
proceso desde caminata por pgid.

**R4 — Regla de precedencia determinista y retiro de `max_wall_seconds`.**
En cada tick del supervisor, orden fijo de evaluación —(c) antes que (a)—;
toda doble violación entre muestras produce `deadline_exceeded`. Retirar
`max_wall_seconds` del descriptor: el reloj de pared tiene dueño único, la
compuerta (c). Cierra H3 con el punto único de decisión que P1 crea (C2).

**R5 — Declarar mínimo de Python.** Recomendado ≥3.11 (única rama con más
de un año de soporte además de 3.12+; 3.10 muere en 2026-10), o justificar
3.9 explícitamente como entorno de verificación legado. Antes de cerrar O1,
re-ejecutar E1–E7 y A1–A2 bajo el mínimo declarado.

**R6 — Precisar la glosa de D1** (N6): reformular a lo verificable del
abstract o citar la sección del full-text que sustente «cuyos frameworks
ofrecían esos mecanismos».

**R7 — Corregir la atribución de `CVE-2026-4269`** en §6 y §9 del
pre-proyecto (N8): separar el bypass de DNS (Unit 42) de la inyección por
propiedad de S3 (el CVE), o citar ambas como incidentes distintos.

## 7. Lo que esta ronda no verificó

- **Nada en Linux**, incluido `/proc/<pid>/statm` como mecanismo de lectura
  de P1 y el comportamiento de `RLIMIT_AS`/`RLIMIT_CPU` que el pre-proyecto
  asume.
- **E9 y P4.3–P4.7** (`setsid`, D-state, reserva virtual en Go/JVM,
  lectura de credenciales, supervisor muerto): sin evidencia en ninguna
  dirección.
- **El resto de las citas de §9** del pre-proyecto (cuatro verificadas de
  muchas; queda pendiente el bloque de capacidades: Biscuit, UCAN, Fly.io,
  zCAP-LD).
- **La criptografía** de §5.3: sin análisis formal, igual que la ronda 2.
- **El full-text** de arXiv 2607.01641 (sólo abstract).
- **Independencia de plataforma/hardware**: misma máquina que la ronda 2
  (C3). Una sola medición de `vsize`/RSS por herramienta.
- **El sobre-conteo de RSS compartido**: afirmado, no medido (N3.3).

---

## Firma

Ronda realizada por **GLM** (`glm-5.2`, zai-coding-plan/glm-5.2), Z.ai.
**Fecha:** 2026-08-14.
**Documentos revisados:** `docs/revision-externa-2026-08-14.md` (ronda 2),
`docs/pre-proyecto.md`, `README.md` @ `325beef`, y la pasada de verificación
previa de esta misma ronda.
**Método:** dos pasadas —verificación y adversarial sobre la propia
verificación—; la segunda corrigió a la primera en seis puntos (§4).

**Veredicto:** la ronda 2 sobrevive la verificación —8 de 9 pruebas
reproducidas en host, E9 pendiente— y su hallazgo central (H1+H2) queda
firmado fuera del sandbox. La pasada 1 sobrevive corregida: seis
correcciones, un hallazgo disuelto (N4→C2), dos nuevos (N6, N8). El
pre-proyecto acumula un error de atribución de CVE que sus dos rondas
previas no vieron porque ninguna verificaba citas; esta lo cerró
parcialmente (quedan las de capacidades). El siguiente commit sigue siendo
el que recomendó la ronda 2 —la suite de P4— ahora con A1 y A2 como tests
de mecanismo del supervisor y con R3–R5 como cambios al pre-proyecto antes
de la primera línea de código.
