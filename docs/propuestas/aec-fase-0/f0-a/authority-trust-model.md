# F0-A — Authority and Trust Model

- **Estado:** cierre F0-A; no es arquitectura adoptada.
- **Clasificación:** `PUBLISHABLE` como candidato; no autoriza publicación.

## Principio

Una invocación sólo puede sostener predicados acotados. Cada predicado debe
nombrar sujeto, autoridad, tiempo, perfil, productor de evidencia, verifier y
trust anchor. La identidad no concede permiso; una decisión no prueba
enforcement; una firma no prueba verdad material.

## Roles

| Rol | Responsabilidad | Autoridad que no debe inferirse |
|---|---|---|
| principal/resource owner | origina intención o delega derechos | operación técnica correcta |
| caller | construye y envía la invocación | autoautorizarse por ser autenticado |
| subject | identidad en cuyo nombre se actúa | ser el actor efectivo |
| actor | entidad que solicita/ejecuta por el subject | impersonación implícita |
| authorization issuer | emite grant con audience/scope/expiry | enforcement del runtime |
| PDP | calcula decisión bajo policy/context | aplicación de la decisión |
| runtime operator | controla despliegue/configuración | independencia como auditor |
| PEP | bloquea o permite en la frontera del efecto | corrección del PDP |
| credential provider | entrega identidad/credencial al workload | autorización de operación |
| scheduler/executor | realiza uno o más intentos | unicidad de intento/efecto |
| evidence producer | afirma hechos/mediciones | que su claim sea verdadero |
| verifier | evalúa evidence con reglas y raíces | decisión final de confiar |
| relying party | decide si el resultado es aceptable | ampliar el alcance del claim |
| trust anchor | raíz aceptada para una verificación | seguridad global del sistema |

## Relaciones mínimas

```text
principal --delegates--> subject/actor
authorization issuer/PDP --authorizes--> request + audience + conditions
caller --dispatches--> runtime admission
runtime admission --commits under profile--> PEP/scheduler
PEP/scheduler --creates 0..n--> attempts
attempts --may cause--> effects
producers --assert--> observations/evidence
verifier --evaluates using roots--> predicate result
relying party --decides--> accept/reject/indeterminate
```

Cada flecha requiere su propia evidencia o debe quedar declarada como supuesto.

## Vector de assurance

No hay nivel total ordenado. Para cada propiedad `p` se registra, como mínimo:

| Estado | Pregunta |
|---|---|
| requested | ¿el caller pidió `p`? |
| authorized | ¿una autoridad permitió `p` para este sujeto/request/audience? |
| configured | ¿la configuración declarada contiene el control asociado? |
| applied | ¿el PEP/runtime afirma haberlo aplicado a este intento? |
| observed | ¿un observador vio el estado o comportamiento relevante? |
| evidenced | ¿existe evidencia ligada a sujeto/invocación/propiedad? |
| verified | ¿un verifier aceptó el predicado bajo trust anchors y policy? |

Los estados no son necesariamente monotónicos: evidencia expira, un profile
deriva y una raíz puede revocarse. Deben incluir tiempo y frescura.

## Binding chain investigable

Sin fijar wire format, una fase posterior tendría que evaluar:

```text
intent_digest
  -> authorization_ref(subject, actor, audience, conditions)
  -> profile_ref(version, digest, issuer, limitations)
  -> admission_ref
  -> attempt_refs[0..n]
  -> outcome_ref
  -> evidence_refs(property, producer, observed_at, coverage)
```

Un enlace ausente no se rellena por inferencia. `profile_ref` autenticado sólo
prueba quién declaró capacidades; no demuestra configuración o enforcement.

## Composiciones de confianza

### Roles separados

Permiten contraste independiente, pero amplían protocolos, claves, latencia y
failure modes. Un verifier separado sólo es independiente si no comparte la
misma raíz material o fuente de datos que el producer.

### Roles colapsados

Un operador puede ser issuer, runtime, PEP y evidence producer. Es válido para
un perfil local si se declara; la evidencia entonces es un claim del operador,
no attestation de tercero. Añadir firma no crea independencia.

### Delegación

Debe conservar subject y actor cuando sean distintos, audience/resource,
expiry, alcance, restricciones de redelegación y cadena truncada explícita. Un
handle bearer se clasifica como material sensible si su posesión basta para
actuar.

## Modelo de evidencia

Toda evidencia candidata debe declarar:

- `producer`, `subject`, `invocation/attempt`, propiedad y perfil;
- tiempo de producción/observación, vigencia, secuencia y replay semantics;
- campos cubiertos y canonicalización;
- mecanismo de autenticidad, verifier previsto y trust anchor, o su ausencia;
- `demonstrates` y `does_not_demonstrate`;
- retención, minimización y clasificación.

Taxonomía: telemetry describe operación; receipt acusa un acto; measurement
registra un valor; attestation formula un claim evaluable; third-party
observation aporta independencia relativa; proof permite verificar un
predicado definido. No son sinónimos.

## Contraste read-only con EKTEL

EKTEL falsifica una abstracción universal fuerte y muestra un perfil de roles
colapsados:

- `PolicyPort.evaluate()` separa conceptualmente PDP de EKTEL, pero el caller de
  ese puerto sigue siendo el PEP responsable de aplicar la decisión.
- La solicitud de policy contiene un subconjunto local: `action_id`,
  `identity_digest`, `command_absolute` y `policy_mode`; no es lenguaje portable
  de autoridad.
- El timeout se comprueba después de retornar `evaluate()`: clasifica una
  respuesta tardía, pero no interrumpe un adaptador bloqueado.
- `ReplayStore.consume_start_token()` define CAS anticipado para M2; el módulo
  declara expresamente que su uso productivo pertenece a M2.
- `SpawnFrontierCounter` declara cero `subprocess/fork/exec/start` productivo y
  que es sólo instrumental de pruebas.
- `EktelActionRequest v1` exige `command_absolute`, `args`, `cwd`, env, stdin y
  output bounds: es un perfil POSIX, no un Core universal.
- El único `artifact_identity_profile` es
  `route_mutable_unverified`, por lo que no demuestra identidad del ejecutable.
- La clave HMAC de operador autentica dentro de un dominio local y colapsa
  issuer/verifier/operator; no constituye attestation independiente.

Consecuencia: EKTEL aporta patrones valiosos de fail-closed, binding y
ambigüedad, pero no demuestra ejecución, aislamiento general, enforcement de
filesystem/network/secrets/cost ni portabilidad multi-runtime. F0-A no corrige
estas ausencias.

Referencias read-only: `src/ports/policy_port.py:44-51`,
`src/application/admit.py:280-342`, `src/ports/replay_store.py:1-16,49-55`,
`src/adapters/spawn_frontier_counter.py:1-13,36-43`,
`contracts/schemas/v1/action-request.schema.json:8-23,34-135` y
`contracts/schemas/v1/capability-payload.schema.json:43-45`.
