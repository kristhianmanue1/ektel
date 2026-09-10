# Informe externo 1 de 3 — G-M2-15

> **CONSERVADO ÍNTEGRO. NO RECONCILIADO.** Este documento es el informe
> original del revisor, transcrito sin edición de contenido. No representa la
> posición del proyecto, no promueve ni degrada ningún gate, y **no se actúa
> sobre él hasta disponer de los tres informes originales**.

## Identidad del revisor y de la corrida

| Qué | Valor |
|---|---|
| Revisor | **OpenAI — GPT-5.6 Sol** |
| Rol | revisor externo independiente del agente ejecutor de M2 |
| Fecha | 2026-09-09 |
| Orden de recepción | **1 de 3** |
| REVIEW-ROOT evaluado | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` |
| MANIFEST-ROOT declarado | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |
| Veredicto | **FIX-AND-RETRY** — P0: 0 · P1: 5 |

## Limitación de ejecución declarada por el revisor

El revisor **no pudo reejecutar las suites**: su entorno no resolvió
`github.com`, de modo que no obtuvo un checkout independiente. Inspeccionó los
archivos exactos del REVIEW-ROOT mediante conector autenticado de GitHub.

En consecuencia, y en sus propias palabras:

- los resultados de 339 pruebas Darwin/Linux **no fueron reejecutados** por
  este revisor;
- los hallazgos están **demostrados por flujo de control estático** y
  acompañados de reproducciones ejecutables;
- **esas reproducciones deben añadirse y ejecutarse durante FIX-AND-RETRY**.

Esta limitación es material para la reconciliación: distingue un hallazgo
*derivado del código* de uno *observado en ejecución*. Se conserva aquí de
forma destacada para que la reconciliación no la pierda de vista.

## Riesgo de contaminación de independencia — atención

Este informe vive en `main`. Los revisores 2 y 3 **deben** trabajar sobre
`git checkout eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e`, que es anterior a este
archivo y por tanto **no lo contiene**.

Si un revisor inspeccionase `HEAD` en lugar del REVIEW-ROOT, vería este
informe y su veredicto dejaría de ser independiente. La regla de checkout del
encargo no es una formalidad: es lo que preserva la independencia una vez que
el primer informe existe en el repositorio.

---

# Informe original (transcripción íntegra)

**Revisión adversarial externa OpenAI — EKTEL M2 / G-M2-15**

Fecha: 2026-09-09
Revisor: OpenAI — GPT-5.6 Sol
Rol: revisor externo independiente del agente ejecutor de M2

## Identidad evaluada

REVIEW-ROOT

`eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e`

MANIFEST-ROOT declarado

`3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae`

El REVIEW-ROOT contiene la formalización de G-M2-12 y mantiene M2 abierto
exclusivamente por G-M2-15.

## Independencia

Esta revisión se realizó sin consultar informes de otros revisores externos de
G-M2-15.

Las rondas adversariales propias del ejecutor se trataron únicamente como
antecedentes de ataque, no como evidencia independiente.

## Limitación de ejecución

Se intentó obtener un checkout independiente del REVIEW-ROOT para ejecutar
pruebas directamente.

El entorno del revisor no pudo resolver github.com, por lo que no fue posible
realizar una segunda ejecución independiente de las suites.

La inspección se realizó sobre los archivos exactos del REVIEW-ROOT mediante el
conector autenticado de GitHub.

Por tanto:

- los resultados de 339 pruebas Darwin/Linux registrados por el proyecto no
  fueron reejecutados por este revisor;
- los hallazgos siguientes están demostrados por flujo de control estático y
  acompañados por reproducciones ejecutables;
- esas reproducciones deben añadirse y ejecutarse durante FIX-AND-RETRY.

## VEREDICTO

**FIX-AND-RETRY**

No procede cerrar G-M2-15 en el estado revisado.

No se encontró evidencia para NO-GO: los defectos identificados parecen
corregibles dentro de la arquitectura y alcance actuales de M2, sin modificar
schemas ni abrir M3/M4.

## Hallazgos

### OAI-M2-01 — P1 MATERIAL — `await_result()` no autentica el `ExecutionHandle`

`terminate()` autentica explícitamente el handle contra la clave e instancia
del coordinador antes de producir efectos.

`await_result()`, en cambio, solamente comprueba que el objeto sea una
instancia de `ExecutionHandle`; después utiliza directamente
`handle.handle_ref` para solicitar el terminal al `ProcessHost`.

Al recibirlo, elimina del registro la entrada asociada a ese `handle_ref` y
libera el slot.

El puerto `ProcessHost.collect_terminal()` tampoco autentica una capability:
recibe únicamente `handle_ref`.

Esto crea una asimetría:

`terminate(handle)` → autenticado

pero:

`await_result(handle)` → `handle_ref` suficiente

**Claim afectado**

- integridad del `ExecutionHandle`;
- G-M2-10;
- obligaciones 4 y 5 de G-M2-15;
- separación capability/reference.

**Reproducción requerida**

1. Iniciar una acción legítima y obtener `Started(handle_ref)`.
2. Construir otro `ExecutionHandle` con el mismo `handle_ref` pero:
   - otra `coordinator_instance`;
   - otro `identity_digest`;
   - otro `action_id`;
   - token inválido.
3. Esperar a que la acción legítima termine.
4. Ejecutar: `svc.await_result(forged_handle)`

**Resultado esperado**

El forged handle debe ser rechazado sin contactar el `ProcessHost` ni alterar
el slot/registro.

**Resultado derivado del código actual**

`await_result()` consulta el terminal por `handle_ref`, puede obtener el
resultado de la acción legítima y después `_release_handle()` elimina la
entrada real por ese mismo ref y libera capacidad.

**Consecuencia**

Un objeto que no posee la capability válida puede:

- acceder al terminal de otra acción;
- interferir en su ownership;
- eliminar su registro;
- alterar el accounting de slots.

**Corrección recomendada**

Antes de tocar `ProcessHost`:

1. autenticar el handle;
2. comprobar `coordinator_instance`;
3. comprobar que el registro contiene exactamente ese handle vivo;
4. sólo entonces realizar `collect_terminal()`.

Añadir regresiones para forged, cross-instance, released y handle de otra
acción.

### OAI-M2-02 — P1 MATERIAL — Un `handle_ref` inválido post-spawn libera capacidad pese a estado indeterminado

Después de que `ProcessHost.spawn()` retorna, EKTEL ya no puede asumir que
ningún proceso fue creado.

Sin embargo, si `handle_ref` no es `str` de longitud 16, `_spawn()` libera
inmediatamente el slot y devuelve:

`start_failed_indeterminate`

Esto es internamente contradictorio: declara incertidumbre sobre la existencia
del proceso, pero devuelve su capacidad al pool como si supiera que no existe.

La propia fixture `FakeProcessHost(bad_ref=True)` registra el spawn y después
devuelve una referencia inválida. La prueba existente comprueba que no se
fabrica un handle, pero no comprueba que el slot permanezca retenido.

Existe además una segunda variante.

`StartService` sólo comprueba longitud 16 antes de construir el
`ExecutionHandle`, pero `Started.__post_init__()` exige además hexadecimal
minúscula.

Un `ProcessHost` que retornara, por ejemplo:

`"gggggggggggggggg"`

superaría la primera comprobación, entraría en `_handles` y posteriormente
`Started()` lanzaría `ValueError`. El `except BaseException` exterior libera el
slot aunque el spawn ya haya ocurrido.

**Claims afectados**

- G-M2-06;
- G-M2-12;
- invariante de capacidad;
- preservación de Indeterminate.

**Reproducción mínima 1**

Con `FakeProcessHost(bad_ref=True)`:

- `out` debe ser indeterminado;
- comprobar además: `svc.slots_in_use == 1`

y que la identidad aparece en `retained_by_indeterminacy`.

El código actual deja el slot libre.

**Reproducción mínima 2**

Crear un `ProcessHost` que complete spawn y devuelva `"g"*16`.

No debe escapar excepción ni liberarse la capacidad.

**Corrección recomendada**

Validar completamente el `handle_ref` mediante una única función canónica antes
de crear cualquier objeto público.

Pero como la validación ocurre después del spawn, cualquier referencia inválida
debe tratarse como post-spawn indeterminado:

- retener slot;
- registrar identidad indeterminada;
- no fabricar handle;
- no liberar automáticamente.

### OAI-M2-03 — P1 MATERIAL — La configuración fail-closed puede eludirse y no existe una fuente única de configuración

`M2Config` documenta explícitamente que construir directamente el dataclass no
valida y que debe utilizarse `M2Config.build()`.

Sin embargo, `StartService` sólo comprueba:

`isinstance(config, M2Config)`

y después confía en sus valores.

Por tanto es posible construir directamente:

- `audit_mode="required"`;
- `max_concurrent_actions=0` o `>64`;
- tiempos fuera de rango;
- valores que `build()` rechazaría;

y `StartService` los acepta como `M2Config`.

Esto contradice el requisito normativo de que tipos/rangos inválidos y
`audit_mode=required` impidan inicializar M2. ADR-012 exige explícitamente
validación fail-closed durante inicialización.

Las pruebas actuales ejercitan `M2Config.build()` pero no intentan pasar a
`StartService` un `M2Config` construido directamente.

**Segunda parte: configuración declarada y configuración aplicada pueden divergir**

`StartService` utiliza de su `M2Config` esencialmente la capacidad para
construir `_SlotPool`.

El `PosixSupervisorHost` mantiene separadamente:

- `termination_grace_ms`;
- `post_kill_drain_ms`;
- `credit_timeout_ms`;
- `eof_drain_timeout_ms`;
- subreaper.

Y `AdmissionService` recibe por separado otro `m2_config` para construir el
`GuaranteePlan`.

Por tanto pueden existir simultáneamente tres configuraciones distintas:

Admission `M2Config`

StartService `M2Config`

PosixSupervisorHost parameters

sin un mecanismo que demuestre que representan el mismo deployment profile.

**Consecuencia**

EKTEL puede declarar una configuración en admisión y aplicar otra en el
supervisor.

Eso rompe la relación:

declared configuration → mechanism applied → evidence

que es precisamente la propiedad que `GuaranteePlan` pretende proporcionar.

**Reproducción**

Construir:

- `M2Config` con grace = 2000;
- `PosixSupervisorHost` con grace = 500;
- `StartService` con ambos.

La inicialización es válida y el supervisor aplica 500 aunque la configuración
declarativa pueda afirmar 2000.

**Corrección recomendada**

Establecer una única configuración validada como source of truth.

Por ejemplo:

`M2Config validated → StartService → PosixSupervisorHost.from_config(config)`

y evitar constructores paralelos con semántica independiente.

Además:

- validar en `M2Config.__post_init__`, o hacer imposible la construcción no
  validada;
- probar explícitamente que `audit_mode=required` no puede entrar mediante
  ningún constructor público;
- probar que valores declarados y aplicados coinciden.

### OAI-M2-04 — P1 MATERIAL — Drift directo contra las strings normativas congeladas por ADR-012

ADR-012 congela exactamente las siguientes assumptions:

`termination_grace_ms_configured=<int>`

`useful_runtime_formula=deadline_eff_ms-applied_grace_ms`

`supervisor_scope=per_action_process`

`subreaper_requested=<0|1>`

La implementación produce en cambio:

`useful_runtime_formula=useful_runtime_ms=deadline_eff_ms-min(termination_grace_ms,deadline_eff_ms)`

y usa por defecto:

`supervisor_scope=per_action`

Las fórmulas pueden ser matemáticamente equivalentes, pero ADR-012 congeló
deliberadamente el texto, orden y forma para evitar semántica libre.

Más importante: las pruebas actuales codifican el valor incorrecto:

`supervisor_scope=per_action`

en lugar del normativo `per_action_process`.

**Claim afectado**

G-M2-11 y conformidad ADR-012.

**Consecuencia**

La suite actualmente puede quedar verde demostrando conformidad consigo misma
mientras contradice el contrato normativo.

Es un ejemplo clásico de:

implementation-test agreement ≠ specification conformance

**Corrección recomendada**

Cambiar implementación y pruebas a los literales normativos exactos.

Añadir un test de igualdad completa de la tupla, no sólo de nombres de claves.

### OAI-M2-05 — P1 MATERIAL — La carrera terminate/deadline no preserva «primer hecho observado»

ADR-012 establece:

- gana el primer hecho observado;
- sólo en empate de observación gana deadline.

El supervisor, sin embargo, conserva únicamente dos booleanos independientes:

- `externally_terminated`;
- `deadline_hit`.

Al final exporta ambos estados, sin timestamp, sequence number ni registro de
cuál ocurrió primero.

`classify()` aplica después una precedencia estática:

1. supervision failure;
2. deadline;
3. external termination.

Por tanto, siempre que ambos booleanos sean verdaderos, deadline gana,
independientemente del orden real de observación.

**Reproducción**

Ejecutar un proceso que ignore SIGTERM:

1. deadline suficientemente lejano;
2. solicitar `terminate()` claramente antes del soft deadline;
3. supervisor observa primero el cierre del canal y fija
   `externally_terminated`;
4. proceso ignora TERM;
5. posteriormente alcanza el deadline y `deadline_hit` se vuelve verdadero;
6. KILL termina el proceso.

Al llegar al coordinador:

`externally_terminated=True`

`deadline_hit=True`

y `classify()` devuelve `deadline_exceeded`.

Pero el contrato exige `terminated`, porque el primer hecho observado fue la
terminación externa.

**Claim afectado**

- D-M2-4;
- G-M2-09;
- G-M2-10;
- determinismo causal del outcome.

**Corrección recomendada**

Registrar causalidad, no sólo estado final.

Por ejemplo, un campo atómico:

`first_terminal_cause`

o una secuencia monotónica local:

`external_termination_seq`

`deadline_seq`

y aplicar:

- menor secuencia gana;
- igualdad → deadline.

Añadir integración real con SIGTERM ignorado y terminación externa claramente
anterior al deadline.

## Revisión de las 16 obligaciones del encargo

| # | Obligación | Resultado OpenAI |
|---|---|---|
| 1 | CAS → spawn | Sin nuevo defecto material detectado |
| 2 | spent/unspent/unknown | Sin nuevo defecto material detectado |
| 3 | Carreras de capacidad | Falla por OAI-M2-02 y OAI-M2-03 |
| 4 | Handles forjados/cross-instance | Falla por OAI-M2-01 |
| 5 | terminate / await_result | Falla por OAI-M2-01 y OAI-M2-05 |
| 6 | deadlines | Falla por OAI-M2-05 |
| 7 | TERM→KILL | Sin nuevo defecto material detectado |
| 8 | backpressure | No encontré regresión nueva en la corrección revisada |
| 9 | pipe escape | La espera está acotada y el escape se declara; sin nuevo P1 |
| 10 | crash durability | Sin nuevo defecto estático; no reejecutado por este revisor |
| 11 | setsid / descendientes | Escape explícitamente declarado; sin nuevo P1 |
| 12 | Linux/Darwin | Diferencias principales declaradas; ejecución externa no repetida |
| 13 | regresión M1 | No observé violación estática; suite reportada no reejecutada |
| 14 | claims > evidencia | Falla por OAI-M2-04 y riesgo de OAI-M2-03 |
| 15 | TCB no autorizada | Sin dependencia nueva inesperada; sí existe problema de autoridad de configuración |
| 16 | alcance M2 | No detecté entrada en M3/M4 ni modificación de schemas/workflows |

## Evaluación general

La arquitectura M2 no parece requerir rediseño.

Los defectos encontrados tienen una característica común:

las fronteras conceptuales son mejores que algunas fronteras de enforcement de
la implementación.

En particular:

- el handle es capability en `terminate`, pero referencia ordinaria en
  `await_result`;
- la indeterminación está bien modelada, pero una rama post-spawn libera
  capacidad como si hubiera certeza;
- la configuración está bien especificada, pero puede construirse sin
  validación y divergir entre componentes;
- la causalidad de terminate/deadline está definida, pero se reduce a dos
  booleanos perdiendo orden;
- el contrato congela strings exactas, pero tests e implementación convergieron
  entre sí sobre valores distintos del contrato.

Éstos son defectos corregibles y no contradicen la arquitectura fundamental de
EKTEL.

## Condición para reintento externo

Después de reconciliar los tres informes iniciales, cualquier FIX debe
incorporar como mínimo pruebas de regresión para los hallazgos aceptados.

Para los hallazgos OpenAI deben existir específicamente pruebas que intenten:

1. `await_result` con handle forjado y cross-instance;
2. `handle_ref` post-spawn inválido conservando el slot indeterminado;
3. construcción directa de `M2Config` inválida;
4. divergencia entre configuración declarada y aplicada;
5. igualdad literal con las assumptions de ADR-012;
6. terminación externa anterior al deadline con proceso que ignore SIGTERM.

Después:

- suite completa Darwin;
- suite completa Linux;
- mypy strict;
- vectores diff cero;
- nuevo MANIFEST-ROOT;
- nuevo REVIEW-ROOT;
- revisión externa del diff correctivo.

## Veredicto final OpenAI

**FIX-AND-RETRY**

P0: 0
P1: 5
P2/P3: no relevantes para el veredicto

G-M2-15 no debe promoverse todavía.

M2 permanece abierto.

M3 permanece bloqueado.
