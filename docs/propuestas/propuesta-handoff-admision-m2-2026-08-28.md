# Borrador separado: handoff de admisión hacia M2

**Fecha:** 2026-08-28. **Estado:** borrador separado de M1-R1, no vinculante.
Sirvió de base para la propuesta
`docs/adr/adr-011-handoff-admision-start.md`, que permanece pendiente de
aceptación explícita. No autoriza implementación de M2, cambios wire, procesos
reales ni supervisión.

## Bloqueo observado

La especificación declara `start(AdmittedAction)`, exige consumir el token por
CAS inmediatamente antes del spawn y define
`deadline_eff = min(deadline_solicitado, exp - now_wall)`. El token de admisión
M1 actual liga identidad, `action_id`, `exp` e `issuer_id`, pero no transporta
el descriptor ejecutable ni el deadline solicitado. Por sí solo no contiene
material suficiente para construir una ejecución y no debe reinterpretarse
como permiso autónomo para inventarlo o recuperarlo de una fuente mutable.

## Límite criptográfico confirmado

`identity_digest` identifica los bytes autenticados del sobre de capacidad,
no los bytes completos del `ActionRequest`. Dos requests con serialización
distinta —o con `metadata_opaque` distinto— pueden producir el mismo digest y
el mismo token de admisión. Por tanto, presentar de nuevo el request junto al
token **no demuestra por sí solo** que sean los bytes observados por `admit`.

`start` tampoco puede limitarse a comparar el `identity_digest`: si utiliza el
descriptor exterior debe repetir la coherencia descriptor↔`action_binding`, el
digest efectivo de stdin, representabilidad, nonce y demás invariantes que
impiden ejecutar material distinto con la misma capacidad.

## Alternativas que deben decidirse antes de M2

### A. Contexto local inmutable

`admit` devuelve un objeto local no serializable que contiene el token y el
descriptor ejecutable ya validado. `start` acepta únicamente ese tipo opaco.
Evita persistencia adicional, pero no sirve como contrato wire ni sobrevive un
reinicio del supervisor.

### B. Digest nuevo del request o descriptor

Una versión posterior del token liga un digest explícito de los bytes completos
del request o de una representación canónica del descriptor ejecutable. Es la
única opción que puede sostener una afirmación criptográfica de identidad
byte-a-byte o semántica, respectivamente; cambia el contrato y requiere versión,
vectores y compatibilidad explícita.

### C. Reenvío con revalidación completa

Introducir conceptualmente un `StartRequest` que lleve:

1. el token de admisión opaco emitido por M1; y
2. un `ActionRequest` que el llamador presenta nuevamente.

`start` vuelve a parsear y ejecuta todas las validaciones determinantes de M1,
verifica MAC/vigencia del token y coherencia completa con la capacidad. Esta
opción puede demostrar equivalencia del material ejecutable, pero no que los
bytes exteriores sean los originalmente observados. El CAS de consumo sigue
inmediatamente antes de cruzar la frontera de proceso.

Las tres opciones deben comparar además su tratamiento de latencia,
confidencialidad de stdin, retención, reinicio y compatibilidad experimental.

## Decisiones que la autoridad debe cerrar

- **Forma de API:** argumento compuesto local o nuevo contrato wire
  experimental y versionado.
- **Identidad:** byte-a-byte del request, representación canónica del descriptor
  o equivalencia semántica revalidada; son garantías diferentes.
- **Deadline:** recomputarlo en `start` con `min(requested, exp-now)` —opción
  recomendada por ser más restrictiva— o firmarlo explícitamente en una
  versión posterior del token.
- **Política:** si el recibo sólo informa o debe quedar atestado dentro del
  material consumido por `start`.
- **Orden de efectos:** representación tipada del crash entre CAS y spawn, y
  evidencia durable de `start_indeterminate`.
- **Retención:** tamaño máximo y tratamiento de stdin inline en la repetición
  del request, sin persistencia implícita.

## Stop rule

No modificar schemas, token, puerto de proceso ni replay CAS hasta que exista
una decisión explícita sobre estos puntos y una tarjeta M2 con DoD y ronda
adversarial propia. Esta propuesta no resuelve las garantías de plataforma de
M2 y no promueve claims.
