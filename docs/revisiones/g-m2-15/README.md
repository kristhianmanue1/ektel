# G-M2-15 — expediente de revisión adversarial externa

**Estado: 3 de 3 informes recibidos — RECOLECCIÓN COMPLETA — RECONCILIACIÓN
PENDIENTE.**

Encargo: `../encargo-revision-externa-m2-2026-09-09.md`.

## Identidades congeladas

| Qué | Valor |
|---|---|
| **REVIEW-ROOT** (documentación, políticas y evidencia) | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` |
| **MANIFEST-ROOT** (implementación) | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |

Cada revisor debe trabajar sobre
`git checkout eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` **y** reproducir el
MANIFEST-ROOT. Si cualquiera difiere, la revisión se detiene.

## Informes recibidos

| # | Revisor | Fecha | Veredicto | P0 | P1 | Reejecutó suites | Informe |
|---|---|---|---|---|---|---|---|
| 1 | OpenAI — GPT-5.6 Sol | 09-09 | **FIX-AND-RETRY** | 0 | 5 | **no** (sin resolución DNS a github.com) | `informe-01-openai-gpt-5-6-sol-2026-09-09.md` |
| 2 | Qwen — familia Alibaba/Qwen | 09-09 | **FIX-AND-RETRY** (además P2: 1 · P3: 2) | 0 | 2 | **sí — Darwin arm64** (339 OK, 4 skips; `mypy --strict` limpio); **Linux no**; 3 sondas adversariales propias fuera del repo (`sondas-qwen/`) | `informe-02-qwen-2026-09-09.md` |
| 3 | OpenCode — GLM 5.3 Flash | 09-09 | **FIX-AND-RETRY** (además P2: 1 · P3: 4) | 0 | 2 | **sí — Darwin arm64** (339 OK, 4 skips; `mypy --strict` limpio; fuzz admisión y fuzz revalidación ejecutados); **Linux no reejecutado**; 3 sondas adversariales reproducidas en ejecución, en `/tmp`, fuera del repo; repo no modificado | `informe-03-opencode-glm-5-3-flash-2026-09-09.md` |

**Metadata de evidencia, no puntuación de credibilidad.** El informe 1 no
reejecutó suites (hallazgos por flujo de control estático con reproducciones
ejecutables); el informe 2 reejecutó la suite Darwin completa y sondas propias
pero no la Linux; el informe 3 reejecutó la suite Darwin completa, ambos
fuzzers y tres sondas adversariales con procesos reales, pero tampoco la
Linux. Estas diferencias de nivel de ejecución se registran para
ponderar la evidencia en la reconciliación; **no** convierten a un informe en
más o menos creíble de forma automática.

**Metadata exposure declarada (informe 2, sin interpretar).** El harness del
revisor Qwen reveló al inicio de su sesión la existencia y el título del
commit `fa3ce89` (informe 1 de 3). El revisor declara no haber leído su
contenido, ni el informe OpenAI, ni este expediente, ni ningún artefacto
posterior al REVIEW-ROOT antes de emitir su veredicto. Clasificado únicamente
como *metadata exposure declarada*: si invalida, reduce o no afecta la
independencia lo decidirá la reconciliación, no este asiento.

## Reglas vigentes de este expediente

1. **Ningún revisor ve el informe de otro antes de emitir su primer
   veredicto.** Los informes ya recibidos viven en `main`, que es **posterior**
   al REVIEW-ROOT: un revisor que respete el checkout indicado no puede verlos.
   Inspeccionar `HEAD` en lugar del REVIEW-ROOT **rompe la independencia**.
2. **No hay reconciliación hasta tener los tres informes originales.** No se
   corrige, no se promueve ni se degrada ningún gate mientras tanto.
3. **La reconciliación pondera evidencia, no cuenta votos.** Un hallazgo P0/P1
   reproducible debe resolverse **aunque los otros dos revisores emitan
   `PROCEED`**.
4. Cada informe se conserva **íntegro**, con su identidad de modelo y harness y
   con sus limitaciones declaradas. Una limitación de ejecución cambia el peso
   de un hallazgo en la reconciliación y por eso se registra en la tabla.

## Collection complete

**COLLECTION-COMPLETE** (2026-09-09). Este marcador significa únicamente:

1. existen **tres informes originales**, conservados íntegros en este
   directorio;
2. cada uno declara su **identidad de modelo y harness**;
3. cada uno declara sobre qué **REVIEW-ROOT y MANIFEST-ROOT** trabajó;
4. las **limitaciones de ejecución** de cada uno están registradas y quedan
   a la vista para ponderar evidencia.

**No significa** que G-M2-15 esté verde, que los hallazgos estén aceptados o
refutados, ni que M2 pueda cerrarse. El gate G-M2-15 sigue **PENDIENTE** de la
reconciliación formal por evidencia y del diff correctivo que derive de ella.

## Prohibido hasta la reconciliación

Hasta que exista acta de reconciliación, queda excluido: modificar `src/`;
modificar `tests/` por findings; corregir código; reinterpretar severidades;
descartar findings; mapear, comparar o declarar coincidencias/contradicciones
entre los tres informes; promover G-M2-15; cerrar M2; iniciar M3.

## Estado de los hitos

M2 permanece **abierto**. M3 permanece **bloqueado**. G-M2-15:
`informes originales = 3/3 · collection = COMPLETE · reconciliation = PENDING
· gate = PENDING`. Nada de este expediente promueve G-M2-15.
