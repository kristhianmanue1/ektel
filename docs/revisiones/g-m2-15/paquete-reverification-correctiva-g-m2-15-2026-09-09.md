# Paquete de re-verificación externa — ronda correctiva FIX-M2-R1..R11

**Fecha:** 2026-09-09.
**Destinatario:** revisión externa del diff correctivo (G-M2-15).
**Pregunta que esta re-verificación debe responder:** ¿quedaron realmente
satisfechas FIX-M2-R1..R11 sin introducir regresiones ni ampliar M2?

## 1. Identidades

| Qué | Valor |
|---|---|
| REVIEW-ROOT original (lo revisado por los tres informes) | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` |
| MANIFEST-ROOT **anterior** (implementación revisada) | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |
| Reconciliación formal (fuente de obligaciones) | commit `dc3da3f2a8c31762743c9ef9016ccc1eb817d0a4` |
| Commit de la ronda correctiva | `0475d9ffa5e2cbd5985f44ce6039b52e28eaea5f` |
| MANIFEST-ROOT **nuevo** (post-correctiva) | `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470` |
| Manifiesto | `docs/evidencia/manifest-m2-sha256.txt` |

## 2. Qué cambió (diff correctivo)

Conteo del commit correctivo completo `dc3da3f..0475d9f`: **16 archivos** —
6 de `src/`, 8 de `tests/` y 2 de `docs/`. El diff de re-verificación,
restringido a código y pruebas, es:

```
git diff dc3da3f..0475d9f -- src tests scripts
```

— **14 archivos** (6 de `src/`, 8 de `tests/`; `scripts/`: 0 cambios). Sin
`contracts/`, sin schemas, sin workflows, sin rutas nuevas fuera del
inventario de 45. El diff de manifiestos confirma exactamente esos 14
archivos de código/prueba (ninguna ruta añadida ni retirada):

```
src/adapters/posix_supervisor.py      tests/escape/test_supervisor_characterization.py
src/application/config.py             tests/integration/test_capacity_slots.py
src/application/start_service.py      tests/integration/test_output_framing.py
src/domain/execution_handle.py        tests/integration/test_start_linearization.py
src/domain/execution_result.py        tests/unit/helpers_m2.py
src/ports/process_host.py             tests/unit/test_deadline_math.py
                                      tests/unit/test_m2_config.py
                                      tests/unit/test_termination_semantics.py
```

## 3. Obligación por obligación

| Obligación | Corrección | Regresión añadida/actualizada |
|---|---|---|
| **FIX-M2-R1** (P1) | `validity_bound` se fusiona en el `raw` del traspaso (`PosixSupervisorHost.collect_terminal`); dict muerto `_validity_bound` eliminado | `test_vigencia_acotada_produce_causa_de_vigencia_end_to_end` (host real, vigencia ≈500 ms → `cause=deadline_validity_exhausted`); `test_el_plazo_efectivo_se_trunca_por_vigencia` afirma que el dato viaja al spawn |
| **FIX-M2-R2** (P1) | Punto único de transferencia: vigilante por acción consume el traspaso, deposita en el handle acuñado (`deposit_terminal_result` privilegiado), libera slot una vez; `await_terminal` del host linealizado en el `pop` | `test_doble_await_concurrente_entrega_una_vez` (barrera); `test_doble_liberacion_no_admite_una_tercera_accion` (capacidad 2, acción B viva: nunca una tercera por doble release) |
| **FIX-M2-R3** (P1) | El slot se libera con el handoff terminal real o su ausencia definitiva — no con `await_result`; el coordinador no retiene handles terminados ni registro creciente | `test_handle_abandonado_no_deja_registro_ni_slot`; `test_handoff_terminal_libera_el_slot` re-encaminada a la ruta real del puerto |
| **FIX-M2-R4** (P2) | `await_result` autentica MAC instancia+capacidad+acción, exige objeto registrado exacto, no toca el host; `store_terminal_result` eliminado (depósito sólo desde el coordinador acuñador) | `test_handle_forjado_no_recolecta_ni_desaloja`; `test_await_result_rechaza_handles_forjados` (forjado/cross-instance/otra acción/depósito externo imposible); pruebas de `terminate` re-encaminadas al depósito del coordinador |
| **FIX-M2-R5** (P3) | Toda rama post-spawn indeterminada retiene slot y registra identidad: ref inválido (tipo/longitud) y ref no-hex de 16 (`"g"*16`, la v2 de OAI-M2-02) | `test_handle_ref_invalido_no_fabrica_handle_y_retienel_slot`; `test_handle_ref_no_hex_es_indeterminado_sin_excepcion` |
| **FIX-M2-R6** (P2) | Validación en `M2Config.__post_init__` (construcción directa no elude rangos ni `audit_mode=required`); `PosixSupervisorHost.from_config` compone desde la única autoridad; rangos normativos completos también en el adaptador | `AutoridadUnicaTests` (4 pruebas); `test_la_configuracion_declarada_es_la_aplicada` (host real: aplicado == declarado) |
| **FIX-M2-R7** (P2) | Literales exactos de ADR-012 §2.3: `useful_runtime_formula=deadline_eff_ms-applied_grace_ms` y `supervisor_scope=per_action_process` | `test_las_assumptions_son_las_congeladas_por_adr_012` (igualdad de tupla completa); `test_claves_orden_y_forma_congelados`; plan aditivo alineado |
| **FIX-M2-R8** (P2) | `first_terminal_cause` registrado en el supervisor (orden de observación, no dos booleanos finales); `classify` decide por primer hecho; empate/desconocido → deadline | `test_primer_hecho_observado_decide_la_carrera` (unit); `test_terminate_antes_del_deadline_gana_el_primer_hecho` (e2e: TERM ignorado, terminate en 300 ms de 2500 útiles → `terminated`, rc -9) |
| **FIX-M2-R9** (P2) | KILL de grupo incondicional al hard deadline tras escalación; PGID capturado al spawn (inmune a reap del líder); watchdog esperado de forma acotada para terminal determinista | `test_nieto_en_el_grupo_recibe_kill_aunque_el_lider_muera_con_term`; `test_proceso_que_obedece_term_muere_con_term_y_no_con_kill` (actualizada: el intento de KILL es incondicional; lo que distingue es el rc) |
| **FIX-M2-R10** (P2, doc) | Fe de erratas del encargo: prevalencia del acta de enmienda G-M2-12 sobre el §4.1 stale | Sección «Fe de erratas» en el encargo (posterior, sin reescribir el original) |
| **FIX-M2-R11** (P3, doc) | Citación exacta del fuzz y addendum de gates reabiertos | `estado-evidencia-m2-2026-09-09.md`: 2000 iteraciones/semilla 20260909 + addendum de ronda correctiva |

## 4. Evidencia de regresión completa

| Verificación | Resultado |
|---|---|
| Suite completa Darwin arm64 (Python 3.12.12) | **355 OK, 4 skips** (los 4: caracterización Linux-only, declarados) |
| Suite completa Linux aarch64 clase V | **355 OK, 1 skip** — contenedor `python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`, `--read-only`, `--network none`, tmpfs para `/tmp` |
| `mypy --strict src` | limpio, 34 archivos |
| Golden vectors | regeneración **diff cero** (91 vectores) |
| Fuzz admisión | sin fallos de oráculo ni crashes |
| Fuzz start/revalidación | 2000 iteraciones, semilla 20260909: `"crashes": [], "divergencias": [], "gate": "OK"` |
| Procesos/supervisores residuales | 0 supervisores vivos tras las suites |
| Rutas | diff dentro del inventario de 45; `contracts/` intacto; sin M3/M4 |

**Nota de caracterización (Linux/contenedor):** durante la ronda se
documentó un artefacto preexistente del entorno contenedor: un descendiente
correctamente muerto por el grupo puede permanecer **zombie** bajo un PID 1
que no recolecta huérfanos, y `os.kill(pid, 0)` reporta zombies como vivos.
Las pruebas de caracterización distinguen ahora zombie de vivo vía
`/proc/<pid>/stat` (un zombie recibió su señal fatal: a efectos de
gobernanza está muerto). El código previo a la ronda muestra el mismo
comportamiento en el mismo contenedor — no es una regresión de la ronda.

## 5. Alcance

Ninguna corrección introdujo schema, wire, M3/M4, capability, sandboxing ni
rutas nuevas. Todas las obligaciones permanecen
`FIX-WITHIN-AUTHORIZED-M2`; la reconciliación no registró ningún
`BLOCKED-BY-NORMATIVE-GAP`.

## 6. Estado

```
corrective_round   = IMPLEMENTED (0475d9f)
new MANIFEST-ROOT  = 365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470
G-M2-15            = FIX-AND-RETRY — pendiente de re-verificación externa
M2                 = OPEN
M3                 = BLOCKED
```

La ronda correctiva **no cierra G-M2-15 por sí misma**. Corresponde la
revisión externa del diff correctivo (`git diff dc3da3f..0475d9f -- src tests
scripts`) con la pregunta de la sección 1 y la regresión completa de la
sección 4 como evidencia.
