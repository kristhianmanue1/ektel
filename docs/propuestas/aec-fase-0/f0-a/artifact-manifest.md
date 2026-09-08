# F0-A — Artifact Manifest

- **Fecha de corte:** 2026-09-08.
- **Estado:** completo para `F0-A-CLOSED`.
- **Alcance de digest:** SHA-256 de bytes locales al cierre; el manifest omite
  su propio digest para evitar autorreferencia inestable.

## Artefactos persistidos

| Artefacto | SHA-256 | Clasificación | Provenance/función |
|---|---|---|---|
| `f0-a/README.md` | `a822e9ec618079b9631ddd1ea4400d0140f988db78a8296ac837fae7f0f00397` | `PRIVATE-SANITIZED` | síntesis root reconciliada |
| `f0-a/source-register.md` | `d3c45a703e2cc3b17043b10d07ff4df637d27888cb2ab890dabd2b9de7fd5772` | `PUBLISHABLE` candidato | corpus público principal; no publicación autorizada |
| `f0-a/vocabulary.md` | `3116f51558d54037de2eef1904fced4ae6197d3067bd63c79dcc218bf21fdd09` | `PUBLISHABLE` candidato | síntesis de corpus y mandato |
| `f0-a/threat-model.md` | `f8eca92a4ecb276753f929087e18977bb9d561597befbc175d91388612be1fe2` | `PUBLISHABLE` candidato | threat model root contrastado |
| `f0-a/authority-trust-model.md` | `12747fd49767d55f1741f9a4839ee95fdc1d63b9c1c2bdceda06a4e171e9e623` | `PUBLISHABLE` candidato | modelo de roles y contraste EKTEL read-only |
| `f0-a/execution-paradigms.md` | `a5a58990f9d90958348e7d68ed232c2d61d68f10588cc114a5ddf8af8892f2e9` | `PUBLISHABLE` candidato | tres familias y gates preliminares |
| `f0-a/open-questions.md` | `54676cab08ec7c497b76281c476b35d8c3f2bf530e2441f5b2b062cb40410fde` | `PRIVATE-SANITIZED` | P1/P2/backlog y stop |
| `f0-a/research-log.md` | `2b2ca525651550f6cc774cb1d1eef9896547299aaa9834bc47c01ad72bba9424` | `PRIVATE-SANITIZED` | proceso, preflight y límites |
| `f0-a/decision-log.md` | `c6514981f3c88f3c5fdb79baaf785f06b8bd1675e308ba3421f8d297eb42164b` | `PRIVATE-SANITIZED` | decisiones y reconciliación |
| `f0-a/f0-a-verdict.md` | `05491e40bf2dd9822882e183dddc114756dabea5d535932a33d6d7c8663f57a6` | `PRIVATE-SANITIZED` | cierre y stop decision |
| `records/model-run-gpt-5-6-sol-standards-2026-09-08.md` | `1f66e9568dddae72a8fd83fe122aa8ee4ec1383fd9266c02cf2953e9c006239a` | `PRIVATE-SANITIZED` | síntesis de crítica standards/trust |
| `records/model-run-gpt-5-6-terra-interop-2026-09-08.md` | `f19884c894370fca3b7d369b8190ae66cdd341c7e64c06f47a2775e4c0b4a622` | `PRIVATE-SANITIZED` | síntesis de crítica interoperability/lifecycle |
| `records/model-run-root-reconciliation-2026-09-08.md` | `4cc49ec3d990d81ee920cc69d519d950bc757330dca2f7ed39281f2fc1c9625a` | `PRIVATE-SANITIZED` | única reconciliación root |
| `f0-a/artifact-manifest.md` | `SELF-DIGEST-OMITTED` | `PRIVATE-SANITIZED` | este inventario; omisión deliberada por autorreferencia |

`PUBLISHABLE` significa sólo candidato saneado. No se ha autorizado publicar.

## Referencias externas no copiadas

Las 12 entradas `SRC-01..SRC-12` de `source-register.md` están clasificadas
`EXTERNAL-REFERENCE`; no se descargaron ni vendorizan sus contenidos.

## Outputs deliberadamente no persistidos

| Output | `content_withheld` | Motivo | Fecha/origen general |
|---|---:|---|---|
| transcripts literales completos de agentes | `true` | minimización; la síntesis conserva claims, desacuerdos, fuentes y límites | 2026-09-08, runtime multimodelo |
| prompts serializados internos | `true` | el runtime no los expone como artefacto estable | 2026-09-08, controller/agents |
| snippets de memoria AN-KLA | `true` | memoria privada, no evidencia ni divulgación autorizada | 2026-09-08, preflight local |
| HTML/PDF completos de fuentes | `true` | referencias públicas bastan; no ejecutar/copiar contenido externo | 2026-09-08, web pública |
| secretos/credenciales/handles bearer | `true` | no fueron necesarios ni consultados | 2026-09-08, no aplica |

## Exclusiones preservadas

No pertenecen a los resultados F0-A y no fueron modificados por la
investigación:

- `docs/propuestas/Mandato-investigacion-Agent-Execution-Contract.md`;
- `project-manifest.yaml`;
- código, contratos, schemas, tests y ADR de EKTEL;
- AN-KLA y consumidores externos.
