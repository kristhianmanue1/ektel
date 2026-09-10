# Informe externo 3 de 3 — G-M2-15

> **CONSERVADO ÍNTEGRO. NO RECONCILIADO.** Este documento es el informe
> original del revisor, transcrito sin edición de contenido. No representa la
> posición del proyecto, no promueve ni degrada ningún gate, y **no se actúa
> sobre él hasta la reconciliación formal de los tres informes originales**.
> La única adición respecto del texto emitido por el revisor es esta cabecera
> de provenance y la tabla de identidad de la corrida.

## Identidad del revisor y de la corrida

| Qué | Valor |
|---|---|
| Revisor | **OpenCode — GLM 5.3 Flash** |
| Rol | tercer revisor externo e independiente del agente ejecutor de M2 |
| Fecha | 2026-09-09 |
| Orden de recepción | **3 de 3** |
| REVIEW-ROOT evaluado | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` |
| MANIFEST-ROOT reproducido | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |
| Veredicto | **FIX-AND-RETRY** — P0: 0 · P1: 2 · P2: 1 · P3: 4 |
| Nivel de ejecución | suite Darwin arm64 completa reejecutada (339 OK, 4 skips), `mypy --strict src` limpio, ambos fuzzers ejecutados, 3 sondas adversariales reproducidas en ejecución; Linux aarch64 **no** reejecutado |
| Repositorio | no modificado por el revisor; HEAD final = REVIEW-ROOT; árbol limpio; sondas en `/tmp` |

---

# Informe de revisión adversarial externa — EKTEL M2 (G-M2-15)

**Tercer revisor externo e independiente.** No he consultado informes de otros revisores, `docs/revisiones/g-m2-15/`, `main`, `origin/main` ni commits posteriores. No he modificado el repositorio ni hecho commits.

## 1. Identidad y entorno

| Verificación | Resultado |
|---|---|
| `git rev-parse HEAD` | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` = REVIEW-ROOT ✔ |
| `git status --porcelain` | vacío ✔ |
| `shasum -a 256 manifest-m2-sha256.txt` | `3e2110174ebe…9524ae` = MANIFEST-ROOT ✔ |
| Regeneración del manifiesto (comando del encargo) | **diff cero en las 95 entradas**; la única línea que difiere es la cabecera, porque el comando del encargo abrevia el hash padre (`31b4e4e...`) y el archivo lleva el completo. Declarado; no es divergencia de contenido |
| `merge-base --is-ancestor 55579bd…` | descendiente de la raíz congelada ✔ |
| SO / arquitectura | macOS (Darwin 25) / **arm64** |
| Python | **3.12.12** (venv del repo) |
| Suite | **339 tests OK, 4 skips** — los 4 son caracterización Linux-only (`test_host_characterization` ×3, `test_supervisor_characterization` ×1), declarados |
| `mypy --strict src` | **limpio, 34 archivos** |
| `fuzz_admision.py` | sin divergencias ni aceptaciones ambiguas |
| `fuzz_start_revalidation.py` | 2000 iteraciones, `"crashes": [], "divergencias": [], "gate": "OK"` |

**Limitaciones:** plataforma única (Darwin arm64); no reejecuté la clase V Linux. Sondas en `/tmp`, nunca dentro del repo. Nota menor de higiene: la suite emite `ResourceWarning` de subprocesos aún vivos en GC (el test de higiene de supervisores pasa con `<20`); es cosmético.

## 2. Findings

---

### EKTEL-M2-EXT3-01 — La causa `deadline_validity_exhausted` es inalcanzable end-to-end: `validity_bound` se calcula, se transporta y se descarta · P1 — **REPRODUCIDO EN EJECUCIÓN**

- **Ubicación:** `src/application/start_service.py:215-218` (calcula `validity_bound` pre-CAS y lo pasa a `spawn`), `src/adapters/posix_supervisor.py:485-540` (`spawn` lo guarda en `SupervisedAction.validity_bound` pero **no lo incluye en el plan JSON**), `posix_supervisor.py:390-429` (el dict `terminal` **no emite `validity_bound`**), `start_service.py:385-389` (`_build_awaited` lee `raw.get("validity_bound")` → siempre `False`).
- **Claim/gate afectado:** D-M2-3 (ADR-012: «`deadline_validity_exhausted` gana cuando la vigencia restante pre-CAS es menor o igual que `deadline_ms`; en empate gana vigencia»), spec §12.8, C4 (resultado tipado por causa), **G-M2-09 declarado VERDE** en `estado-evidencia-m2-2026-09-09.md`.
- **Reproducción:** sonda en `/tmp` con host real: `exp` a 500 ms, `deadline_ms=30000`, `time.sleep(60)`, gracia 200 ms. `remaining_validity (≈500) <= deadline (30000)` → la norma exige `deadline_validity_exhausted`.
- **Esperado:** `cause=deadline_validity_exhausted`.
- **Observado:** `cause=deadline_duration` (`ES deadline_validity_exhausted: False`). La regla de empate y de acotamiento por vigencia sólo existe en `tests/unit/test_deadline_math.py` contra la función pura `classify`/`validity_exhausted`; **ninguna prueba de integración la ejerce con el host real** (la única de causa real usa deadline de duración pura).
- **Causa raíz:** el dato se pierde en la frontera adaptador→terminal; `SupervisedAction.validity_bound` es un campo muerto.
- **Consecuencia:** toda acción cuyo plazo fue recortado por vigencia del token —caso común cerca de `exp`— reporta una causa wire incorrecta; un gate declarado verde con una propiedad que sólo vive en unitarios.
- **Recomendación:** propagar `validity_bound` en el plan JSON, emitirlo en `terminal`, y añadir una prueba end-to-end con vigencia acotada. Reejecutar G-M2-09.

---

### EKTEL-M2-EXT3-02 — El slot no se libera en el handoff terminal real: handle terminado y abandonado agota la capacidad permanentemente · P1 — **REPRODUCIDO EN EJECUCIÓN**

- **Ubicación:** `src/application/start_service.py:337-368` (`await_result`/`_release_handle` son la **única** ruta de liberación post-spawn), `src/adapters/posix_supervisor.py:611-624` (el terminal se entrega sólo cuando alguien llama `await_terminal`/`collect_terminal`).
- **Claim/gate afectado:** D-M2-2(a) (ADR-012: «El slot se libera en fallo pre-spawn o **cuando el resultado terminal y su salida pasan a ser propiedad del handle**»), G-M2-12 criterio 7 («Liberación correcta de capacidad — CUMPLE»), spec §12.6.
- **Reproducción:** sonda con capacidad 1 y host real: `start` de una acción que termina en milisegundos; **no** se llama `await_result`; se espera 4 s (proceso recogido, `T` frame procesado).
- **Esperado:** el handoff terminal libera el slot; la segunda acción arranca.
- **Observado:** `slots_in_use == 1` tras el termino; la segunda acción → `StartFailed(capacity:no_slot)`. Además `PosixSupervisorHost._actions[ref]` retiene el `SupervisedAction` con stdout/stderr para siempre (el pop sólo ocurre en `await_terminal`), y `StartService._handles` retiene el handle. Variante agravada: si el supervisor muere sin terminal, `await_result` devuelve `None` **sin liberar el slot** y no existe API de recuperación.
- **Causa raíz:** no hay transferencia en segundo plano coordinador→handle; la liberación quedó acoplada a `await_result`. Las pruebas que acreditan el criterio (`CapacidadTests`) usan el doble determinista y **fabrican el handoff manualmente** con `handle.store_terminal_result(...)` — la propiedad se verifica en una ruta que el host real nunca toma.
- **Consecuencia:** con `max_concurrent_actions` agotado por abandonos, el coordinador queda inutilizable sin reinicio; contradice tests==código!=ADR y el veredicto CUMPLE del acta de enmienda.
- **Recomendación:** liberar el slot cuando `_collect` recibe `T`/`X` (o en el primer `done`), y pruebas end-to-end de abandono y de muerte del supervisor. Reejecutar G-M2-12 (criterio 7) y G-M2-10.

---

### EKTEL-M2-EXT3-03 — El KILL de grupo no se dispara si el líder murió con TERM: descendiente en el mismo grupo que ignora TERM sobrevive al hard deadline · P2 — **REPRODUCIDO EN EJECUCIÓN**

- **Ubicación:** `src/adapters/posix_supervisor.py:311-328` (`deadline_watchdog`: `if child.poll() is None: killed.set(); kill_group()` — el KILL está condicionado a que el líder siga vivo).
- **Claim/gate afectado:** C3 («terminación dirigida del grupo observado»), G-M2-11 («se mide que el descendiente observado muere con el grupo»), comentario del propio test `test_kill_mas_pipes_retenidos_declara_cierre_forzado` («un nieto que permanece en el grupo también recibe el KILL»). Los escapes declarados son `setsid`/double-fork; este descendiente **nunca salió del grupo**.
- **Reproducción:** sonda: líder con handler de TERM que sale limpiamente; nieto **en el mismo grupo** con `SIGTERM=SIG_IGN`; gracia 300 ms, deadline 1500 ms.
- **Esperado:** el KILL del grupo alcanza al nieto observado (como afirma el test contraparte).
- **Observado:** líder `returncode 0` (murió con TERM), `killed=False` (el KILL nunca se envió: `poll()` ya no era `None`), **nieto vivo tras el hard deadline** (pid 71879; eliminado por el revisor). El terminal declara `eof_drain_forced_close=True` —un hecho de pipes— sin ningún indicador del descendiente superviviente. La suite cubre «líder ignora TERM» (KILL llega) y «nieto obedece TERM» (muere), pero **no la combinación** líder-obedece/nieto-ignora.
- **Causa raíz:** gating del KILL por lividad del líder en lugar de dispararlo incondicionalmente al alcanzar `hard_deadline_at` si hubo escalación.
- **Consecuencia:** fuga de proceso más allá del plazo sin declaración de escape; la evidencia de G-M2-11 es más estrecha que la propiedad que C3 y el test contraparte afirman. N4 atenúa (no hay promesa de muerte universal), pero el mecanismo existe y falla silenciosamente en una clase no declarada.
- **Recomendación:** al vencer `hard_deadline_at`, intentar `killpg` una vez sea cual sea el estado del líder (el fallo `ProcessLookupError` ya se traga), y declarar el resultado en `measurements`. Añadir la prueba de la combinación.

---

### EKTEL-M2-EXT3-04 — `await_result` no autentica nada y puede devolver un resultado fabricado vía `store_terminal_result` pública · P3 — **CONFIRMADO POR INSPECCIÓN ESTÁTICA**

- **Ubicación:** `src/application/start_service.py:337-362` (sin verificación de token ni de registro), `src/domain/execution_handle.py:84-94` (`store_terminal_result` pública, acepta objeto arbitrario), `start_service.py:352-357` (devuelve lo almacenado **sin tipar**).
- **Claim afectado:** simetría con D-M2-4 (`terminate` rechaza handle forjado/cruzado con MAC; `await_result` acepta cualquier objeto con un `handle_ref` de 16 hex —el identificador que sí circula por el cable—); obligación de falsificación 5 («resultado fabricado»).
- **Esperado (hipótesis de falsificación):** un handle fabricado no debería poder recolectar la salida de una acción ajena ni liberar su slot.
- **Observado:** un `ExecutionHandle` construido directamente con un `handle_ref` válido colecciona el `AwaitedExecution` de esa acción, expulsa el handle real de `_handles` y libera el slot. Asimismo, cualquier tenedor puede `store_terminal_result` y hacer que `await_result` entregue un objeto arbitrario no tipado (la propia suite lo usa como atajo).
- **Causa raíz:** la autenticación se implementó sólo en `terminate`; el modelo de amenaza de un solo proceso lo abarata, pero la asimetría es real y la firma `-> object` no garantiza el tipo prometido en la docstring.
- **Consecuencia:** dentro del proceso, exfiltración de salida de acciones ajenas y confusión de tipos; sin impacto cross-proceso.
- **Recomendación:** verificar registro/instancia en `await_result` (y fechar el token si se quiere simetría) o declarar explícitamente la confianza en el llamador in-proceso; restringir `store_terminal_result` a la ruta del coordinador.

---

### EKTEL-M2-EXT3-05 — Los documentos del mismo árbol se contradicen sobre el estado de G-M2-12 · P3 — **DOCUMENTAL**

`docs/revisiones/encargo-revision-externa-m2-2026-09-09.md` §4.1 ordena: «G-M2-12 está PARCIAL y su enmienda es un borrador sin firmar. Un revisor que lo trate como verde está equivocado». Pero `docs/decisiones/enmienda-g-m2-12-2026-09-09.md` registra la enmienda **aprobada** por el dueño, la reevaluación de los diez criterios y `G-M2-12 = VERDE`, y `estado-evidencia-m2-2026-09-09.md` lo promueve. El encargo quedó stale respecto del acta. **Recomendación:** corregir el encargo o asentar nota de prevalencia (acta > encargo).

### EKTEL-M2-EXT3-06 — Evidencia de fuzz no reproducible al dígito · P3 — **DOCUMENTAL**

G-M2-01 en `estado-evidencia` afirma «fuzz de 3000 iteraciones»; `scripts/fuzz_start_revalidation.py:90` tiene default **2000** y mi corrida por defecto ejecutó 2000. No es falsificable sin el log de la corrida original. **Recomendación:** citar semilla e iteraciones exactas en la evidencia.

### EKTEL-M2-EXT3-07 — Autoridad temporal duplicada con validación más débil en el adaptador que aplica TERM→KILL · P3 — **CONFIRMADO POR INSPECCIÓN ESTÁTICA**

`PosixSupervisorHost.__init__` valida `termination_grace_ms >= 0` y `post_kill_drain_ms > 0` pero **no** los techos 60000/10000 de D-M2-3, que sólo aplica `M2Config.build()`; además introduce `credit_timeout_ms`/`eof_drain_timeout_ms` (rangos en `config.py`, defaults espejados en el adaptador) que no constan en la tabla congelada de ADR-012 §2.3. Un despliegue que construya el host directamente se salta los rangos normativos. **Recomendación:** unificar la validación en un único punto (inyectar `M2Config` o extraer el validador) y documentar los dos parámetros nuevos como configuración local M2.

---

## 3. Tabla de obligaciones 1–16

| # | Obligación | Resultado |
|---|---|---|
| 1 | CAS → spawn: sólo CONSUMED crea proceso | **NO FALSIFICADA** (comparación por identidad; truthy/subtipos/tipos ajenos sin autoridad; sin dependencia inyectable entre CAS y spawn) |
| 2 | Reconciliación spent/unspent/unknown | **NO FALSIFICADA** (matriz exacta de ADR-011 §2.6; `__eq__` mentiroso y tipos hostiles rechazados; `unspent` nunca spawn directo) |
| 3 | Capacidad / doble liberación | **FALSIFICADA** (la cota se mantiene bajo carrera de 16 hilos, pero EXT3-02: slot no liberado en handoff real → agotamiento permanente; doble liberación con clamping no rompe la cota) |
| 4 | Handles forjados/cross/otra acción | **NO FALSIFICADA** para `terminate` (MAC por instancia+digest+acción; ver tests y código); ver EXT3-04 para la asimetría de `await_result` (P3) |
| 5 | terminate/await_result: doble efecto/resultado | **NO FALSIFICADA** en `terminate` (mismo receipt, un solo efecto, post-resultado no contacta ni reclasifica); matiz EXT3-04 |
| 6 | Deadlines y causalidad end-to-end | **FALSIFICADA** (EXT3-01: causa por vigencia inalcanzable end-to-end; la aritmética `ceil_exact_ms`, plazo cero pre-CAS y empates pura es correcta) |
| 7 | TERM→KILL | **NO FALSIFICADA** para el líder (ignora TERM/TERM+STOP → KILL medido, `-9`); el defecto del grupo es EXT3-03 |
| 8 | Backpressure y créditos | **NO FALSIFICADA** (frames ≤64 KiB, `max_unacked ≤ 1` medido, coordinador lento conserva prefijo (R3), canal cerrado degrada sin esperar la cota) |
| 9 | No-hang/pipes/stdin/descendientes-flood | **NO FALSIFICADA** (stdin 1 MiB no leído, flood, nieto con pipes: todo acotado; cierre forzado declarado) |
| 10 | Crash durability | **NO FALSIFICADA** (SIGKILL real antes/después del CAS sobre `FileReplayStore`: `unspent` reconsumible / `spent` irreabrible; sin handle fabricado) |
| 11 | Descendientes gobernados vs escapes | **FALSIFICADA** (EXT3-03: descendiente en el grupo sobrevive al KILL que no se dispara; el escape declarado es sólo `setsid`) |
| 12 | Linux/Darwin sin divergencias no declaradas | **NO FALSIFICADA en Darwin** — skips declarados, subreaper Linux-only y Darwin `unsupported` declarados en código y tests. La clase V Linux no fue reejecutable en este host: **limitación declarada**, no hallazgo |
| 13 | Regresión M1 | **NO FALSIFICADA** (`admit.py` sólo aditivo y byte-idéntico con `m2_config=None`; `SpawnFrontier` y sus 20 pruebas intactas; `__init__` sólo añaden; suite completa verde) |
| 14 | Claims más fuertes que la evidencia | **FALSIFICADA** (G-M2-09 y G-M2-12-criterio 7 sobreafirmados: EXT3-01 y EXT3-02; contradicción documental EXT3-05; EXT3-06) |
| 15 | TCB no autorizada | **NO FALSIFICADA** (stdlib-only; `ctypes`→`prctl` única excepción declarada de ADR-006; cero dependencias runtime nuevas; `contracts/` intacto) |
| 16 | Alcance (nada M3/M4, schemas, workflows) | **NO FALSIFICADA** (las 28 rutas del diff `4beb7ebe..HEAD -- src tests scripts` están una a una en el inventario de 45; sin schemas, sin workflows, sin tag/release; M3 no iniciado; `audit_mode=required` impide inicializar) |

## 4. Veredicto

## **FIX-AND-RETRY**

Fundamento: dos hallazgos **P1 reproducidos en ejecución** (EXT3-01 causa wire incorrecta sistemática; EXT3-02 agotamiento permanente de capacidad con hosts reales) y un P2 reproducido (EXT3-03). Ninguno compromete la frontera de seguridad (CAS, replay, fail-closed y regresión M1 se mantienen íntegros), por lo que no procede NO-GO; pero conforme al encargo §6, un hallazgo material reproducible debe resolverse aunque el resto esté verde. Tras corregir: reejecutar gates afectados (G-M2-09, G-M2-10, G-M2-11, G-M2-12-criterio 7), regresión completa en ambas plataformas, actualizar manifiesto y solicitar re-verificación externa del diff correctivo.

## 5. Estado final

```
eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e   (= REVIEW-ROOT)
git status --porcelain  →  vacío (árbol limpio)
```

🎙 jarvis: ektel · verificación · He intentado romper cada promesa del árbol congelado y tres cayeron con pruebas en mano: la causa por vigencia no llega al resultado, un handle abandonado agota la capacidad para siempre y un nieto del grupo escapa del KILL si el líder murió con TERM. Todo lo demás —el CAS, el replay, la frontera M1— se mantuvo en pie; queda servido el veredicto: corregir y reintentar.
