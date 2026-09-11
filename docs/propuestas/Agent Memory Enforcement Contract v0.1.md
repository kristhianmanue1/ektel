# Agent Memory Enforcement Contract v0.1

## Estado

**Tipo:** contrato experimental portable para runtimes/harnesses de agentes  
**Origen empírico:** campaña Prime Agent × AN-KLA y DSH × AN-KLA  
**Objetivo inmediato:** servir como contrato de entrada para EKTEL  
**Estado:** borrador para revisión adversarial y consenso

---

# 1. Propósito

Este contrato define las propiedades mínimas que debe satisfacer un runtime o harness para integrar una memoria gobernada como AN-KLA de forma que:

1. el agente no dependa de recordar voluntariamente utilizar memoria;
2. la pérdida de contexto no elimine la obligación de recuperar continuidad;
3. ninguna acción material protegida ocurra sin haber satisfecho previamente las condiciones de memoria;
4. el modelo pueda proponer escrituras de memoria sin poder otorgarse autoridad;
5. las transiciones de memoria queden ligadas a evidencia, revisión y estado observable;
6. el sistema pueda distinguir cierre correcto, cierre incompleto, fallo y ambigüedad;
7. subagentes y mecanismos de delegación no hereden autoridad implícitamente;
8. cualquier degradación relevante reduzca capacidades en lugar de permitir ejecución silenciosa.

El contrato no prescribe AN-KLA como única implementación de memoria.

AN-KLA es actualmente el sujeto de referencia utilizado para derivar y probar estas propiedades.

---

# 2. Principios fundamentales

Mantener siempre:

`MODEL INTENT ≠ AUTHORITY`

`MEMORY ≠ TRUTH`

`MEMORY ≠ CANONICAL SOURCE`

`RETRIEVAL ≠ AUTHORITY`

`PROPOSAL ≠ PLAN`

`PLAN ≠ COMMIT`

`COMMIT ≠ TRUTH`

`HASH ≠ SIGNATURE`

`DELEGATION ≠ AUTHORITY INHERITANCE`

`PROCESS TERMINATION ≠ SUCCESSFUL CLOSE`

`QUERY PLANE ≠ COMMAND PLANE`

---

# 3. Modelo abstracto

El runtime debe poder implementar conceptualmente:

```text
SESSION ENTER
      ↓
MEMORY RECOVERY
      ↓
CONTEXT VALIDATION
      ↓
CAPABILITY GATE
      ↓
MATERIAL WORK
      ↓
MATERIALITY OBSERVATION
      ↓
MEMORY PROPOSAL
      ↓
AUTHORITY MEDIATION
      ↓
PLAN
      ↓
COMMIT
      ↓
POST-COMMIT VERIFY
      ↓
CLOSE / HANDOFF
```

La memoria y el runtime deben permanecer desacoplados mediante contratos públicos.

---

# 4. Roles

## 4.1 Model

Puede:

- razonar;
- producir propuestas;
- solicitar acciones;
- interpretar memoria;
- sugerir facts, episodes o continuidad;
- generar rationale y source references.

No puede considerarse autoridad sobre sí mismo.

---

## 4.2 Runtime / Harness

Debe actuar como:

- Policy Enforcement Point;
- observador de capabilities;
- mediador de efectos;
- gestor de continuidad host-side;
- derivador de evidence disponible;
- guardián del command plane;
- árbitro de cierre lógico.

El runtime no debe asumir que el modelo obedecerá prompts.

---

## 4.3 Memory System

Debe proporcionar públicamente, cuando corresponda:

- estado;
- revisión;
- verify;
- retrieval;
- continuidad/checkpoint;
- planning;
- commit;
- CAS o protección de revisión;
- reason codes;
- read-back;
- manejo de transacciones ambiguas.

La memoria no debe depender del modelo para proteger sus invariantes internos.

---

## 4.4 Human / Operator

La autoridad humana no debe inferirse.

Debe existir evidencia explícita cuando una transición requiera decisión humana.

---

# 5. Mandatory Policy Composition

## MEC-01 — Policies antes de agentes

Las policies obligatorias deben cargarse y validarse antes de crear agentes o exponer capabilities materiales.

Orden requerido:

```text
BOOT
 ↓
LOAD REQUIRED POLICIES
 ↓
VERIFY POLICY SET
 ↓
CREATE AGENT
 ↓
REGISTER / EXPOSE CAPABILITIES
```

No permitido:

```text
CREATE AGENT
 ↓
EXPOSE CAPABILITIES
 ↓
LOAD POLICY LATER
```

---

## Justificación experimental

Prime Agent mostró que una policy correcta puede resultar inútil si algunos workers nacieron antes de cargarla.

DeepSeek Harness mostró una topología más robusta al montar plugins antes de crear agentes.

---

# 6. Policy Generation Fencing

## MEC-02 — Generación de policy

El runtime debe poder identificar qué generación/version/hash de policy protege a cada agente o worker.

Debe existir conceptualmente:

```text
policy_generation
policy_hash
loaded_at
runtime_identity
```

Un worker con policy stale no debe conservar capabilities protegidas después de un rollout obligatorio.

---

# 7. Per-Agent Enforcement State

## MEC-03 — Estado independiente

Cada agente debe mantener estado de enforcement independiente.

No se permite que un agente hijo herede implícitamente:

- continuity lease;
- dirty state;
- authority;
- evidence;
- receipts;
- close state.

Estado conceptual mínimo:

```text
UNBOUND
CONTEXT_VALID
WORKING
DIRTY
CLOSE_REQUIRED
CLOSED_SUCCESS
CLOSED_INCOMPLETE
DEGRADED
```

---

# 8. Mandatory Memory Recovery

## MEC-04 — Recovery host-side

El agente no debe decidir voluntariamente si consulta memoria cuando la policy exige continuidad.

El runtime debe recuperar o provocar obligatoriamente:

- status;
- verify;
- retrieval/context assembly;
- checkpoint/continuity state.

---

## MEC-05 — Capsule

El runtime debe inyectar una cápsula de continuidad acotada.

Debe conservar, cuando exista:

- project/scope identity;
- revision;
- checkpoint;
- goal;
- next step;
- blockers;
- selected records;
- degradation metadata;
- excluded-summary metadata;
- untrusted-memory flag.

La cápsula no debe promover memoria a autoridad.

---

# 9. Consistent Recovery

## MEC-06 — Protección TOCTOU

El runtime no debe producir una cápsula a partir de una mezcla de revisiones.

Si no existe snapshot transaccional público, aplicar un patrón equivalente a:

```text
status R1
→ verify
→ assemble
→ status R2
```

Aceptar sólo:

`R1 == R2`

Si la revisión cambia:

- descartar;
- retry acotado.

Si no logra estabilizarse:

`DEGRADED`

y las capabilities materiales permanecen bloqueadas.

---

# 10. Capability Enforcement Point

## MEC-07 — PEP antes del efecto

Toda capability material protegida debe atravesar un punto de policy antes de ejecutar su body.

Conceptualmente:

```text
CAPABILITY REQUEST
       ↓
POLICY
   ┌───┴───┐
 ALLOW    DENY
   │        │
 EXECUTE   STOP
```

La policy debe ejecutarse antes del efecto.

---

# 11. Complete Mediation

## MEC-08 — Toda ruta material debe converger

El runtime debe mantener un inventario del capability set.

Cada capability debe clasificarse como:

- READ_ONLY;
- MATERIAL;
- UNKNOWN.

Default seguro:

`UNKNOWN → MATERIAL`

cuando esté en juego enforcement.

No se puede declarar complete mediation mientras exista una capability material no evaluada.

---

## Scope de la garantía

Complete mediation siempre debe declararse respecto de:

- runtime version;
- profile;
- plugin set;
- capability inventory.

Cambiar el capability set invalida la garantía previa hasta revalidación.

---

# 12. Materiality Observation

## MEC-09 — Dirty derivado del efecto

`DIRTY` debe producirse por observación host-side de una capability material exitosa.

No por afirmación del modelo.

Ejemplos:

```text
read → no dirty

write success → dirty

denied write → no dirty

failed write without effect → no dirty

unknown effect → tratar conservadoramente
```

---

# 13. Context Loss / Compaction

## MEC-10 — Invalidación de continuidad

Compactación, resume, pérdida de contexto o evento equivalente debe provocar invalidación de continuity state cuando no pueda demostrarse preservación segura.

Flujo:

```text
CONTEXT_VALID
 ↓
COMPACTION
 ↓
INVALID
 ↓
RECOVER MEMORY
 ↓
NEW CAPSULE
 ↓
CONTEXT_VALID
```

El modelo no debe poder continuar materialmente usando sólo lo que recuerda.

---

# 14. Delegation Confinement

## MEC-11 — Child isolation

Un subagente debe obtener su propio enforcement state.

Un padre con:

`CONTEXT_VALID`

no autoriza automáticamente al hijo.

El hijo material debe pasar:

```text
UNBOUND
→ recovery
→ CONTEXT_VALID
```

---

## MEC-12 — No authority inheritance

El hijo puede recibir una tarea.

No recibe automáticamente:

- tool-observed authority;
- human authority;
- receipts;
- transaction rights;
- close state;
- memory-write permissions.

---

# 15. Query Plane / Command Plane

## MEC-13 — Separación

Las operaciones de lectura y escritura deben estar separadas.

Query plane:

- status;
- verify;
- retrieve;
- assemble-context;
- checkpoint read.

Command plane:

- proposals;
- planning;
- authority derivation;
- write;
- checkpoint transitions.

No es obligatorio utilizar protocolos diferentes, pero sí fronteras de policy distintas.

---

# 16. Proposal-Based Writes

## MEC-14 — El modelo propone

El modelo no recibe conceptualmente:

`write_memory()`

Debe recibir:

`propose_memory_transition()`

Una proposal puede contener:

- statement;
- type;
- source references;
- rationale;
- requested representation.

No debe contener campos que concedan authority.

---

# 17. Authority Derivation

## MEC-15 — Authority no controlada por el modelo

El modelo no puede declararse:

- tool_observed;
- human_confirmed;
- trusted;
- authoritative.

La authority debe derivarse del evidence disponible en el host y del contrato de la memoria.

---

## MEC-16 — Model-derived ceiling

Una afirmación proveniente únicamente de razonamiento del modelo debe conservar el techo de authority definido por la memoria/policy.

Intentar representación superior debe:

- rechazarse;
- reducirse explícitamente;
- o producir reason code.

Nunca elevarse silenciosamente.

---

# 18. Tool-Observed Evidence

## MEC-17 — Observación real

`tool_observed` sólo puede utilizarse cuando el runtime observó realmente la operación.

Ejemplo:

```text
command
exit code
output/artifact hash
timestamp
execution identity
```

No aceptar:

> "ejecuté la prueba y pasó"

como evidencia.

---

# 19. Human Authority

## MEC-18 — No fabricar consentimiento

Cuando se requiera autoridad humana:

- solicitar aprobación;
- registrar evidencia correspondiente;
- o dejar la transición pendiente/rechazada.

Nunca inferir:

`human said yes`

desde texto generado por el modelo.

---

# 20. Proposal Binding

## MEC-19 — Inmutabilidad lógica de proposal

Una proposal validada debe quedar ligada por digest o mecanismo equivalente.

Modificar:

- statement;
- source refs;
- representation;
- authority context;
- base revision;

requiere nueva planificación.

---

# 21. Plan Binding

## MEC-20 — Plan ligado a proposal + authority + revisión

Un plan debe quedar ligado como mínimo a:

```text
proposal digest
authority digest/context
base revision
```

Un plan viejo no debe servir para proposal nueva.

---

# 22. CAS / Stale Protection

## MEC-21 — No commit stale

Si la memoria avanza entre planificación y commit:

```text
R0 → plan
R1 appears
commit(plan R0)
```

debe producir:

`STALE / CAS FAILURE / REPLAN REQUIRED`

Nunca commit silencioso sobre base stale.

---

# 23. Replay Resistance

## MEC-22 — Replay

Repetir:

- proposal;
- plan;
- transaction id;
- commit request;

no debe crear una segunda transición accidental.

El sistema debe proporcionar semántica explícita:

- idempotent;
- duplicate;
- stale;
- already committed;
- rejected.

---

# 24. Ambiguous Commit Outcome

## MEC-23 — Ambigüedad explícita

Si el commit puede haber ocurrido pero el runtime pierde/rompe la respuesta:

NO clasificar automáticamente como:

- SUCCESS;
- FAILURE.

Clasificar:

`AMBIGUOUS`

Después utilizar:

- status snapshot;
- transaction inspect;
- read-back;
- revision comparison.

---

## Justificación experimental

DSH × AN-KLA v0.3.4 produjo un commit real seguido de fallo del mediator al interpretar output.

El resultado correcto no era "failed".

Era "unknown until reconciled".

---

# 25. Post-Commit Verification

## MEC-24 — Read-back

Un commit no queda aceptado por el mediator únicamente porque respondió:

`committed:true`.

Debe verificar cuando sea viable:

- revisión nueva;
- record recuperable;
- contenido esperado;
- authority esperada;
- transaction status.

---

# 26. Close / Handoff

## MEC-25 — Dirty no puede ser SUCCESS sin cierre

Si:

`dirty = true`

el agente no puede alcanzar:

`CLOSED_SUCCESS`

sin comprobar la transición de continuidad requerida.

---

## MEC-26 — Liveness

El sistema tampoco debe entrar en loop infinito.

Si el cierre no puede resolverse después de una policy acotada:

```text
CLOSED_INCOMPLETE
```

o estado terminal equivalente.

Nunca convertir cierre incompleto en éxito.

---

# 27. Close Verification by State

## MEC-27 — No parsing de comandos

No reconocer cierre porque el agente ejecutó una string como:

`checkpoint commit`

Verificar el efecto observable en el memory system:

- revisión;
- checkpoint;
- transaction;
- pending continuity.

---

# 28. Fail-Closed

## MEC-28 — Degradación

Ante:

- memory unavailable;
- verify failure;
- malformed output;
- timeout;
- invalid authority;
- stale plan;
- ambiguous transition;
- policy exception;

las capabilities protegidas deben reducirse.

No:

`warning → continue material work`

---

# 29. Fail-Closed by Design

## MEC-29 — No contar crashes como seguridad

Un `ReferenceError`, excepción inesperada o crash que casualmente bloquee una operación no constituye enforcement válido.

Debe demostrarse que:

`DENY`

provino de policy explícita.

---

# 30. Evidence Logging

## MEC-30 — Evidencia host-side

Registrar sin secretos:

- timestamp;
- agent/session identity;
- policy generation;
- runtime version;
- capability;
- classification;
- pre-state;
- decision;
- post-state;
- memory revision;
- proposal digest;
- plan digest;
- transaction id;
- resulting revision;
- close outcome.

---

# 31. Secrets

## MEC-31 — Separación de secretos

El modelo no debe recibir:

- attest keys;
- HMAC secrets;
- signing material;
- tokens internos de mediator.

Los secrets no deben aparecer en logs.

---

# 32. Bootstrap Failure

## MEC-32 — Required policy load

Si una policy declarada obligatoria no puede cargarse:

el runtime no debe crear normalmente un agente con capabilities materiales protegidas.

Resultado aceptable:

- boot fails;
- restricted diagnostic mode;
- no material capabilities.

---

# 33. Capability Inventory Binding

## MEC-33 — Garantía ligada al inventario

Un resultado:

`COMPLETE_MEDIATION = PASS`

debe quedar ligado a un inventario concreto de tools/capabilities.

Nueva tool/plugin:

→ garantía stale  
→ revalidación requerida.

---

# 34. Experimental Profiles

Un runtime puede declarar perfiles de assurance:

## P0 — Procedural

El modelo recibe instrucciones.

Sin enforcement mecánico.

## P1 — Consumption Enforced

Memory recovery obligatoria antes de trabajo material.

## P2 — Lifecycle Enforced

Incluye:

- dirty tracking;
- compaction recovery;
- child isolation;
- close enforcement.

## P3 — Governed Write

Incluye:

- proposal;
- authority mediation;
- plan binding;
- CAS;
- read-back;
- ambiguity handling.

## P4 — Complete Mediation

Todas las capabilities materiales del perfil pasan por el PEP.

## P5 — OS / Reference Monitor

El proceso controlado por el modelo tampoco puede evadir el mediator mediante syscalls, filesystem directo u otros canales fuera del runtime.

---

# 35. Requisitos mínimos para EKTEL

EKTEL debería evaluar, como mínimo:

- MEC-01 mandatory policy composition;
- MEC-02 generation fencing;
- MEC-03 per-agent state;
- MEC-07 PEP before capability;
- MEC-08 complete mediation;
- MEC-10 context-loss recovery;
- MEC-11 child isolation;
- MEC-15 authority separation;
- MEC-21 CAS;
- MEC-23 ambiguity;
- MEC-25 successful close;
- MEC-28 fail-closed;
- MEC-32 bootstrap failure.

No significa que EKTEL deba implementar AN-KLA.

Significa que debe permitir que una memoria gobernada pueda imponer estas condiciones mediante contrato.

---

# 36. Lecciones de Prime Agent

## Demostrado

Un PEP correcto no basta si no se garantiza su presencia en todos los workers.

Fallos observados:

- extensions cacheadas por worker;
- workers pre-policy;
- cobertura inconsistente;
- enforcement probabilístico;
- degradación operacional al endurecer el mecanismo.

## Requisito derivado

`policy presence` debe ser propiedad del runtime, no accidente del lifecycle del cliente.

---

# 37. Lecciones de DeepSeek Harness

## Demostrado en perfil probado

DeepSeek permitió:

- plugins obligatorios antes del agente;
- PEP pre-execute;
- state per-agent;
- child isolation;
- compaction recovery;
- close enforcement;
- fail-closed;
- revision-race detection;
- complete mediation del profile;
- command-plane reservation;
- proposal-based writes;
- authority ceilings;
- CAS;
- replay handling;
- ambiguous commit reconciliation.

## Limitación

La evidencia está ligada a:

- DSH 0.1.5-rc.1;
- perfil `aria-ankla-test`;
- capability inventory probado;
- adapters experimentales concretos.

No extrapolar universalmente.

---

# 38. Relación con AN-KLA

AN-KLA proporciona actualmente varias de las primitivas necesarias:

- governed records;
- revisions;
- verify;
- retrieval;
- checkpoints;
- plan-write;
- commit-write-plan;
- authority ceilings;
- receipts;
- CAS;
- transaction behavior;
- host hooks.

El runtime no debe absorber AN-KLA.

AN-KLA no debe convertirse en runtime.

La integración ocurre mediante contratos.

---

# 39. Relación con SKEVI

SKEVI puede utilizar este contrato para definir:

- gates;
- metodología experimental;
- criterios de promoción;
- evidencia requerida;
- adversarial;
- candidate freezing.

SKEVI no debe convertirse en PEP runtime.

---

# 40. Relación con Scopos

Scopos puede:

- observar conversaciones;
- conservar historia;
- aportar provenance temporal;
- registrar qué ocurrió.

No debe convertirse automáticamente en authority provider.

---

# 41. Relación con Ágora

Ágora puede consumir posteriormente información de:

- Scopos;
- AN-KLA;
- otras fuentes.

Este contrato no define todavía escritura o consumo de niveles L1…LN.

Ágora permanece fuera de alcance.

---

# 42. Relación con CAGF

El contrato operacionaliza varios principios compatibles con CAGF:

- el agente no puede autoevaluarse como única autoridad;
- evidence y authority deben separarse;
- el evaluado no debe controlar unilateralmente el mecanismo de validación;
- los transitions deben quedar auditables;
- ausencia de evidencia no debe convertirse en verdad.

CAGF sigue siendo marco normativo superior, no dependencia runtime.

---

# 43. Hipótesis para EKTEL

## E-MEC-1

EKTEL puede cargar policies obligatorias antes de exponer capabilities.

## E-MEC-2

Toda capability material declarada atraviesa un PEP verificable.

## E-MEC-3

Un child no hereda continuity/authority sin derivación explícita.

## E-MEC-4

Una policy ausente/rota produce fail-closed.

## E-MEC-5

Una memoria externa puede invalidar capabilities mediante contrato sin que EKTEL dependa de su implementación.

## E-MEC-6

EKTEL distingue SUCCESS, INCOMPLETE, FAILED y AMBIGUOUS.

## E-MEC-7

EKTEL puede mantener query plane separado del command plane.

---

# 44. Criterio de conformidad

Un runtime no debe declararse conforme por implementar APIs con nombres similares.

Debe demostrar comportamiento falsable.

Cada MEC relevante requiere:

`precondition`
→ `attack`
→ `policy decision`
→ `effect/non-effect`
→ `external verification`

---

# 45. No objetivos

Este contrato NO define:

- protocolo de memoria universal;
- formato universal de facts;
- modelo de embedding;
- L1/L2/LN;
- UI;
- transporte MCP obligatorio;
- backend de almacenamiento;
- autenticación humana completa;
- multi-host consensus;
- blockchain;
- economía entre agentes.

---

# 46. Resultado buscado

El objetivo final es permitir:

```text
MEMORY SYSTEM
      │
      │ contracts
      ▼
RUNTIME / EKTEL
      │
      │ capabilities
      ▼
AGENT
```

sin que:

- la memoria controle el runtime;
- el runtime controle la semántica interna de la memoria;
- el modelo sea autoridad sobre ambos.

---

# 47. Estado del contrato

`AMeC v0.1 = EXPERIMENTAL`

Derivado de evidencia real.

No declarar estándar.

Siguiente paso recomendado:

1. revisión adversarial independiente;
2. comparación contra EKTEL actual;
3. gap analysis;
4. seleccionar subconjunto MEC mínimo para M2/M3;
5. producir hipótesis falsables;
6. implementar sólo los gaps demostrados.

---

# Regla final

El contrato debe preservar esta idea:

> La memoria puede recordar.  
> El runtime puede impedir.  
> El modelo puede proponer.  
> La evidencia puede justificar.  
> Ninguna de esas funciones debe confundirse con las demás.