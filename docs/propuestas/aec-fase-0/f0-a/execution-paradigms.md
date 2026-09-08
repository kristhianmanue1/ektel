# F0-A — Clasificación preliminar de paradigmas

- **Estado:** cierre F0-A; análisis superficial de tres familias.
- **Clasificación:** `PUBLISHABLE` como candidato; no autoriza publicación.
- **Límite:** no es el stress test F0-C ni define perfiles normativos.

## Familias examinadas

| Dimensión | Local process/container | Remote execution/job | Remote tool/API |
|---|---|---|---|
| Casos | POSIX, OCI, EKTEL como falsificador | REAPI, Kubernetes Job | MCP tool call |
| Identidad nativa | PID/OCI ID/handle local | operation name, UID, action digest | request ID + tool name/server |
| Dispatch | llamada local/spawn/create | submit/queue/admission del control plane | request transportada al servidor |
| Intentos | usualmente caller/runtime local | cero a múltiples; duplicación y caché nativas | implementación del servidor, a menudo opaca |
| Inicio observable | process/container running | worker/Pod/attempt; no igual a operation | procesamiento del request; no prueba efecto |
| Éxito técnico | wait/exit o estado runtime | resultado RE o política agregada del Job | result/isError según proveedor |
| Timeout | proceso o supervisor local | puede excluir cola/overhead | cliente/servidor, transport-specific |
| Cancelación | señal/best effort y carreras | controller/API; intentos pueden sobrevivir | notificación opcional, puede llegar tarde |
| Efectos | fuera del exit status | fuera de Job/ActionResult salvo perfil | fuera del result salvo semántica del tool |
| Evidencia típica | wait status/log local | API state, CAS, logs, scheduler | server result/log/receipt |
| TCB dominante | OS, runtime, supervisor, operador | control plane, scheduler, workers, CAS, identity | host, transport, auth server, tool server, API externa |

## Pérdidas semánticas que no deben ocultarse

1. Un `exit 0`, un Job `Complete`, un RE cache hit y `isError=false` no son el
   mismo predicado.
2. El mismo program puede iniciar más de una vez en un Job; REAPI permite
   intentos redundantes paralelos; un wrapper no puede reportarlos como una
   ejecución única.
3. Un cache hit produce un resultado válido para REAPI sin ejecutar ahora.
4. Cancelar puede significar señal enviada, operación marcada, notificación
   recibida o procesamiento detenido. Ninguno prueba ausencia/reversión de
   efectos.
5. IDs nativos tienen alcance distinto y no deben convertirse sin más en una
   identidad global durable.
6. Un deadline local y el timeout de una Action remota pueden cubrir intervalos
   diferentes.

## Núcleo preliminar que podría sobrevivir

F0-A no lo adopta como AEC Core. Sólo registra invariantes candidatos para
falsación posterior:

- correlación global separada de IDs nativos;
- profile obligatorio, versionado y con semántica resoluble;
- referencias/digests de intent y authorization, con audience/expiry;
- multiplicidad de attempts de primera clase;
- outcomes que preserven `indeterminate`, cache y cancelación parcial;
- declaración explícita de retry, idempotency, cancellation/effect model;
- evidencia con autoridad, tiempo, cobertura, verifier y trust anchor;
- rechazo pre-dispatch de una incompatibilidad material conocida;
- semántica no representable declarada, nunca convertida en downgrade.

No deben entrar al núcleo común: `argv`, filesystem, env, exit code, Pod,
container, HTTP, tool annotations, CAS, scheduler, signals ni side-effect model
específico.

## Evaluación anti-trivialidad preliminar

| Gate del mandato | ¿Puede un sobre mínimo aportar valor? | Estado F0-A |
|---|---|---|
| rechazo pre-dispatch | sí, si profile/requirements tienen semántica normativa | plausible, no demostrado |
| binding request-auth-dispatch-outcome | sí mediante referencias autenticadas | plausible, no diseñado |
| outcomes sin colapsar efecto/negocio | sí mediante predicados calificados | respaldado conceptualmente |
| requested..verified separados | sí; OPA/SPIFFE/SLSA muestran separaciones | respaldado conceptualmente |
| evidencia correlacionada | sí mediante sujeto/invocation/property | plausible, no demostrado |
| decisión portable relevante | quizá rechazo de incompatibilidad y preservación de incertidumbre | P2 abierto |
| no representable sin downgrade | sí como regla fail-closed | plausible, no probado |

El núcleo no supera aún el criterio anti-trivialidad: ese diseño y comparación
corresponden a F0-B. F0-A sí demuestra que un Core fuerte y semánticamente
uniforme es incompatible con el corpus.

## Controles negativos para una fase autorizada posterior

1. RE cache hit versus `/bin/true`: ambos “éxito”, uno puede no ejecutar ahora.
2. Job con `successPolicy` parcial versus proceso `exit 0`.
3. pérdida de respuesta + retry cuando el primer efecto pudo ocurrir.
4. cancelación MCP tardía después de comprometer un efecto.
5. Job que reintenta una escritura externa no idempotente.
6. dos ejecutores envueltos por un único `sh`/proxy: uniformidad de fachada, no
   interoperabilidad.

Estos casos se registran como backlog; no se ejecutaron en F0-A.
