# G-M2-15 — expediente de revisión adversarial externa

**Estado: EN CURSO — 2 de 3 informes recibidos. SIN RECONCILIAR.**

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
| 3 | *pendiente* | — | — | — | — | — | — |

**Metadata de evidencia, no puntuación de credibilidad.** El informe 1 no
reejecutó suites (hallazgos por flujo de control estático con reproducciones
ejecutables); el informe 2 reejecutó la suite Darwin completa y sondas propias
pero no la Linux. Estas diferencias de nivel de ejecución se registran para
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

## Estado de los hitos

M2 permanece **abierto**. M3 permanece **bloqueado**. Nada de este expediente
promueve G-M2-15.
