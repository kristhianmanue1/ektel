# ADR-001: Alcance y modelo de amenaza M0–M3

**Estado:** **aceptado** — Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com), 2026-08-19. Normativo; aún no autoriza implementación por sí solo (la autorización de M0 es un acto separado, propuesta §21.6).

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Contexto normativo:** propuesta §4 (no-objetivos), §12 (modelo de amenaza),
§13 (stop rule). Decisiones vigentes: D1 (alcance) y D6 (exclusiones).

## 1. Decisión propuesta

1. **Alcance (D1 formalizada):** ektel M0–M3 es un runtime local que gobierna
   únicamente su propia frontera de ejecución: admisión G0 (validación +
   capacidad raíz), resolución local del comando, supervisión de un grupo de
   procesos, resultado tipado y registro de transiciones observadas. Nada más.
2. **Modelo de amenaza:** se adopta §12 de la propuesta como normativo,
   incluyendo la lista de "fuera del modelo" (atacante con control del host,
   kernel comprometido, escape por `setsid`/double-fork, D-state, red y
   filesystem no aislados, muerte simultánea de supervisor y almacén).
3. **Exclusiones (D6 formalizada):** se mantienen íntegras las exclusiones de
   §4 hasta nuevo acto de consenso. La stop rule de M3 es parte del alcance:
   cerrar M3 no inicia M4.
4. **Lenguaje público prohibido:** la documentación no usará "ejecución
   segura", "auditoría completa" ni "límites duros" sin calificador (§12.2).
5. **"Local" se define:** un solo host, un solo usuario operador, procesos
   del mismo UID; cualquier despliegue multiusuario o multitenant está fuera
   del modelo y requiere propuesta nueva.

## 2. Motivación

D1 y D6 están aceptadas como decisión de consenso, pero el alcance y el
modelo de amenaza son la referencia que toda futura objeción, feature
request y documento público citarán. Sin ADR, §4 y §12 son texto de
propuesta; con ADR, son la frontera contra la que se mide el scope creep.

## 3. Alternativas consideradas

### A. Adoptar §4 + §12 tal cual (propuesta)

A favor: ya pasaron cuatro rondas de revisión externa y una consolidación;
las exclusiones son explícitas y cada una tiene razón documentada.
En contra: ninguna decisión nueva; el ADR es formalización, no diseño.

### B. Ampliar el modelo de amenaza a aislamiento fuerte (sandbox real)

En contra: contradice D1/D6, exige mecanismos de plataforma no
caracterizados (E1–E3 no cubren namespaces/seccomp), y es exactamente el
scope creep que la stop rule prohíbe. Rechazada para M0–M3.

### C. Estrechar aún más (sólo admisión, sin supervisor)

En contra: dejaría M2/M3 sin objeto; la supervisión acotada es el valor
central del runtime frente a un `subprocess` ad-hoc (ver la revisión de
`sandbox.py` de Argos, `docs/revisiones/revision-argos-sandbox-2026-08-19.md`,
que muestra el costo de supervisión informal).

## 4. Consecuencias

- Todo cambio que amplíe alcance o modelo de amenaza requiere reabrir D1/D6
  por consenso y un ADR nuevo; no se cuela en implementación.
- La tabla pública de claims/no-claims (§21.4) deriva de este ADR: los
  no-claims son §4 + §12.2 traducidos a lenguaje de usuario.
- Cualquier garantía futura de aislamiento nace como propuesta M4+ con su
  propia caracterización empírica, no por analogía (regla D7a).

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | "Local" sin definir permite despliegues multiusuario que el modelo de amenaza no cubre. | **Incorporada:** §1.5 fija un host, un operador, un UID. |
| A2 | El modelo excluye "atacante con control del host", pero el runtime corre como ese mismo usuario: un proceso supervisado puede escribir el AuditSink local si conoce su ruta. | **Incorporada parcialmente:** queda declarado que el proceso ejecutado no puede escribir el registro autoritativo (propuesta §6.3) como invariante de diseño, y que la protección de la ruta del sink es responsabilidad del despliegue (permisos de filesystem), no de M0–M3. Se añade a no-claims: "ektel no defiende su almacén contra el proceso supervisado más allá de la separación de escritura por diseño". |
| A3 | La stop rule es social, no técnica: nada impide un M4 implícito. | **Refutada:** toda gobernanza de alcance es social; el mecanismo real es que los contratos v1 no tienen dónde colgar routing/memoria/delegación, y D6 exige acto de consenso. Suficiente para M0–M3. |

## 6. Criterio de revisión

Reabrir si se propone cualquier exclusión de §4 como objetivo, o si una
evidencia de plataforma contradice la clasificación de §12.2.

## 7. Decisiones que este ADR no toma

- Mecanismos concretos de cada garantía → ADR-006 (plataforma) y tabla de
  garantías de M2.
- Frontera del PolicyPort → ADR-008.
