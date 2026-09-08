# Model run record — interoperability/lifecycle

- **Fecha:** 2026-09-08.
- **Provider/surface:** OpenAI Codex multi-agent runtime.
- **Model solicitado por controller:** `gpt-5.6-terra`.
- **Model reportado por el agente:** `GPT-5 Codex`; no se expuso revisión más
  granular.
- **Role:** crítica independiente de interoperabilidad, lifecycle,
  anti-trivialidad y negative controls.
- **Run reference:** `/root/f0a_interop` (nombre canónico efímero del
  orquestador; no es un identificador público).
- **Contexto heredado:** sólo autorización y pregunta pública F0-A; instrucción
  de no inspeccionar repo privado ni editar archivos.
- **Input digest:** no disponible; prompt serializado no expuesto.
- **Fuentes accesibles:** web pública primaria.
- **Tools:** consulta web; sin ejecución de código externo.
- **Clasificación:** `PRIVATE-SANITIZED`.
- **Output original:** no persistido literalmente; síntesis fiel debajo.
- **Errores:** ninguno reportado.

## Síntesis del output

El revisor rechazó **H-common**, admitió **H-profiles** sólo si el núcleo se
limita a correlación, autoridad declarada, evidencia e incertidumbre, y juzgó
**H-family** la explicación más sólida. La causa principal es que retries,
cache, múltiples intentos, cancelación y éxito difieren materialmente entre
POSIX/OCI, Remote Execution/Kubernetes y MCP.

Propuso separar `submitted`, `admitted`, `attempt_started*`,
`attempt_finished*` y `terminal_observed`; declarar `idempotency_class`,
`retry_policy`, `cancel_guarantee`, `effect_model` y capabilities; y conservar
outcomes abiertos como succeeded, failed, cancelled, indeterminate y
superseded con semántica de perfil.

Controles negativos conservados:

1. RE cache hit frente a `/bin/true`;
2. Job con successPolicy parcial frente a exit 0;
3. timeout + retry con primer efecto desconocido;
4. cancelación MCP tardía;
5. Job duplicando una escritura externa;
6. wrapper único que oculta dos ejecutores sin demostrar interoperabilidad.

## Limitaciones declaradas

- análisis documental público al 2026-09-08;
- sin implementaciones ni repos privados;
- fuentes tratadas como claims, no autoridad de diseño.
