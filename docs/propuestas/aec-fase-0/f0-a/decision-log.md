# F0-A — Decision Log

- **Estado:** cerrado para F0-A.
- **Clasificación:** `PRIVATE-SANITIZED`.

| ID | Decisión de investigación | Evidencia/razón | Consecuencia |
|---|---|---|---|
| DL-01 | Usar tres hipótesis competidoras | el mandato prohíbe una H0 universal | no se fuerza una conclusión binaria |
| DL-02 | Limitar corpus a 12 primarias/principales y 0 secundarias | presupuesto y trazabilidad | referencias adicionales pasan a backlog |
| DL-03 | Examinar tres familias semánticamente distantes | local, scheduler remoto y tool/API cubren contrastes fuertes | no se amplía a workflows/agentes recursivos |
| DL-04 | `invocation -> attempts` es `0..n` | Kubernetes y REAPI contradicen unicidad | multiplicidad es de primera clase |
| DL-05 | Separar cinco lifecycles | cancelación, cache, reintento y efectos sobreviven fronteras | no existe un `status` total único |
| DL-06 | Rechazar `success` universal | exit, Job Complete, cache hit y tool result difieren | outcomes deben calificarse por perfil/predicado |
| DL-07 | Conservar `indeterminate` | pérdida de respuesta/cancelación tardía no prueba ausencia de efecto | prohibido convertir duda en failure/success |
| DL-08 | Separar PDP de PEP | OPA y EKTEL ilustran decisión versus aplicación | policy receipt no prueba enforcement |
| DL-09 | Tratar identity/authn/authz/capability como conceptos distintos | OAuth, SPIFFE y autoridad local tienen alcances distintos | no se infiere permiso por identidad |
| DL-10 | Evidencia necesita producer, verifier y trust anchor | SLSA/CloudEvents sólo cubren claims/contextos acotados | firma no equivale a verdad material |
| DL-11 | H-common fuerte queda desfavorecida | contradicciones de lifecycle y outcome en las tres familias | no diseñar contrato monolítico uniforme |
| DL-12 | No resolver aún H-profiles vs H-family | dos críticas independientes divergen y anti-trivialidad es F0-B | P2-02 explícito; inclinación provisional a H-family |
| DL-13 | Cerrar F0-A con `F0-A-CLOSED` | todos los entregables existen y no hay P1 | detenerse; ninguna fase posterior autorizada |

## Reconciliación de la ronda independiente

Ambas críticas coinciden en:

- no existe evidencia de un estándar actual que integre toda la premisa;
- un contrato uniforme fuerte pierde semántica de intentos, cache, cancelación,
  resultado, autoridad o evidencia;
- identidad no equivale a autorización y PDP no equivale a enforcement;
- cualquier continuidad requiere perfiles explícitos y fail-closed ante
  semántica no representable.

Difieren en el rótulo preferido:

- la crítica de standards/trust prefiere **H-profiles**, entendida como
  expediente común mínimo + perfiles obligatorios;
- la crítica de interoperability/lifecycle considera **H-family** más honesta y
  sólo admite H-profiles si el Core se reduce a correlación e incertidumbre.

La reconciliación no cuenta votos. Bajo el gate anti-trivialidad, un sobre que
sólo correlaciona aún no justifica un Core. Por ello F0-A registra
**H-family como inclinación provisional**, mantiene **H-profiles como competidor
serio** y rechaza únicamente **H-common fuerte** dentro del corpus. Resolver la
disputa exigiría F0-B, que no está autorizada.
