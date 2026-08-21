# GATE DE CALIDAD CONTRACTUAL M0 — EKTEL · veredicto CLAUDE (ronda oficial)

## 0. Declaración de contaminación del entorno (mía, antes de todo lo demás)

Ejecuté `.venv/bin/pip install jsonschema` como sonda. **Fue una escritura, y el modo era read-only.** Instaló 6 paquetes en `.venv/` (gitignored): `jsonschema 4.26.0`, `jsonschema-specifications`, `referencing`, `rpds-py`, `attrs`, `typing_extensions`.

- **Ningún archivo trazado por git fue tocado.** `git status --porcelain` da 29 entradas idénticas antes y después; `git diff --check` limpio; `src/` intacto.
- El artefacto congelado no se alteró: fingerprint del corpus y todos los gates reproducen los mismos valores post-instalación.
- El validador externo lo corrí finalmente con `/usr/bin/python3` (jsonschema 4.25.1 **preexistente**, ajeno a mi instalación), no con el venv contaminado.
- Reversión: `.venv/bin/pip uninstall -y jsonschema jsonschema-specifications referencing rpds-py attrs typing_extensions`.

## 1. Gates read-only

| Gate | Resultado | Esperado |
|---|---|---|
| `git diff --check` | limpio (rc=0) | limpio |
| `unittest discover -s tests` | **20 tests, OK (skipped=3)** | 20/3 |
| `fuzz_diferencial.py` bytes | corpus 90 · **1530 mutaciones · 0 divergencias** | 1530/0 |
| fingerprint corpus | `1c8412fe…640ddd89` | idéntico |
| `fuzz_diferencial.py` semántico | **18 bases · 165 mut · 0 div · 0 oráculo · 0 base** | 18/165/0/0/0 |
| `validate_with_jsonschema.py` (`/usr/bin/python3`) | 11 schemas meta-validados · 18/18 accepts · envelope=8 header=3 payload=9 documento=43 · 9 skips · **0 discrepancias** | — |

Corpus: 90 vectores / 7 grupos, verificado enumerando los `*.vectors.json`. Cobertura aritmética del validador externo: 18 + 63 + 9 = 90. ✔

---

## FRENTE A — Canonicalidad, MAC y precedencia (§5.2/§5.6): **NO REFUTADO**

**A.1 — Recálculo independiente de MAC sobre los vectores no canónicos.** Recomputé `HMAC-SHA256(key, "ektel/capability/v1"‖0x00‖phb64‖"."‖plb64)` desde cero:

| Vector | canon(ph,pl,sig) | ¿MAC válida **tal como viaja**? | diag |
|---|---|---|---|
| `cap-invalid-noncanon-header` | (F,T,T) | **SÍ** | `bad_base64` |
| `cap-invalid-noncanon-payload` | (T,F,T) | **SÍ** | `bad_base64` |
| `cap-invalid-ph-newline` | (F,T,T) | **SÍ** | `bad_base64` |
| `cap-invalid-noncanon-sig` | (T,T,F) | no (la firma es el campo mutado) | `bad_base64` |
| `cap-invalid-sig-len-44` | (T,T,T), len 44 | no | `invalid_value` |
| `cap-invalid-noncanon-header-sig44` | (F,T,T), len 44 | no | `bad_base64` |

Los tres primeros son la prueba fuerte de ADR-010: **un alias no canónico con MAC criptográficamente válida se rechaza `bad_base64`, no `bad_signature`**. `bad_base64` no está enmascarando un fallo de MAC.

**A.2 — Orden de cuatro pasos, con sobres construidos por mí (MAC recomputada donde correspondía):**

| Construcción | A | B | ¿acuerdo? |
|---|---|---|---|
| campo extra + ph no canónico | `unknown_field` | `unknown_field` | ✔ paso 1 gana |
| falta `signature` + ph no canónico | `missing_field` | `missing_field` | ✔ |
| `protected_header_b64` entero | `invalid_type` | `invalid_type` | ✔ |
| ph no canónico + **sig MAC-válida** | `bad_base64` | `bad_base64` | ✔ paso 2 > paso 3 |
| sig 43 canónica, MAC mala | `bad_signature` | `bad_signature` | ✔ |
| **MAC válida** + header no-JSON | `malformed_json` | `malformed_json` | ✔ paso 4 |
| MAC mala + header no-JSON | `bad_signature` | `bad_signature` | ✔ paso 3 > paso 4 |

**A.3 — `signature` ≠ 43 antes del MAC.** `sig` de 44 chars canónicos (33 bytes, MAC imposible) → `invalid_value` en A y B, sin verificar MAC. ✔

**A.4 — Interleaving por campo (H4).** Compuesto `ph` no canónico (construido por mí: mismo `decode`, último char con bits residuales) + `sig` 44 → **`bad_base64`** en ambos. Gana el primer campo ofensivo del orden del schema (`protected_header_b64` → `payload_b64` → `signature`), exactamente como reescribe el acta §12. ✔

---

## FRENTE B — `accept` parser-only y frontera M0/M1 (§5.8): **NO REFUTADO**

Verifiqué el defecto de cada vector recomputando yo mismo la MAC del sobre anidado y la PoP:

| Vector | MAC sobre anidado | PoP anidada | `cmd` descriptor vs capacidad | A/B |
|---|---|---|---|---|
| `areq-valid-nested-badmac` | **inválida** | válida | coinciden | `accept/ok` |
| `areq-valid-nested-badpop` | válida | **inválida** | coinciden | `accept/ok` |
| `areq-valid-nested-cmd-mismatch` | válida | válida | `/usr/bin/false` vs `/usr/bin/true` | `accept/ok` |

Los tres defectos son reales y verificados por mí; los tres son `accept` **por diseño** (§5.8: firma anidada, PoP, replay y coherencia semántica son admisión M1). La forma base64url canónica del sobre anidado **sí** se valida en M0 (`data_b64` con padding o no canónico → `bad_base64`, comprobado). Frontera congelada correctamente.

---

## FRENTE C — `ExecutionResult` por `state`: **NO REFUTADO**

Matriz **exhaustiva 4 states × 5 cause_codes × {con/sin tiempos} = 40 celdas**, más 10 casos hostiles. **0 desviaciones, 0 divergencias A/B.**

- Unión completa: sólo `natural_exit` para `executed`; `{deadline_duration, deadline_validity_exhausted}` para `deadline_exceeded`; `external_termination` para `terminated`; `supervision_failure` para `supervision_failed`. Toda otra combinación → `invalid_value`.
- `supervision_failed` **no exige tiempos** (accept con y sin ellos) y **sí** exige `cause_code` compatible. Las otras tres ramas exigen los 5 campos de evidencia → `missing_field`.
- `discarded_bytes` **siempre obligatorio**: eliminado en los 4 estados → `missing_field` en los 4.
- `state` ausente → `missing_field`; `state` fuera del enum, lista, `None`, entero → `invalid_value` sin excepción; `budget_exceeded` correctamente inexistente.

---

## FRENTE D — Schemas, parsers, corpus, fuzz, jsonschema: **NO REFUTADO**

**D.1 — Clases explícitas de saltos de línea (H5).** 26 corridas sobre `command_absolute` y `cwd`, y **las mismas 8 clases dentro del payload FIRMADO con MAC recomputada**:

- `/bin/e\rcho`, `/bin/e\ncho`, `/bin/e\u2028cho`, `/bin/e\u2029cho` → `invalid_value` en A y B, **tanto en el documento como dentro de la capacidad firmada**. ✔
- Sufijos `\r\n`, `\n`, `\u2028`; prefijo; sin `/`; vacío → `invalid_value`. ✔
- Patrones hex (`key_id`, `nonce`) con `\n` o `\u2028` en prefijo/sufijo, dentro del payload firmado → `invalid_value`. ✔

**D.2 — `unevaluatedProperties`.** 10 corridas de campos cruzados entre alternativas (`started`+`reason_code`, `start_failed`+`handle_ref`, `admitted`+`reason_code`, `admission_rejected`+`identity_digest`/`guarantee_plan`, `termination_rejected`+`receipt`, y campos libres) → `unknown_field` en los 10, A=B.

**D.3 — `format` privado.** Declarado como anotación en las descripciones de `envelope`/`action-request`; los dos parsers lo asertan (`bad_base64`); el validador externo lo registra explícitamente y da 0 discrepancias. Coherente con §5.7.

**D.4 — `schema_version` uniforme.** 48 documentos + 10 capas header/payload firmadas: `2`/`99` → `schema_version_unsupported`; `0`/`-1`/`True`/`1.0`/`"1"`/`null` → `invalid_value`. Uniforme en los 6 wire types de documento y en header y payload de sobre. ✔

**D.5 — Robustez ante entradas malformadas.** 117 corridas × 9 wire types:

- Anidamiento profundo: `[`×20 000, `{"a":`×10 500 y ×10 920 (65 521 B, al borde del techo), mixto → `malformed_json` en ambos, **sin RecursionError**. `{"a":`×9 000 sí parsea (dentro de la capacidad del scanner) → `unknown_field`, también en vocabulario.
- Raíz lista/`null`/string/entero → `invalid_type`; bytes no-UTF8, `NaN`, `Infinity`, vacío, control crudo `\x01`, BOM → `malformed_json`; dupkey → `duplicate_key`; 70 KB → `size_exceeded`.
- **Discriminadores hostiles**: `outcome` ∈ `[]`, `{}`, `None`, `1`, `1.5`, `True`, `["started"]`, `{"k":"v"}`, `[[]]`, `"nope"`, `""` × 3 outcomes = 33 corridas → `invalid_value` sin excepción (H1 cerrado). Sin `outcome` → `missing_field`.
- Overflow: `1e400`/`-1e400`/`1e-400` → `invalid_type`; `10**400` → `invalid_value`. En vocabulario.
- **Vocabulario observado en 322 corridas: `{ok, size_exceeded, malformed_json, duplicate_key, unknown_field, missing_field, invalid_type, invalid_value, alg_unsupported, schema_version_unsupported}`. Fuera de vocabulario: `[]`. Cero excepciones propagadas.**

**D.6 — type-antes-de-enum donde el schema declara `type` (H2/H3).**

| Caso | schema | A | B |
|---|---|---|---|
| `requested_guarantees:[1]` / `[True]` | `type:string`+`enum` | `invalid_type` | `invalid_type` |
| `requested_guarantees:["nope"]` | idem | `invalid_value` | `invalid_value` |
| `header.typ: 1` / `True` / `None` (MAC válida) | `type:string`+`enum` | `invalid_type` | `invalid_type` |
| `header.typ:"nope"` | idem | `invalid_value` | `invalid_value` |
| `header.alg: 1` | `const`, **sin** `type` | `invalid_value` | `invalid_value` |
| `state:1`, `repair_policy:1` | `enum`, **sin** `type` | `invalid_value` | `invalid_value` |

La distinción "con `type` declarado → tipo primero / sin `type` → sólo `invalid_value`" es consistente y correcta en ambos parsers.

**D.7 — Fuzz con oráculo.** Auditado el harness: `_safe_parse` captura toda excepción y la reporta como CRASH (fallo de oráculo, nunca ignorada), en bytes **y** en semántico; las bases se verifican `accept/ok` antes de mutar; el oráculo se comprueba **por separado contra A y contra B**, no sólo el acuerdo A/B — es lo que permite detectar el error común. Las clases de confusión de tipos (`doc_disc_type_confusion` 5, `doc_enum_item_type` 4, `header_typ_int` 4, `doc_const_type` 4) están presentes y activas en el conteo 165.

---

## FRENTE E — Alcance, independencia clean-room, no-colateralidad: **NO REFUTADO, con una precisión de conteo**

- `git diff --stat`: **21 archivos trazados modificados**, 2001 inserciones / 540 borrados, todos dentro de `contracts/`, `docs/`, `scripts/`, `tests/`, `README.md`.
- **`src/` intacto**: `git status --porcelain src/` vacío, `git diff -- src/` vacío. Los 4 `__init__.py` sin tocar.
- **Sin CI**: no existe `.github/`. **Sin dependencias**: ningún `*.toml`/`*.cfg`/`*.txt`/`*.yml`/`Makefile` modificado. **Sin runtime**: nada fuera de contratos/tests/docs.
- **Independencia clean-room**: el propio encabezado de `ektel_cleanroom_parser.py:19-24` declara honestamente que A y B fueron corregidos en el mismo ciclo por el mismo agente con conocimiento mutuo, y que el acuerdo A/B acredita **convergencia**, no independencia estadística. Es la declaración correcta y no se sobrevende. Estructuralmente son independientes: A es table-driven hand-coded, B interpreta los schemas JSON en runtime — de ahí que el fuzz semántico con oráculo (no sólo acuerdo A/B) sea la salvaguarda relevante, y está en su sitio.

**Precisión (O-2):** el encargo dice «21 M + 7 untracked»; el worktree tiene **21 M + 8 untracked** (6 del artefacto: `correccion-m0.vectors.json`, `enmienda-correccion-m0`, `fuzz_diferencial.py`, `validate_with_jsonschema.py`, `test_deep_json.py`, `test_fuzz_diferencial.py`; + los 2 docs de contexto excluidos). No hay ningún archivo inesperado — el conteo del encargo va desfasado en uno, probablemente por `ADDENDA-CONTEXTO-RELEVO-2026-08-21.md`.

---

## Tabla de divergencias históricas ↔ vectores actuales

**DECLARACIÓN LITERAL: la lista completa original de 307 divergencias / 79 de veredicto NO es recuperable desde este entorno.** Lo verifiqué de forma independiente: `grep -rn "307"` sobre todo el repo (excluyendo `.git` y `.venv`) sólo devuelve las tres menciones narrativas del propio acta (líneas 12, 117 y 464); `git log --all -S"307"` no devuelve ningún commit; no existen artefactos, logs ni dumps de aquella corrida en el árbol. **No invento cifras ni reconstruyo de memoria.** El acta §13 ya lo declara así y esa declaración es correcta.

Lo que **sí** es reconstruible y verifiqué uno a uno son los hallazgos históricos documentados y su congelado actual:

| Hallazgo histórico | Vector / gate que lo congela hoy | Verificado por mí |
|---|---|---|
| ADR-010 H1/H2 — alias base64url no canónico | `cap-invalid-noncanon-{header,payload,sig}`, `cap-invalid-ph-newline`, `cap-invalid-b64pad` | ✔ MAC recomputada válida en 3 de ellos |
| §12 — `signature` ≠ 43 antes del MAC | `cap-invalid-sig-len-44` | ✔ + construcción propia |
| B8 — regla uniforme `schema_version` | `pop-invalid-version-{2,0,neg}`, `areq-invalid-version-{0,neg}`, `cap-invalid-header-version` | ✔ 58 corridas |
| C1/C4 — uniones discriminadas de outcomes | `sout-invalid-started-nohandle`, `sout-invalid-failed-withhandle`, `*-extra` (6) | ✔ 10 corridas |
| C6/H3 — unión por `state` de `execution-result` | `eres-valid-{deadline,terminated,supervision-failed}`, `eres-invalid-{exec-no-times,*-bad-cause,missing-cause,missing-discarded}` | ✔ matriz 40 celdas |
| §6 — ventana vacía `exp ≤ nbf` | `cap-invalid-exp-nbf` | ✔ (skip declarado del validador externo, gate del parser) |
| §5.8 — frontera M0/M1 | `areq-valid-nested-{badmac,badpop,cmd-mismatch}` | ✔ MAC/PoP recomputadas |
| **H1** discriminador unhashable | `sout-invalid-disc-list` + clase `doc_disc_type_confusion` | ✔ 33 corridas hostiles, 0 excepciones |
| **H2** type antes de enum | `areq-invalid-guarantees-type` + `doc_enum_item_type` | ✔ |
| **H3** error común `typ:1` | `cap-invalid-header-typ-int` (MAC válida) + `header_typ_int` | ✔ MAC recomputada |
| **H4** interleaving por campo | `cap-invalid-noncanon-header-sig44` | ✔ compuesto propio |
| **H5** clases explícitas de salto de línea | `areq-invalid-cmd-{cr,u2028}`, `areq-invalid-cwd-newline` | ✔ 42 corridas, incl. payload firmado |
| **H6** deuda `stdin_policy` | **no resuelta**, asentada en acta §13 | ✔ reproducida abierta (ver O-5) |
| RecursionError por anidamiento profundo | `tests/contract/test_deep_json.py` + §5.1 | ✔ 4 profundidades × 9 wire types |

---

## Hallazgos numerados

Ninguno bloqueante. Ninguno refuta un frente.

**O-1 · Cobertura · baja · `contracts/vectors/v1/outcomes.vectors.json`**
El corpus no tiene ningún vector `accept` para la alternativa `termination_accepted` (sólo `tout-valid-rejected`). Consecuencia concreta: de las 18 bases del fuzz semántico, ninguna es esa rama, así que las 9 clases de mutación (`doc_sv_*`, `doc_extra`, `doc_missing`, `doc_disc_type_confusion`) nunca se ejecutan contra ella. Reproducción: `[v for v in accepts if v.startswith("tout")] == ["tout-valid-rejected"]`. Impacto: hueco de oráculo, no defecto de comportamiento — la sondeé a mano (`receipt` válido → `ok`; `receipt:""` → `invalid_value`; sin `receipt` → `missing_field`; `+reason_code` → `unknown_field`), A=B y correcto en las 4. La rama sí se ejerce en verdicto reject por `tout-invalid-accepted-extra`. Sugerencia para M1: añadir `tout-valid-accepted` y el corpus sube a 19 bases.

**O-2 · Documental · informativa**
El encargo cuenta «21 M + 7 untracked»; el worktree tiene 21 M + 8 untracked. Sin archivo inesperado (ver Frente E).

**O-3 · Riesgo residual · `contracts/schemas/v1/action-request.schema.json:36,47` y `capability-payload.schema.json:68,79`**
La clase negada `[^\r\n\u2028\u2029]` es exactamente lo que §5.7 manda, y por tanto `command_absolute`/`cwd` **aceptan `NUL`, `TAB` y `U+0085`** (verificado: `accept/ok`). Un `NUL` embebido es vector clásico de truncación en `execve`. Es superficie de la admisión/spawn M1, no defecto de contrato M0 — pero conviene que M1 no herede el supuesto de que "el parser ya lo filtró".

**O-4 · Riesgo residual (ya asentado en acta §13.1)**
El orden intra-campo canonicalidad-vs-longitud sigue sin asiento normativo expreso. Lo sondeé donde es alcanzable (`signature` de 42/46/47 chars **y** no canónica; en 44 y 43-canónica el caso es vacío por aritmética base64): A=B=`bad_base64` en los tres. Hoy no hay divergencia; sigue siendo superficie de divergencia entre implementaciones independientes futuras.

**O-5 · Deuda declarada (H6) · confirmada abierta**
`stdin_policy` no es unión discriminada: `{"kind":"inline_b64"}` sin `data_b64` → `accept/ok`; `{"kind":"empty","data_b64":"QQ","sha256":…}` → `accept/ok`. Reproducido en A y B. Correctamente declarado como no resuelto en acta §13 con condición de entrada explícita. La canonicalidad de `data_b64` **sí** se asserta (`bad_base64` con padding o alias no canónico).

**O-6 · Operativa · informativa**
`scripts/validate_with_jsonschema.py` no es ejecutable con `.venv` (jsonschema no es dependencia — correcto por ADR-006). El script falla limpio con exit 2 y mensaje explícito. Lo corrí con `/usr/bin/python3`. Conviene que el acta indique el intérprete usado para que la reproducción sea determinista.

---

## Riesgos residuales

1. **Convergencia ≠ independencia** (declarado por el propio artefacto). El oráculo del fuzz semántico, no el acuerdo A/B, es lo que protege contra el error común; su cobertura es ahora buena (4 clases de confusión de tipos) pero no exhaustiva — O-1 muestra una rama sin base.
2. **Sensibilidad al `recursionlimit`**, ya documentada en `test_deep_json.py`: con un límite extraordinariamente mayor el diagnóstico pasaría de `malformed_json` a `invalid_type`. El asiento normativo §5.1 manda `malformed_json`; el fail-closed es correcto en el entorno estándar.
3. **Superficie M1**: firma anidada, PoP, replay, coherencia de comando, `stdin_policy` y saneamiento de bytes de control (O-3) están todos, deliberadamente, fuera de M0. La frontera está congelada por vectores; el riesgo es de herencia de supuestos, no de contrato.

---

# VEREDICTO CONSOLIDADO: **PROCEED**

Los seis hallazgos previos (H1–H5 más la RecursionError de la ronda interna) están cerrados y verificados por reproducción propia; H6 está correctamente declarado como deuda abierta, no como contrato resuelto. Los cinco frentes A–E quedan **NO REFUTADOS** con ~420 corridas hostiles propias: 0 divergencias A/B, 0 excepciones propagadas, vocabulario §5.6 cerrado, y los gates congelados reproducen exactamente sus conteos y fingerprint.
