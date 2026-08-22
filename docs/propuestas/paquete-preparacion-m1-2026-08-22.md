# Paquete de preparación para la decisión sobre M1 (admisión)

**Estado:** **propuesta para decisión del dueño — NO es autorización.** Nada en
este documento autoriza M1, implementación, commit, push, publicación ni
cambio de contrato. **Decidida (2026-08-22):** el dueño aceptó D-P1..D-P4 y
autorizó M1 con condiciones expresas — acta:
`docs/decisiones/autorizacion-m1-2026-08-22.md`. El mismo día el dueño
autorizó una **adenda** (origen: rondas Pinax R1/R2) que sustituye las
formulaciones ambiguas de la orden, y una **adenda final** que levantó las
pausas restantes (sal/`key_id`, precedencia) y cerró las rondas Pinax —
texto operativo vigente en el plano (b) y la sección «Reglas finales
autorizadas» del acta. Este paquete no afirma implementación: la
autorización la dio el dueño por canal, no este documento.

**Fecha:** 2026-08-22.
**Autor:** Ejecutor OpenCode (GLM 5.2), sesión `ektel-opencode-ejecutor-pre-m1-01`,
por encargo del Controlador (canal tmux efímero; dossiers en
`/private/tmp/ektel-m1-prep-20260822-01/`). Sin commit, sin push, sin escritura
de memoria AN-KLA en este intento.
**Baseline:** `main` limpio, `HEAD = origin/main = 43731b8` (verificado antes de
escribir). La ronda adversarial sobre este paquete se registra en
`docs/revisiones/2026-08-22-pre-m1-adversarial.md`.

## 0. Advertencia de lectura

Este documento es una **propuesta**: describe opciones, gates y decisiones. No
es un acta de autorización (las actas viven en `docs/decisiones/` y sólo el
dueño las firma). Confundir propuesta con autorización es exactamente el defecto
que este paquete existe para evitar. La autorización de M1, si procede, es un
acto separado con alcance cerrado (especificación v1.2 §19 punto 6; acta de
autorización de M0, restricciones). **Ese acto ocurrió el 2026-08-22**
(acta: `docs/decisiones/autorizacion-m1-2026-08-22.md`); la propuesta en sí
no autorizó nada entonces ni lo autoriza ahora.

## 1. Estado real del proyecto (sin inflar)

- **M0 está cerrado a nivel contractual y publicado**: doble PROCEED externo
  (Codex y Claude sobre el mismo MANIFEST-ROOT `sha256:47302f74…`), cierre
  registrado en `fba5a35`, evidencia durable en
  `docs/revisiones/2026-08-21-m0-gate-final/` (commit `ecfde79…`).
  `contracts/` contiene los wire schemas v1, 90 vectores dorados y dos parsers
  de referencia (uno **clean-room de origen, con independencia debilitada y
  declarada** — `contracts/README.md`, R5: el acuerdo A/B acredita
  convergencia de dos estilos, no independencia estadística; la mirada
  independiente fue la re-verificación externa).
- **M1 quedó autorizado el 2026-08-22** (acta
  `docs/decisiones/autorizacion-m1-2026-08-22.md`, con condiciones expresas;
  al redactar este paquete no lo estaba — especificación §19.6; autorización
  M0: «cada hito posterior requiere su propia autorización»). **M2 y M3
  siguen sin autorizar.**
- **Deuda M0 abierta y declarada:** H6 `stdin_policy` (acta de corrección M0
  §13; confirmada abierta por el gate Claude, O-5). **Observaciones no
  bloqueantes del gate final:** O-1 (sin base accept para
  `termination_accepted`), O-2 (desfase de conteo documental del encargo;
  informativa, sin archivo inesperado según el propio veredicto), O-3 (NUL/TAB/`U+0085` aceptados en
  `command_absolute`/`cwd` por diseño del contrato), O-4 (orden intra-campo sin
  asiento expreso), O-6 (intérprete del validador externo). Este paquete trata
  H6, O-1 y O-3 expresamente (§5 y §6); O-2, O-4 y O-6 quedan registradas como
  superficie menor sin acción propuesta aquí.
- **Claims:** todos siguen en estado **P** (propuesta). Nada de este paquete
  promueve un claim a V; la promoción es por claim al superar su suite
  (nota de estado de `docs/claims-y-no-claims.md`).

## 2. Delimitación de M1 (propuesta de alcance para decidir)

Fuente normativa: especificación v1.2 §15 «M1 — Admisión» y propuesta histórica
§13 M1, que la especificación adopta «sin cambios». El entregable es el
**pipeline de admisión completo y verificable**, no la supervisión.

### 2.1 Dentro de M1

1. **Parser estricto de admisión.** Dos capas sobre los wire contracts v1
   congelados: (i) la capa de contrato ya gateada en M0 (forma, JSON
   estricto, canonicalidad, vocabulario cerrado de diagnósticos) reutilizada
   sin modificación; (ii) la **semántica de admisión** que M0 excluyó por diseño
   (§5.8): verificación de la firma del sobre anidado en el `ActionRequest`,
   PoP anidada, coherencia `command_absolute` del descriptor ↔
   `action_binding.command_absolute` de la capacidad, y vigencia.
2. **Identidad determinista.** `identity_digest` reproducible: SHA-256 de
   `protected_header_b64 + "." + payload_b64` tal como viaja (§6.5); dos
   serializaciones distintas son identidades distintas (por diseño; la
   canonicalidad base64url sólo cierra aliases de los mismos bytes, ADR-010
   §6).
3. **Verificación de capacidad raíz.** HMAC-SHA256 con dominio
   `ektel/capability/v1`, perfil byte-exacto §5.2, orden de cuatro pasos
   congelado (estructura → base64url canónico → MAC → semántica);
   `exp > nbf` obligatorio (§6.9); vigencia contra reloj de pared con
   tolerancia de skew declarada (§7.3).
4. **PoP.** `invocation_proof` con dominio `ektel/pop/v1` sobre
   `len(nonce) || nonce || payload_digest`: el nonce queda ligado al
   descriptor concreto y no es reusable con otro payload bajo la misma
   capacidad (ADR-003 §1.5).
5. **Replay store con semántica de reinicio** (§7.4–7.5). Dos registros CAS
   durable distintos: `nonce_reservation` (clave `(issuer_id, nonce)`,
   `free → reserved`, durante `admit`) y `start_token_consumption` (clave
   `identity_digest`, `unspent → spent`, inmediatamente antes de la creación
   del proceso). Perfil `posix-fsync-dir/v1` (con `F_FULLFSYNC` en Darwin).
   El store **sobrevive reinicios**: tras reiniciar, los registros cargados
   siguen rechazando replays; no hay ventana de replay por reinicio. Sin
   store disponible, la admisión **rechaza** (fail-closed); store en memoria
   sólo en pruebas. Un nonce permanece reservado hasta `exp + tolerancia`.
6. **PolicyPort nulo y adaptador de prueba** (ADR-008). El núcleo se prueba
   completo sin CAGF: contract tests contra el puerto nulo y uno falso
   (`Allow`/`Deny`/`Indeterminate`/timeout; el adaptador de prueba intenta
   mutar la solicitud y el núcleo evalúa su propia copia inmutable,
   ADR-008 A2). El perfil de despliegue declara
   `policy_mode ∈ {absent, optional, required}`.
7. **Orden fijo de validación de admisión** (propuesta §6.2, adoptada por la
   especificación §4): versión y forma → valores y tamaños → identidad
   completa → firma/confianza/vigencia/PoP → nonce y replay → decisión del
   `PolicyPort`, si está configurado → disponibilidad de evidencia
   obligatoria previa al inicio. **Sin efectos parciales antes de terminar
   la admisión** (la reserva de nonce es el único efecto durable, y es
   idempotente por CAS). *(El paso 7 —evidencia obligatoria previa al
   inicio— queda **inerte en M1** por ADR-008 A3: la matriz
   `policy_mode × audit_mode` se prueba en M2/M3 y el AuditSink no existe
   hasta M3; el acto de autorización puede fijar `audit_mode=optional` como
   condición expresa.)*
8. **Camino hasta la compuerta de creación de proceso.** El criterio de salida
   M1 «ningún caso inválido inicia proceso» exige que la compuerta exista y
   sea observable para poder probar que lo inválido nunca la cruza. La
   **forma** de esa compuerta en M1 es la decisión D-P4 (§10): recomendación —
   verificación instrumental (spawn contabilizado/stub) sin supervisión, que
   es M2.

### 2.2 Fuera de M1 (cada uno requiere acto propio)

- **Toda la mecánica de supervisión** (M2): `setpgid`, terminación graduada,
  salida acotada, subreaper, reloj monotónico de plazos, estados post-inicio,
  tabla de garantías por plataforma.
- **Eventos y AuditSink** (M3): `RuntimeEvent v1`, sink durable, recibos,
  política de reintentos. La emisión durable del evento `policy_degraded`
  (spec §9) es superficie M3; en M1 la degradación de política es visible en el
  resultado de admisión, no en un evento persistido (el vehículo concreto —
  un campo de `guarantees_applied`/`guarantee_plan` u otro — se pinea en el
  acto de autorización, para que G7 sea verificable sin ambigüedad).
- **Cambios al wire contract v1 congelado**, salvo los que el dueño autorice
  expresamente dentro del acto M1 (D-P2 añade un vector dorado; D-P1
  alternativa (b) enmendaría §8.1 y exigiría re-gate del contrato — acto
  mayor, no parte de M1 por defecto).
- **Carril de caracterización** (§7 de este paquete): x86_64, durabilidad
  bajo fallo, RSS por muestreo.
- **Todo lo excluido por la stop rule** del ciclo (memoria, routing,
  delegación, plugins, CAGF completo, aislamiento fuerte): propuesta y
  autorización nuevas; la stop rule no se toca.

## 3. Criterios de salida de la especificación → gates verificables

La especificación v1.2 §15 M1 fija cuatro criterios. Cada uno se convierte en
gate ejecutable con evidencia conservada; los conteos exactos se congelan al
cerrar M1 (no aquí; aquí se define qué debe medir cada gate).

| Criterio (spec §15 M1) | Gate | Qué prueba y cómo falla |
|---|---|---|
| Ningún caso inválido inicia proceso | **G1** Suite negativa de admisión: todo vector **de veredicto reject** del corpus M0 (90 vectores en total, 18 de ellos accept) rechazado en la **capa de contrato** con el diagnóstico §5.6 esperado del propio vector (los vectores M0 llevan diagnósticos de parser de contrato, no `reason_code`s), y, si una entrada **inválida** cruza a la **capa de admisión**, rechazada con `reason_code` cerrado del vocabulario **§8.3**; conteo exacto congelado por capa. Falla si un vector inválido produce `Admitted`. |
| | **G2** Prohibición de spawn ante inválidos: instrumentación de la frontera de creación de proceso (contador/verificador de la compuerta D-P4) = **0 creaciones** tras la suite negativa + fuzz; falla si cualquier entrada inválida cruza la compuerta. |
| | **G3** Orden de validación (propuesta §6.2) fijo y observable: rechazos deterministas por capa con la precedencia congelada de **§5.6/§5.2** (diagnósticos de contrato) y el orden de admisión de la propuesta §6.2; pruebas de precedencia con dobles causas (p. ej. MAC rota + capacidad expirada → el cripto precede a la vigencia según §5.2/§6.2); falla ante razón no determinista o fuera del vocabulario que corresponda a su capa. |
| Vectores criptográficos negativos pasan | **G4** Negativos cripto enumerados y nombrados, con el vocabulario que corresponde a cada capa: contrato §5.6 — MAC rota (`bad_signature`), alias no canónico **con MAC válida** (`bad_base64`, ADR-010), `signature` ≠ 43 (`invalid_value`), `alg_unsupported`, `schema_version` mayor (`schema_version_unsupported`), `typ` discordante, `exp <= nbf` (`invalid_value`); admisión §8.3 (`reason_code` de `AdmissionRejected`) — expirada contra reloj de pared con tolerancia (`capability_rejected`), PoP con nonce o digest equivocados, nonce reutilizado (replay, §7.4); y en `StartOutcome` (§8.3) — token de admisión ya gastado → `StartFailed` con `capability_rejected` (§8.3 asigna ese código al perdedor concurrente y §6.6 manda que `start` re-verifique consumo único — `capability_rejected`, asignado por la letra al caso vecino (perdedor concurrente), es el que encaja aquí; el acto de autorización puede asentarlo). Los vectores M0 cubren la capa de contrato; M1 añade vectores de admisión (reloj de pared, replay, consumo) porque esas capas no existen en M0. Falla si un negativo pasa o diagnostica fuera del vocabulario de su capa. |
| | **G5** Identidad determinista: recomputación de `identity_digest` conforme a los vectores dorados; misma serialización → mismo digest; serialización distinta → digest distinto. Falla ante cualquier divergencia. |
| Fallos de dependencia requerida fail-closed | **G6** Replay store: caído, inaccesible, con error de fsync o **lleno** (ADR-004 A2: límite de tamaño declarado; al alcanzarlo, rechazo) → `AdmissionRejected`, nunca admisión en memoria fuera de pruebas. Falla si una dependencia caída produce `Admitted`. |
| | **G7** PolicyPort según perfil: `required` + puerto ausente/indisponible/`Indeterminate`/`Allow` expirado o tardío → rechazo (§9, ADR-008 B7); `optional` → degradación declarada en el resultado (no silenciosa); contract tests con puerto nulo y falso. Falla si el modo no queda declarado o un `Allow` inválido se acepta. |
| Fuzzing sin aceptación ambigua | **G8** Fuzz de admisión determinista **con oráculo**, extendiendo la disciplina M0 (bases válidas verificadas antes de mutar; oráculo por mutación —veredicto, diagnóstico, capa, clase— comprobado contra la implementación y contra la referencia por separado; detección de error común; crash = fallo del gate, nunca excepción propagada). Conteo y fingerprint del corpus congelados. «Sin aceptación ambigua» = toda aceptación coincide con el oráculo; toda divergencia u omisión falla el gate. |
| | **G9** Regresión M0 intacta: fuzz diferencial A/B de contrato (bytes 1530/0 + semántico 18/165/0/0/0), suite `tests/` y regeneración diff cero siguen pasando sin modificación de `contracts/`. Si D-P2 se aprueba, los conteos congelados se re-basan a los del corpus resultante (91 vectores / 19 bases semánticas / fuzz de bytes re-basado a las 17 mutaciones por vector del corpus nuevo) y ese re-congelado forma parte del gate; hasta entonces, los conteos vigentes son los de M0. |

**Obligaciones y entregables M1 heredados** (también gates de cierre):

- **G10** Rechazo de claves duplicadas en el parser de admisión vía
  `object_pairs_hook` con detección (ADR-002, consecuencia; el parseo por
  defecto de Python acepta duplicados silenciosamente).
- **G11** Recolección de nonces expirados por TTL (`exp + tolerancia`) y
  límite de tamaño del store con rechazo fail-closed (ADR-004, consecuencia y
  A2).
- **G12** Creación de CI con `mypy --strict` como herramienta de desarrollo
  (ADR-006 A8: «obligación que M1 debe crear, no hecho consumado»; hoy no
  existe CI en el repositorio).
- **G13** Métrica de latencia de admisión medida y declarada (ADR-004,
  consecuencia: la escritura durable síncrona está en el camino crítico).
- **G14** Tolerancia de skew como parámetro de despliegue versionado (inicial
  30 s), registrado en el resultado (ADR-004 A3; §7.3). §7.3 sitúa el registro
  en el **evento de admisión** — superficie M3: en M1 el registro vive en el
  resultado de admisión, con vehículo a pinear en el acto de autorización
  (ídem nota de §2.2 sobre `policy_degraded`).
- **G15** Plataforma del gate: suite completa en Linux aarch64 (primaria,
  ADR-006) y Darwin arm64 con degradaciones declaradas; clase de evidencia
  (L/V/R) declarada por corrida, como en M0.
- **G16** Semántica de reinicio del replay store (entregable §15 M1, §7.4):
  tras reiniciar el runtime (proceso nuevo contra el mismo store durable),
  los registros cargados siguen rechazando replays de nonces reservados y
  tokens gastados; prueba de integración con el store durable real (no en
  memoria). Falla si un replay es admitido tras reinicio, si el store no
  sobrevive al reinicio, o si la reintroducción de una admisión con nonce
  nuevo no se comporta como admisión nueva.

## 4. Congelados de diseño para M1 (invariantes no negociables)

Estas reglas se **proponen** como congeladas para cualquier implementación
M1 — a incorporar como condiciones expresas del acto de autorización; si el
dueño las adopta, violarlas es defecto M1:

1. **Precedencia fail-closed de admisión** (orden de la propuesta §6.2 + capas
   de §5.2/§5.6): ante entradas con múltiples defectos, gana el primer defecto del
   orden congelado; un rechazo nunca se degrada a aceptación por fallo
   parcial, y un fallo **ambiguo** (crash, timeout, estado desconocido) se
   clasifica como rechazo.
2. **Negativos cripto cerrados:** la lista de G4 es el vocabulario de lo que
   M1 debe atrapar; ampliarla exige versión de contrato o acta. *(Regla de
   clausura propuesta por este paquete — no cita norma previa: la lista la
   redacta §3; el acto de autorización la adopta o enmienda.)*
3. **Replay en dos CAS** (§7.4): reserva de nonce en `admit`, consumo de
   token antes de crear proceso; el perdedor concurrente recibe
   `capability_rejected`; un crash tras el CAS de consumo y antes del spawn
   deja el token **gastado** y produce `start_failed_indeterminate` — nunca
   habilita replay; la reconciliación consulta el store por
   `identity_digest`, nunca reinyecta.
4. **Dependencia caída = rechazo.** Replay store o política requerida
   indisponibles → `AdmissionRejected`. No existe modo degradado silencioso.
5. **Fuzz con oráculo, sin aceptación ambigua:** la aceptación sólo es válida
   si coincide con el oráculo; el acuerdo entre dos implementaciones no
   sustituye al oráculo (lección B9/M0: el error común A/B sólo lo detiene el
   oráculo).
6. **Prohibición de spawn ante inválidos:** ninguna entrada rechazada (o no
   validada) puede alcanzar la creación de proceso; la compuerta es observable
   (G2) por construcción.
7. **`admit` sin efectos parciales** antes de terminar la admisión (propuesta
   §6.2), salvo la reserva CAS idempotente del nonce.

## 5. H6 — `stdin_policy` (decisión D-P1; deuda M0 expresamente abierta)

**El defecto, fiel al acta §13 y al gate Claude (O-5):** `stdin_policy` NO es
unión discriminada en el contrato: `{"kind":"inline_b64"}` sin `data_b64` es
`accept/ok` hoy; `kind:"empty"` con `data_b64`/`sha256` también. M0 congeló
los wire contracts como están; imponer dependencia de campos por `kind` exigía
enmendar §8.1 y regenerar contratos ya gateados. La canonicalidad de
`data_b64` **sí** se aserta (`bad_base64`). La condición de entrada registrada
en el acta: orden del dueño + acta de enmienda al diseñar el admission parser
M1 (o ADR propio antes). **Este paquete no resuelve H6; lo pone en decisión.**

| Alternativa | Qué exige | Consecuencias |
|---|---|---|
| **(a) Regla semántica de la capa de admisión M1** (recomendada) | El parser de admisión impone la dependencia por `kind` como regla de SU capa (análogo a §5.8: regla del parser, no del wire): `inline_b64` exige `data_b64` canónico y ausencia de contradicción; `empty` prohíbe `data_b64`/`sha256`. Rechazo con `malformed_descriptor`. Vectores de admisión nuevos (no del corpus M0). | El contrato M0 queda intacto (sin re-gate); la deuda queda resuelta **a nivel de admisión** en M1; el wire sigue permitiendo la forma incoherente, documentado como regla de la capa superior. Si un futuro consumidor usa el parser de contrato sin admisión, la holgura persiste (declarado). |
| (b) Enmienda del contrato §8.1 | Unión discriminada en el schema + regeneración de vectores + acta de enmienda + re-gate externo del contrato M0. | Cerradura total (contrato y admisión), pero reabre un artefacto cerrado con doble PROCEED; costo alto; es un acto mayor fuera del alcance M1 por defecto. |
| (c) Aplazar al spawn (M2) | El núcleo decide qué hace con el stdin incoherente sólo al crear el proceso. | M1 admite entradas cuya incoherencia se descubre tarde; debilita el criterio «ningún caso inválido inicia proceso» y hereda el riesgo a M2; la deuda sigue abierta un hito más. |

**Recomendación razonada:** (a). Resuelve la deuda donde vive la decisión
(la admisión decide qué hace el núcleo con el stdin antes de spawn, según el
acta), sin reabrir M0 y sin contratar el costo de (b). **Decisión: pendiente
del dueño (D-P1). Este documento no la firma.** *(Decidida el 2026-08-22:
opción (a), luego **ampliada por adenda del dueño** — stdin ligado byte a
byte a la capacidad: `empty` = sólo `{kind:"empty"}` con digest de `b""`;
`inline_b64` exige `data_b64` canónico y `sha256` con triple comparación;
discordancia = `malformed_descriptor` antes de PoP/replay/inicio — ver §10 y
acta, plano (b); la precedencia por capa quedó fijada por la adenda final:
incoherencia interna → `malformed_descriptor`; discordancia contra el
`action_binding` autenticado (incluido digest de stdin) →
`capability_rejected`.)*

## 6. O-1 y O-3 (decisiones D-P2 y D-P3; NO resueltos aquí)

### O-1 — sin base accept para `termination_accepted` (D-P2)

**El hallazgo, fiel al gate Claude:** el corpus no tiene ningún vector accept
para la alternativa `termination_accepted` (sólo `tout-valid-rejected`); por
eso ninguna de las 18 bases del fuzz semántico ejerce esa rama y las clases de
mutación nunca corren contra ella. La rama fue sondeada a mano por el revisor
(comportamiento correcto en 4 casos, A=B); es **hueco de oráculo**, no defecto
de comportamiento.

| Opción | Consecuencias |
|---|---|
| (i) Añadir `tout-valid-accepted` como ítem de trabajo M1 (recomendada) | Corpus 90 → 91; bases del fuzz semántico 18 → 19; re-congelar fingerprint y conteos; re-ejecutar todos los gates de contrato. Toca `contracts/` (generator + vectores) — la autorización M1 debe incluirlo expresamente. |
| (ii) Dejar el hueco documentado | Cero costo; el hueco de oráculo persiste y la rama `termination_accepted` queda sin base de mutación en todo el ciclo M0–M3 si nadie la añade después. |

**Recomendación razonada:** (i), como parte del trabajo M1 autorizado (no de
este paquete): costo mínimo, cierra un hueco de oráculo detectado por el gate
final. **Decisión: pendiente del dueño (D-P2).** *(Decidida el 2026-08-22:
opción (i) — ver §10 y acta de autorización M1.)*

### O-3 — NUL/TAB/`U+0085` en `command_absolute`/`cwd` (D-P3)

**El hallazgo, fiel al gate Claude:** la clase negada
`[^\r\n\u2028\u2029]` es exactamente lo que §5.7 manda; por eso el contrato
**acepta** `NUL`, `TAB` y `U+0085` (verificado `accept/ok`). Un `NUL` embebido
es vector clásico de truncación en `execve`. Es superficie de la
admisión/spawn, no defecto de contrato M0 — pero M1 no debe heredar el
supuesto de que «el parser ya lo filtró».

| Opción | Consecuencias |
|---|---|
| (i) Regla de admisión M1: rechazo de bytes de control en `command_absolute`/`cwd` con `reason_code` cerrado (recomendada, con alcance mínimo garantizado: `NUL`) | `NUL` es byte imposible en una ruta POSIX (terminador de cadena): su rechazo en admisión es inequívoco y sin falsos positivos. Si el dueño amplía a TAB/`U+0085`/C0-completo, gana defensa contra truncación/exfiltración por confusión de bytes, al costo de rechazar rutas legales pero sospechosas que hoy el contrato admite (decisión de política local, versionada). |
| (ii) Manejar en el spawn (M2) | M1 admite rutas con `NUL`; el riesgo de truncación viaja hasta M2; si M2 lo olvida, el defecto es de la capa más peligrosa (creación de proceso). |
| (iii) Enmienda de schema | Cambia el contrato M0 cerrado; mismo costo de acto mayor que H6-(b); innecesario si la regla vive en admisión. |

**Recomendación razonada:** (i) con alcance **mínimo `NUL`** obligatorio; la
ampliación a TAB/`U+0085` queda a elección del dueño (se señala el trade-off;
no se elige por él). **Decisión: pendiente del dueño (D-P3).** *(Decidida el
2026-08-22: mínimo `NUL`, luego **ampliada por adenda del dueño** — NUL
rechazado también en cada elemento de `args` y en nombres/valores de
`env_allowlist_values`; nombre de entorno no vacío y sin `=`; TAB/`U+0085`
admitidos como límite consciente — y precisada por la **adenda final**
(regla 4: `os.fsencode` sobre las cadenas destinadas al futuro `execve`;
`UnicodeEncodeError` → `malformed_descriptor`; TAB/`U+0085` permitidos
cuando representables) — ver §10 y acta.)*

## 7. Carril de caracterización — explícitamente separado de M1

Tres frentes quedan **fuera** de M1 y este paquete **no** los autoriza; son un
carril de caracterización con autorización propia si el dueño los ordena:

1. **x86_64 real.** Puerta de pre-producción, no de M1–M3 (ADR-006; no-claim
   N12). Ninguna afirmación de portabilidad hasta caracterización en hardware
   o VM real. La autorización M0 dejó la ampliación de caracterización de
   plataforma como trabajo pendiente aparte.
2. **Durabilidad bajo fallo.** Niveles 1–2 (SIGKILL del escritor;
   `dm-flakey`/`dm-log-writes` en Linux) se validan en **M3**; el nivel 3
   (corte físico real) no es testeable sin hardware (supuesto declarado, N5).
   Nota de frontera: el replay store de M1 usa el perfil
   `posix-fsync-dir/v1` y M1 prueba **su** orden de protocolo y su semántica
   de reinicio del proceso (reiniciar el runtime no habilita replay); las
   pruebas de crash-consistency del dispositivo son superficie M3.
3. **RSS por muestreo.** Observación best-effort con fallos silenciosos
   posibles (README); no es mecanismo de control, `budget_exceeded` no existe
   en v1 (ADR-005), y su caracterización no autoriza ningún límite.

Aprobar M1 **no** aprueba ninguno de estos tres frentes.

## 8. Archivos y capas que una futura implementación M1 podría tocar

Enumeración para el acto de autorización (nada de esto se ejecuta en este
paquete; hoy `src/` sólo contiene `__init__.py` de placeholder con docstring,
sin código):

| Capa | Contenido previsto |
|---|---|
| `src/domain/` | Tipos de admisión (`ActionRequest` de dominio, `AdmissionOutcome`), identidad/digest, verificación de capacidad (HMAC, dominios, canonicalidad), PoP, vigencia con tolerancia. |
| `src/ports/` | Protocolo `ReplayStore`, protocolo `PolicyPort` (§9.1). |
| `src/adapters/` | Replay store de archivo (`posix-fsync-dir/v1`, `F_FULLFSYNC` en Darwin), PolicyPort nulo, adaptador de política de prueba. |
| `src/application/` | Orquestación `admit` (+ compuerta de `start` según D-P4) con el orden fijo de la propuesta §6.2. |
| `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/adversarial/` | Gates G1–G16 por capa: unitarios de dominio, contrato contra el corpus M0 + vectores de admisión, integración de reinicio del store y concurrencia CAS, adversariales de replay/mutación. |
| `scripts/` | Extensión determinista del fuzz a la capa de admisión (bases aceptadas por la admisión, oráculo por mutación). |
| CI (`.github/` o equivalente) | Creación del pipeline con `mypy --strict` como herramienta de desarrollo (G12; no existe hoy). |
| `contracts/` | **Sólo** bajo D-P2, aprobada por el dueño el 2026-08-22 (acta de autorización M1): `tout-valid-accepted` en generator + corpus + re-congelado de fingerprint. Cualquier otro cambio de contrato queda fuera. |
| `docs/` | Acta de autorización M1 (firma del dueño), actas de enmienda si las hay, registro de estado post-M1. |

## 9. Stop rules, rollback y definición de terminado de la implementación M1

### Stop rules de la implementación M1

1. **Parar al cerrar:** todos los gates G1–G16 verdes en la plataforma
   primaria + Darwin declarada + ronda adversarial fresca `PROCEED` sobre el
   manifest del artefacto M1. Sin ronda adversarial no hay cierre.
2. **Parar y volver al dueño (BLOQ)** si el trabajo exige: tocar
   `docs/especificacion/`, ADRs, `contracts/` más allá de D-P2 aprobada,
   dependencias nuevas, M2/M3, o cualquier decisión no delegada.
3. **Nada de M2/M3 se cuela:** si un test «necesita» crear y supervisar
   procesos reales, es M2; si «necesita» eventos persistentes, es M3. El
   gate G2 se satisface con la forma de compuerta que el dueño fije en D-P4.
4. **Stop rule del ciclo intacta:** cerrar M3 no inicia M4 (ADR-001);
   gobernanza de alcance social + contratos sin dónde colgar scope creep.

### Rollback

El árbol no contiene trabajo de implementación (`src/` sin código); todo M1
es aditivo (código y tests nuevos,
CI nueva, docs nuevas; `contracts/` sólo bajo D-P2 con regeneración
determinista verificable por diff). El rollback es `git revert`/reset al
commit de autorización; no existe migración de estado (el replay store es
archivo nuevo bajo directorio de despliegue, no migración de datos existentes).

### Definición de terminado

Gates G1–G16 verdes con conteos y fingerprints congelados; fuzz de admisión
con oráculo y sensibilidad demostrada (divergencia artificial, error común,
crash); regresión M0 intacta; ronda adversarial fresca `PROCEED` sobre hashes
idénticos; acta del dueño cerrando M1; tabla claims actualizada **sólo** por
los claims cuya suite M1 ejecutó (nota de la tabla: C1–C4 y C10 con la suite
M1; C3 y C5–C7 con M2/M3) — promoción por claim, con prueba conservada.

## 10. Decisiones para el dueño (decididas el 2026-08-22)

| # | Decisión | Opciones | Recomendación | Estado |
|---|---|---|---|---|
| D-P1 | H6 `stdin_policy`: dónde vive la coherencia por `kind` | (a) regla de admisión M1 · (b) enmienda de contrato §8.1 · (c) aplazar a M2 | **(a)** — resuelve la deuda en la capa que decide, sin reabrir M0 (§5) | **ACEPTADA (a), ampliada por adenda del dueño (2026-08-22)** — stdin ligado byte a byte a la capacidad (regla 1 de la adenda; acta, plano (b)); precedencia por capa fijada por la adenda final (regla 2) |
| D-P2 | O-1: añadir `tout-valid-accepted` al corpus como trabajo M1 | (i) añadir · (ii) dejar el hueco documentado | **(i)** — cierra hueco de oráculo con costo mínimo (§6) | **ACEPTADA (i)** — ampliada por adenda (regla 4: manifest/conteos nuevos; dossier M0 histórico inmutable); confirmada por Pinax R2 — acta |
| D-P3 | O-3: bytes de control en `command_absolute`/`cwd` | (i) rechazo en admisión (mínimo `NUL`; opcional TAB/`U+0085`) · (ii) diferir a M2 · (iii) enmienda de schema | **(i) mínimo `NUL`**; ampliación a elección del dueño (§6) | **ACEPTADA, ampliada por adenda del dueño (2026-08-22)** — NUL rechazado en `command_absolute`, `cwd`, `args` y entorno, nombre de entorno no vacío y sin `=` (regla 2 de la adenda; acta, plano (b)); TAB/`U+0085` admitidos como límite consciente; representabilidad `os.fsencode` autorizada por la adenda final (regla 4) |
| D-P4 | Forma de la compuerta de spawn en M1 (para G2) | (α) stub instrumental contabilizado, sin procesos reales · (β) proceso real mínimo sin supervisión — **roza M2**: el inicio del grupo observado es entregable M2 (spec §15); elegirlo exige ampliar alcance explícitamente | **(α)** — prueba «ningún inválido inicia» por construcción + contador, sin adelantar M2 (§2.1, punto 8) | **ACEPTADA (α)** — precisada por adenda (regla 5: spy/test double sólo de pruebas; cero `subprocess`/`fork`/`exec`/API `start`/ProcessHost/supervisión en producción M1); confirmada por Pinax R2 — acta |

Condición adicional de la misma orden (no era decisión del paquete): la
clave de operador ausente, ilegible o inválida debe fallar cerrado con gate
propio usando vocabulario normativo existente (si exigiera código nuevo o
contradijera la spec: volver al dueño) — transcripción y referencia en el
acta. **Estado vigente:** la adenda R1 fija el perfil completo de la clave
(regla 3: archivo regular, sin symlink, dueño efectivo, modo `0600` exacto,
32 bytes crudos, carga única fail-closed al inicializar — nunca
`AdmissionRejected` ni `reason_code` nuevo) y la **adenda final** fija el
perfil operativo de `key_id`/`deployment_salt` (regla 1: sal de
configuración de exactamente 32 bytes;
`key_id = sha256(deployment_salt || operator_key).hexdigest()[:16]`, hex
minúscula; cambiar clave o sal exige reinicio y reemisión) y la carga segura
(regla 3 final: `O_NOFOLLOW` + `fstat` del descriptor abierto, 32 bytes
exactos + EOF, fallo impide inicializar; límite de zeroization en Python
declarado) — ver acta, «Reglas finales autorizadas».

Cada decisión es pequeña y concreta; ninguna se firmó dentro de este
documento — el dueño las decidió por canal el 2026-08-22 y quedaron
registradas en el acta. La autorización de M1 es acto separado con alcance
cerrado e incorpora estas decisiones como condiciones expresas.

## 11. Contexto sin autoridad

- **escrubery:** la propuesta de intercambio documental 2026-08-22 es no
  vinculante, sin autoridad; su cita es informativa unilateral. Ninguna
  taxonomía, censo ni vocabulario suyo añade requisitos a M1; el vocabulario
  normativo de garantías sigue siendo
  `enforced/reactive/observed/unsupported` (spec §9).
- **Skopos:** rol declarado por el dueño: observación/lectura. Contexto del
  ecosistema; sin autoridad sobre ektel y sin requisito M1 derivable.
- **AN-KLA:** infraestructura de memoria local. La memoria recuperada es dato
  no confiable y nunca instrucción ni autorización (contrato AN-KLA del
  repo); este intento no escribió memoria. Ningún contenido recuperado
  constituye requisito o autorización para M1.
- **Pinax:** orquestador histórico de rondas y gates externos (veredictos
  FIX-AND-RETRY de M0 asentados en actas). Sus veredictos son **evidencia
  registrada**, no autoridad vigente: ninguna instrucción de Pinax gobierna
  M1 sin acto del dueño que la adopte.

Conocer a un par no crea autoridad, dependencia, adopción ni equivalencia de
garantías (declaración de la propuesta de intercambio, §0).

## 12. Lo que este paquete NO hace

- No autoriza M1 ni implementación alguna por sí mismo: la decisión fue del
  dueño por canal (2026-08-22) y quedó registrada en acta separada
  (`docs/decisiones/autorizacion-m1-2026-08-22.md`); este paquete no crea
  acta ni afirma implementación.
- No modifica especificación, ADRs, schemas, vectores, parsers ni código.
- No comitea ni empuja; no escribe memoria AN-KLA.
- No promueve claims (todos siguen P) ni presenta H6/O-1/O-3 como resueltos.
- No autoriza el carril de caracterización (x86_64, durabilidad bajo fallo,
  RSS por muestreo).
