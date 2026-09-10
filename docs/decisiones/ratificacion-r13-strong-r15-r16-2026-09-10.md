# Decisión humana normativa — R13-STRONG, R15 y R16

**Fecha:** 2026-09-10. **Autoridad:** decisión explícita del dueño por canal.
**Referencia:** adjudicación en `dc3de184de495abe022c656fb8b947a1b976ed8f`,
[adjudicación arquitectónica](../revisiones/g-m2-15/adjudicacion-arquitectonica-r13-r14-2026-09-10.md).
Este asiento organiza la decisión recibida; no pretende ser transcripción literal.

## 1. Ratificación

Se ratifica `R13-STRONG = BLOCKED-BY-NORMATIVE-GAP` para
`arbitrary Python code executing inside the same coordinator process`.
Se conserva `R13 = NOT-SATISFIED bajo su formulación fuerte`.
Objetos, closures, sentinels, name mangling, threads y referencias internas
no constituyen una frontera de seguridad contra el intérprete compartido.

No-claim autorizado, reproducido literalmente:

> EKTEL M2 no proporciona aislamiento de seguridad frente a código Python
> arbitrario ejecutándose dentro del mismo proceso del coordinador ni garantiza
> que dicho código no pueda inspeccionar o modificar estado interno del runtime.

No autoriza una frontera posterior ni la asigna a M3.

## 2. Threat model ratificado

Confiables para R15/R16: coordinador, Admission/Start internos autorizados,
Host autorizado/configurado y estado interno local mediante interfaces admitidas.
Siguen siendo hostiles las entradas: requests, tokens, handles, fingerprints del
caller, tipos hostiles, concurrencia, secuencias abusivas, timeouts y malformados.
Composiciones incompatibles de componentes genuinos no se excluyen del rechazo.

Fuera de claim: introspección/modificación arbitraria del intérprete, sustitución
arbitraria de componentes confiables, Host malicioso con autoridad equivalente y
extracción/modificación de memoria. No convierte fallos parciales normales de
Host/ReplayStore en supuestos de éxito ni elimina reconciliación.

## 3. Construcción expresamente autorizada

**FIX-M2-R15 — Terminal writer separation bajo threat model M2:** ningún consumidor
puede suministrar, depositar ni cerrar autoritativamente el terminal por interfaces
admitidas. Writer interno, transición exactly-once y como máximo una entrega si
existe resultado; ausencia/abandono no obligan a fabricar una entrega. Preservar R12.

**FIX-M2-R16 — Admission issuance provenance binding:** evidencia creada por
Admission durante emisión reconocida. Caller transporta token/StartRequest, pero
no declara emisor, fingerprint ni asociación reconocida. Antes de CAS/spawn:

```text
recognized Admission emission == Start required configuration == Host committed configuration
```

Ausencia, ambigüedad o divergencia fallan cerrado antes del CAS/spawn; el intento
no consume el token. La evidencia puede ser local, efímera, acotada e independiente
del ReplayStore, con lifecycle explícito. No existe registro público de token con
fingerprint autodeclarado. No crecimiento ilimitado.

Perder evidencia tras reinicio implica fail-closed: no reconstruirla desde token
v1. Continuidad de provenance entre reinicios exige otra decisión. La durabilidad
de replay existente permanece. La comprobación pre-CAS acredita el compromiso del
Host confiable, no el éxito de todos los efectos futuros del SO.

## 4. Resoluciones de implementación dentro de la autorización

Estas son decisiones técnicas del implementador, no citas atribuidas al dueño:

- Diseñar A; conservar StartRequest/token v1. Admission M2 posee evidencia y una
  identidad de propietario Start local. Construir otro Start con el mismo Admission
  invalida su evidencia anterior y el lookup del propietario anterior; no es recuperación.
- Capacidad N derivada de `max_concurrent_actions` (1..64), independiente de slots
  y handles. Serializar admisiones M2; antes del pipeline rechazar saturación con
  el reason existente `capability_rejected`, `retryable=True`, diagnóstico
  `m2:issuance_capacity`. No reservar nonce para un rechazo por saturación.
- Ruta M1 sin `m2_config` conserva exactamente su pipeline y diagnósticos.
  La extensión de emisión M2 está autorizada por §3 de este acto; no se generaliza
  a cambios de PolicyPort, wire ni decisiones de admisión M1.
- Expirar al vencer vigencia estricta de Start; preservar evidencia para fallo
  pre-CAS/unspent/unknown. Retirar en consumo/spent, después del spawn si éste
  corresponde, sin introducir locks de Admission entre CAS y spawn. El resultado
  retenido no conserva evidencia de emisión. Los intentos que ya resolvieron el
  snapshot siguen sujetos a capacidad, vigencia y CAS; no adquieren otro derecho.
- Los strings token se usan completos como clave con comparación exacta; no se usa
  sólo action_id. El emisor se reconoce por el Admission ligado al Start, no por
  identidad histórica universal. No se transportan fingerprints nuevos en wire.

Superficies consumidoras: `start`, `handle_for`, `await_result`, `terminate`,
propiedades de diagnóstico y operaciones de receipt/abandono del handle.
`AdmissionService.admit` es la única ruta pública que produce emisiones: valida
la admisión completa, no acepta asociaciones prefabricadas. Constructores son
composición confiable, pero todo Start acepta sólo evidencia de su emisor ligado;
el string legado `declared_config_fingerprint` no tiene autoridad.
Métodos `_...` y callbacks writer no son interfaces consumidoras; esto es
separación por diseño, no aislamiento fuerte. No se elimina una operación pública
vigente de inicio/consumo para ocultar un contraejemplo.

## 5. Frontera y parada

R15/R16 son `AUTHORIZABLE-WITHIN-M2` con construcción ahora **AUTORIZADA** únicamente
sin wire/schema nuevos, cambios sustantivos a contratos congelados fuera de esta
ratificación, IPC nuevo, procesos de aislamiento, persistencia nueva ni M3/M4.
Si dejan de cumplirse esas condiciones: `BLOCKED-BY-NORMATIVE-GAP`, detener la
implementación y devolver evidencia. No crear una solución de aislamiento.

Alcance de esta corrección: Admission/Start, handle y snapshot operativo del Host;
fixtures/pruebas M2 y documentación normativa/evidencia correspondiente. ReplayStore,
revalidación pura, schemas, vectores, SpawnFrontier y fixtures M1 permanecen intactos.

Después de implementar: regresión completa, replay de contraejemplos, nuevo
MANIFEST-ROOT, nuevo CORRECTIVE-REVIEW-ROOT y re-verificación externa.
La autorización de construir no adjudica conformidad del futuro diff.

```text
normative_ratification = RATIFIED-BY-HUMAN
corrective_action_3 = AUTHORIZED
R13 = NOT-SATISFIED
R13-STRONG = BLOCKED-BY-NORMATIVE-GAP
G-M2-15 = CORRECTIVE-FIX-AND-RETRY
M2 = OPEN
M3 = BLOCKED
```

No se autoriza cierre de G-M2-15 ni M2, ni inicio M3. El acto no borra la
adjudicación previa ni sus findings; resuelve sus decisiones humanas pendientes
en el alcance expresamente ratificado aquí.
