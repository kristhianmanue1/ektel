# contracts/ — wire schemas v1, vectores dorados y parsers de referencia (M0)

**Estado:** API **experimental** (spec v1.2 §16). Sin compromiso de estabilidad
hasta cerrar M0 con la prueba de implementación independiente (R5).

**Fuente normativa:** `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2,
adoptada 2026-08-20). Autorización: `docs/decisiones/autorizacion-m0-2026-08-20.md`.

## Contenido

- `schemas/v1/` — wire schemas v1 (JSON Schema, subconjunto estricto). Los
  sobres firmados comparten `envelope.schema.json` y
  `protected-header.schema.json`.
- `vectors/v1/` — vectores dorados por grupo: **bytes + digest esperado +
  diagnóstico esperado** (§5.4), válidos e inválidos. Generados de forma
  determinista por `scripts/generate-golden-vectors.py`; la clave incluida en
  `index.json` es **sólo de prueba**.
- `parsers/reference/` — parser A (validación hand-coded).
- `parsers/clean-room/` — parser B: escrito desde la spec, los schemas y los
  vectores, **sin leer el código del parser A** (R5); es table-driven
  (interpreta los schemas en runtime), deliberadamente distinto en estilo.

## Verificación

```sh
.venv/bin/python -m unittest discover -s tests          # 10 tests
.venv/bin/python scripts/generate-golden-vectors.py     # re-emite vectores
```

Los vectores son un artefacto de conformidad: cualquier parser de referencia
debe reproducir veredicto, diagnóstico e `identity_digest` exactos.

## Vocabulario de diagnósticos de parser (cerrado, M0)

`ok`, `malformed_json`, `duplicate_key`, `unknown_field`, `missing_field`,
`invalid_type`, `invalid_value`, `size_exceeded`, `bad_base64`,
`bad_signature`, `alg_unsupported`, `schema_version_unsupported`.

Es vocabulario de **parser de contrato**, distinto de los `reason_code` de
admisión (§8.2) y de los estados de ejecución (§8.3); no mezclar.

## Lo que esto NO es

- No es el parser estricto de admisión de M1 (ese vive en `src/` con replay
  store y PolicyPort).
- No prueba durabilidad ni supervisión; congela sólo los contratos de cable.
