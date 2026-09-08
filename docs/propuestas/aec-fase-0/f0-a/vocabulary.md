# F0-A — Vocabulario controlado

- **Estado:** cierre F0-A; provisional para investigación posterior.
- **Clasificación:** `PUBLISHABLE` como candidato; no autoriza publicación.

## Regla de uso

Los términos siguientes evitan equivalencias falsas. Ninguno constituye aún un
campo, schema, wire format o requisito normativo de AEC.

| Término | Definición operativa F0-A | No significa |
|---|---|---|
| bounded effectful invocation | Solicitud identificable para intentar una operación con límites declarados y posibles efectos externos | proceso único, sesión, workflow o efecto exactamente una vez |
| intent | Descripción estable de lo que el caller solicita | autorización, admisión o ejecución |
| invocation | Instancia protocolaria de una intención | intento del executor |
| dispatch | Acto de ofrecer o entregar una invocación a una frontera de ejecución | inicio observado ni efecto |
| admission | Decisión de aceptar responsabilidad bajo un perfil y condiciones explícitas | ejecución, policy allow aislado ni garantía aplicada |
| attempt | Instancia concreta en la que un executor trata de realizar la operación | invocación completa; puede haber cero, uno o varios |
| executor | Mecanismo que realiza un intento: proceso, worker, controlador o herramienta | runtime completo ni autoridad |
| effect | Cambio externo atribuible materialmente a la operación | exit code, respuesta o evento por sí solo |
| occurrence | Hecho que una fuente afirma u observa que ocurrió | prueba causal o evento único |
| observation | Registro de un observador sobre estado u ocurrencia | verdad completa del sistema |
| outcome | Clasificación protocolaria de lo conocido al cerrar una etapa | éxito de negocio ni ausencia de efectos |
| result | Datos producidos por executor o proveedor | outcome global ni evidencia verificada |
| receipt | Acuse emitido por un participante sobre una acción o transición | attestation independiente |
| telemetry | Señales operativas producidas para observación | receipt, proof o causalidad |
| measurement | Valor obtenido mediante procedimiento y sujeto identificados | attestation ni garantía aplicada |
| attestation | Claim estructurado con sujeto, productor y alcance, potencialmente autenticable | veracidad automática del claim |
| proof | Evidencia que permite verificar un predicado definido bajo supuestos y trust anchors explícitos | seguridad general |
| provenance | Información que liga un artefacto o claim con productor, proceso e inputs relevantes | corrección o ausencia de manipulación dentro de todo el TCB |
| evidence | Objeto o referencia usado para sostener un predicado, con productor, frescura, alcance y límites | garantía global |
| verified | Un verifier ejecutó un procedimiento especificado y aceptó un predicado bajo trust anchors explícitos | verdadero fuera de ese modelo de confianza |
| capability declaration | Declaración versionada de lo que un runtime dice soportar | que lo aplicará en una invocación |
| profile | Semántica versionada de operación, lifecycle, garantías y errores | etiqueta descriptiva libre |
| compatibility | El caller puede decidir antes de dispatch que declaraciones y requisitos no son incompatibles | enforcement real ni equivalencia entre runtimes |
| authorization | Decisión de una autoridad de permitir acciones concretas sobre recursos/audiencias | autenticación o policy evaluation aislada |
| authentication | Validación de una identidad o credencial bajo un trust anchor | autoridad para ejecutar |
| PDP | Componente que calcula una decisión de política | componente que aplica la decisión |
| PEP | Componente en la frontera de acción que aplica una decisión | origen necesariamente independiente de evidencia |
| configured | Un control aparece configurado | que estuvo activo en el intento |
| applied | El PEP/runtime declara o registra aplicación de un control | que se observó su eficacia |
| observed | Un observador registró un estado o hecho | causalidad o cobertura completa |
| evidenced | Existe evidencia identificada para un predicado | que un verifier la validó |
| idempotency key | Clave para correlación/deduplicación según un dominio definido | idempotencia del efecto |
| request deduplication | Prevención o detección de solicitudes repetidas dentro de una ventana | at-most-once dispatch o exactly-once effect |
| single-use authorization | Credencial cuya reutilización se rechaza | un único intento o efecto |
| at-most-once dispatch | La frontera promete no despachar más de una vez bajo condiciones precisas | que el executor no se duplicó después |
| operation-level idempotency | Repetir la operación bajo su perfil converge al efecto definido | que no hubo múltiples intentos |
| ambiguous effect outcome | La evidencia disponible no permite concluir si ocurrió un efecto | failure; debe permanecer indeterminado |
| cancellation requested | El caller pidió detener procesamiento | cancelación efectiva ni reversión de efectos |
| cancellation observed | Un observador registró que un mecanismo atendió cancelación | ausencia de efectos previos o supervivientes |
| deadline | Límite temporal con alcance declarado | timeout universal; puede excluir cola u overhead |
| trust anchor | Raíz explícita usada para aceptar identidad, firma o evidencia | autoridad universal |
| TCB | Clausura de componentes cuya corrección debe asumirse para sostener un predicado | lista de dependencias general |
| downgrade | Pérdida u omisión de una propiedad requerida al traducir perfiles | compatibilidad aceptable |
| indeterminate | La etapa no puede clasificarse de forma segura con evidencia disponible | retryable, failed o succeeded |

## Vocabulario de lifecycle

Se conservan cinco ciclos independientes:

1. **invocation:** creada, modificada, cerrada;
2. **dispatch:** no intentado, ofrecido, aceptado, rechazado, ambiguo;
3. **executor:** pendiente, iniciado, terminado, perdido;
4. **effect:** no observado, observado, reconciliado, compensado, indeterminado;
5. **evidence:** producido, persistido, verificado, expirado o indisponible.

Una transición en un ciclo no se propaga automáticamente a los demás. La
cardinalidad `invocation -> attempt` es `0..n`.

## Outcomes mínimos conceptuales

No son un schema. F0-A sólo establece que una fase posterior no debe colapsar:

- `rejected`: no hubo admisión bajo ese perfil;
- `protocol_succeeded`: la interacción protocolaria terminó como se esperaba;
- `executor_succeeded` / `executor_failed`: significado definido por perfil;
- `cancelled`: sólo con alcance explícito de lo cancelado;
- `indeterminate`: no se conoce de forma segura el estado relevante;
- `superseded`: otra observación/operación reemplazó la vigencia de ésta.

`protocol_succeeded`, `executor_succeeded`, `effect_succeeded` y
`business_succeeded` son predicados distintos.

## Expresiones prohibidas sin predicado

No usar aisladamente: `secure runtime`, `trusted agent`, `verified execution`,
`successful run`, `cancelled`, `exactly once`, `compliant`, `proof of
execution`. Deben indicar propiedad, sujeto, perfil, autoridad, tiempo y límite.
