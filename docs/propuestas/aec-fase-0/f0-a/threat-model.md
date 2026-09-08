# F0-A — Threat Model

- **Estado:** completo para el alcance epistemológico de F0-A.
- **Clasificación:** `PUBLISHABLE` como candidato; no autoriza publicación.
- **Objeto:** una futura bounded effectful invocation entre caller y runtime.
  No evalúa una implementación AEC inexistente.

## Assets

1. Integridad y procedencia de intent/request.
2. Autoridad y límites del grant.
3. Integridad del binding entre request, autorización, admission e intentos.
4. Frontera de ejecución y restricciones aplicadas.
5. Secretos, handles bearer y datos sensibles.
6. Integridad, disponibilidad y confidencialidad de resultados/evidencia.
7. Capacidad de reconstruir ambigüedad, duplicación y causalidad sin inventar
   certeza.
8. Presupuestos de recursos y efectos externos no reversibles.

## Actores y autoridades

- principal/resource owner; caller; authorization issuer; PDP; runtime
  operator; PEP; credential provider; scheduler/executor; evidence producer;
  verifier; trust anchor; operador de data/evidence plane.
- Los roles pueden colapsarse, pero esa composición debe declararse. El colapso
  reduce independencia y no convierte un receipt propio en observación de
  tercero.

## Trust roots y boundaries

| Boundary | Activo cruzado | Supuesto mínimo | Fallo relevante |
|---|---|---|---|
| principal -> caller | intención/consentimiento | caller representa al principal dentro de alcance | confused deputy o autoridad inventada |
| caller -> authorization issuer/PDP | solicitud y contexto | autenticación, audience y replay válidos | grant excesivo, swapping, stale policy |
| caller -> runtime admission | request, profile y grant | canonicalización y binding verificables | TOCTOU, downgrade, perfil falso |
| admission/PDP -> PEP | decisión | PEP interpreta y aplica la misma versión | allow sin enforcement |
| control -> data/sensitive plane | referencias | mínimo privilegio, expiry, no logging material | exfiltración o delegación accidental |
| scheduler -> executor | intento | identidad y configuración observables | worker sustituto o drift |
| executor -> effect target | operación | semántica del perfil y reconciliación | efecto duplicado/huérfano |
| runtime -> evidence plane | eventos/resultados | producer y cobertura explícitos | evidencia fabricada, incompleta o stale |
| verifier -> consumer | veredicto | trust anchors y algoritmo identificados | “verified” sin predicado/raíz |

## Capacidades del atacante

Se supone que un atacante puede:

- enviar, repetir, reordenar, retrasar o truncar requests y respuestas;
- manipular campos no ligados criptográficamente y explotar diferencias de
  canonicalización;
- controlar un caller, tool server, worker o plugin no confiable;
- inducir timeouts, particiones, crashes y pérdida de acknowledgements;
- provocar reintentos concurrentes, cache hits o resultados tardíos;
- presentar capability/profile/evidence stale o emitido para otra audiencia;
- intentar inyección mediante argumentos, metadata, tool descriptions,
  resultados y referencias;
- leer logs o stores mal minimizados;
- abusar de recursos hasta límites permitidos.

No se supone que pueda romper primitivas criptográficas correctas ni comprometer
simultáneamente todos los trust anchors; si controla un componente del TCB, los
predicados que dependen de él dejan de sostenerse y eso debe ser visible.

## Supuestos explícitos

- Los relojes pueden divergir; la vigencia necesita tolerancia y semántica de
  frescura.
- Redes y procesos pueden fallar por omisión; pérdida de respuesta no equivale
  a no ejecución.
- Un runtime honesto puede tener semánticas de reintento/caché incompatibles
  con otro.
- Identidad, autorización, enforcement, observación y verificación son actos
  separados.
- Criptografía autentica una declaración bajo claves aceptadas; no prueba su
  verdad material.
- Ninguna idempotency key ofrece exactly-once de efectos por sí sola.

## Amenazas y tratamiento conceptual

| ID | Amenaza | Consecuencia no tolerable | Control o requisito investigable | Residuo que debe declararse |
|---|---|---|---|---|
| T01 | request tampering/swapping | ejecutar otra intención | digest/canonicalización y binding grant-request | semántica del input sigue siendo de perfil |
| T02 | replay de request/grant | efectos repetidos | nonce/single-use/dedup con dominio y ventana | crash tras consumo deja outcome ambiguo |
| T03 | confused deputy/delegación excesiva | usar autoridad del runtime fuera de intención | subject/actor, audience, resource, expiry y no-delegation | autoridad local interpreta el perfil |
| T04 | capability/profile spoofing | aceptar garantías inexistentes | issuer autenticado, versión/digest, vigencia | autenticidad no prueba enforcement |
| T05 | discovery-dispatch drift | ejecutar bajo configuración distinta | binding profile -> admission -> outcome y revalidación | drift dentro del intento puede quedar no observable |
| T06 | PDP/PEP gap | policy allow registrado pero no aplicado | receipt de decisión separado de evidencia del PEP | PEP y producer colapsados reducen independencia |
| T07 | downgrade silencioso | perder límites requeridos | rechazo fail-closed de propiedades desconocidas/no representables | compatibilidad requiere semántica de perfil |
| T08 | duplicación por retry/scheduler | efectos no idempotentes múltiples | cardinalidad de attempts, retry/effect model, reconciliation | no prometer exactly-once |
| T09 | cache confundida con ejecución nueva | claim falso de “se ejecutó” | outcome distingue cache hit/attempt | cache puede ser correcta sólo bajo perfil reproducible |
| T10 | timeout/cancel race | declarar que no ocurrió un efecto | `indeterminate`, cancel requested/observed separados | efectos pueden sobrevivir al executor |
| T11 | executor/worker sustituto | TCB o aislamiento distinto | identidad/configuración de instancia e intent evidence | identidad de workload no prueba configuración |
| T12 | evidence forgery/equivocation | auditoría falsa | producer, subject, signature, sequence, coverage | producer comprometido puede mentir |
| T13 | stale/replayed evidence | aceptar estado anterior | issued/observed time, expiry, nonce/sequence | frescura no prueba causalidad |
| T14 | telemetry confundida con proof | garantía inflada | taxonomía y `demonstrates/does_not_demonstrate` | observabilidad puede ser parcial |
| T15 | secret/handle leakage | autoridad reutilizable expuesta | referencias scoped, audience, expiry, redacción | bearer handles siguen siendo sensibles |
| T16 | prompt/tool-output injection | control plane contaminado | tratar contenido como dato no confiable, schemas/allowlists | validación sintáctica no prueba intención segura |
| T17 | resource/cost exhaustion | impacto operativo o financiero | budget profile y enforcement local | no hay garantía común sin medidor/PEP |
| T18 | identity conflated with authority | acción no autorizada | separar authn, authz y PEP; least privilege | roles colapsados deben declararse |
| T19 | lifecycle collapse | resultado erróneo o pérdida de huérfanos | cinco lifecycles y causal links explícitos | reconciliación puede permanecer inconclusa |
| T20 | adapter laundering | wrapper oculta semántica/TCB | negative controls, loss matrix, profile limitations | un API uniforme puede seguir siendo trivial |

## Consecuencias

No tolerables: ejecución fuera de autoridad; secretos en evidencia/logs; downgrade
silencioso; convertir ambigüedad en éxito o fallo; afirmar enforcement sin PEP;
afirmar verificación sin verifier/trust anchor; ocultar múltiples intentos.

Tolerables sólo si son explícitas: indisponibilidad fail-closed, outcome
`indeterminate`, ausencia de garantía no requerida, evidencia parcial marcada,
cancelación best-effort de perfil.

## Fuera de alcance F0-A

- demostrar aislamiento de un sandbox;
- resistencia física/side channels y compromiso total del host;
- gobernanza legal de cada dominio de negocio;
- seleccionar criptografía, wire format o proveedor;
- implementar mitigaciones en EKTEL u otros consumidores;
- cuantificar probabilidad o impacto en una implementación aún inexistente.

Estos límites no eliminan amenazas: impiden presentarlas como resueltas.
