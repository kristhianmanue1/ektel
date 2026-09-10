# Informe de re-verificación externa G-M2-15 — ronda correctiva 1

## Metadata

| Campo | Valor |
|---|---|
| Revisión | Re-verificación externa del diff correctivo |
| Fecha | 2026-09-10 |
| CORRECTIVE-REVIEW-ROOT | `64409b6efed54973c26034cc593d7ed0c85b4d47` |
| Commit de implementación correctiva | `0475d9ffa5e2cbd5985f44ce6039b52e28eaea5f` |
| Reconciliación | `dc3da3f2a8c31762743c9ef9016ccc1eb817d0a4` |
| MANIFEST-ROOT post-correctiva | `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470` |
| MANIFEST-ROOT anterior | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |
| Plataforma host | Darwin arm64, Python 3.12.12 |
| Plataforma adicional | Linux aarch64, imagen `sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea` |
| Naturaleza | Revisión externa, sólo lectura; sin corrección de código |
| Veredicto original | **CORRECTIVE-FIX-AND-RETRY** |

Este documento conserva íntegramente el resultado de la re-verificación
externa. No adjudica ni reinterpreta sus findings y no promueve ningún gate.

## Veredicto

**CORRECTIVE-FIX-AND-RETRY**

FIX-M2-R4 y FIX-M2-R6 no quedaron completamente satisfechas. Además, el nuevo
vigilante introdujo una regresión P1 reproducible: una acción terminal inmediata
puede perder su `ExecutionHandle` antes de que el llamador consiga obtenerlo.

No se encontró P0 ni ampliación de alcance hacia M3/M4, pero permanecen un P1 y
dos P2 corregibles dentro de M2.

## Identidad y alcance

- `HEAD`: `64409b6efed54973c26034cc593d7ed0c85b4d47`.
- Checkout detached ejecutado durante la revisión.
- Árbol final limpio: `git status --porcelain` sin salida.
- MANIFEST-ROOT nuevo verificado:
  `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470`.
- Los hashes internos del manifiesto pasaron íntegramente `shasum -c`.
- MANIFEST-ROOT anterior reproducido desde la reconciliación:
  `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae`.
- Diff correctivo confirmado: 6 `src/`, 8 `tests/`, 0 `scripts/`; 14 archivos
  de implementación/pruebas y 16 totales con los dos documentos.
- `contracts/` y `scripts/` sin cambios.
- `git diff --check` limpio.
- No se modificó ni creó ningún archivo del repositorio durante la revisión.

## Resultado obligación por obligación

| Obligación | Resultado | Evidencia |
|---|---|---|
| R1 | **SATISFIED** | Replay original con host y proceso reales: vigencia restante ≈2000 ms frente a deadline 5000 ms produjo `deadline_exceeded / deadline_validity_exhausted`. El dato llega mediante `SupervisedAction.validity_bound` → `collect_terminal()` → `_build_awaited()`. |
| R2 | **SATISFIED** | Sonda histórica repetida: `doble_entrega=0/40`, `corrupcion_slot=0/40`; con capacidad 2 y otra acción viva no hubo sobre-admisión. El `pop` del host está linealizado. La vía alternativa de fabricación se adjudica a R4. |
| R3 | **SATISFIED** | Con capacidad 1, una acción real terminó sin `await_result`; después del terminal quedaron `slots=0`, `pending_actions=0` y la segunda acción inició. Sin embargo, el mecanismo introdujo la regresión CORR-M2-01. |
| R4 | **NOT-SATISFIED** | Los handles falsos/cross-instance/capability distinta fueron rechazados sin nuevo contacto al host. Pero `deposit_terminal_result()` sigue siendo una superficie pública utilizable por un llamador ordinario y acepta cualquier objeto si recibe la referencia pública al servicio. También se aceptó un objeto distinto con datos copiados una vez eliminado el registro legítimo. Véase CORR-M2-02. |
| R5 | **SATISFIED** | Tipo inválido, longitud inválida y `"g"*16` terminaron en `start_failed_indeterminate`, con `slots_in_use=1` e identidad registrada en `retained_by_indeterminacy`; no escapó excepción ni se fabricó ausencia. |
| R6 | **NOT-SATISFIED** | La construcción directa inválida, `audit_mode=required` y rangos inválidos ya fallan; `from_config()` copia correctamente un perfil. Pero Admission, Start y Host todavía aceptan configuraciones independientes y divergentes. Sonda e2e: declarado 2000 ms, Start 1500 ms, aplicado 500 ms, sin rechazo. Véase CORR-M2-03. |
| R7 | **SATISFIED** | Comparación literal con ADR-012: `useful_runtime_formula=deadline_eff_ms-applied_grace_ms` y `supervisor_scope=per_action_process`, en orden exacto. |
| R8 | **SATISFIED** | Proceso ignorando TERM: terminate claramente anterior produjo `terminated/external_termination`, rc `-9`; deadline claramente anterior seguido de terminate produjo `deadline_exceeded/deadline_duration`, rc `-9`. Empate/desconocido conserva precedencia de deadline en prueba normativa. |
| R9 | **SATISFIED** | Replay real líder-obedece/nieto-ignora: `deadline_hit=True`, intento KILL registrado, líder rc `0` y nieto del mismo grupo dejó de estar vivo. El PGID se captura antes del reap y el KILL ya no depende de la vida del líder. |
| R10 | **SATISFIED** | La fe de erratas preserva el texto histórico, declara que la enmienda fue aprobada antes del REVIEW-ROOT y establece inequívocamente la prevalencia del acta; no altera retrospectivamente el texto viejo. |
| R11 | **SATISFIED** | La evidencia vigente cita exactamente 2000 iteraciones y semilla `20260909`; “3000” aparece sólo identificado como la cifra histórica no reproducible. |

## Findings nuevos

### CORR-M2-01 — P1 — Pérdida prematura del `ExecutionHandle`

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/application/start_service.py:314-350`, especialmente
  `_watch_terminal()` y `handle_for()`.
- **Claim afectado:** `Started { handle }`, posibilidad de ejecutar
  `await_result(ExecutionHandle)` y preservación del resultado terminal.
- **Reproducción:** un `ProcessHost` conforme entrega el terminal inmediatamente
  al retornar de `spawn`. El vigilante deposita el resultado y elimina
  `_handles[ref]` antes de que `start()` retorne o antes de la llamada inmediata
  a `handle_for()`.
- **Resultado:** `handle_for(started.handle_ref) is None` en **500/500**
  iteraciones sin demora del llamador; también 50/50 con una pausa de 2 ms.
- **Esperado:** después de recibir `Started`, el llamador debe poder adquirir el
  handle local que necesita `await_result` y `terminate`.
- **Observado:** el único registro que permite obtenerlo ya fue desalojado. El
  resultado queda dentro de un objeto que ningún llamador recibió.
- **Consecuencia:** pérdida completa de resultado/stdout/stderr y del derecho
  operativo de terminación para acciones rápidas, pese a haberse devuelto
  `Started`.
- **Recomendación:** linealizar la entrega inicial del `ExecutionHandle` al
  llamador antes de permitir su desalojo. El ciclo terminal puede liberar
  slot/registro del runtime, pero no debe destruir la única vía por la que el
  llamador adquiere el handle. Si esto exigiera cambiar el contrato congelado,
  detener y declarar el gap en vez de modificarlo silenciosamente.

### CORR-M2-02 — P2 — El depósito terminal sigue siendo invocable por un llamador ordinario

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/domain/execution_handle.py:98-111`,
  `src/application/start_service.py:385-417` y
  `tests/integration/test_capacity_slots.py:128-140`.
- **Claim afectado:** FIX-M2-R4, resultado no fabricable y transferencia
  terminal única.
- **Reproducción 1:** `handle.deposit_terminal_result(fake, svc)` devuelve
  `True`; `svc.await_result(handle)` devuelve exactamente `fake`.
- **Reproducción 2:** tras consumir ese objeto fabricado, entregar el terminal
  real permite un segundo `await_result` con el resultado real.
- **Reproducción 3:** un objeto distinto con los datos/token copiados,
  precargado con un objeto falso, es aceptado después de que el vigilante
  elimina el registro legítimo.
- **Esperado:** sólo la ruta interna del coordinador puede depositar un
  `AwaitedExecution` tipado; un llamador ordinario u objeto distinto nunca
  puede hacerlo.
- **Observado:** se eliminó `store_terminal_result` por nombre, pero su capacidad
  se sustituyó por otro método público cuya “autoridad” es la referencia
  ordinaria al `StartService`.
- **Consecuencia:** resultado fabricado, confusión de tipos y doble entrega.
- **Recomendación:** retirar el depósito de la superficie del handle accesible
  al llamador y mantener una autoridad interna no reutilizable. La validación
  debe exigir identidad exacta incluso después del cierre del registro,
  mediante el estado/tombstone necesario.

### CORR-M2-03 — P2 — La autoridad única de configuración sigue siendo optativa

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/application/admit.py:143-176`,
  `src/application/start_service.py:115-139` y
  `src/adapters/posix_supervisor.py:505-551`.
- **Claim afectado:** FIX-M2-R6; configuración declarada igual a configuración
  aplicada.
- **Reproducción:** `AdmissionService` con gracia 2000, `StartService` con 1500
  y `PosixSupervisorHost` directo con 500 se construyen sin error. Una ejecución
  real emitió assumption declarada `2000`, mientras el resultado midió gracia
  aplicada `500` y runtime útil `2000`.
- **Esperado:** una sola autoridad o rechazo determinista de perfiles
  divergentes.
- **Observado:** `from_config()` funciona si el integrador decide usarlo, pero
  el constructor directo sigue público y `StartService` no comprueba que su
  host ni Admission compartan el mismo perfil. La prueba llamada “autoridad
  única” sólo compara `from_config()` consigo mismo.
- **Consecuencia:** `GuaranteePlan` puede declarar una configuración distinta
  de la aplicada por el supervisor.
- **Recomendación:** introducir una composición normal única que construya
  Admission/Start/Host desde la misma instancia validada, o validar
  obligatoriamente identidad/igualdad del perfil en las fronteras.
  `from_config()` no debe ser meramente una ruta recomendada.

## Regresión y evidencia adicional

- Darwin arm64, Python 3.12.12: `355 tests OK`.
  - Corrida sandbox: 5 skips; el adicional fue únicamente RSS no observable por
    restricción de `ps`.
  - La caracterización RSS aislada pasó al repetirla con visibilidad de
    procesos. No se presenta esto como una única corrida exacta de 4 skips.
- Linux aarch64, imagen exacta
  `sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`,
  repositorio read-only y sin red: **355 OK, 1 skip**.
- `mypy` no estaba en `PATH`; `.venv/bin/python -m mypy --strict src` pasó:
  34 archivos sin issues.
- Golden vectors: `--check` sin diff; **91** vectores contados.
- Fuzz admisión: sin fallos.
- Fuzz start/revalidación: **2000 iteraciones**, semilla **20260909**, sin
  crashes ni divergencias.
- Supervisores residuales: `pgrep -fl src.adapters.posix_supervisor` sin
  resultados después de las corridas.
- Se observaron `ResourceWarning` de procesos todavía vivos durante GC, también
  documentados en el informe pre-correctivo; al cierre no quedó supervisor
  vivo. No se clasificaron como regresión nueva.
- No se observó deadlock, hang, pérdida de output posterior a `T`, liberación
  durante estado indeterminado ni regresión Linux específica adicional.

## Limitaciones declaradas

- La corrida Darwin completa dentro del sandbox produjo un quinto skip por
  falta de visibilidad de RSS. La prueba aislada pasó al repetirla con acceso a
  la enumeración de procesos; no se afirmó una única corrida completa exacta
  de `355 OK, 4 skips`.
- `mypy --strict src` no estaba disponible como ejecutable directo; se usó el
  entorno Python 3.12 del proyecto con mypy instalado.
- La ausencia de supervisores residuales se verificó por enumeración posterior,
  separada de la corrida completa.

## Conclusión original

La ronda corrigió efectivamente siete obligaciones técnicas y las dos
documentales, pero no cerró R4 ni R6. El mecanismo usado para R2/R3 creó además
una regresión P1 que invalida el handoff de acciones terminales rápidas. El
alcance de archivos permanece dentro de M2, pero la conformidad material no.

Estado derivado de la revisión:

- G-M2-15: no conforme.
- M2: permanece abierto.
- M3: permanece bloqueado.
- HEAD final: `64409b6efed54973c26034cc593d7ed0c85b4d47`.
- Árbol final: limpio.
