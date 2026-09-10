# G-M2-15 — expediente de revisión adversarial externa

**Estado: ratificación humana R13-STRONG/R15/R16 asentada; tercera corrección
R15/R16 implementada; re-verificación independiente 3 PROCEED dentro del modelo
ratificado. El veredicto no adjudica cierre de gate.
R13 fuerte BLOCKED-BY-NORMATIVE-GAP; R13/R14 conservan NOT-SATISFIED.
G-M2-15 = CORRECTIVE-FIX-AND-RETRY. M2 = OPEN.
M3 = BLOCKED.**

Reconciliación por evidencia: `reconciliacion-g-m2-15-2026-09-09.md`.
Ronda correctiva y paquete de re-verificación:
`paquete-reverification-correctiva-g-m2-15-2026-09-09.md`
(nuevo MANIFEST-ROOT: `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470`).

Re-verificación externa de la ronda correctiva:
`informe-reverification-correctiva-01-2026-09-10.md` —
**CORRECTIVE-FIX-AND-RETRY**; R4 y R6 no satisfechas; findings nuevos
CORR-M2-01 (P1), CORR-M2-02 (P2) y CORR-M2-03 (P2).

Adjudicación de la re-verificación correctiva 1:
`adjudicacion-reverification-01-2026-09-10.md` — CORR-M2-01..03
**ACCEPTED-CONFIRMED**; define FIX-M2-R12..R14 y determina
**R12..R14 = AUTHORIZABLE-WITHIN-M2**. R1, R2, R3, R5, R7, R8, R9, R10 y R11
permanecen históricamente `SATISFIED`; R4 y R6 permanecen históricamente
`NOT-SATISFIED` y sus residuos se trasladan sin reescribirlos.

Segunda ronda correctiva:
`paquete-reverification-correctiva-02-g-m2-15-2026-09-10.md` — implementación
de FIX-M2-R12..R14 en `273d09be488d9315e68e140d4553837944c1fd1f`;
MANIFEST-ROOT `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95`.
R12..R14 quedan `IMPLEMENTED / PENDING-EXTERNAL-REVERIFICATION`; no se
declaran satisfechas por este asiento.

Re-verificación externa de la ronda correctiva 2:
`informe-reverification-correctiva-02-2026-09-10.md` —
**CORRECTIVE-FIX-AND-RETRY**; R12 `SATISFIED`; R13 y R14 `NOT-SATISFIED`;
findings FIND-R13-A (P2), FIND-R13-B (P3) y FIND-R14-A (P2), todos
REPRODUCIDO. Conservado íntegro; el asiento original no lo adjudicó.

Adjudicación arquitectónica posterior:
[adjudicacion-arquitectonica-r13-r14-2026-09-10.md](adjudicacion-arquitectonica-r13-r14-2026-09-10.md).
Acepta los tres findings por la evidencia preservada y el contraste estático;
no reejecuta sus sondas. Distingue encapsulación, disciplina de capabilities
y frontera de seguridad. Conserva R13 fuerte como no satisfecha y registra
su gap; propone R15 (terminal writer separation) y R16 (provenance local de
emisión). No adopta silenciosamente un nuevo threat model ni modifica contratos
congelados: no-claim, handoff/reinicio, capacidad de evidencia y encaje en
Admission requieren decisión normativa humana. Diseño A recomendado como
candidato local; aislamiento fuerte queda fuera, sin asignarlo a M3.

MANIFEST-ROOT vigente verificado y preservado:
`9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95`.

La identidad anterior corresponde al acto documental post-Astra, sin cambios
de implementación entonces. La decisión humana posterior
[ratifica y autoriza R15/R16](../../decisiones/ratificacion-r13-strong-r15-r16-2026-09-10.md).
La tercera corrección separa writer terminal, rechaza handles incompletos y
vincula Start a evidencia efímera producida por Admission. No ofrece aislamiento
frente a introspección. Nuevo MANIFEST-ROOT de implementación:
`b59553bcb6d4ab696357354ba63ffbae398609ea48426610b447d43bec660588`.

[Paquete correctivo 3](paquete-reverification-correctiva-03-g-m2-15-2026-09-10.md):
CORRECTIVE-REVIEW-ROOT `f944493bc9872414daf3d46d7ae230adcbfcf42e`;
385 tests completos en Darwin (5 skips) y Linux aarch64 (1 skip), mypy y fuzzers.
[Informe independiente 3](informe-reverification-correctiva-03-2026-09-10.md):
122 pruebas focalizadas y sondas propias; R15/R16 SATISFIED según el revisor
bajo el modelo ratificado, sin finding bloqueante. Se conserva su observación
de demora posible de Started después del spawn por contención de Admission.
No se afirma latencia de retorno acotada ni diversidad de modelos en esta revisión.

Encargo: `../encargo-revision-externa-m2-2026-09-09.md`.

## Identidades congeladas de la revisión original

Las instrucciones de checkout siguientes corresponden al ciclo original de
tres revisores. No reemplazan las identidades posteriores de cada ronda ni
el HEAD documental de entrada de la adjudicación arquitectónica.

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

```text
initial_collection        = COMPLETE
initial_reconciliation    = COMPLETE
corrective_round_1        = NOT-CONFORMING
reverification_1          = COMPLETE
adjudication_1            = COMPLETE
corrective_round_2        = IMPLEMENTED
reverification_2          = COMPLETE / NOT-CONFORMING
architectural_adjudication = COMPLETE / DOCUMENTARY-ONLY
R12                       = SATISFIED
R13                       = NOT-SATISFIED
R13-STRONG                = BLOCKED-BY-NORMATIVE-GAP
R14                       = NOT-SATISFIED
R15                       = IMPLEMENTED / EXTERNAL-REVERIFICATION-PROCEED
R16                       = IMPLEMENTED / EXTERNAL-REVERIFICATION-PROCEED
normative_ratification    = RATIFIED-BY-HUMAN
corrective_action_3       = IMPLEMENTED / EXTERNAL-REVERIFICATION-PROCEED

G-M2-15 = CORRECTIVE-FIX-AND-RETRY
M2       = OPEN
M3       = BLOCKED
```

G-M2-01, G-M2-05, G-M2-06, G-M2-10, G-M2-11, G-M2-12, G-M2-14 y G-M2-15
permanecen con evidencia de la re-verificación 2. No se promueve ningún gate.
La adjudicación arquitectónica no equivale a aceptación del diff posterior.
Su ratificación y autorización ya constan en el acto humano enlazado. La tercera
corrección recibió re-verificación independiente; ni su PROCEED ni las pruebas
del implementador adjudican cierre del gate. R12 conserva la evidencia existente;
R13/R14 no se cierran mediante el nuevo alcance propuesto de R15/R16.
