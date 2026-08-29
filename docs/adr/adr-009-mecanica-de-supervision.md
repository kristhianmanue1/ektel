# ADR-009: Mecánica de supervisión (salida acotada, terminación graduada, grupo y subreaper)

**Estado:** **aceptado y enmendado por ADR-012** — Kristhian Manuel Jimenez
Sanchez (krisnova@hotmail.com), 2026-08-19; parámetros, topología y separación
plan/aplicación fijados el 2026-08-28. Normativo; no autoriza implementación
M2 por sí solo.

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Origen:** revisión externa 2026-08-19 (F4): la mecánica de supervisión no
tenía hogar decisional. **Absorbe R3** (`output_limits` sin mecanismo
declarado) de la ronda adversarial interna. Contexto normativo: propuesta
§6.3 (supervisor), §7.2 (`output_limits`), §8 (clases de garantía), §13-M2
("no hay hangs en la suite acotada"). Evidencia: E1–E3
(`docs/evidencia/caracterizacion-linux-2026-08-18.md`) y la revisión de
`sandbox.py` de Argos (`docs/revisiones/revision-argos-sandbox-2026-08-19.md`,
F1/F3/F7 allí).

## 1. Decisión propuesta

1. **Salida acotada por bucle de lectura con drenado, no por rlimit.** El
   supervisor lee stdout/stderr con un bucle acotado: al alcanzar
   `output_limits` **sigue leyendo y descarta** (drenar-y-descartar), lo
   declara en `stdout_truncation`/`stderr_truncation` junto con el conteo
   de bytes descartados, y el límite no mata al proceso por sí mismo (la
   muerte la producen las compuertas: deadline, terminación). Esta
   semántica queda **decidida aquí, no diferida a M2** (ronda correctiva
   2026-08-19, B6): cerrar el pipe puede matar o alterar al proceso
   mediante SIGPIPE y dejar de leer puede bloquearlo; drenar y descartar
   preserva el progreso del supervisado con memoria acotada del
   supervisor. **`RLIMIT_FSIZE` queda descartado como mecanismo primario**:
   no está caracterizado en las plataformas objetivo (E-gates) y actúa
   sobre archivos, no sobre pipes. Motivación empírica adicional: la
   captura ilimitada es una bomba de memoria contra el propio supervisor
   (Argos F7), y en Darwin ni `RLIMIT_AS` existe como red de seguridad
   (E1).
2. **Sin hang post-kill.** Tras `SIGKILL` al grupo, la espera de EOF usa
   `post_kill_drain_ms`: entero exacto, default 1000, rango 1..10000
   (ADR-012). Si expira, el supervisor cierra los pipes y declara
   `post_kill_forced_pipe_close=1`. Este plazo sólo acota la latencia de
   entrega de pipes; no amplía el deadline ni cambia cuándo se recogió el
   principal. Un descendiente con descriptores heredados no puede colgar al
   supervisor (Argos F3; criterio M2).
3. **Terminación graduada con gracia fija:** `SIGTERM` al grupo,
   `termination_grace_ms` entero exacto, default 2000 y rango 0..60000,
   después `SIGKILL` al grupo. El deadline se considera cumplido cuando el
   proceso principal es recogido; la gracia está presupuestada dentro del
   deadline efectivo (el supervisor inicia la secuencia de terminación
   antes del vencimiento, no después) **y ese descuento es visible en el
   contrato**: el `GuaranteePlan` declara la configuración y la fórmula,
   mientras `guarantees_applied` declara la gracia y el tiempo útil realmente
   aplicados (enmienda ADR-012); gracia 0 (SIGKILL directo) es configuración
   válida declarada. El
   supervisor computa y registra dos instantes (segunda revisión externa
   2026-08-20, C6): `soft_termination_at` (inicio de la escalación =
   deadline efectivo menos gracia) y `hard_deadline_at` (cota absoluta); la
   clasificación del estado final es por causa, según ADR-005 punto 3.
4. **Topología y grupo:** un coordinador runtime crea un proceso supervisor
   dedicado por acción; éste queda fuera del grupo ejecutado y crea el grupo
   propio sin `preexec_fn`. `setsid`/double-fork por parte del
   supervisado es escape declarado fuera del modelo (§12.2, ADR-001); el
   resultado lo declara, no lo persigue.
5. **Sólo el supervisor dedicado se declara subreaper en Linux cuando el
   despliegue requiera contabilidad multi-nivel.** Evidencia E2: sin
   `prctl(PR_SET_CHILD_SUBREAPER)` el CPU de un nieto huérfano es
   irrecuperable; con él se recupera vía `wait4`. Es Linux-only: en Darwin
   la magnitud "contabilidad CPU multi-nivel" se declara `unsupported`
   (ADR-006 §4), sin mitigación conocida. La declaración de subreaper es
   parte del plan como solicitud y del resultado como uso real, con su clase
   (`observed`/`reactive` según la magnitud), nunca `enforced`.
6. **Contabilidad de CPU: clase `observed`.** El supervisor registra
   `cutime/cstime` (hijo directo recogido) y, con subreaper, descendientes
   reparentados; estas mediciones alimentan el resultado pero **ninguna
   decisión de control** en v1 (D5: `budget_exceeded` no existe). Las
   mediciones incompletas nunca se presentan como límite preventivo
   (propuesta §8 regla 3).

## 2. Motivación

R3 dejó `output_limits` sin mecanismo; F4 notó que tampoco lo tenían la
gracia de terminación, la unidad de terminación ni la asimetría de
supervisión entre plataformas. Son cuatro decisiones de la misma capa
(qué hace exactamente el supervisor con descriptores, señales y grupos) y
deben cambiar juntas o no cambiar: por eso un solo ADR.

## 3. Alternativas consideradas

### A. Bucle acotado + gracia fija + grupo + subreaper opcional (propuesta)

A favor: cada mecanismo está caracterizado (E1–E3) o es portable por
construcción (bucle de lectura); las clases de garantía resultantes son
honestas por plataforma; cierra los tres huecos demostrados en el sandbox
de Argos (F1/F3/F7 allí).
En contra: el bucle de lectura es código del supervisor en el camino
crítico de E/S; se mitiga con límites y pruebas de presión en M2.

### B. `RLIMIT_FSIZE` / `RLIMIT_AS` como mecanismos primarios

En contra: no caracterizados (`RLIMIT_FSIZE`) o directamente rechazados en
Darwin (`RLIMIT_AS`, E1); además no actúan sobre pipes. Rechazada como
primaria; un despliegue Linux puede añadirlos como defensa en profundidad
declarada.

### C. Contabilidad de CPU como garantía de control (`reactive`/`enforced`)

En contra: contradice D5 (sin `budget_exceeded` en v1) y la revisión
externa F7 (no publicar como claim lo que el producto no gobierna).
Rechazada para v1.

## 4. Consecuencias

- M2 hereda cuatro obligaciones testeables: truncamiento declarado,
  ausencia de hang post-kill, gracia SIGTERM→SIGKILL determinista, y tabla
  de garantías por plataforma con subreaper en Linux / `unsupported` en
  Darwin.
- ADR-012 añade framing/propiedad de salida, supervisor por acción,
  `max_concurrent_actions`, valores temporales exactos y memoria publicada;
  su gate M2 es obligatorio junto con éste.
- El caso "proceso no cooperativo" de la matriz §14.2 se prueba contra la
  secuencia completa TERM→gracia→KILL→espera acotada de EOF.
- La tabla pública de claims/no-claims ya refleja la retirada del claim de
  contabilidad (F7); este ADR es su hogar normativo.

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | Dejar de leer stdout sin matar el proceso puede bloquearlo (pipe lleno) y convertir un límite de salida en un deadlock del supervisado. | **Incorporada y cerrada (ronda correctiva 2026-08-19, B6):** la semántica es **drenar y descartar** tras el límite (punto 1) — ni cerrar el pipe (SIGPIPE puede matar o alterar al supervisado) ni dejar de leer (bloqueo); el supervisor nunca cuelga y el truncamiento se declara con conteo de bytes descartados. |
| A2 | La gracia "presupuestada dentro del deadline" adelanta la terminación: un proceso que habría terminado a tiempo recibe SIGTERM antes. | **Incorporada parcialmente:** la gracia se descuenta del deadline efectivo y eso se declara en el `GuaranteePlan`; el despliegue puede fijar gracia 0 (SIGKILL directo) aceptando la pérdida de terminación cooperativa. |
| A3 | Declararse subreaper cambia la semántica de reparentado de todo el proceso supervisor, incluidas acciones ajenas. | **Incorporada:** el subreaper se declara por proceso supervisor de acción (o se acepta explícitamente el alcance de proceso completo como supuesto declarado en el `GuaranteePlan`); la decisión exacta es de M2 y debe quedar en la tabla de garantías con sus supuestos. |

## 6. Criterio de revisión

Reabrir si: la caracterización de `RLIMIT_FSIZE` se completa y resulta
suficiente; una magnitud de CPU obtiene mecanismo clasificado y probado
(habilitaría `budget_exceeded` en v2, ADR-005 §6); o aparece mitigación de
huérfanos en Darwin.

## 7. Decisiones que este ADR no toma

- Los valores concretos de gracia, drenaje, capacidad, framing y propiedad ya
  no están abiertos: los fija ADR-012. `output_limits` permanece en el
  `ActionRequest` wire v1.
- Estados terminales resultantes → ADR-005.
