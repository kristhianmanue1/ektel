# F0-A — Source Register

- **Estado:** cierre F0-A.
- **Fecha de corte:** 2026-09-08.
- **Clasificación:** `PUBLISHABLE` como candidato; no autoriza publicación.
- **Método:** corpus deliberadamente acotado a 12 fuentes primarias o de
  autoridades principales y 0 secundarias. La inclusión indica relevancia, no
  adopción ni autoridad sobre EKTEL.

## Registro

### SRC-01 — POSIX `waitpid()`

- **Título/productor:** *The Open Group Base Specifications Issue 8,
  `waitpid()`*; The Open Group / IEEE.
- **URL:** <https://pubs.opengroup.org/onlinepubs/9799919799/functions/waitpid.html>
- **Versión/fecha:** POSIX.1-2024, Issue 8, 2024.
- **Consulta:** 2026-09-08.
- **Tipo:** standard.
- **Claim:** un padre puede observar terminación y estado de un proceso hijo;
  esa observación local no prueba efectos externos ni identidad global.
- **Función:** soporte para separar executor lifecycle de effect lifecycle.
- **Límite:** no cubre entrega remota, reintentos, autorización ni evidencia
  distribuida.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-02 — OCI Runtime Specification

- **Título/productor:** *Open Container Initiative Runtime Specification*;
  OCI.
- **URL:** <https://specs.opencontainers.org/runtime-spec/runtime/?v=v1.3.0>
- **Versión/fecha:** v1.3.0, noviembre de 2025.
- **Consulta:** 2026-09-08.
- **Tipo:** standard.
- **Claim:** define un ciclo local de contenedor
  `creating/created/running/stopped`; el ID es de alcance host y no constituye
  una identidad global de invocación.
- **Función:** soporte y control negativo frente a un lifecycle universal.
- **Límite:** no es scheduler, contrato de autorización ni prueba de efectos.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-03 — Kubernetes Jobs

- **Título/productor:** *Jobs*; Kubernetes SIG Apps.
- **URL:** <https://kubernetes.io/docs/concepts/workloads/controllers/job/>
- **Versión/fecha:** documentación canónica consultada el 2026-09-08; las
  condiciones terminales citadas se documentan para v1.31+.
- **Consulta:** 2026-09-08.
- **Tipo:** implementation/API documentation.
- **Claim:** aun con paralelismo y completions igual a uno y sin restart del
  contenedor, un programa puede iniciar dos veces; `successPolicy` puede
  declarar éxito con un subconjunto de Pods exitosos.
- **Función:** contradicción de `one request = one attempt` y de un `success`
  global.
- **Límite:** depende de versión, feature gates y configuración del clúster.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-04 — Remote Execution API v2

- **Título/productor:** *Remote Execution API v2*; Bazel
  `remote-apis`.
- **URL:** <https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto>
- **Versión/fecha:** API v2, revisión `main` observada el 2026-09-08.
- **Consulta:** 2026-09-08.
- **Tipo:** protocol specification.
- **Claim:** `Execute` no garantiza a lo sumo una ejecución; el servidor puede
  ejecutar en paralelo intentos redundantes que sobrevivan al cierre de la
  operación. Un resultado también puede provenir de caché. El timeout de
  `Action` excluye cola y overhead.
- **Función:** contradicción de exactly-once y soporte para capabilities,
  perfiles, caché e intentos separados.
- **Límite:** orientado a builds/tests reproducibles y CAS, no a efectos
  externos arbitrarios.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-05 — CloudEvents

- **Título/productor:** *CloudEvents Specification*; CNCF.
- **URL:** <https://github.com/cloudevents/spec/blob/ce@v1.0.2/cloudevents/spec.md>
- **Versión/fecha:** v1.0.2.
- **Consulta:** 2026-09-08.
- **Tipo:** standard/specification.
- **Claim:** un evento es un registro que expresa una ocurrencia y su contexto;
  una misma ocurrencia puede producir más de un evento.
- **Función:** soporte para separar occurrence, producer, observation y
  evidence envelope.
- **Límite:** no garantiza entrega, orden, unicidad causal ni veracidad de la
  ocurrencia.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-06 — SLSA Provenance

- **Título/productor:** *SLSA Provenance*; SLSA / Linux Foundation.
- **URL:** <https://slsa.dev/spec/v1.2/provenance>
- **Versión/fecha:** v1.2, estado Approved.
- **Consulta:** 2026-09-08.
- **Tipo:** specification.
- **Claim:** provenance es información verificable sobre dónde, cuándo y cómo
  se produjo un artefacto; su interpretación depende del track y del builder
  reconocido.
- **Función:** soporte para provenance y para distinguir claim firmado de hecho
  material.
- **Límite:** se especializa en supply chain; no prueba unicidad ni efectos de
  una ejecución runtime genérica.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-07 — OAuth 2.0 Token Exchange

- **Título/productor:** *RFC 8693: OAuth 2.0 Token Exchange*; IETF.
- **URL:** <https://www.rfc-editor.org/rfc/rfc8693.html>
- **Versión/fecha:** RFC 8693, enero de 2020.
- **Consulta:** 2026-09-08.
- **Tipo:** Internet Standards Track RFC.
- **Claim:** permite intercambiar tokens con `resource`, `audience`, `scope`,
  sujeto y actor; el modelo de confianza concreto y la semántica del token
  siguen siendo propios del despliegue.
- **Función:** soporte para delegación restringida y separación subject/actor.
- **Límite:** intercambiar credenciales no define autorización de ejecución ni
  prueba enforcement.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-08 — OAuth 2.0 Rich Authorization Requests

- **Título/productor:** *RFC 9396: OAuth 2.0 Rich Authorization Requests*;
  IETF.
- **URL:** <https://www.rfc-editor.org/rfc/rfc9396.html>
- **Versión/fecha:** RFC 9396, mayo de 2023.
- **Consulta:** 2026-09-08.
- **Tipo:** Internet Standards Track RFC.
- **Claim:** `authorization_details` expresa autorización fina por tipos; un AS
  debe rechazar tipos/campos desconocidos, pero la semántica y comparación de
  detalles son específicas de la API.
- **Función:** soporte para fail-closed y perfiles de autorización.
- **Límite:** no crea una semántica portable de “ejecutar”.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-09 — SPIFFE Workload API

- **Título/productor:** *SPIFFE Workload API*; SPIFFE Project.
- **URL:** <https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/>
- **Versión/fecha:** estándar estable, versión `latest` observada el
  2026-09-08.
- **Consulta:** 2026-09-08.
- **Tipo:** standard.
- **Claim:** ofrece identidades criptográficas portables mediante perfiles y
  trust bundles; la implementación local identifica al caller fuera de banda y
  decide qué identidad entregar.
- **Función:** soporte para identidad de workload, audience y trust domains.
- **Límite:** identidad autenticada no equivale a autorización ni a integridad
  de ejecución.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-10 — Open Policy Agent deployment architecture

- **Título/productor:** *How to Deploy OPA*; Open Policy Agent / CNCF.
- **URL:** <https://www.openpolicyagent.org/docs/deploy>
- **Versión/fecha:** documentación viva consultada el 2026-09-08.
- **Consulta:** 2026-09-08.
- **Tipo:** implementation architecture/guidance.
- **Claim:** OPA es PDP; la aplicación es PEP. La decisión puede ser local o
  remota, con distintas propiedades de latencia y disponibilidad.
- **Función:** soporte para separar decisión de enforcement.
- **Límite:** documentación de una implementación; no demuestra que un PEP
  aplicó una decisión.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-11 — Model Context Protocol 2025-06-18

- **Título/productor:** *MCP Tools, Cancellation and Authorization*; Model
  Context Protocol.
- **URLs:** <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>,
  <https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation>,
  <https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization>.
- **Versión/fecha:** revisión 2025-06-18.
- **Consulta:** 2026-09-08.
- **Tipo:** protocol specification; las tres páginas son secciones de una misma
  revisión normativa y se cuentan como una fuente versionada.
- **Claim:** una tool call separa errores de protocolo y de herramienta;
  annotations son no confiables salvo servidor confiable; cancelar es opcional,
  puede ignorarse o llegar después de completarse el procesamiento.
- **Función:** contradicción de `cancel requested = effect prevented` y soporte
  para perfil de tool invocation.
- **Límite:** no define idempotencia universal, transacción de efectos ni
  veracidad material del resultado del proveedor.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

### SRC-12 — OWASP Agentic AI Threats and Mitigations

- **Título/productor:** *Agentic AI — Threats and Mitigations*; OWASP GenAI
  Security Project.
- **URL:** <https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/>
- **Versión/fecha:** publicado el 2025-02-17.
- **Consulta:** 2026-09-08.
- **Tipo:** security guidance/threat modeling.
- **Claim:** agentic systems amplify threats por autonomía, herramientas,
  memoria y cadenas de acciones; requieren controles en límites de autoridad,
  inputs/outputs y observabilidad.
- **Función:** contexto y checklist adversarial del Threat Model.
- **Límite:** guidance, no estándar; categorías amplias no prueban un riesgo ni
  un control concreto en EKTEL.
- **Disponibilidad:** pública; consultada.
- **Artefacto:** `EXTERNAL-REFERENCE`.

## Fuentes evaluadas pero no incorporadas

- **NIST AI Agent Standards Initiative, actualización 2026-08-14:** confirma
  que identidad, autorización, seguridad e interoperabilidad están aún en fase
  de iniciativa, gap analysis y protocolos emergentes. Se dejó en backlog para
  no exceder 12 fuentes y porque no aporta semántica contractual normativa.
- **NIST draft concept paper sobre agent identity/authorization:** útil para una
  fase posterior de perfiles de identidad, pero es draft y se solapa con RFC
  8693/9396 y SPIFFE.
- **W3C Verifiable Credentials:** aporta representación de credenciales, no
  cierra intentos, cancelación, outcome o causalidad de efectos.
- **MCP release candidate 2026-07-28:** sus Tasks y cambios de autorización son
  material de seguimiento; no sustituyó en este corpus a una revisión normativa
  publicada y estable.

Estas referencias son backlog, no corpus y no se usaron para decidir F0-A.
