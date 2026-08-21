# Acta de enmienda — corrección de M0 tras la doble NO-GO externa

**Fecha:** 2026-08-20.
**Autoridad:** regla de gobernanza del consenso v1.2 (toda enmienda posterior
lleva acta explícita) + instrucción de Pinax
(`/Users/krisnova/www/pinax/rondas/2026-08-20-m0-ektel-externas/instruccion-agente-ektel-correccion-m0.md`)
avalada por el dueño ("Autorizado: … el paquete completo de correcciones",
2026-08-20). **Ampliada el mismo 2026-08-20** por el veredicto
**FIX-AND-RETRY** de Pinax (6 bloqueantes; sin commit/push, sin cierre de
M0, sin rondas externas), avalado por el dueño.
**Base:** veredictos NO-GO de Codex (3 bloqueantes) y Claude (fuzz
diferencial: 307 divergencias, 79 de veredicto), síntesis de Pinax con
reproducciones propias; H1/H2 además reproducidos por este agente antes de
aceptarlos.

## 1. Decisión normativa nueva

**ADR-010 (aceptado 🔒 2026-08-20):** base64url canónico obligatorio — bits
residuales en cero, verificado re-codificando; alternativa (a) del brief.
Cierra la maleabilidad de firma (H1) y la inestabilidad de `identity_digest`
frente a re-encoding (H2). Aplicado en spec §5.2, schemas (formato
`ektel-b64u-canonical`), ambos parsers y vectores nuevos
(`cap-invalid-noncanon-sig`, `cap-invalid-noncanon-payload`).

## 2. Correcciones de código y contratos

| Hallazgo | Corrección |
|---|---|
| Parser A no aplicaba los schemas (`$ref` = any, sin pattern/min/enum; `GUARANTEES_ENUM` muerto; bool==int) | Reescrito: tablas completas con pattern (fullmatch), min/max, enums aplicados, `capability_envelope`/`invocation_proof` validados estructuralmente, bool ≠ int |
| Parser B: `re.search` permitía `\n` final | Corregido entonces con `re.fullmatch` (snapshot original); **precisado por FIX-AND-RETRY**: `pattern` conserva la semántica Draft 2020-12 (no anclada, `re.search`) y son los schemas los que auto-anclan sus patrones (`^`…`(?![\s\S])`) — ver §8, B1 |
| Uniones sin discriminación (`started` sin `handle`) | Schemas con `oneOf` + discriminador `const` + `not`; ambos parsers validan por alternativa (campos obligatorios en ella, prohibidos fuera) |
| Vocabulario de admisión desdoblado | Colapsado a la letra de §8.3: `capability_invalid/expired/reused` retirados; vector dorado `aout-valid-rejected` regenerado con `capability_rejected` |
| `capability_rejected` en `StartFailed` (contradicción Codex↔Claude) | **Queda en el schema**; la enmienda es a §8.3 (resolución de Pinax: conflicto interno de la spec, §7.4 lo exige). Codex no retrató su bloqueante 3: queda asentado aquí |
| Precedencia de diagnósticos invertida A↔B (90 casos) | Precedencia fija en spec §5.6; ambos parsers la implementan; iteración de campos en orden del schema |
| `identity_digest` inestable / firma maleable | ADR-010 (arriba) |
| `exp <= nbf` sin regla | §6.9 nuevo: ventana vacía → `invalid_value` en parser de contrato |
| Límites de tamaño ambiguos | §5.1: techo global de 64 KiB ES la regla |
| Letra de §6.6/§6.8 ambigua (concatenación) | Enmendada: token de admisión y token de terminación son sobres firmados estándar §5.2 (la implementación era mejor que la letra) |
| `size_exceeded` ausente del vocabulario documentado | Incluido en el vocabulario cerrado de diagnósticos (§5.6 y contracts/README) |

## 3. Corpus ampliado (70 vectores, 7 grupos)

Clases nuevas (grupo `correccion-m0` + adiciones en grupos existentes):
sobre/proof escalar, entero negativo, decimal, `exp == nbf`, `typ` cruzado
con MAC válida, firma no canónica y payload re-encodado con MAC válida
(ADR-010), campos reordenados con firma válida (acepta con SU digest),
uniones mal formadas (`started` sin `handle_ref`, `start_failed` con
`handle_ref`, `admitted` sin `guarantee_plan`), código retirado
`capability_expired`, `\n` final en `key_id`, `schema_version: true`,
doble causa (mutación de payload + MAC rota → `bad_signature`, porque §5.2
manda verificar antes de decodificar). **Adiciones FIX-AND-RETRY:**
prefijo en `key_id`, sufijo en `nonce`, `\n` final en `cwd` y en
`protected_header_b64` (bad_base64), campo extra en cada alternativa de las
tres uniones discriminadas (§8/B2). **Adiciones FIX-AND-RETRY 2 (§9):**
seis de `guarantees_applied` (B7) y seis de `schema_version` (B8,
incluido header firmado con versión 2 y MAC válida).

## 4. Verificación (snapshot 2026-08-20, clase L; re-corridas FIX-AND-RETRY y FIX-AND-RETRY 2)

- 70/70 vectores: ambos parsers coinciden en veredicto, diagnóstico y digest.
- Suite completa `python -m unittest discover -s tests`: **14 tests OK
  (3 skips Linux-only en Darwin)** — incluyen el gate permanente de fuzz
  (bytes + semántico + fingerprint congelado + sensibilidad).
- Generador determinista re-verificado tras los cambios; gate de diff cero
  vía `EKTEL_VECTORS_OUT` (copia temporal + `diff -r`).

## 4.1 Ronda adversarial propia sobre la corrección (gate de la instrucción)

- **Fuzz diferencial propio (corrida original, snapshot 2026-08-20, clase
  L):** 959 mutaciones (bit flips, truncados, prefijos/sufijos de espacio y
  `\n`) sobre los entonces 48 vectores → **1 divergencia encontrada y
  corregida** (el parser A validaba `capability_envelope` dentro de
  ActionRequest sin canonicalidad; B sí, vía `$ref`). Tras el fix: 0
  divergencias.
- **Fuzz diferencial versionado (FIX-AND-RETRY, punto 4):** la corrida
  quedó persistida como reproducción determinista en
  `scripts/fuzz_diferencial.py` (semilla 20260820, 17 mutaciones/vector,
  clases cerradas: bitflip, flip_two_bits, truncate, prefix/suffix de `\n`
  y espacio, insert_char) con gate permanente en
  `tests/contract/test_fuzz_diferencial.py`. Re-corrida sobre los 58
  vectores: **986 mutaciones → 1 divergencia nueva encontrada y corregida**
  — el parser A no imponía la longitud exacta 43 de `signature` que el
  schema declara (`^[A-Za-z0-9_-]{43}…`): una mutación de inserción daba
  A=`bad_signature` vs B=`invalid_value`; corregido en A (`exact: 43`,
  validado antes del MAC como propiedad sintáctica del sobre). Estado
  final: **0 divergencias en 986 mutaciones**, verificable en cada corrida
  de la suite.
- **Hallazgo propio de precedencia:** el vector de doble causa inicial
  asumía que la estructura del payload gana al MAC — falso: §5.2 manda
  verificar antes de decodificar, así que `bad_signature` gana. Vector
  corregido y precedencia asentada en §5.6.
- **Hallazgo propio de vocabulario:** `schema_version: true` cae por
  enum/const como `invalid_value`, no `invalid_type` (el tipo se evalúa
  dentro de la comparación con tipo estricto); documentado en el vector.
- **Cobertura:** añadido vector de `size_exceeded` (estaba documentado en
  §5.6 pero no ejercitado).
- **Retracciones:** ninguna más allá de las dos correcciones anteriores.

### 4.2 Independencia clean-room: estado declarado (FIX-AND-RETRY, punto 6)

El parser B se escribió originalmente sin leer el código del parser A
(R5). En esta corrección —y en la FIX-AND-RETRY— **ambos parsers fueron
modificados en el mismo ciclo por el mismo agente**, con conocimiento
mutuo de los hallazgos externos y del acuerdo esperado en los vectores.
Eso **debilita la independencia** que R5 quería acreditar: el acuerdo A/B
actual acredita **convergencia** de dos implementaciones de estilos
distintos (hand-coded vs table-driven sobre schemas) frente al corpus
versionado y al fuzz determinista, **no** independencia estadística de
dos autores aislados. La mirada independiente queda a cargo de la
re-verificación externa (gate de salida pendiente). Declarado también en
`contracts/README.md` y en el docstring del parser B.

## 5. Lo que queda abierto

- Ronda de verificación externa post-corrección con Codex y Claude sobre
  este diff (gate de salida de la instrucción).
- El fuzz de Claude (79 divergencias de veredicto clasificadas) es la mina
  de futuros vectores: pedir la lista clasificada.
- M0 sigue SIN cerrarse hasta esa re-verificación.

## 6. Lo que este acta NO hace

- No cierra M0 ni promueve claims (todos siguen en estado P).
- No toca la stop rule ni autoriza M1+.
- No comitea ni empuja: el paquete (incluida esta acta) queda SIN COMMIT
  pendiente de autorización por operación del dueño (stop rule del
  veredicto FIX-AND-RETRY).

## 7. Precisión de alcance de ADR-010 (FIX-AND-RETRY, punto 5)

ADR-010 **cierra los aliases base64url no canónicos de los mismos bytes
decodificados** (H1/H2): por cada contenido binario existe a lo sumo una
cadena wire aceptada. **No afirma** identidad estable entre
serializaciones JSON semánticamente equivalentes: claves reordenadas o
espacios distintos son bytes distintos y `identity_digest` distintos, por
diseño (spec §5.2/§6.5: se firma lo que viaja; dos serializaciones
distintas son identidades distintas; la canonicalización JSON está
prohibida en v1, §5.3). v1 identifica el **wire autenticado**, no una
forma normalizada del documento. Registrado como sección §6 de ADR-010
(precisión post-consenso con esta acta; la decisión no cambia).

## 8. Correcciones del veredicto FIX-AND-RETRY (2026-08-20)

| # | Bloqueante | Corrección aplicada |
|---|---|---|
| B1 | `pattern` redefinido como fullmatch | Semántica Draft 2020-12 restituida (§5.7 nuevo de la spec): patterns NO anclados en el estándar; los schemas auto-anclan (`^`…`(?![\s\S])`) y rechazan prefijos, sufijos y `\n` final por sí mismos. Parsers A y B usan `search` (A con patrones internos anclados; B interpreta los schemas). Vectores: `cap-invalid-keyid-prefix`, `cap-invalid-nonce-suffix`, `areq-invalid-cwd-newline`, `cap-invalid-ph-newline` |
| B2 | Campos desconocidos abiertos en outcomes | `unevaluatedProperties: false` (Draft 2020-12) en admission/start/termination-outcome, compatible con el `oneOf` discriminado; vectores de campo extra en cada una de las 6 alternativas |
| B3 | `format` presentado como comprobación garantizada | Documentado (spec §5.7, envelope/action-request schemas, contracts/README): `format: ektel-b64u-canonical` es formato privado y anotación en JSON Schema; requiere aserción explícita del consumidor; los parsers ektel lo asiertan (`bad_base64`) |
| B4 | Fuzz 959 no reproducible | Persistido: `scripts/fuzz_diferencial.py` determinista (semilla 20260820, corpus base = vectores versionados, clases cerradas, salida JSON) + gate permanente `tests/contract/test_fuzz_diferencial.py`; re-corrida: 986 mutaciones, 0 divergencias (§4.1) |
| B5 | Alcance de ADR-010 sobredimensionado | Precisión añadida (ADR-010 §6 + spec §6.5): cierra aliases de los mismos bytes; no afirma identidad entre serializaciones equivalentes (§7 de esta acta) |
| B6 | Independencia clean-room sin declarar | Declarada (§4.2, contracts/README, parser B): debilitada por corrección en el mismo ciclo por el mismo agente; acuerdo A/B = convergencia, no independencia; la independencia la restaura la re-verificación externa |

**Efecto colateral del fuzz versionado (B4):** la divergencia
`signature`-43 (§4.1) es un hallazgo nuevo que la métrica perecedera no
dejaba ver; evidencia de que el gate permanente era la corrección
correcta y no retirar la métrica.

## 9. Segundo FIX-AND-RETRY de Pinax (2026-08-20)

Mismo estado: sin commit, sin push, M0 abierto, sin rondas externas.
`CONTEXTO-RELEVO-2026-08-20.md` intacto y fuera del paquete.

### Reproducciones exactas ANTES de corregir (clase L, re-ejecutadas)

- **B7** (`execution-result` con `guarantees_applied[0].magnitude=""`):
  A=`reject/invalid_value` vs B=`accept/ok` (también con
  `assumptions` de 65): el parser A imponía minLength/maxItems que ni el
  schema ni B tenían.
- **B8** (`invocation-proof`, MAC de PoP vigente): `schema_version=2` →
  A=`invalid_value` vs B=`schema_version_unsupported` (divergencia);
  `0`/`-1` → ambos `unsupported` en documentos generales (mal
  clasificado: la regla los quiere como `invalid_value`).

### Correcciones aplicadas

| # | Bloqueante | Corrección |
|---|---|---|
| B7 | `guarantees_applied` desalineado | `execution-result.schema.json` alineado con `guarantee_plan`: `minLength: 1` en magnitude/platform/mechanism/failure_mode y `maxItems: 64` en assumptions/known_escapes; parser A conserva sus restricciones (ahora también en el schema y en B); 6 vectores negativos (`eres-invalid-empty-{magnitude,platform,mechanism,failure_mode}`, `eres-invalid-{assumptions,known-escapes}-65`) |
| B8 | `schema_version` no uniforme | Regla congelada y aplicada en ambos parsers: entero > 1 → `schema_version_unsupported` (pre-check de versión mayor, también en invocation-proof y en header/payload firmados); entero <= 0 → `invalid_value` (cae en la validación de valor, tras unknown/missing según precedencia §5.6); booleano → `invalid_value`. Vectores: `pop-invalid-version-{2,0,neg}`, `areq-invalid-version-{0,neg}`, `cap-invalid-header-version` (header sv=2 con MAC válida) |
| B9 | cobertura perecedera | Fuzz de BYTES conservado (70×17 = **1190** mutaciones; las 986 originales incluidas). Fuzz SEMÁNTICO: 19 clases, **517 mutaciones, 0 divergencias A/B** — ⚠️ conteo histórico de esta ronda, SUPERPUESTO por §10/B9.1: esas bases incluían vectores reject y carecían de oráculo; el conteo vigente y honesto es el de §10 (12 bases accept, 94 mutaciones con oráculo). El gate congela conteo exacto + fingerprint sha256 del corpus (`d399f950…52f0c`, 70 vectores) con prueba de SENSIBILIDAD a divergencia artificial |

### Correcciones documentales

- **Conteo de patterns corregido:** los schemas contienen **21 claves
  `pattern` auto-ancladas** (verificado por recorrido programático:
  21/21 con `^`…`(?![\s\S])`), no 31 — el 31 del reporte anterior contaba
  coincidencias de TEXTO en descripciones, no claves del schema.
- **Docstring del parser B corregido:** `schema_version: true` →
  `invalid_value` (decía `invalid_type`); coincide con el vector
  `areq-invalid-bool-version`.
- **Guía para validadores genéricos** (contracts/README + spec §5.7):
  registrar TODOS los schemas locales por `$id`; NO resolver
  `https://ektel.local` por red (dominio privado declarativo); registrar y
  asertar `ektel-b64u-canonical`.

### Prueba con validador genérico (jsonschema Draft 2020-12)

`scripts/validate_with_jsonschema.py` (versionado; herramienta externa,
NO dependencia del proyecto — se corrió con jsonschema 4.25.1 en un venv
efímero): los ONCE schemas pasan meta-validación Draft 2020-12; con
registro local por `$id` + format checker asertado, sobre los 70
vectores: **70 comprobados, 0 discrepancias, 22 skipped-by-design**
(gates de parser/cripto puros y defectos internos de payload firmado,
listados uno a uno por el script con su razón).

### Verificación final (re-corrida, clase L)

`git diff --check` limpio · suite 14 tests OK / 3 skips (separados abajo)
· regeneración diff cero vía `EKTEL_VECTORS_OUT` · 70/70 vectores con
acuerdo A/B total · fuzz bytes 1190/0 · fuzz semántico 517/0 ·
jsonschema genérico 0 discrepancias.

## 10. Tercer FIX-AND-RETRY de Pinax (2026-08-20)

Autorización limitada: sólo B9 y su documentación/pruebas. Sin commit, sin
push, M0 abierto, sin rondas externas. `CONTEXTO-RELEVO-2026-08-20.md`
intacto y fuera del paquete.

### Reproducción ANTES de corregir (defectos del propio fuzz B9)

- Las bases semánticas NO eran sólo accept: el fuzz semántico de la ronda
  anterior mutaba 67 vectores cualesquiera (incluidos rejects) y sin
  verificar que A/B aceptaran la base.
- Sin oráculo: sólo acuerdo A/B — un error común a ambos parsers pasaba
  inadvertido (demostrado en la prueba de sensibilidad nueva).
- `doc_missing` usaba `sorted(doc)[0]`: en `start_failed` eliminaba el
  discriminador `outcome` (→ invalid_value, no missing_field) y pudo
  haber eliminado campos opcionales.
- El validador externo clasificaba TODO defecto interno de sobre como
  "payload opaco" sin examinar capas; `alg_unsupported` no se comprobaba
  en el header.

### Correcciones aplicadas (B9.1/B9.2/B9.3)

| # | Corrección |
|---|---|
| B9.1 | `load_corpus` conserva `expect` (veredicto+diagnóstico); el fuzz semántico parte EXCLUSIVAMENTE de los 12 vectores accept; cada base se verifica contra A y B como `accept/ok` ANTES de mutar (cualquier fallo → `base_errors`, el gate falla). Conteos honestos: 12 bases, 94 mutaciones (el "517" de la ronda anterior queda retirado: mezclaba bases reject) |
| B9.2 | Oráculo por mutación: veredicto + diagnóstico + capa + clase; comprobación SEPARADA contra A y contra B, más el acuerdo diferencial. Matriz congelada: sv>1→`schema_version_unsupported`; sv 0/neg/bool→`invalid_value`; extra→`unknown_field`; requerido ausente→`missing_field`; patrón/minLength/maxItems→`invalid_value`. Campos deterministas por wire_type y alternativa (`DOC_REQUIRED`, `OUTCOME_REQUIRED`, etc.; NUNCA `sorted(doc)[0]`). MAC re-computada en sobres y PoP (causa única). Prueba de ERROR COMÚN: A y B saboteados con el mismo diagnóstico incorrecto (`schema_version_unsupported`→`invalid_value`) → acuerdo A/B intacto (0 divergencias), el ORÁCULO detiene el gate en A y en B. La prueba de divergencia artificial se conserva |
| B9.3 | `validate_with_jsonschema.py` estratificado: envelope → decodificación b64url canónica offline → protected-header → payload por wire type → documento; accepts exigen TODAS las capas; rejects visibles exigen rechazo en la capa esperada (`alg_unsupported` en header, verificado); skips sólo fuera de JSON Schema con razón individual (json-estricto ×2, bytes ×1, mac ×5, §6.9 exp>nbf ×1, typ↔wire_type ×1) |

### Resultados (clase L)

- Validador estratificado: 11 schemas meta-validados; 12/12 accepts
  válidos en todas las capas; rechazos por capa envelope=5, header=2,
  payload=9, documento=32 (33 tras la reclasificación de NaN, §10.1);
  10 skips razonados (9 tras §10.1); **0 discrepancias**.
- Fuzz semántico nuevo: 12 bases accept (0 errores de base), 94
  mutaciones, 0 divergencias A/B, **0 fallos de oráculo**.
- Fuzz bytes: 1190 mutaciones, 0 divergencias, fingerprint del corpus
  sin cambios (`d399f950…52f0c`).
- Suite: 16 tests OK / 3 skips Linux-only.

### Ronda adversarial (gate interno pre-reporte)

Revisión adversarial con agente fresco sobre el diff completo, con siete
blancos específicos (bases accept, matriz del oráculo, detección de
error común, MAC recompuestas, capas del validador, conteos congelados,
alcance M0). Acta íntegra de la ronda: §10.1.

#### §10.1 Acta de la ronda adversarial (agente fresco, 2026-08-20)

Blancos (7/7 NO REFUTADOS, con evidencia de ejecución propia): bases
semánticas accept filtradas y verificadas (12, gate falla vía
base_errors); matriz del oráculo con cadena de causa verificada por
clase contra ambos parsers y schemas (94×2 comprobaciones, 0 fallos);
detección de error común simulando el oráculo roto (el test FALLA sin
oráculo: no puede pasar por accidente); MAC recompuestas sin causas
secundarias (las mutaciones doc de PoP no tocan campos cubiertos por su
MAC; doc_missing elimina `mac` → missing_field antes de verificar);
validador externo 12/12 accepts en todas las capas y 0 discrepancias;
conteos/fingerprint coincidentes con ejecución real; alcance M0 limpio y
CONTEXTO-RELEVO intacto y excluido (mtime anterior al paquete).

Hallazgos de la ronda y fix-and-retry aplicado:
- **H1 (menor):** contracts/README decía «14 tests» (obsoleto: son 16).
  Corregido a 16.
- **H2 (menor):** el skip de `areq-invalid-nan` estaba mal clasificado:
  json.loads estándar PARSEA NaN y el schema SÍ lo rechaza (`float` no
  es `integer`). Reclasificado: el validador ahora comprueba ese vector
  (rechazo en capa documento; skips 10→9, documento 32→33).
  `duplicate_key` mantiene su skip con razón precisa (json.loads colapsa
  claves; el rechazo del schema sería por causas ajenas a la duplicación).
- **H3 (observación):** código muerto en parser B (condición imposible
  en el bucle de propiedades). Eliminado sin cambio conductual.

Observaciones aceptadas sin cambio: el validador no decodifica el sobre
anidado dentro de action-request (coherente con el modelo de capas: la
validación estructural del anidado es vía $ref, su payload b64 es opaco
para el schema); el skip typ↔wire_type es relativo a los artefactos
vigentes (header schema único con enum de 3 valores).

Veredicto de la ronda: `proceed` (sin bloqueantes). Tras el
fix-and-retry de H1-H3 se ejecutó una SEGUNDA ronda adversarial fresca
confirmatoria (§10.2).

#### §10.2 Segunda ronda adversarial (post fix-and-retry)

Agente fresco distinto, sobre los diffs regenerados tras H1-H3. H1/H2/H3
confirmados corregidos con evidencia de ejecución (suite 16/3, validador
documento=33/skips=9/0 discrepancias, condición imposible ausente en
parser B). Todos los gates re-ejecutados coinciden con lo declarado
(bytes 1190/0 + fingerprint íntegro; semántico 12/94/0/0/0; regen diff
cero; diff --check limpio). Alcance del fix verificado por mtime e
identidad de diffs: sólo los cuatro archivos declarados (contracts/README,
validador, parser B, acta). CONTEXTO-RELEVO intacto y ausente de los
diffs (las tres menciones en el acta son textuales, no inclusión).
Observaciones sin impacto: la acreditación de no-colateralidad es por
mtime + identidad regenerada (el diff byte-exacto de la ronda 1 no se
conservó aparte). Veredicto: **`proceed`** (sin hallazgos menores ni
bloqueantes).

## 11. Corrección contractual H1–H3 + P1 (2026-08-21)

Orden: FIX-AND-RETRY limitado a hallazgos confirmados. Sin commit, sin
push, sin rondas externas oficiales, sin M1+, sin dependencias nuevas.
`CONTEXTO-RELEVO-2026-08-20.md` permanece separado del paquete; sus
conteos se corrigen en `ADDENDA-CONTEXTO-RELEVO-2026-08-21.md` (P1),
que declara el relevo evidencia operativa no normativa y reafirma que
la autorización de commit/push procede del dueño por operación.

### Reproducciones (antes → después, clase L)

- **H1**: la spec §5.2 decía "el receptor verifica antes de decodificar"
  con el base64 estricto como "defensa en profundidad", mientras ambos
  parsers ya rechazaban el alias no canónico ANTES del MAC; y §5.2
  ordenaba "localizar signature → verificar MAC → decodificar" sin el
  paso base64 explícito. → §5.2 ahora congela los cuatro pasos
  (estructura exterior → base64url estricto+canónico como test de
  pertenencia SIN interpretar JSON → MAC sobre cadenas ASCII →
  interpretación semántica), con la canonicalidad como **precondición de
  admisión**; §5.5 explicita `bad_base64` antes de `bad_signature`
  (paso 2 → paso 3). Vector nuevo `cap-invalid-noncanon-header`
  (protected_header_b64 alias no canónico de los mismos bytes, MAC
  VÁLIDA recalculada) → reject/bad_base64 en A y B (junto al existente
  `cap-invalid-noncanon-payload`, mismo principio en payload).
- **H2**: `accept` no tenía semántica congelada; action-request podía
  leerse como que "valida" los anidados. → spec §5.8 nueva: accept =
  aceptación del parser para el wire type, nunca autorización/admisión;
  envelopes y PoP como objeto superior SÍ verifican cripto; action-request
  M0 valida sólo estructura exterior; firma/PoP/replay/coherencia
  anidados = M1. Vectores `areq-valid-nested-{badmac,badpop,cmd-mismatch}`
  congelan accept/ok consciente (sin campos nuevos: regla del parser).
- **H3**: `execution-result` tenía opcionalidad excesiva (cause_code y
  toda la evidencia opcionales en todos los estados). → unión por state
  vía `allOf/if/then` (schema), `_check_execution_result_state` (parser
  A) e intérprete `if/then` (parser B): executed=natural_exit + tiempos
  + truncación; deadline_exceeded∈{deadline_duration,
  deadline_validity_exhausted} + tiempos; terminated=external_termination
  + tiempos; supervision_failed=supervision_failure SIN tiempos (rama
  propia: evidencia posiblemente inexistente). **Decisión
  `discarded_bytes` (autorizada por el encargo): alternativa (a) —
  siempre presente, 0 cuando no hubo truncación** — factible en todos
  los estados, schema plano, testeable. Nueve vectores nuevos (3 accept
  + 6 reject: sin tiempos, causa incompatible ×3, sin cause_code, sin
  discarded_bytes).

### Corpus y gates tras la corrección

83 vectores (7 grupos) · suite 16 OK / 3 skips Linux-only · regeneración
diff cero (`EKTEL_VECTORS_OUT`) · acuerdo A/B 83/83 · fuzz bytes 1411/0
(fingerprint congelado `cbed3298…618b5`) · fuzz semántico 18 bases
accept / 148 mutaciones / 0 divergencias / 0 oráculo / 0 errores de base
· validador externo estratificado: 0 discrepancias. Reproducciones
individuales H1/H2/H3: todas OK (script del reporte, clase L).

### Ronda adversarial fresca (pre-reporte)

Ver §11.1.

### §11.1 Ronda adversarial fresca (2026-08-21) y cierre

Revisor independiente (subagente de contexto fresco, primera exposición),
diffs completos + código + spec leídos, gates y reproducciones ejecutados
por el revisor. **9/9 blancos NO REFUTADOS**: (1) coherencia literal
§5.2/§5.6 — orden de 4 pasos consistente y ejecutado exactamente por A y
B; (2) precedencia inequívoca — MAC de ambos vectores no canónicos
re-validada independientemente por el revisor (válida; el único motivo de
rechazo es la canonicalidad), cap-invalid-mac → bad_signature; (3) accept
≠ autorización (§5.8 expresa; cero campos wire nuevos en el diff de
schemas); (4) frontera M0/M1 congelada con citas explícitas; (5)
evidencia por estado suficiente y obtenible (supervision_failed sin
tiempos, verificado); (6) cause_code compatible + requerido global;
(7) alcance contenido (21 M + untracked del paquete; sin src/, CI ni
dependencias); (8) relevo separado (diff vacío; ADDENDA lo declara no
normativo); (9) gates reproducidos uno a uno con conteos idénticos
(16/3, 83, diff cero, 1411/0 + fingerprint, 18/148/0/0/0, validador
11·18/18·6-2-9-39·9 skips·0). Veredicto: **`PROCEED`**.

Fix-and-retry posterior sobre los hallazgos menores del revisor:
H1-R (referencias cruzadas "§5.5"→"§5.6" en docstrings de A y B — la
precedencia es el punto 6 de §5); typos "asiertan/asierte"→"asertan/
aserte" (spec §5.7, envelope/action-request schemas, contracts/README).
Observaciones aceptadas sin cambio: la nota de briefing del vector
cap-invalid-mac (vive en capability-envelope.vectors.json, no en
correccion-m0); el re-anclaje de patterns/format de rondas previas en el
diff de action-request (mismo worktree, cero campos nuevos); la longitud
≠ 43 de signature cae como invalid_value en "estructura del sobre" —
decisión deliberada documentada en el código (hallazgo del fuzz),
pendiente de asiento literal en una futura acta si se requiere.

Estado final: **PROCEED** sobre el artefacto final. Sin commit, sin
push, M0 abierto y sin rondas externas oficiales.

## 12. Asiento normativo: signature con longitud distinta de 43 (gate externo, 2026-08-21)

Una `signature` cuya longitud no sea **43 caracteres** canónicos se
rechaza como **`invalid_value`**, ANTES de cualquier verificación de
MAC. **Precisión de ubicación (corrección H4 del gate Claude,
2026-08-21; el asiento original la situaba exclusivamente en el "paso 1:
estructura exterior" de §5.2, lo cual es impreciso):** los tres campos
del sobre se validan **por campo, en el orden declarado por el schema**
(`protected_header_b64` → `payload_b64` → `signature`), y en cada campo
se aplican sus chequeos propios — patrón/longitud (→ `invalid_value`) y
alfabeto/canonicalidad (→ `bad_base64`) — TODO ello antes del MAC. En
solitario, `signature` ≠ 43 chars → `invalid_value`. En el **caso
compuesto** (header no canónico + firma de longitud inválida) gana el
**primer campo ofensivo en el orden del schema**: como
`protected_header_b64` precede a `signature`, el resultado es
`bad_base64` (congelado por el vector `cap-invalid-noncanon-header-sig44`). Esa clasificación es **deliberada** y forma parte
de la precedencia vigente (§5.6: estructura → `bad_base64` →
`bad_signature` → header → payload): una firma HMAC-SHA256 (32 bytes)
mide exactamente 43 caracteres en base64url sin padding, de modo que
otra longitud no es una firma degenerada sino **estructura inválida** —
y produce `invalid_value`, no `bad_signature`. **No es un resultado
accidental de uno de los parsers**: los tres coinciden por construcción
— `envelope.schema.json` fija el patrón `^[A-Za-z0-9_-]{43}(?![\s\S])`,
el parser A impone `exact: 43` en su tabla de campos y el parser B
interpreta el patrón del schema. Congelado por el vector
`cap-invalid-sig-len-44` (44 chars canónicos = 33 bytes →
reject/`invalid_value` en A y B, con MAC no verificada por precedencia).
Conteos derivados actualizados: corpus **84** vectores; fuzz bytes
**1428** mutaciones, fingerprint
`694c7339c7eeac737ba94a4a38c2d0dc83ef80271bc32c80860fe1d71bd6387b`;
fuzz semántico sin cambios (18 bases accept / 148 mutaciones).

## 13. M0-FAR-CLAUDE-01 — fix-and-retry tras el gate Claude (2026-08-21)

Veredicto Claude: FIX-AND-RETRY (2 bloqueantes, 3 menores, 1 observación;
informe congelado en el dossier efímero del gate). **Toda edición de esta
sección invalidó el PROCEED previo de Codex y el veredicto previo de
Claude**; ambas rondas se repitieron sobre el manifest final. Los cinco
hallazgos sustantivos fueron reproducidos localmente ANTES de corregir y
verificados DESPUÉS:

| # | Defecto (reproducción antes) | Corrección (después) |
|---|---|---|
| H1 bloqueante | `start-outcome` con `outcome:[]` → A: `TypeError: unhashable type: 'list'`; B: `reject/invalid_value` | `_parse_union` valida el tipo del discriminador antes de usarlo como clave; list/dict/set/bytearray → `invalid_value` (enum-only, sin tipo declarado). Vector `sout-invalid-disc-list`. Ahora: A=B=`reject/invalid_value` |
| H2 bloqueante | `requested_guarantees:[1]` → A: `invalid_type`; B: `invalid_value` (enum antes que type) | `check()` de B evalúa `type` antes que `const`/`enum` en todos los caminos. Vector `areq-invalid-guarantees-type`. Ahora: A=B=`invalid_type` (§5.6) |
| H3 menor (error común) | header `typ:1` con MAC válida → A=B=`invalid_value` (ambos mal) | A: enums con tipo declarado (`vt`) comprueban tipo primero (sólo `typ`, único type+enum del repo); B: ya por H2. Vector `cap-invalid-header-typ-int` + clase de oráculo `header_typ_int`. Ahora: A=B=`invalid_type` |
| H4 menor | acta §12 ubicaba sig≠43 exclusivamente en "paso 1 estructura exterior"; compuesto header-no-canónico+sig-44 daba `bad_base64` | §12 y §5.6 reescritos: validación del sobre **por campo en orden de schema**, patrón/longitud→`invalid_value` y alfabeto/canonicalidad→`bad_base64` por campo, todo antes del MAC; compuesto gana el primer campo ofensivo. Vector `cap-invalid-noncanon-header-sig44` → `bad_base64` |
| H5 menor | `/bin/e\rcho` y `/bin/e\u2028cho` → A=B=`accept/ok` (`.` de Python no excluye CR/U+2028/2029; ECMA-262 sí) | Patrones de `command_absolute`/`cwd` (ambos schemas + parser A) con **clase negada explícita** `[^\r\n\u2028\u2029]`; §5.7 congela la semántica independiente del motor para las cuatro clases. Vectores `areq-invalid-cmd-{cr,u2028}`. Ahora: A=B=`reject/invalid_value` |

**Fortalecimiento del oráculo (obligatorio)**: nuevas clases
deterministas de confusión de tipos — `doc_disc_type_confusion`
(discriminador=[] sobre 5 bases outcome), `doc_enum_item_type`
(guarantees=[1] sobre 4 bases), `header_typ_int` (MAC re-computada, 4
bases), `doc_const_type` (state=1, enum-only, 4 bases). El harness
captura excepciones de cualquier parser (`_safe_parse`): crash = fallo
de oráculo, nunca se propaga ni se ignora; también en fuzz de bytes.
Pruebas de sensibilidad artificiales para las tres situaciones:
divergencia A/B (preexistente), **error común A/B sobre la clase nueva**
(invalid_type→invalid_value sabotaje doble: el acuerdo A/B no lo ve, el
oráculo sí) y **crash** (parser que lanza RuntimeError: el gate reporta
CRASH). La lista histórica 307/79 sigue declarada NO recuperable; no se
inventó ni reconstruyó.

**H6 — deuda explícita (NO resuelta en M0)**: `stdin_policy` NO es unión
discriminada: `{"kind":"inline_b64"}` sin `data_b64` es accept hoy;
`kind:"empty"` con `data_b64`/`sha256` también. Razón: M0 congela los
wire contracts como están; imponer dependencia de campos por `kind`
exigiría enmendar §8.1/spec y regenerar contratos ya gateados — es
superficie de la **admisión M1**, que decide qué hace el núcleo con el
stdin antes de spawn. Condición de entrada: orden del dueño + acta de
enmienda al diseñar el admission parser M1 (o ADR propio si se quiere
antes). No se crea unión, ni campos wire nuevos, ni se presenta como
contrato resuelto.

Conteos finales del intento: corpus **90** vectores/7 grupos; fuzz bytes
**1530/0** (fingerprint
`1c8412fec52ea6a457397a1f8a55c86bcc4503728ff2e3da882f6ffe640ddd89`);
fuzz semántico **18 bases accept / 165 mutaciones / 0 divergencias / 0
oráculo / 0 errores de base**; suite **18 tests** (3 skips Linux-only);
validador estratificado 11 schemas · 18/18 accepts · envelope=8 header=3
payload=9 documento=43 · 9 skips · 0 discrepancias.

### §13.1 Ronda adversarial interna (pre-oficial) y cierre del intento

Revisor fresco (subagente): 654 corridas hostiles propias + 2730
mutaciones tipadas re-MACadas + 65 combos cross-field. H1–H5, gates,
alcance y congelados verificados sin hallazgos. **Un bloqueante**
(encontrado también como error común): `RecursionError` con JSON
anidado profundo (~16 500 niveles, 33 KB **dentro** del techo de 64
KiB) en los 9 wire types y ambos parsers — `json.loads` del stdlib
lanza `RecursionError` (no `ValueError`), que escapaba de la capa de
JSON estricto; también alcanzable dentro del protected header de un
sobre con MAC válida. **Fix aplicado**: captura explícita de
`RecursionError` en `_strict_loads` (A) y `strict_json` (B) →
`malformed_json` fail-closed; asiento normativo en §5.1 de la spec
(profundidad excesiva → malformed_json, sin excepción propagada); test
permanente `tests/contract/test_deep_json.py` (documento profundo en 4
wire types × ambos parsers + header firmado profundo con MAC válida).
Observaciones aceptadas sin cambio (menores): orden intra-campo
(canonicalidad vs longitud dentro del mismo campo) no asentado
expresamente — A=B hoy, superficie de divergencia futura entre
implementaciones independientes; `1e400` (overflow numérico) cae en
vocabulario (invalid_type/invalid_value) sin asiento específico en
§5.1. Suite tras el fix: **20 tests** (3 skips). Corpus y conteos del
fuzz SIN cambios (90/1530/18/165; el gate de profundidad vive en test
propio, no engorda el corpus).
