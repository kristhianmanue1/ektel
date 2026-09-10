# Informe externo 2 de 3 — G-M2-15

> **CONSERVADO ÍNTEGRO. NO RECONCILIADO.** Este documento es el informe
> original del revisor, transcrito sin edición de contenido. No representa la
> posición del proyecto, no promueve ni degrada ningún gate, y **no se actúa
> sobre él hasta disponer de los tres informes originales**.

## Identidad del revisor y de la corrida

| Qué | Valor |
|---|---|
| Revisor | **Qwen — familia Alibaba/Qwen** |
| Rol | revisor externo independiente del agente ejecutor de M2 |
| Fecha | 2026-09-09 |
| Orden de recepción | **2 de 3** |
| REVIEW-ROOT evaluado | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` (checkout detached verificado, árbol limpio) |
| MANIFEST-ROOT reproducido | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` (95/95 hashes idénticos; única diferencia: comentario de cabecera con SHA de padre truncado en el comando del encargo) |
| Veredicto | **FIX-AND-RETRY** — P0: 0 · P1: 2 · P2: 1 · P3: 2 |

## Nivel de ejecución declarado por el revisor

- **Suite Darwin completa reejecutada: sí** — `python -m unittest discover`:
  **339 OK, 4 skips** (coincidente con la línea base declarada);
  `mypy --strict src` limpio en 34 archivos.
- **Suite Linux: NO reejecutada** (limitación declarada; la evidencia Linux
  queda sin verificación independiente de este revisor).
- **Sondas adversariales propias:** 3 scripts ejecutados **fuera del
  repositorio** (`/tmp`), con procesos y store reales; conservadas por
  provenance en `sondas-qwen/` junto a este informe. Conservarlas **no** es
  verificarlas: la comprobación de las reproducciones de este revisor
  corresponde a la fase posterior, no a este asiento.

## Metadata exposure declarada — sin reinterpretar

El harness del revisor inyectó al inicio de su sesión un snapshot de git que
reveló la **existencia y el título** de un commit posterior al REVIEW-ROOT:
`fa3ce89` ("docs(G-M2-15): conservar informe externo 1 de 3 — SIN
reconciliar"). El revisor declara no haber leído su contenido, ni el informe
OpenAI, ni `docs/revisiones/g-m2-15/`, ni ningún artefacto posterior al
REVIEW-ROOT antes de emitir su veredicto.

Esto se clasifica únicamente como **metadata exposure declarada**. Este asiento
**no** concluye si invalida, reduce o no afecta la independencia: eso pertenece
a la reconciliación posterior.

---

# INFORME DE REVISIÓN ADVERSARIAL EXTERNA — EKTEL M2 (G-M2-15)

**Revisor:** Qwen (familia de modelo Alibaba/Qwen), externo e independiente.
**Fecha:** 2026-09-09.
**Modalidad:** primer veredicto, derivado exclusivamente del objeto congelado.
Sin reconciliación con otros revisores.

**REVIEW-ROOT:** `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e`
**MANIFEST-ROOT:** `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae`

---

## 1. Verificación de identidad (§1 del protocolo)

| Comprobación | Resultado |
|---|---|
| `git checkout --detach eb5590b…` → `git rev-parse HEAD` | `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e` ✅ exacto |
| `git status --porcelain` | vacío ✅ |
| `shasum -a 256 docs/evidencia/manifest-m2-sha256.txt` | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` ✅ = MANIFEST-ROOT |
| Ancestro `55579bd` | descendiente confirmado ✅ |
| Regeneración del manifiesto | **95/95 hashes idénticos**. La única diferencia es el comentario de cabecera: el encargo trunca el SHA del padre (`31b4e4e...`) y el manifiesto lo lleva completo. Defecto del comando del encargo, no del árbol. Identidad de código reproducida ✅ |

## 2. Declaración de ejecución (§6)

- **Plataforma:** Darwin 25.6.0, macOS 26.6.2 (25G83), **arm64**.
- **Python:** 3.12.12 (`.venv` del proyecto). El `python3` del sistema es 3.9.6 y no se usó.
- **Suite completa reejecutada:** sí — `python -m unittest discover -s tests -t .`:
  **339 OK, 4 skips, 104 s**, coincidente con la línea base Darwin declarada.
  (Nota: `pytest` no existe en el venv; la suite es unittest.)
- **`mypy --strict src`:** reejecutado, limpio en 34 archivos ✅.
- **Sondas adversariales propias:** 3 scripts en `/tmp` (nunca en el repositorio),
  con procesos y store reales; se citan en cada hallazgo:
  - `/tmp/probe_gm215_1_validity_bound.py`
  - `/tmp/probe_gm215_2_await_race.py`
  - `/tmp/probe_gm215_3_cas_zero.py`
- **Limitaciones:**
  - (a) **No reejecuté la suite Linux aarch64** — la evidencia Linux (339 OK,
    1 skip, subreaper aplicado, F_FULLFSYNC n/a) queda sin verificación
    independiente mía.
  - (b) No ejecuté pruebas de presión extrema (excluidas por §2.2 del paquete).
  - (c) El snapshot de git inyectado al inicio de mi sesión reveló la
    *existencia* de un commit posterior en `main` (`fa3ce89`, "informe externo
    1 de 3"); **no leí su contenido ni ningún artefacto posterior al
    REVIEW-ROOT**, pero la exposición del título queda declarada para la
    reconciliación.

## 3. Hallazgos

### F1 — `deadline_validity_exhausted` inalcanzable en la ruta real · **P1 · CONFIRMADO Y REPRODUCIDO**

- **Ubicación:** `src/application/start_service.py:387` (`_build_awaited`),
  `src/adapters/posix_supervisor.py:536` y diccionario `terminal` de
  `_supervisor_main` (~l. 380-430).
- **Claim afectado:** alcance técnico §8 / D-M2-3 / ADR-005: «empate
  duración/vigencia → **gana vigencia** (`deadline_validity_exhausted`)»;
  G-M2-09 declarado verde con «aritmética pura completa y TERM→KILL con
  procesos reales».
- **Reproducción:** sonda `/tmp/probe_gm215_1_validity_bound.py`. Token con
  `exp = NOW+3`, `deadline_ms = 5000`, reloj de start `NOW+1` →
  `remaining ≈ 2000 ms < 5000` ⇒ `validity_bound = True`, plazo efectivo
  2000 ms. Comando real `/bin/sleep 5` bajo `PosixSupervisorHost` +
  `FileReplayStore` reales.
- **Resultado observado:** `outcome=deadline_exceeded`,
  `deadline_effective_ms=2000`, pero **`cause=deadline_duration`** en lugar de
  `deadline_validity_exhausted`.
- **Causa raíz:** `StartService._start_with_slot` calcula `validity_bound` y lo
  pasa a `host.spawn(…, validity_bound=…)`, que lo guarda en
  `SupervisedAction.validity_bound` — y ahí muere: **nunca se fusiona en el
  dict `terminal`** (el supervisor tampoco lo recibe ni lo emite;
  `PosixSupervisorHost._validity_bound` es un dict muerto, ver F4).
  `_build_awaited` lee `raw.get("validity_bound")` → siempre `None` → `False`.
  Las pruebas unitarias sólo ejercitan `classify()` puro; ninguna prueba
  end-to-end atraviesa StartService+host real con vigencia acotada (grep:
  `deadline_validity_exhausted` sólo aparece en `test_deadline_math.py`).
- **Agravante de proceso:** la ronda propia inc1-3 ya advirtió (informativo,
  l. 149) que `validity_exhausted` estaba «definida y sin uso; su consumidor
  llega en INC-M2-4». INC-M2-4 añadió el consumidor pero **no completó el
  cableado**, y el gate se declaró verde.
- **Consecuencia:** el resultado wire reporta sistemáticamente la causa de
  plazo **equivocada** cuando la vigencia (no la duración pedida) acotó la
  ejecución. En un producto cuyo valor es la tipificación honesta del
  resultado, la distinción entre las dos causas de plazo es parte del
  contrato, y hoy es código muerto en la ruta real.
- **Recomendación:** fusionar `action.validity_bound` en el `raw` del handoff
  (p. ej. en `PosixSupervisorHost.collect_terminal`,
  `raw = dict(action.terminal); raw["validity_bound"] = action.validity_bound`)
  y añadir prueba de integración que aserte
  `cause == deadline_validity_exhausted` con proceso real.

### F2 — Carrera en `await_terminal`: doble entrega del resultado y doble liberación de slot → sobre-admisión por encima de `max_concurrent_actions` · **P1 · CONFIRMADO Y REPRODUCIDO**

- **Ubicación:** `src/adapters/posix_supervisor.py`, `await_terminal`
  (~l. 613-625): `get` → `done.wait` → `pop` **no atómicos**, y el valor del
  `pop` se descarta; `src/application/start_service.py`, `await_result` +
  `_release_handle`.
- **Claims afectados:** D-M2-2(a) cota de capacidad (`max_concurrent_actions`
  no excedible); D-M2-4 «el handoff transfiere la propiedad **una vez**,
  linealizado atómicamente en el handle»; criterio 5 de la enmienda G-M2-12
  («`max_concurrent_actions` bajo concurrencia real — CUMPLE»); obligaciones 3
  y 5 del encargo.
- **Reproducción:** sonda `/tmp/probe_gm215_2_await_race.py`. Dos hilos con
  `Barrier` llaman `await_result` sobre el **mismo** handle ya completado.
- **Resultado observado:** **doble entrega 40/40 iteraciones** (determinista,
  no heisenbug): ambos hilos reciben un `AwaitedExecution`. Ambos ejecutan
  `_release_handle` → `_slots.release()` **dos veces por una sola acción**.
  Demostración de consecuencia con `max_concurrent_actions=2`: con una acción
  larga (`/bin/sleep 4`) viva, `slots_in_use` cayó a **0** (esperado 1) y se
  admitieron **2 starts adicionales** ⇒ 3 procesos supervisados vivos
  simultáneos con capacidad 2.
- **Causa raíz:** ambos llamadores obtienen el mismo `SupervisedAction` (el
  `get` de ambos ocurre antes del `pop` de cualquiera), `done.wait` retorna
  inmediato para los dos, y el `pop(…, None)` del perdedor devuelve `None`
  **sin que se consulte**; los dos retornan la acción y fabrican handoffs
  gemelos.
- **Atenuante honesto:** requiere dos `await_result` concurrentes sobre el
  mismo handle. Pero (a) la clase se presenta como thread-safe y las pruebas
  de concurrencia son parte del gate; (b) el daño **no queda confinado al
  handle mal usado**: corrompe el contador global de capacidad y permite
  excederla para acciones inocentes; (c) viola la unicidad de propiedad del
  handoff (D-M2-4).
- **Recomendación:** transferir la propiedad con el `pop` mismo: esperar
  `done` sobre una referencia leída, y luego
  `with self._lock: action = self._actions.pop(handle_ref, None); if action is None: return None`.
  El segundo llamador recibe `None` (ausencia honesta) y no libera slot.
  Añadir prueba de regresión con barrera.

### F3 — El encargo normativo contradice al árbol que congela · **P2 · CONFIRMADO (documental)**

§4.1 del encargo declara G-M2-12 «PARCIAL, borrador sin firmar» cuando el
mismo REVIEW-ROOT contiene el acta firmada y el gate promovido.

- **Ubicación:** `docs/revisiones/encargo-revision-externa-m2-2026-09-09.md`
  §4.1 vs `docs/decisiones/enmienda-g-m2-12-2026-09-09.md` (acta con
  transcripción íntegra de la aprobación del dueño) y
  `docs/evidencia/estado-evidencia-m2-2026-09-09.md` («G-M2-12 = VERDE bajo
  criterio enmendado»).
- **Evidencia:** `git show eb5590b` confirma que el commit que asentó la
  enmienda **no tocó el encargo**; el texto «Un revisor que lo trate como
  verde está equivocado» quedó fosilizado en la raíz congelada.
- **Claim afectado:** obligación 14 («gates parciales leídos como verdes») en
  ambas direcciones: un revisor literalista trataría como defecto un gate
  legítimamente promovido; otro podría tratar como válida una instrucción del
  encargo que el árbol desmiente.
- **Consecuencia:** riesgo de contaminación de la reconciliación de los tres
  revisores.
- **Recomendación:** fe de erratas al encargo (o nota de reconciliación) que
  refleje que la enmienda fue aprobada y asentada **antes** del REVIEW-ROOT.
  Mi evaluación independiente: la promoción es legítima — el acta existe, la
  reevaluación de los diez criterios está documentada con pruebas citadas, y
  verifiqué que la formulación prohibida («se probó 16 GiB») no aparece en
  ninguna parte del árbol.

### F4 — Código muerto: `PosixSupervisorHost._validity_bound` · **P3 · CONFIRMADO**

- **Ubicación:** `src/adapters/posix_supervisor.py:477`. Dict inicializado,
  jamás escrito ni leído.
- **Consecuencia:** vestigio del cableado incompleto de F1; sugiere una
  propagación que no existe.
- **Recomendación:** eliminarlo o completarlo como parte del fix de F1.

### F5 — Inconsistencia interna: `spawn:handle_ref_invalid` libera el slot pero reporta indeterminado · **P3 · HIPÓTESIS — NO REPRODUCIDA** (inalcanzable con los adaptadores entregados)

- **Ubicación:** `src/application/start_service.py`, `_spawn` (~l. 277-279):
  si el host devuelve un `handle_ref` de tipo/longitud inválidos, se libera el
  slot y se devuelve `start_failed_indeterminate` **sin registrar en
  `_retained`** — contrario al principio H5 que la propia clase aplica dos
  líneas antes (indeterminado ⇒ slot retenido y observable, porque podría
  haber un proceso vivo).
- **Reproducción:** sólo con un adaptador `ProcessHost` defectuoso/hostil; el
  host POSIX real siempre devuelve 16 hex. No lo reproduje como defecto en
  producción; lo registro como inconsistencia lógica determinista en el código.
- **Consecuencia potencial:** proceso vivo no contabilizado si un host futuro
  viola el contrato.
- **Recomendación:** tratar el ref inválido como la excepción genérica:
  retener slot + registrar identidad en `_retained`.

## 4. Resultado por obligación de falsación (§4)

| # | Obligación | Resultado de mi intento de falsación |
|---|---|---|
| 1 | Linealización CAS→spawn | **No falsificada.** Sonda 3A: 8 hilos, mismo token, store durable real → 1 `Started`, 7 `capability_rejected(cas:already_spent)`, 1 spawn, `spent` sobrevive reapertura. Comparaciones por identidad; muestra de reloj fresca antes del CAS. |
| 2 | Reconciliación spent/unspent/unknown | **No falsificada.** `unspent` → `start_failed` sin spawn; tipos ajenos y `truthy` sin autoridad; store muerto (sonda 3, colateral) → `start_failed_indeterminate(cas:unavailable:unknown)`, nunca spawn. Matriz del suite verde. |
| 3 | Carreras de capacidad | **FALSIFICADA vía F2** (doble liberación de slot → sobre-admisión demostrada). La carrera de *starts* distintos (CarreraDeSlots, 16 hilos) sí resiste. |
| 4 | Handles forjados/cross-instance | **No falsificada.** MAC HMAC ligada a (instancia, identity_digest, action_id), comparación en tiempo constante; suite cubre forjado, cruzado, otra acción, otra instancia. |
| 5 | terminate/await_result | **Parcialmente falsificada vía F2** (doble entrega del resultado). Lo demás resiste: receipt idéntico en repetición, post-resultado no contacta al supervisor ni reclasifica, timeout → `None` honesto. |
| 6 | Deadlines | **Parcialmente falsificada vía F1** (la causa vigencia-gana no llega al wire real). Aritmética pura correcta; plazo cero → rechazo **antes** del CAS con token `unspent` (sonda 3B); plazo efectivo respetado (TERM a los 1500 ms útiles observados). |
| 7 | TERM→KILL | **No falsificada.** Watchdog monotónico; KILL al grupo ineludible salvo escape `setsid` (declarado); gracia aplicada y reportada (`termination_grace_ms_applied=500` observado en sonda 1). |
| 8 | Backpressure | **No falsificada.** Semáforo(1) por stream, pico `max_unacked` medido (H11) y probado; coordinador lento ≠ caído (R3); el canal de acks es inaccesible al proceso ejecutado. |
| 9 | Pipe escape | **No falsificada.** Drenaje EOF acotado (`eof_drain_forced_close`), pumps daemon, sin `pipe.close()` bloqueante; suite no-hang (5 clases hostiles) verde. |
| 10 | Crash durability | **No falsificada** (suite G-M2-06 con SIGKILL real reejecutada por mí en Darwin; persistencia fsync+rename+fsync-dir con `F_FULLFSYNC`). |
| 11 | Escapes setsid | **No falsificada.** Promesas alineadas con N3/N4; `terminate_group` documenta que no promete muerte universal; G-M2-11 mide escapado vivo y lo declara. |
| 12 | Divergencias Linux/Darwin | **No evaluables en su mitad Linux** — limitación declarada (§2). En Darwin: subreaper `unsupported` declarado, skips coherentes con la línea base. |
| 13 | Regresiones M1 | **No falsificada.** 339 OK/4 skips; `helpers_m1.py`, frontera instrumental y tests adversariales M1 intactos en el diff; `admit.py` aditivo opt-in (`m2_config=None` ⇒ byte-idéntico). |
| 14 | Claims > evidencia | **Parcialmente falsificada:** F1 (G-M2-09 verde con una distinción de causa no ejercitada end-to-end) y F3 (encargo fosilizado). La separación payload/RSS y la formulación analítica de G-M2-12 **sí** se respetan en todo el árbol. |
| 15 | Ampliaciones de TCB | **No falsificada.** stdlib-only; `ctypes`/`prctl` es la excepción parcial ya declarada (ADR-006); sin dependencias nuevas. |
| 16 | Violaciones de alcance M2 | **No falsificada.** `git diff 4beb7ebe..HEAD -- contracts` **vacío**; las 28 rutas src/tests/scripts del diff están todas en el inventario del alcance técnico; las 5 rutas preservadas intactas; nada de M3/M4/x86_64. |

La duplicación `test_las_cotas_publicadas_siguen_las_formulas` fue verificada:
clases distintas (`TerminacionGraduadaTests` l.391, `CotasDePayloadTests`
l.435), contenido distinto — **no es defecto**, coincido con la declaración
del encargo.

## 5. Veredicto

> # FIX-AND-RETRY

Dos hallazgos **P1 materiales y reproducibles**:

- **F1:** causa de plazo equivocada en el wire real, falsifica una propiedad
  explícitamente prometida y un gate declarado verde.
- **F2:** carrera determinista que corrompe la cota de capacidad global y
  duplica la entrega del resultado, falsifica el criterio 5 de G-M2-12 y la
  linealización de D-M2-4.

Ambos tienen corrección acotada y verificable. Conforme a §7 del encargo:
corregir, reejecutar los gates afectados (G-M2-09, G-M2-12 criterio 5,
G-M2-05/10 en lo que toque a F2), regresión completa en ambas plataformas,
actualizar manifiesto y solicitar re-verificación externa del diff correctivo.
F3 debe resolverse documentalmente antes de la reconciliación para no
contaminarla.

**Estado del repositorio:** sin modificación alguna por mi parte; HEAD
permanece detached en `eb5590b…` con árbol limpio, como exige el protocolo.
Las sondas viven en `/tmp/probe_gm215_{1,2,3}_*.py` y se conservan para la
reconciliación.
