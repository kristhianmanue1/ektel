Mandato de investigación: Agent Execution Contract

Estado: pre-M2 de EKTEL
Naturaleza: investigación, diseño contractual y consenso adversarial
Regla principal: NO implementar M2 todavía.

1. Situación

EKTEL se encuentra deliberadamente detenido antes de M2.

La pausa no representa un bloqueo de implementación. Se ha identificado una decisión arquitectónica que debe resolverse antes de continuar: varios sistemas independientes pueden necesitar ejecutar agentes, herramientas, procesos, modelos o acciones antes de que exista un runtime común plenamente desarrollado.

Si cada sistema resuelve localmente esa necesidad, existe el riesgo de que aparezcan runtimes parciales e incompatibles embebidos en distintos proyectos.

El objetivo de este trabajo es evitarlo.

No se pretende diseñar un contrato privado de EKTEL.

Se pretende investigar y definir un contrato neutral de ejecución agéntica, provisionalmente denominado:

Agent Execution Contract, AEC.

La relación deseada es:

Componente solicitante
→ Agent Execution Contract
→ runtime conforme
→ mecanismos concretos de enforcement

EKTEL podrá convertirse posteriormente en una implementación de ese contrato, pero el contrato NO debe depender de EKTEL.

Otros runtimes, sandboxes, servicios remotos o implementaciones futuras deben poder satisfacerlo.

2. Estado arquitectónico previo de EKTEL

Preservar como baseline, no como conclusión obligatoria, las siguientes decisiones.

EKTEL fue concebido como un runtime pequeño, independiente y con arquitectura hexagonal.

M1 resolvió la admisión.

El diseño posterior contempla que EKTEL pueda admitir acciones, iniciar y supervisar procesos, producir resultados tipados y registrar transiciones observables.

Se persiguen propiedades como fail-closed, trazabilidad causal, contratos versionados y validación determinista.

Existe conceptualmente PolicyPort para mantener la gobernanza/política externa separada del mecanismo de ejecución.

Se estableció además una restricción deliberada:

M2 y M3 no deben crecer implícitamente hasta convertirse en un sistema completo de capability enforcement.

El primer ciclo de desarrollo termina en M3.

El aislamiento fuerte, sandboxing avanzado o ampliaciones sustanciales del Trusted Computing Base requieren decisión arquitectónica explícita.

Como posible evolución posterior se había considerado:

ticket
→ identidad/rol
→ PolicyPort
→ capability grant
→ sandbox/runtime
→ ejecución
→ evidencia

Esta cadena es una hipótesis arquitectónica, no una especificación que deba conservarse a toda costa.

3. Problema que debe resolverse

Otros componentes independientes pueden necesitar hoy pequeños mecanismos locales para ejecutar procesos, herramientas o agentes.

Esos mecanismos pueden ser necesarios temporalmente.

No deben evolucionar accidentalmente hasta convertirse en runtimes propietarios.

El AEC debe permitir distinguir entre:

un runtime conforme;

un execution adapter;

un execution shim provisional;

un harness experimental;

y lógica propia del dominio que simplemente solicita una ejecución.

Los mecanismos provisionales deben poder existir, pero deben declarar explícitamente sus limitaciones y resultar sustituibles posteriormente.

4. Regla de independencia

No diseñar:

“el contrato que necesita EKTEL”.

Diseñar:

“el contrato mínimo que debería existir entre un componente que solicita ejecución agéntica y cualquier runtime capaz de realizarla de forma gobernable, observable y segura”.

Después se comprobará si EKTEL puede implementarlo.

La dirección de dependencia debe ser:

EKTEL → AEC

y nunca:

AEC → EKTEL.

5. No contaminar inicialmente la investigación con el ecosistema existente

En la primera fase NO utilizar las implementaciones actuales de AN-KLA, SKEVI, Skopos, Ágora u otros proyectos como fuente normativa del contrato.

No inferir requisitos simplemente porque uno de esos sistemas ya los implementa de determinada manera.

No convertir accidentalmente las decisiones históricas del ecosistema en un supuesto “estándar”.

Primero obtener requisitos mediante evidencia externa, modelos de seguridad, runtimes existentes, estándares, literatura y análisis adversarial.

Posteriormente habrá una fase explícita de compatibility mapping contra los proyectos existentes.

Los proyectos actuales son consumidores potenciales y casos de prueba del contrato, no autoridades sobre su diseño.

6. Investigación externa obligatoria

Antes de proponer el contrato, investigar el estado actual de la industria.

Como mínimo examinar:

NIST y sus trabajos actuales relacionados con agentes, AI Risk Management y estándares de sistemas agénticos.

OWASP, incluyendo seguridad de agentes, excessive agency, tool security, least privilege, sandboxing, tool chaining, secretos y límites de recursos.

Patrones PDP/PEP: Policy Decision Point y Policy Enforcement Point.

Open Policy Agent como referencia madura de separación entre decisión de política y enforcement, sin asumir que OPA tenga que formar parte de la solución.

Capability-based security.

Principle of least privilege.

Deny-by-default y fail-closed.

Sandboxing y aislamiento de procesos.

Control de filesystem.

Network egress policy.

Tool authorization.

Gestión y exposición de secretos.

Identidad y delegación.

Resource governance.

Timeouts, retries, recursion y límites de coste.

Auditabilidad y provenance de ejecución.

Idempotencia y cancelación.

Resultados tipados.

Evidencia de ejecución.

Interoperabilidad entre runtime y caller.

Investigar además runtimes y sistemas agénticos existentes cuando aporten patrones relevantes.

Separar claramente:

estándar formal;

recomendación industrial;

patrón arquitectónico;

implementación existente;

y propuesta propia.

No presentar una práctica popular como estándar si no lo es.

7. Pregunta principal

Determinar:

¿Cuál es el contrato mínimo, neutral respecto al runtime, que permite a un componente solicitar una ejecución agéntica y obtener un resultado verificable sin necesitar conocer cómo el runtime implementa internamente aislamiento, procesos, herramientas o políticas?

8. Dimensiones candidatas del contrato

No asumir que esta enumeración es definitiva. Debe ser atacada durante las rondas adversariales.

Investigar si el contrato necesita representar al menos:

identidad del solicitante;

identidad o clase del ejecutor;

identificador de tarea;

operación solicitada;

inputs;

outputs esperados;

herramientas solicitadas;

operaciones permitidas por herramienta;

filesystem read scopes;

filesystem write scopes;

network policy;

network destinations;

process spawning;

subprocess policy;

environment;

secrets;

credenciales delegadas;

capabilities;

working directory;

resource limits;

wall-clock timeout;

CPU;

memoria;

almacenamiento;

tokens;

coste;

número de tool calls;

retry budget;

recursion/delegation budget;

human approval requirements;

cancellation;

idempotency;

expected side effects;

result schema;

error taxonomy;

execution identity;

runtime identity;

policy decision reference;

timestamps;

provenance;

evidence;

logs;

artefactos producidos;

integridad de artefactos;

y versión del contrato.

Preguntar adversarialmente cuáles pertenecen realmente al contrato y cuáles deben quedar fuera.

El objetivo NO es producir un manifiesto gigantesco.

El objetivo es encontrar el mínimo suficiente.

9. Separación fundamental de responsabilidades

Analizar explícitamente la separación entre:

Policy Decision Point, PDP

y

Policy Enforcement Point, PEP.

Un componente puede declarar:

“necesito esta capacidad”.

Una política puede decidir:

“esta capacidad está autorizada”.

El runtime debe hacer efectivo:

“el proceso sólo puede ejercer estas capacidades”.

No asumir que un LLM, prompt, archivo de configuración o declaración del propio agente constituye enforcement.

Las restricciones declarativas sin enforcement deben identificarse como tales.

10. Execution shims provisionales

Definir formalmente qué constituye un execution shim provisional.

Un shim puede permitir que un proyecto continúe desarrollándose mientras no exista todavía un runtime completo.

Pero debe:

tener superficie mínima;

ser sustituible;

no apropiarse del contrato;

declarar qué partes del AEC implementa;

declarar qué partes NO implementa;

no afirmar aislamiento que no proporciona;

no convertirse silenciosamente en autoridad de seguridad;

y permitir migración posterior hacia un runtime conforme.

Determinar si se necesita un nivel explícito de conformidad, por ejemplo:

declarativo;

observacional;

enforced;

isolated.

No adoptar esos nombres sin analizarlos primero.

11. Multi-runtime desde el diseño

El contrato debe permitir que existan varios runtimes.

Ejemplos conceptuales:

runtime local ligero;

runtime con sandbox;

runtime basado en contenedores;

runtime remoto;

runtime especializado para ejecución de código;

runtime especializado para herramientas;

runtime de alta seguridad.

No diseñar una abstracción que sólo pueda implementar EKTEL.

Tampoco diseñar para todos los escenarios imaginables si eso destruye la simplicidad.

12. Hipótesis falsables

Evaluar al menos:

H0-AEC:

“No existe suficiente invariancia entre runtimes agénticos para justificar un Agent Execution Contract común; cualquier contrato útil terminará acoplado a una implementación concreta.”

Intentar derrotarla.

Y posteriormente:

H0-EKTEL:

“El diseño actual de EKTEL M2 no puede implementar el Agent Execution Contract sin aumentar sustancialmente su Trusted Computing Base o violar sus fronteras arquitectónicas.”

No modificar EKTEL para hacer verdadera o falsa esta hipótesis.

Evaluarlo después de congelar el AEC candidato.

13. Proceso multiagente y multimodelo

El trabajo debe utilizar agentes/modelos con contexto suficientemente independiente.

Modelo coordinador/orquestador: GPT-5.6 Sol.

Revisores adversariales: utilizar las versiones actuales disponibles de Claude Opus y Qwen de mayor capacidad apropiada para razonamiento técnico.

Registrar versiones/model IDs realmente utilizados. No inventarlos previamente.

Los revisores deben recibir el problema y la evidencia necesaria, pero evitar heredar conclusiones de los demás antes de emitir su primera evaluación.

Primera ronda:

cada modelo produce independientemente:

requisitos mínimos;

amenazas;

omisiones;

riesgos de sobreingeniería;

estándares relevantes;

y propuesta de frontera.

Segunda ronda:

cada modelo recibe las propuestas anonimizadas o claramente atribuidas de los demás y debe intentar falsarlas.

Buscar especialmente:

capabilities ausentes;

privilegios implícitos;

confused deputy;

prompt injection;

tool injection;

filesystem escape;

network escape;

secret leakage;

identity confusion;

TOCTOU;

replay;

side effects no declarados;

fallos parciales;

runtime crash;

caller crash;

cancelación;

resultados ambiguos;

evidence spoofing;

y crecimiento innecesario del TCB.

Tercera ronda:

resolver desacuerdos mediante evidencia.

No utilizar votación mayoritaria como sustituto de argumentación.

Dos modelos repitiendo el mismo supuesto no constituyen evidencia independiente.

14. Regla epistemológica

Toda afirmación relevante debe clasificarse conceptualmente como:

hecho observado;

fuente externa;

inferencia;

decisión de diseño;

hipótesis;

o cuestión abierta.

No tomar documentación de memoria, agentes o repositorios como verdad simplemente porque esté escrita.

Cuando una afirmación describa comportamiento de software existente, verificar código, pruebas o ejecución cuando sea razonablemente posible.

La memoria es evidencia potencial, no autoridad automática.

15. Resultado esperado de la investigación

Producir inicialmente:

un mapa de estándares y patrones relevantes;

un threat model;

una matriz de requisitos candidatos;

una matriz de desacuerdos entre modelos;

una propuesta AEC v0.1;

un esquema conceptual del contrato;

una taxonomía de errores;

una definición de execution shim provisional;

un modelo de conformidad;

y un registro de decisiones rechazadas.

El contrato debe indicar claramente:

MUST;

SHOULD;

MAY;

y OUT OF SCOPE,

utilizando semántica normativa consistente.

16. Sólo después: compatibility mapping

Cuando el AEC candidato haya sobrevivido las rondas adversariales, realizar una fase independiente contra:

EKTEL;

SKEVI;

AN-KLA;

Skopos;

Ágora;

y otros consumidores relevantes.

Para cada uno preguntar:

¿Qué necesita solicitar al runtime?

¿Qué está implementando localmente hoy?

¿Es dominio propio o ejecución?

¿Puede expresarse mediante AEC?

¿Qué shim provisional existe?

¿Qué debería desaparecer cuando exista un runtime conforme?

¿Qué jamás debería delegarse al runtime?

No modificar esos proyectos durante esta fase.

El resultado es únicamente un compatibility/gap analysis.

17. Reevaluación específica de EKTEL

Finalmente comparar AEC v0.1 contra el diseño congelado de EKTEL.

Determinar:

qué partes ya satisface M1;

qué partes pertenecen naturalmente a M2;

qué partes podrían pertenecer a M3;

qué partes deben quedar post-M3;

qué partes deberían implementarse mediante adapters;

qué partes pertenecen a PolicyPort;

qué partes corresponden a un sandbox externo;

y qué partes EKTEL nunca debería poseer.

Evaluar explícitamente si M2 necesita cambiar.

Clasificar el resultado como:

compatible sin cambios sustanciales;

compatible con cambios acotados;

requiere revisión arquitectónica;

o incompatible con la frontera actual de EKTEL.

18. Prohibiciones

No implementar M2.

No ampliar silenciosamente M2/M3.

No construir un sandbox nuevo durante esta investigación.

No escoger EKTEL como runtime universal por anticipado.

No convertir AN-KLA, SKEVI, Skopos o Ágora en dependencias del contrato.

No introducir memoria dentro del runtime salvo que la investigación demuestre una necesidad contractual mínima.

No confundir observabilidad con enforcement.

No confundir autenticación con autorización.

No confundir identidad con autoridad.

No confiar en restricciones escritas únicamente en prompts.

No aumentar el TCB sin justificarlo.

No adoptar tecnologías porque sean populares.

No diseñar un estándar interno gigantesco para cubrir futuros hipotéticos.

19. Criterio de éxito

El trabajo será satisfactorio si al terminar podemos entregar el mismo AEC a dos runtimes técnicamente diferentes y ambos pueden implementar el contrato sin conocer los proyectos consumidores.

Además, un consumidor debe poder cambiar de un runtime conforme a otro sin modificar su semántica de dominio.

Si esto no puede lograrse razonablemente, documentar por qué y considerar falsada la premisa del AEC común.

20. Principio rector

Los componentes son propietarios de su dominio.

Las políticas son propietarias de las decisiones que les corresponden.

El runtime es propietario de la ejecución que puede hacer cumplir.

El contrato es propietario únicamente de la frontera interoperable entre ellos.

No construir código hasta saber dónde termina cada una de esas responsabilidades.