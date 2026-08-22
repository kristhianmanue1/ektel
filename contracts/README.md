# contracts/ — wire schemas v1, vectores dorados y parsers de referencia (M0)

**Estado:** API **experimental** (spec v1.2 §16), sin compromiso de
estabilidad. M0 está cerrado a nivel contractual y publicado: doble PROCEED
externo (Codex y Claude sobre el mismo MANIFEST-ROOT `sha256:47302f74…`),
cierre registrado en `fba5a35` y evidencia durable en
`docs/revisiones/2026-08-21-m0-gate-final/` (commit
`ecfde79818e74c358a515e43590106e20e013cfd`). M1, M2 y M3 no están
autorizados.

**Fuente normativa:** `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2,
adoptada 2026-08-20). Autorización: `docs/decisiones/autorizacion-m0-2026-08-20.md`.

## Contenido

- `schemas/v1/` — wire schemas v1 (JSON Schema Draft 2020-12, subconjunto
  estricto). Los sobres firmados comparten `envelope.schema.json` y
  `protected-header.schema.json`.
- `vectors/v1/` — vectores dorados por grupo: **bytes + digest esperado +
  diagnóstico esperado** (§5.4), válidos e inválidos. **Corpus: 91 vectores
  / 19 accept** (fingerprint
  `0d4d11fedc5e579f4b547a0bf659d0c25bdf803a4d752f5d91bcadec2487ede7`).
  *Atribución:* el doble PROCEED del gate final M0 cubre **exclusivamente**
  su manifest original de 90 vectores
  (`docs/revisiones/2026-08-21-m0-gate-final/`, inmutable); el corpus de 91
  incluye `tout-valid-accepted` (base accept de `termination_accepted`,
  cierra el hueco de oráculo O-1) como **evidencia M1 autorizada por D-P2**
  (acta `docs/decisiones/autorizacion-m1-2026-08-22.md` + adenda R1 regla
  4). Generados de forma determinista por `scripts/generate-golden-vectors.py` (la variable
  `EKTEL_VECTORS_OUT` redirige la salida a un directorio temporal para el
  gate de diff cero); la clave incluida en `index.json` es **sólo de
  prueba**.
- `parsers/reference/` — parser A (validación hand-coded).
- `parsers/clean-room/` — parser B: escrito desde la spec, los schemas y los
  vectores, **sin leer el código del parser A** (R5); es table-driven
  (interpreta los schemas en runtime), deliberadamente distinto en estilo.
- `scripts/fuzz_diferencial.py` — fuzz diferencial A/B **determinista y
  versionado** en dos familias: **bytes** (semilla 20260820, 17
  mutaciones/vector, 8 clases, acuerdo A/B) y **semántica** (bases
  exclusivamente accept verificadas contra A y B antes de mutar; cada
  mutación declara oráculo —veredicto, diagnóstico, capa y clase— y se
  comprueba contra A y contra B por separado, además del acuerdo A/B; en
  sobres y PoP la MAC se RE-COMPUTA tras mutar para que el diagnóstico
  sea de causa única). El gate permanente
  (`tests/contract/test_fuzz_diferencial.py`) congela el conteo exacto y
  el fingerprint sha256 del corpus y verifica la sensibilidad del
  detector tanto a divergencia artificial como a ERROR COMÚN A/B (ambos
  parsers saboteados con el mismo diagnóstico incorrecto: lo detiene el
  oráculo).
- `scripts/validate_with_jsonschema.py` — validación EXTERNA estratificada
  (Draft 2020-12): envelope → header decodificado → payload por wire type
  → documento. Requiere `jsonschema>=4.18` en un intérprete/venv efímero;
  NO es dependencia del proyecto.

## Semántica de `pattern` y `format` (FIX-AND-RETRY 2026-08-20)

- `pattern` conserva la semántica de JSON Schema Draft 2020-12: regex
  ECMA-262 con coincidencia **no anclada**. Ningún documento de este
  proyecto la reinterpreta como fullmatch. Los patrones de los schemas v1
  están **auto-anclados** (`^` al inicio, `(?![\s\S])` como fin absoluto),
  de modo que el propio schema rechaza prefijos, sufijos y newline final —
  también ante un validador genérico cuyo motor ancle `$` antes de un
  `\n` final (p. ej. `re.search` de Python). Vectores: prefijo, sufijo y
  newline en campos con patrón (§5.7 de la spec).
- `format: ektel-b64u-canonical` es un formato **privado**. En JSON Schema,
  `format` es anotación por defecto: un validador genérico **no** comprueba
  la canonicalidad base64url (ADR-010) salvo que el consumidor registre y
  aserte ese formato explícitamente. Los parsers de referencia ektel SÍ lo
  asertan (`bad_base64`); un validador genérico sin esa aserción sólo
  aplicará el `pattern` de alfabeto y dará `invalid_value`, no
  `bad_base64`. No afirme conformidad de canonicalidad con un validador que
  no conozca este formato.
- Los tres outcomes cierran campos desconocidos **por el schema mismo**
  (`unevaluatedProperties: false`, Draft 2020-12): una propiedad sólo es
  válida si la evalúa la raíz o la alternativa discriminada elegida; los
  parsers lo reportan como `unknown_field`. Vectores: campo extra en cada
  alternativa (§8.3).

## Independencia clean-room: estado declarado (R5)

El parser B se escribió originalmente sin leer el código del parser A. En
la corrección de la doble NO-GO (2026-08-20) y en esta corrección
FIX-AND-RETRY, **ambos parsers fueron modificados en el mismo ciclo por el
mismo agente**, con conocimiento mutuo de los hallazgos y del acuerdo
esperado en los vectores. Eso **debilita la independencia** que R5 quería
acreditar: el acuerdo A/B actual acredita convergencia de dos
implementaciones de estilos distintos frente al corpus versionado, no
independencia estadística de dos autores aislados. La mirada independiente
quedó a cargo de la re-verificación externa, ya ejecutada con doble PROCEED
(Codex y Claude; evidencia durable en
`docs/revisiones/2026-08-21-m0-gate-final/`), no del acuerdo A/B. Declarado
así en el acta de corrección M0 (§4.2).

## Verificación

```sh
.venv/bin/python -m unittest discover -s tests          # 20 tests
.venv/bin/python scripts/generate-golden-vectors.py     # re-emite vectores
ektel_vectors_tmp="$(mktemp -d)"
EKTEL_VECTORS_OUT="$ektel_vectors_tmp" \
  .venv/bin/python scripts/generate-golden-vectors.py
diff -r "$ektel_vectors_tmp" contracts/vectors/v1       # diff cero
.venv/bin/python scripts/fuzz_diferencial.py            # bytes+semántico, 0 divergencias
```

Los vectores son un artefacto de conformidad: cualquier parser de referencia
debe reproducir veredicto, diagnóstico e `identity_digest` exactos.

## Vocabulario de diagnósticos de parser (cerrado, M0)

`ok`, `malformed_json`, `duplicate_key`, `unknown_field`, `missing_field`,
`invalid_type`, `invalid_value`, `size_exceeded`, `bad_base64`,
`bad_signature`, `alg_unsupported`, `schema_version_unsupported`.

Es vocabulario de **parser de contrato**, distinto de los `reason_code` de
admisión (§8.2) y de los estados de ejecución (§8.3); no mezclar.

## Cómo validar con un consumidor genérico (Draft 2020-12)

Los schemas usan `$id` con el host **`https://ektel.local`**, que NO existe
en la red. Un validador genérico debe configurarse así:

1. **Registrar TODOS los schemas locales por `$id`** (p. ej.
   `referencing.Registry` / `RefResolver` con los once archivos de
   `schemas/v1/` mapeados a sus URI `https://ektel.local/contracts/schemas/v1/…`).
2. **No resolver `https://ektel.local` por red**: es un dominio privado
   declarativo; sin el registro local la resolución falla (y así debe ser).
3. **Registrar y asertar el formato `ektel-b64u-canonical`**: en JSON
   Schema, `format` es anotación salvo que el consumidor lo aserte. Sin
   esa aserción, un validador genérico NO comprueba la canonicalidad
   base64url (ADR-010) — sólo aplicará los `pattern` de alfabeto y
   reportará `invalid_value` en vez del `bad_base64` del vocabulario de
   parser.

`scripts/validate_with_jsonschema.py` es la prueba de referencia de esta
configuración con la librería `jsonschema` ≥ 4.18 (herramienta de
verificación externa, NO dependencia del proyecto: se corre con un
intérprete que la tenga instalada; la suite stdlib-only no la requiere).
Valida por capas: envelope exterior → protected header decodificado →
payload según wire type → documento; exige rechazo en la capa esperada
para todo defecto visible al schema y deja skips sólo para lo
verdaderamente fuera de JSON Schema, con razón individual.

## Lo que esto NO es

- No es el parser estricto de admisión de M1 (ese vive en `src/` con replay
  store y PolicyPort).
- No prueba durabilidad ni supervisión; congela sólo los contratos de cable.
