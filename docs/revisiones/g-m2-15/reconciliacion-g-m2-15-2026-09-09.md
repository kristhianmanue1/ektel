# Reconciliación formal por evidencia — G-M2-15

**Fecha:** 2026-09-09.
**Naturaleza:** acto exclusivamente documental. No modifica `src/`, no
modifica `tests/` funcionales, no implementa fixes, no regenera el
MANIFEST-ROOT, no cierra G-M2-15, no cierra M2, no inicia M3.

## 1. Identidades de entrada

| Qué | Valor |
|---|---|
| Referencia documental de entrada | `cf17be4f0be049bf98b22c58664a68c9a94ad351` |
| MANIFEST-ROOT (implementación revisada) | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` — intacto |
| REVIEW-ROOT (paquete original de revisión) | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` |

Los tres revisores trabajaron sobre el mismo REVIEW-ROOT. Los revisores 2 y 3
reprodujeron el MANIFEST-ROOT (95/95 hashes). El revisor 1 no ejecutó checkout
(limitación declarada) e inspeccionó los archivos del REVIEW-ROOT por conector.

## 2. Informes fuente

| # | Revisor | Veredicto | Hallazgos | Nivel de ejecución |
|---|---|---|---|---|
| 1 | OpenAI — GPT-5.6 Sol | FIX-AND-RETRY | 5 (P1×5) | sólo estático; reproducciones ejecutables propuestas, no corridas |
| 2 | Qwen — familia Alibaba/Qwen | FIX-AND-RETRY | 5 (P1×2, P2×1, P3×2) | suite Darwin completa + `mypy` + 3 sondas con procesos reales; Linux no |
| 3 | OpenCode — GLM 5.3 Flash | FIX-AND-RETRY | 7 (P1×2, P2×1, P3×4) | suite Darwin completa + `mypy` + fuzzers + 3 sondas con procesos reales; Linux no |

Ninguno de los tres informes se modifica en este acto. Los tres emitieron
FIX-AND-RETRY; conforme al principio de adjudicación, **la coincidencia de
veredictos no demuestra ningún finding**: cada finding se adjudica por su
propia evidencia.

Metadata de proceso conservada sin reinterpretar: el harness del revisor 2
reveló la existencia/título del commit del informe 1 (declarado por el
revisor); el snapshot de git del revisor 3 no reveló informes previos. Ningún
hallazgo de este acto se apoya en la posición de un revisor, sino en su
evidencia.

## 3. Metodología

1. **Matriz completa sin descarte** de los 17 findings (§4), conservando ID
   original, severidad original, clase de evidencia, claim/gate, reproducción,
   consecuencia, recomendación y limitaciones del revisor.
2. **Agrupación por causa raíz**, no por parecido textual (§5). No se fusionan
   hallazgos por compartir archivo o capa; propiedades distintas conservan
   obligaciones distintas aunque compartan zona (p. ej. «doble liberación de
   slot» ≠ «slot nunca liberado»).
3. **Adjudicación por la cadena claim → evidencia → reproducción →
   consecuencia** (§6), con verificación independiente de cada hecho de código
   decisorio contra el árbol `cf17be4` (código idéntico al MANIFEST-ROOT en
   `src/`).
4. **Severidad reconciliada por impacto demostrado** (§7), no por promedio ni
   por número de revisores. Un P1 estático puede bajar si su condición es
   imposible bajo los adaptadores autorizados, con explicación.
5. **Obligaciones correctivas** FIX-M2-R* (§8) y verificación de gaps
   normativos (§10).

Nota de honestidad metodológica: el razonamiento estático inicial del revisor 3
que descartaba la doble liberación de slot («el clamping en 0 la hace
inocua») era **incorrecto** — el clamp evita el underflow pero no evita que el
decremento extra robe capacidad a otras acciones vivas. La evidencia dinámica
del revisor 2 (sobre-admisión medida) prevalece. Se registra como ejemplo del
principio: la unidad de decisión es la evidencia, no el razonamiento de un
revisor.

## 4. Matriz completa de findings (17)

| ID | Revisor | Sev. orig. | Clase de evidencia | Claim/gate afectado | Reproducción | Consecuencia | Recomendación | Limitación del revisor |
|---|---|---|---|---|---|---|---|---|
| OAI-M2-01 | OpenAI | P1 | estática | integridad de `ExecutionHandle`; G-M2-10; oblig. 4/5 | flujo de control + pasos de repro | un objeto sin capability puede recolectar el terminal ajeno, evictar el registro y liberar slot | autenticar handle + registro vivo antes de `collect_terminal` | no ejecutó suites |
| OAI-M2-02 | OpenAI | P1 | estática | G-M2-06; G-M2-12; preservación de indeterminación | 2 repros mínimas propuestas (bad_ref; ref hex-inválido → `Started` raise) | rama post-spawn indeterminada libera slot; variante 2 libera slot con spawn ocurrido | validación canónica única; post-spawn inválido retiene slot y registra identidad | no ejecutó suites |
| OAI-M2-03 | OpenAI | P1 | estática | G-M2-01; G-M2-11; fail-closed de inicialización | repro de divergencia declared/applied propuesta | bypass de `M2Config.build()`; tres fuentes de configuración pueden divergir | fuente única validada propagada (`from_config`); imposible construir no-validado | no ejecutó suites |
| OAI-M2-04 | OpenAI | P1 | estática | G-M2-11; conformidad literal ADR-012 | diff textual vs ADR-012 §2.3 | `assumptions` emitidas ≠ strings congeladas; tests codifican el valor desviado | literales normativos exactos + test de igualdad de tupla completa | no ejecutó suites |
| OAI-M2-05 | OpenAI | P1 | estática | D-M2-4; ADR-005; G-M2-09; G-M2-10 | repro propuesta (TERM ignorado, terminate antes del deadline) | con ambos booleanos, `classify()` da deadline siempre; «primer hecho observado» no es registrable | registrar orden/secuencia; menor secuencia gana; empate → deadline | no ejecutó suites |
| F1 | Qwen | P1 | dinámica (sonda 1) | D-M2-3; G-M2-09 | sonda real: vigencia 2000 ms < deadline 5000 → `cause=deadline_duration` | causa de plazo equivocada en wire real; regla vigencia-gana es código muerto | fusionar `validity_bound` en el `raw` del handoff + prueba e2e | Linux no ejecutado |
| F2 | Qwen | P1 | dinámica (sonda 2) | D-M2-2(a) cota; D-M2-4 unicidad de handoff; G-M2-12 crit. 5 | sonda: doble `await_result` concurrente → doble entrega 40/40; capacidad 2 → 3 procesos vivos | corrupción del contador de capacidad global; sobre-admisión | transferir propiedad con el `pop` atómico; segundo llamador `None` | Linux no ejecutado |
| F3 | Qwen | P2 | documental | oblig. 14 (gates parciales leídos como verdes, en ambas direcciones) | `git show eb5590b`: el encargo no fue tocado al asentar la enmienda | texto stale del encargo instruye mal a revisores | fe de erratas / nota de prevalencia | — |
| F4 | Qwen | P3 | estática | higiene / vestigio de F1 | única mención de `_validity_bound` en l. 477 | dict muerto que sugiere propagación inexistente | eliminar o completar con el fix de F1 | — |
| F5 | Qwen | P3 (HIPÓTESIS) | estática | consistencia interna post-spawn | no reproducida: requiere host que viole contrato | ref inválido libera slot sin registrar en `_retained` (contrario a H5) | tratar ref inválido como la excepción genérica | inalcanzable con adaptadores entregados |
| EXT3-01 | GLM | P1 | dinámica (sonda A) | D-M2-3; spec §12.8; C4; G-M2-09 | sonda real: vigencia ≈500 ms < deadline 30000 → `cause=deadline_duration` | toda acción acotada por vigencia reporta causa incorrecta | propagar `validity_bound` a plan JSON y `terminal` + prueba e2e | Linux no reejecutado |
| EXT3-02 | GLM | P1 | dinámica (sonda B) | D-M2-2(a) liberación en handoff; G-M2-12 crit. 7; spec §12.6 | sonda real: acción terminada, handle abandonado → slot retenido; 2.ª acción `capacity:no_slot` | agotamiento permanente de capacidad; registro del host crece sin límite; muerte del supervisor nunca libera | liberar slot al recibir `T`/`X`; rutas de recuperación | Linux no reejecutado |
| EXT3-03 | GLM | P2 | dinámica (sonda C) | C3; G-M2-11; escapes declarados | sonda real: líder muere con TERM, nieto en el mismo grupo ignora TERM → nieto vivo tras hard deadline | el KILL de grupo no se dispara (gated por lividad del líder); escape no declarado | `killpg` incondicional al vencer `hard_deadline_at` + medición | Linux no reejecutado |
| EXT3-04 | GLM | P3 | estática | simetría D-M2-4; oblig. 5 («resultado fabricado») | flujo de control | `await_result` sin autenticación; `store_terminal_result` pública permite resultado no tipado | verificar registro/instancia; restringir `store_terminal_result`; tipo del retorno | en-modelo (un proceso) |
| EXT3-05 | GLM | P3 | documental | integridad documental del encargo | texto §4.1 del encargo vs acta de enmienda | contradicción dentro del mismo REVIEW-ROOT | errata o nota de prevalencia | — |
| EXT3-06 | GLM | P3 | documental | citación exacta de evidencia | `estado-evidencia` «3000 iteraciones» vs default 2000 sin log | evidencia de fuzz no reproducible al dígito | citar semilla e iteraciones exactas | — |
| EXT3-07 | GLM | P3 | estática | D-M2-3 rangos; TCB de configuración | `PosixSupervisorHost.__init__` valida >0 pero no techos 60000/10000; knobs extra fuera de la tabla ADR-012 | el adaptador que aplica TERM→KILL acepta rangos no normativos | unificar validación; documentar knobs | — |

## 5. Agrupación por causa raíz

| Grupo | Causa raíz | Findings | Relación |
|---|---|---|---|
| **G-A** | La causalidad vigencia-acotó-el-plazo se calcula en el coordinador y se pierde en la frontera adaptador→terminal; el consumidor (`classify`) nunca la recibe | F1, EXT3-01, F4 | **Mismo defecto**, doble detección independiente con reproducciones dinámicas independientes. F4 es vestigio del mismo cableado incompleto |
| **G-B** | La transferencia de propiedad del terminal no está linealizada en un punto único (`get`→`wait`→`pop` no atómicos; el `pop` del perdedor se descarta) | F2 | Única |
| **G-C** | La liberación del slot quedó acoplada a `await_result` (acto del llamador) en vez del handoff terminal (hecho del runtime); sin ruta de recuperación para ausencia | EXT3-02 | Única. **Distinta de G-B**: sobre-admisión (F2) vs agotamiento (EXT3-02). Comparten zona (ciclo de vida slot/handoff) pero ninguna corrección de una demuestra la propiedad de la otra |
| **G-D** | Frontera de confianza asimétrica: el handle es capability en `terminate` y mera referencia en `await_result`; el almacén del resultado es público y no tipado | OAI-M2-01, EXT3-04 | **Mismo defecto**, detección independiente (estática ambas) |
| **G-E** | Las ramas post-spawn indeterminadas no tratan uniformemente la retención de capacidad | OAI-M2-02 (v1 y v2), F5 | **Misma causa raíz**; F5 es la v1 de OAI-M2-02; la v2 (hex-inválido → `Started` raise → release) es una ruta adicional de la misma inconsistencia |
| **G-F** | No existe una única autoridad de configuración validada propagada de extremo a extremo (bypass de construcción, tres fuentes divergentes, validación débil en el adaptador) | OAI-M2-03, EXT3-07 | EXT3-07 es faceta de la misma causa; **subsumida** |
| **G-G** | La implementación y los tests convergieron entre sí sobre valores distintos de las strings congeladas por ADR-012 | OAI-M2-04 | Única |
| **G-H** | La precedencia «primer hecho observado» se reduce a booleanos sin orden; `classify` impone precedencia estática | OAI-M2-05 | Única |
| **G-I** | La escalación KILL del grupo está condicionada a la lividad del líder en `hard_deadline_at` | EXT3-03 | Única; distinta de los escapes `setsid` (declarados) |
| **G-J** | Documentos normativos/evidencia inconsistentes con el árbol o no reproducibles al dígito | F3, EXT3-05, EXT3-06 | F3 y EXT3-05 son **el mismo defecto** (doble detección); EXT3-06 es independiente |

## 6. Adjudicación finding por finding

| ID | Estado | Justificación |
|---|---|---|
| F1 | **ACCEPTED-CONFIRMED** | Reproducido dinámicamente por Qwen y por GLM con sondas independientes y parámetros distintos; verificado contra el árbol: `SupervisedAction.validity_bound` se asigna y nunca se lee; el dict `terminal` no emite la clave; grep confirma que `deadline_validity_exhausted` sólo aparece en unitarios de la función pura |
| EXT3-01 | **ACCEPTED-CONFIRMED** | Mismo defecto que F1 (G-A); se conserva el ID por preservación íntegra; la obligación única es FIX-M2-R1 |
| F2 | **ACCEPTED-CONFIRMED** | Reproducido dinámicamente 40/40 con consecuencia medida (capacidad 2 → 3 procesos vivos); verificado contra el árbol: `await_terminal` hace `get`→`wait`→`pop` sin atomicidad y descarta el resultado del `pop` |
| EXT3-02 | **ACCEPTED-CONFIRMED** | Reproducido dinámicamente; verificado: la única liberación post-spawn vive en `_release_handle` (ruta `await_result`); el pop del host ocurre sólo en `await_terminal`; ausencia sin terminal no libera ni ofrece recuperación |
| EXT3-03 | **ACCEPTED-CONFIRMED** | Reproducido dinámicamente; verificado: `kill_group()` está tras `if child.poll() is None`; N4 no cubre el defecto porque el descendiente permanece en el grupo gobernado y el mecanismo implementado (KILL de grupo) afirma alcanzarlo (comentario del test contraparte) sin hacerlo en esta clase |
| OAI-M2-01 | **ACCEPTED-STATIC** | Flujo de control verificado: `await_result` comprueba sólo `isinstance`; usa `handle_ref` sin MAC ni registro; `collect_terminal` no autentica. Coincidente con EXT3-04 (G-D). La reproducción dinámica queda como prueba de regresión obligatoria del fix |
| EXT3-04 | **ACCEPTED-STATIC** | Mismo defecto que OAI-M2-01, más la variante «resultado fabricado» vía `store_terminal_result` pública y retorno sin tipo; subsumida en la misma obligación FIX-M2-R4 |
| OAI-M2-02 | **ACCEPTED-STATIC** | v1 verificada (`release` + indeterminado sin `_retained`, contradictorio con H5). v2 verificada contra el árbol: `Started.__post_init__` exige hex (start_outcomes.py:49-50) y `_spawn` sólo comprueba longitud → ref de 16 no-hex construye y registra `ExecutionHandle`, `Started` lanza `ValueError`, el `except BaseException` de `start()` libera el slot con spawn ocurrido |
| F5 | **ACCEPTED-STATIC** | Es la v1 de OAI-M2-02 (G-E). La hipótesis del revisor quedó elevada por verificación estática del flujo; la inalcanzabilidad con los adaptadores entregados se refleja en la severidad, no en el estado |
| OAI-M2-03 | **ACCEPTED-STATIC** | Verificado: `StartService`/`AdmissionService` aceptan `M2Config` por `isinstance`; el dataclass permite construcción no validada; tres fuentes de configuración sin mecanismo de igualdad; la divergencia declared/applied es construible con adaptadores autorizados |
| OAI-M2-04 | **ACCEPTED-STATIC** | Verificado textualmente: `config.py` emite `useful_runtime_formula=useful_runtime_ms=deadline_eff_ms-min(…)` y `supervisor_scope=per_action`; ADR-012 §2.3 congela `useful_runtime_formula=deadline_eff_ms-applied_grace_ms` y `supervisor_scope=per_action_process`; `test_m2_config.py:212` codifica el valor desviado → tests==código≠ADR |
| OAI-M2-05 | **ACCEPTED-STATIC** | Verificado: el terminal exporta sólo `deadline_hit`/`externally_terminated` sin orden; `classify()` antepone deadline siempre. D-M2-4 exige «primer hecho observado gana; empate → deadline». Defecto de causalidad real; la repro propuesta es parte del fix |
| F4 | **SUBSUMED por FIX-M2-R1** | Dict muerto verificado (única mención, l. 477); se elimina o completa dentro del cableado de validity_bound |
| EXT3-07 | **SUBSUMED por FIX-M2-R6** | Faceta de validación del adaptador dentro de la autoridad única de configuración |
| F3 | **DOCUMENTATION-FIX** | Verificado: el encargo §4.1 conserva texto stale frente al acta de enmienda asentada en el mismo REVIEW-ROOT; la promoción de G-M2-12 es legítima (acta + reevaluación documentada; Qwen verificó además la ausencia de la formulación prohibida «se probó 16 GiB») |
| EXT3-05 | **DOCUMENTATION-FIX** | Mismo defecto que F3 (G-J); obligación única FIX-M2-R10 |
| EXT3-06 | **DOCUMENTATION-FIX** | Verificado: `estado-evidencia` afirma 3000 iteraciones; el default del script es 2000; sin log no es reproducible al dígito. La corrección es de citación, no de código |

**Totales:** ACCEPTED-CONFIRMED 5 · ACCEPTED-STATIC 7 · SUBSUMED 2 ·
DOCUMENTATION-FIX 3 · HYPOTHESIS-UNCONFIRMED 0 · REJECTED 0. Total 17.

## 7. Severidades reconciliadas

| Grupo / ID | Sev. original(es) | Reconciliada | Justificación de impacto |
|---|---|---|---|
| F1 + EXT3-01 (G-A) | P1 / P1 | **P1** | Reproducida por dos revisores de forma independiente; sistemática: toda acción acotada por vigencia reporta causa wire incorrecta |
| F2 (G-B) | P1 | **P1** | Reproducida; corrompe la cota global y permite sobre-admisión para acciones inocentes |
| EXT3-02 (G-C) | P1 | **P1** | Reproducida; agotamiento permanente de capacidad sin ruta de recuperación |
| EXT3-03 (G-I) | P2 | **P2** | Reproducida; fuga de proceso no declarada. N4 no la oculta: el descendiente permanece en el grupo gobernado |
| OAI-M2-01 + EXT3-04 (G-D) | P1 / P3 | **P2** | Baja desde P1 (OpenAI): la condición exige construir un objeto in-proceso, y en el modelo autorizado (un host, un usuario, un proceso) el atacante in-proceso ya puede llamar al host directamente — no hay escalada cross-process. Sube desde P3 (GLM): viola el invariante local capability-del-handle, permite robar salida de acciones ajenas y corromper slots/registro, también por accidente de uso. Impacto demostrado: invariante roto, no frontera de seguridad nueva |
| OAI-M2-03 (G-F) | P1 | **P2** | Baja desde P1: el bypass exige que el despliegue construya el dataclass directamente contra su contrato documentado; ninguna ruta entregada lo hace; la divergencia declared/applied es observable en `guarantees_applied` (el resultado declara lo aplicado). Impacto demostrado: gobernanza de configuración eludible, no comportamiento erróneo de las rutas shipped |
| OAI-M2-04 (G-G) | P1 | **P2** | Baja desde P1: conformidad literal, sin consecuencia de comportamiento; pero viola el freeze deliberado de ADR-012 y los tests codifican el valor desviado (no es cosmético: es tests==código≠ADR) |
| OAI-M2-05 (G-H) | P1 | **P2** | Baja desde P1: misma familia de defecto que G-A (resultado tipado incorrecto) pero con disparador estrecho (carrera terminate-antes-del-deadline con TERM ignorado) y sin impacto de capacidad/seguridad. No baja por «nadie más lo detectó»: baja por alcance del impacto; la condición no es imposible, luego no baja a P3 |
| OAI-M2-02 + F5 (G-E) | P1 / P3 | **P3** | Baja desde P1 (OpenAI) con explicación conforme a §7: ambas variantes son **inalcanzables con los adaptadores autorizados** (el host POSIX real emite siempre 16 hex); son una inconsistencia lógica determinista ante hosts futuros que violen el contrato del puerto. Se corrige porque la preservación de indeterminación es invariante |
| F4 | P3 | **P3** | Vestigio; subsumida en FIX-M2-R1 |
| F3 + EXT3-05 (G-J encargo) | P2 / P3 | **P2** | Sube desde P3 (GLM): el encargo instruye activamente a los revisores a tratar como parcial un gate legítimamente promovido — defecto de gobernanza con efecto procesal demostrado, no cosmético; diferible porque dos revisores lo detectaron independientemente |
| EXT3-06 (G-J fuzz) | P3 | **P3** | Citación de evidencia no reproducible al dígito; corrección documental |

**Resumen reconciliado por grupos de causa raíz:** P0 = 0 · **P1 = 3** (G-A,
G-B, G-C) · **P2 = 6** (G-D, G-F, G-G, G-H, G-I, G-J-encargo) · **P3 = 2**
(G-E, G-J-fuzz). Los 17 findings individuales heredan la severidad de su
grupo; las severidades originales de cada revisor permanecen en la matriz de
§4 sin edición.

## 8. Obligaciones correctivas

Ninguna obligación diseñará el parche línea a línea; fijan causa raíz, alcance,
propiedad requerida, regresión mínima, gates y criterio de cierre.

### FIX-M2-R1 — Cablear `validity_bound` hasta el resultado (P1) — fusiona F1, EXT3-01; subsume F4

- **Causa raíz:** G-A. **Archivos permitidos:** `src/application/start_service.py`, `src/adapters/posix_supervisor.py`, pruebas de integración nuevas.
- **Incorrecto:** `cause=deadline_duration` cuando la vigencia acotó el plazo; `SupervisedAction.validity_bound` muerto; dict `_validity_bound` muerto.
- **Requerido:** `cause=deadline_validity_exhausted` end-to-end cuando `remaining_validity <= deadline_ms` (incluido empate) con host real; el dato sobrevive coordinador→supervisor→terminal→clasificación, o se elimina el campo muerto si la propagación se resuelve por otra vía equivalente.
- **Regresión mínima:** prueba de integración con vigencia acotada (host real) que aserte la causa; prueba de empate.
- **Gates que reabren:** G-M2-09. **Evidencia:** corrida Darwin y Linux. **Cierre:** causa correcta observada en ambas plataformas y gate G-M2-09 reverdecedo con la prueba citada.

### FIX-M2-R2 — Linealizar la entrega del terminal en un punto único (P1) — F2

- **Causa raíz:** G-B. **Archivos permitidos:** `src/adapters/posix_supervisor.py`, `src/application/start_service.py`, pruebas nuevas.
- **Incorrecto:** doble entrega del `AwaitedExecution` y doble liberación de slot ante `await_result` concurrentes; sobre-admisión medible.
- **Requerido:** la propiedad del terminal se transfiere **exactamente una vez** (pop atómico); el segundo llamador recibe ausencia honesta; el contador de capacidad queda exacto.
- **Regresión mínima:** prueba con barrera de doble `await_result` (segundo → `None`, `slots_in_use` exacto); repro de sobre-admisión convertida en test de frontera.
- **Gates:** G-M2-12 (criterio 5), G-M2-10, G-M2-05. **Cierre:** criterio 5 reverdecedo con la prueba de concurrencia citada en ambas plataformas.

### FIX-M2-R3 — Liberar el slot en el handoff terminal real (P1) — EXT3-02

- **Causa raíz:** G-C. **Archivos permitidos:** `src/application/start_service.py`, `src/adapters/posix_supervisor.py`, pruebas nuevas.
- **Incorrecto:** slot retenido tras el termino si nadie llama `await_result`; `_actions` del host y `_handles` del servicio crecen sin límite; muerte del supervisor sin terminal nunca libera ni ofrece recuperación.
- **Requerido:** el slot se libera cuando el terminal (o su ausencia definitiva) es recibido por el runtime, no por acto del llamador; handle abandonado no retiene slot ni registro; la ausencia por pérdida del supervisor libera con ruta explícita observable.
- **Regresión mínima:** abandonar handle terminado → slot libre y `pending_actions` acotado; simular ausencia → slot libre.
- **Gates:** G-M2-12 (criterio 7), G-M2-10. **Cierre:** criterio 7 reverdecedo con pruebas end-to-end citadas (no dobles con `store_terminal_result` manual como única evidencia).

### FIX-M2-R4 — Frontera de confianza de `await_result` (P2) — fusiona OAI-M2-01, EXT3-04

- **Causa raíz:** G-D. **Archivos permitidos:** `src/application/start_service.py`, `src/domain/execution_handle.py`, `src/ports/process_host.py`, pruebas nuevas.
- **Incorrecto:** `await_result` acepta cualquier objeto con `handle_ref` válido; puede recolectar terminals ajenos, evictar registros y liberar slots; `store_terminal_result` pública permite resultados fabricados no tipados.
- **Requerido:** `await_result` autentica handle (token/instancia/registro vivo) antes de contactar al host, con la misma disciplina de `terminate`; el almacenamiento del resultado queda restringido a la ruta del coordinador; el retorno es `AwaitedExecution | None`.
- **Regresión mínima:** forjado, cross-instancia, otra acción, liberado → rechazo sin contacto al host ni efecto en slot/registro; resultado almacenado por ruta no coordinadora → imposible.
- **Gates:** G-M2-10. **Cierre:** matriz de handles negativos de `await_result` verde en ambas plataformas. Nota: si la corrección revelara la necesidad de un contrato nuevo para el handle, detener y declarar gap — no se anticipa aquí.

### FIX-M2-R5 — Indeterminación post-spawn uniforme (P3) — fusiona OAI-M2-02 (v1 y v2), F5

- **Causa raíz:** G-E. **Archivos permitidos:** `src/application/start_service.py`, pruebas nuevas.
- **Incorrecto:** ref inválido (tipo/longitud) libera slot sin registrar identidad; ref de 16 no-hex construye handle, registra, y `Started` lanza liberando slot con spawn ocurrido.
- **Requerido:** toda rama que no pueda afirmar la ausencia de proceso retiene slot + registra identidad en `_retained`; validación canónica única del `handle_ref` antes de construir objetos públicos; ninguna rama post-spawn propaga excepción liberando capacidad.
- **Regresión mínima:** `bad_ref` → indeterminado + `slots_in_use==1` + identidad en `retained_by_indeterminacy`; host que devuelve `"g"*16` → indeterminado sin excepción ni liberación.
- **Gates:** G-M2-06, G-M2-12. **Cierre:** ambas ramas cubiertas; preservación de indeterminación verificada.

### FIX-M2-R6 — Autoridad única de configuración (P2) — fusiona OAI-M2-03; subsume EXT3-07

- **Causa raíz:** G-F. **Archivos permitidos:** `src/application/config.py`, `src/application/start_service.py`, `src/application/admit.py`, `src/adapters/posix_supervisor.py`, pruebas nuevas.
- **Incorrecto:** `M2Config` construible sin validar y aceptado por `isinstance`; tres fuentes de configuración divergentes (admisión / servicio / host); el adaptador aplica rangos no normativos y knobs fuera de la tabla ADR-012.
- **Requerido:** única fuente validada imposible de eludir por constructor público (validación en `__post_init__` o construcción no-validada imposible); propagación de un mismo perfil a admisión, servicio y host (p. ej. `from_config`); el adaptador valida los rangos completos; prueba de igualdad configuración-declarada == configuración-aplicada.
- **Regresión mínima:** construcción directa inválida rechazada en toda frontera pública; divergencia grace declarado/aplicado detectada; `audit_mode=required` imposible por cualquier constructor.
- **Gates:** G-M2-01, G-M2-11, G-M2-12 (criterio 9). **Cierre:** igualdad declarada/aplicada demostrada en ambas plataformas.

### FIX-M2-R7 — Conformidad literal con ADR-012 §2.3 (P2) — OAI-M2-04

- **Causa raíz:** G-G. **Archivos permitidos:** `src/application/config.py` (valores emitidos), `src/application/admit.py`, `tests/unit/test_m2_config.py` (el test codifica el valor desviado; su corrección es de conformidad, no de funcionalidad), pruebas de igualdad completas.
- **Incorrecto:** `useful_runtime_formula=useful_runtime_ms=deadline_eff_ms-min(termination_grace_ms,deadline_eff_ms)` y `supervisor_scope=per_action` en lugar de las strings congeladas `useful_runtime_formula=deadline_eff_ms-applied_grace_ms` y `supervisor_scope=per_action_process`.
- **Requerido:** las entradas `clave=valor` de `assumptions` idénticas, en orden y forma, a las congeladas por ADR-012.
- **Regresión mínima:** test de igualdad de la tupla completa contra los literales del acta (no sólo claves).
- **Gates:** G-M2-11, G-M2-01. **Cierre:** tupla idéntica al acta verificada en ambas plataformas. Nota normativa: esto **conforma** la implementación al contrato vigente; no lo modifica.

### FIX-M2-R8 — Causalidad «primer hecho observado» terminate/deadline (P2) — OAI-M2-05

- **Causa raíz:** G-H. **Archivos permitidos:** `src/adapters/posix_supervisor.py`, `src/domain/execution_result.py`, `src/application/start_service.py`, pruebas nuevas.
- **Incorrecto:** con `deadline_hit` y `externally_terminated` ambos verdaderos, `classify()` devuelve `deadline_exceeded` sin información de orden, contraviniendo D-M2-4 (primer hecho gana; empate → deadline).
- **Requerido:** el supervisor registra el orden de observación (o causa primera) y la clasificación lo respeta; en empate real, deadline.
- **Regresión mínima:** proceso que ignora TERM con `terminate` claramente anterior al soft deadline → `terminated/external_termination`; carrera simultánea → `deadline_exceeded`.
- **Gates:** G-M2-10, G-M2-09. **Cierre:** precedencia observada correcta en ambas plataformas.

### FIX-M2-R9 — KILL de grupo incondicional tras la escalación (P2) — EXT3-03

- **Causa raíz:** G-I. **Archivos permitidos:** `src/adapters/posix_supervisor.py`, pruebas nuevas.
- **Incorrecto:** al vencer `hard_deadline_at` el KILL sólo se envía si el líder vive; un descendiente del grupo gobernado que ignora TERM y cuyo líder murió con TERM sobrevive sin declaración.
- **Requerido:** alcanzada la escalación, intentar `killpg` del grupo con independencia del estado del líder (el `ProcessLookupError` ya se tolera) y declarar el hecho en `measurements`; los escapes reales (`setsid`) siguen declarándose como tales.
- **Regresión mínima:** combinación líder-obedece/nieto-ignora → nieto muerto al hard deadline (o hecho declarado si la plataforma no permite alcanzarlo); la combinación líder-ignora sigue cubierta por el test existente.
- **Gates:** G-M2-11, G-M2-09. **Cierre:** la propiedad «descendiente observado muere con el grupo» demostrada también en la combinación no cubierta.

### FIX-M2-R10 — Fe de erratas del encargo (P2, documental) — fusiona F3, EXT3-05

- **Contenido:** nota de prevalencia o fe de erratas en el encargo (o acta propia) que deje constancia de que la enmienda G-M2-12 fue aprobada y asentada antes del REVIEW-ROOT, que la promoción a VERDE es legítima, y que §4.1 del encargo quedó stale. No se reescribe el REVIEW-ROOT congelado: la corrección vive en documento posterior.
- **Cierre:** nota asentada y citada por el expediente.

### FIX-M2-R11 — Citación exacta de la evidencia de fuzz (P3, documental) — EXT3-06

- **Contenido:** la evidencia debe citar semilla, iteraciones exactas y comando de cada fuzzer (o corregir la cifra «3000» a lo realmente ejecutado).
- **Cierre:** `estado-evidencia` reproducible al dígito contra logs o comando declarado.

## 9. Gates afectados (reapertura)

| Gate | Motivo | Obligaciones |
|---|---|---|
| G-M2-05 | concurrencia de `await_result` | FIX-M2-R2 |
| G-M2-06 | retención post-spawn indeterminada | FIX-M2-R5 |
| G-M2-01 | validación de configuración | FIX-M2-R6, FIX-M2-R7 |
| G-M2-09 | causa por vigencia; precedencia terminate/deadline; KILL de grupo | FIX-M2-R1, FIX-M2-R8, FIX-M2-R9 |
| G-M2-10 | frontera de `await_result`; handoff único | FIX-M2-R2, FIX-M2-R3, FIX-M2-R4, FIX-M2-R8 |
| G-M2-11 | descendientes en el grupo; strings congeladas; declared/applied | FIX-M2-R6, FIX-M2-R7, FIX-M2-R9 |
| G-M2-12 | criterios 5, 7 y 9 de la enmienda | FIX-M2-R2, FIX-M2-R3, FIX-M2-R5, FIX-M2-R6 |
| G-M2-14 | regresión completa tras los fixes | todas |
| G-M2-15 | re-verificación externa del diff correctivo | todas |

## 10. Gaps normativos

Ninguna obligación requiere schema nuevo, contrato wire, M3/M4, capability,
sandboxing o rutas fuera del inventario autorizado. Todas se declaran:

**FIX-WITHIN-AUTHORIZED-M2.**

Notas: FIX-M2-R7 **conforma** la implementación a las strings congeladas por
ADR-012 (no modifica contrato); FIX-M2-R4 no anticipa contrato nuevo de handle
— si su resolución lo exigiera, se detendrá ese incremento y se declarará
`BLOCKED-BY-NORMATIVE-GAP` en ese momento, sin ampliar M2 silenciosamente.

## 11. Estado final de G-M2-15

```
collection         = COMPLETE
reconciliation     = COMPLETE
corrective_action  = REQUIRED
G-M2-15            = NOT-CONFORMING / FIX-AND-RETRY
M2                 = OPEN
M3                 = BLOCKED
```

`reconciliation = COMPLETE` significa únicamente que el expediente ya sabe
**qué** debe corregirse (11 obligaciones, 3 de ellas P1). No significa que
esté corregido. G-M2-15 no puede promoverse mientras existan findings
materiales aceptados sin corregir y re-verificar. G-M2-15 no puede promoverse
mientras ese estado persista. La implementación correctiva
comienza en el acto siguiente, obligación por obligación, con reejecución de
los gates afectados y revisión externa del diff correctivo.
