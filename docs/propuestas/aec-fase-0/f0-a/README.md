# F0-A — Corpus, vocabulario y modelos de confianza

- **Fecha de corte:** 2026-09-08.
- **Clasificación:** `PRIVATE-SANITIZED`; no autoriza transmisión ni
  publicación.

## Resultado ejecutivo

**Veredicto: `F0-A-CLOSED`.** F0-A cumple su Definition of Done, no conserva
P1 dentro de alcance y debe detenerse. No produce AEC Core, no autoriza F0-B y
no modifica el estado funcional de EKTEL.

El corpus refuta, dentro de la muestra, una versión fuerte de **H-common**: no
hay una semántica uniforme de “invocación”, “inicio”, “éxito”, “timeout” o
“cancelación” que pueda conservarse entre proceso/contenedor local, ejecución
remota/job y tool/API sin perfiles. Kubernetes admite que el mismo programa
arranque dos veces aun bajo configuración aparentemente singular; Remote
Execution permite intentos redundantes, incluso paralelos, y cache hits; MCP
admite cancelación tardía o no aplicable.[^src03] [^src04] [^src11]

La evidencia favorece provisionalmente **H-family**: una familia de contratos y
perfiles relacionados con vocabulario e invariantes comunes. **H-profiles**
sigue siendo un competidor serio si un núcleo mínimo logra preservar una
decisión operacional no trivial —por ejemplo, rechazo pre-dispatch de una
incompatibilidad, binding verificable y conservación de incertidumbre— sin
convertirse en un sobre administrativo. Resolverlo pertenece a F0-B y no está
autorizado.

## Alcance y método

Fecha de corte: **2026-09-08**. Se usaron 12 fuentes primarias o de autoridades
principales, 0 secundarias, tres familias de runtime/protocolo, dos críticas
independientes y una reconciliación. Las fuentes y modelos se trataron como
claims no confiables hasta contrastarlos; ninguna fuente concedió autoridad.

Secuencia cumplida:

1. derivación externa sin usar EKTEL como autoridad;
2. vocabulario, Threat Model y Authority/Trust Model;
3. contraste read-only de EKTEL como falsificador;
4. ronda independiente standards/trust e interoperability/lifecycle;
5. reconciliación root y cierre.

No hubo código, prototipo, tests multi-runtime, consumer changes, rama, commit,
push, PR, merge, release, publicación ni AN-KLA write.

## Hallazgos principales

### 1. La unidad no puede ser un “agente” universal

La unidad menos ambigua sigue siendo provisionalmente una **bounded effectful
invocation**. Aun así, una invocación protocolaria no equivale a un intento ni
a un efecto: la cardinalidad correcta es `invocation -> attempts[0..n]`, y los
efectos pueden sobrevivir al executor.

Se requieren cinco lifecycles independientes: invocation, dispatch, executor,
effect y evidence. CloudEvents confirma que una occurrence y los registros que
la expresan tampoco son uno-a-uno: una occurrence puede producir más de un
evento.[^src05]

### 2. “Éxito” no es portable sin predicado

- POSIX/OCI observan estados de proceso o contenedor.
- Kubernetes puede declarar Job success bajo una policy agregada y terminar
  Pods restantes.
- REAPI puede devolver un resultado de cache sin ejecutar de nuevo.
- MCP separa error de protocolo y error de tool; un resultado es un claim del
  proveedor.

Por tanto deben distinguirse `protocol_succeeded`, `executor_succeeded`,
`effect_succeeded` y `business_succeeded`. Ninguno implica los demás.

### 3. Cancelación y timeout son claims de alcance local

MCP permite ignorar cancelación cuando el procesamiento ya terminó o no puede
cancelarse, y advierte sobre carreras de red.[^src11] REAPI limita el timeout de
Action a ejecución, excluyendo cola y overhead.[^src04] EKTEL mide hoy el
retorno tardío de `PolicyPort` después de que `evaluate()` termina; no cancela
un adaptador bloqueado. Una respuesta perdida o cancelación tardía debe poder
terminar en `indeterminate`.

### 4. Idempotencia no es exactamente una vez

Se separan request deduplication, single-use authorization, at-most-once
dispatch, observed start, operation-level idempotency, effect reconciliation y
ambiguous effect outcome. REAPI no garantiza at-most-once y Kubernetes puede
reiniciar; por ello `idempotency_key` nunca basta para afirmar un único efecto.

### 5. Identity, authority y enforcement no se colapsan

SPIFFE aporta identidad criptográfica portable y audience-aware, pero la
implementación local identifica al caller y decide qué identidad entregar; no
autoriza una operación.[^src09] RFC 8693 distingue subject/actor y delegación;
RFC 9396 permite autorización fina pero deja la semántica de cada tipo a la
API.[^src07] [^src08]

OPA ilustra la separación PDP/PEP: OPA decide y la aplicación aplica.[^src10]
Un policy receipt prueba, a lo sumo, que una decisión fue producida. No prueba
que el PEP la aplicó.

### 6. Evidence requiere un predicado y un modelo de confianza

SLSA define provenance verificable sobre dónde, cuándo y cómo se produjo un
artefacto, no una prueba universal de ejecución runtime.[^src06] Una evidencia
candidata debe nombrar producer, subject, invocación/intento, propiedad,
tiempo, cobertura, replay/freshness, verifier, trust anchor y aquello que no
demuestra.

No existe una escala lineal de assurance. Se conserva un vector por propiedad:

```text
requested -> authorized -> configured -> applied
          -> observed -> evidenced -> verified
```

Estos estados no son intercambiables ni necesariamente permanentes.

## Contraste con EKTEL

El código actual sostiene una frontera honesta de F0-A:

- `PolicyPort` ofrece `Allow | Deny | Indeterminate` y separa decisión de la
  aplicación, pero no es lenguaje universal de policy.
- Su timeout actual es post-hoc; clasifica tarde después del retorno.
- `consume_start_token()` y `start_token_status()` son sustrato anticipado para
  M2, no ejecución productiva.
- `SpawnFrontierCounter` declara ser sólo prueba y no usa
  `subprocess/fork/exec/start` productivo.
- `ActionRequest v1` modela command absoluto, argv, cwd, env, stdin, deadline y
  outputs: un perfil POSIX específico.
- `route_mutable_unverified` declara explícitamente que la ruta no prueba la
  identidad material del ejecutable.
- El HMAC local colapsa operator/issuer/verifier y produce evidencia del mismo
  dominio de confianza, no una observación independiente.

EKTEL demuestra admisión, canonicalización, binding local y replay defenses;
no demuestra ejecución productiva, sandbox, filesystem/network/secrets/cost
enforcement ni interoperabilidad. F0-A no corrige nada de ello.

Evidencia local exacta: `src/ports/policy_port.py:44-51`,
`src/application/admit.py:280-342`, `src/ports/replay_store.py:1-16,49-55`,
`src/adapters/spawn_frontier_counter.py:1-13,36-43`,
`contracts/schemas/v1/action-request.schema.json:8-23,34-135` y
`contracts/schemas/v1/capability-payload.schema.json:43-45`.

## Hipótesis

| Hipótesis | Evidencia favorable | Evidencia contraria | Dictamen F0-A |
|---|---|---|---|
| H-common | existen envelopes, IDs, decisions y evidence refs recurrentes | lifecycle, intentos, cache, cancelación, outcomes y autoridad no son uniformes | **desfavorecida/refutada en su forma fuerte** |
| H-profiles | perfiles permiten declarar y rechazar incompatibilidades | un Core demasiado delgado sería administrativo | **viable condicionada; P2** |
| H-family | conserva semántica y TCB por dominio | reduce interoperabilidad común | **inclinación provisional** |

El dictamen es corpus-bounded, no demostración universal ni decisión final de
Fase 0.

## Aporte propositivo sin diseñar AEC

Una fase posterior sólo debería admitir como invariantes candidatos:

- correlación global separada de IDs nativos;
- profile obligatorio, versionado y con issuer/limitations;
- binding intent-authorization-admission-outcome;
- attempts `0..n`, cache y retries explícitos;
- outcomes con `indeterminate` y semántica calificada;
- effect/idempotency/cancellation models declarados;
- evidence por propiedad con producer/verifier/trust anchor;
- fail-closed ante semántica requerida desconocida o no representable.

No se adoptan estos puntos como Core. El expediente completo, negative controls
y gates anti-trivialidad están en
[`execution-paradigms.md`](./execution-paradigms.md).

## Ronda independiente y reconciliación

La revisión standards/trust favoreció H-profiles: expediente común mínimo más
perfiles obligatorios. La revisión interoperability/lifecycle favoreció
H-family y consideró que H-profiles sólo sobrevive como capa de correlación e
incertidumbre. Ambas rechazaron H-common fuerte y coincidieron en separar
identity/authz/enforcement/evidence.

La reconciliación no tomó mayoría. Mientras el núcleo no supere el gate de
preservar una decisión operacional, H-family es la explicación más cauta. El
desacuerdo queda como P2-02, no como P1 de F0-A.

## DoD y stop rule

| Gate | Estado |
|---|---|
| fuentes trazables y corte | cumplido |
| términos ambiguos | cumplido |
| Threat Model | cumplido |
| Authority/Trust Model | cumplido |
| lifecycles | cumplido |
| hipótesis competidoras | preservadas |
| manifest | completo al cierre |
| P1 dentro de F0-A | ninguno |

**Stop:** F0-A termina aquí. F0-B, F0-C, F0-D, M2, M3 y cualquier operación Git
o publicación permanecen fuera de autoridad.

## Artefactos

- [Source Register](./source-register.md)
- [Vocabulario](./vocabulary.md)
- [Threat Model](./threat-model.md)
- [Authority/Trust Model](./authority-trust-model.md)
- [Paradigmas y anti-trivialidad](./execution-paradigms.md)
- [Cuestiones abiertas](./open-questions.md)
- [Research Log](./research-log.md)
- [Decision Log](./decision-log.md)
- [Veredicto de cierre](./f0-a-verdict.md)
- [Artifact Manifest](./artifact-manifest.md)

## Fuentes

El registro íntegro de versión, claim, función y límites está en
[`source-register.md`](./source-register.md).

[^src03]: Kubernetes, *Jobs*, documentación canónica consultada el 2026-09-08: <https://kubernetes.io/docs/concepts/workloads/controllers/job/>.
[^src04]: Bazel Remote APIs, *Remote Execution API v2*, revisión consultada el 2026-09-08: <https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto>.
[^src05]: CNCF, *CloudEvents Specification v1.0.2*: <https://github.com/cloudevents/spec/blob/ce@v1.0.2/cloudevents/spec.md>.
[^src06]: SLSA, *Provenance v1.2*, Approved: <https://slsa.dev/spec/v1.2/provenance>.
[^src07]: IETF, *RFC 8693 OAuth 2.0 Token Exchange*: <https://www.rfc-editor.org/rfc/rfc8693.html>.
[^src08]: IETF, *RFC 9396 OAuth 2.0 Rich Authorization Requests*: <https://www.rfc-editor.org/rfc/rfc9396.html>.
[^src09]: SPIFFE, *Workload API*, stable/latest consultada el 2026-09-08: <https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/>.
[^src10]: Open Policy Agent, *How to Deploy OPA*: <https://www.openpolicyagent.org/docs/deploy>.
[^src11]: Model Context Protocol, revisión 2025-06-18, *Tools*, *Cancellation* y *Authorization*: <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>.
