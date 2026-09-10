# Sondas adversariales del revisor Qwen (informe 2 de 3)

**CONSERVADAS POR PROVENANCE. NO VERIFICADAS EN ESTE ASIENTO.**

Copias byte-a-byte de los scripts que el revisor Qwen ejecutó en `/tmp`
(fuera del repositorio) durante su revisión del REVIEW-ROOT
`eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e`, citados en su informe
(`../informe-02-qwen-2026-09-09.md`):

| Sonda | Hallazgos / obligaciones que ejercita | Resultado declarado por el revisor |
|---|---|---|
| `probe_gm215_1_validity_bound.py` | F1 (P1) — causa `deadline_validity_exhausted` inalcanzable en ruta real | FALSIFICADA (reproducida) |
| `probe_gm215_2_await_race.py` | F2 (P1) — carrera `await_terminal`, doble entrega y sobre-admisión | FALSIFICADA (40/40 determinista) |
| `probe_gm215_3_cas_zero.py` | O1 linealización CAS (8 hilos, mismo token) y O6 plazo cero antes del CAS | No falsificadas |

Requisitos declarados: ejecutables con `.venv/bin/python` desde la raíz del
repo sobre el REVIEW-ROOT; escriben sólo en directorios temporales propios.

La comprobación independiente de estas reproducciones por el agente ejecutor
**no** forma parte de este asiento; corresponde a la fase posterior a la
reconciliación de los tres informes (encargo §7).
