# G-M2-15 — expediente de revisión adversarial externa

**Estado: EN CURSO — 1 de 3 informes recibidos. Sin reconciliar.**

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
| 2 | *pendiente* | — | — | — | — | — | — |
| 3 | *pendiente* | — | — | — | — | — | — |

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
