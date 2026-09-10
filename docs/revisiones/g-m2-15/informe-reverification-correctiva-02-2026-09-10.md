# Informe de re-verificación externa G-M2-15 — ronda correctiva 2

## Metadata

| Campo | Valor |
|---|---|
| Revisión | Re-verificación externa del diff correctivo 2 (FIX-M2-R12..R14) |
| Fecha | 2026-09-10 |
| Revisor | OpenCode — GLM 5.3 Flash (harness CLI opencode) |
| CORRECTIVE-REVIEW-ROOT 2 | `8c087be6276784046254fc3d144242eee6836e6e` |
| Commit de implementación correctiva 2 | `273d09be488d9315e68e140d4553837944c1fd1f` |
| Adjudicación previa | `adjudicacion-reverification-01-2026-09-10.md` |
| Paquete revisado | `paquete-reverification-correctiva-02-g-m2-15-2026-09-10.md` |
| MANIFEST-ROOT post-correctiva 2 | `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95` |
| MANIFEST-ROOT anterior | `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470` |
| Plataforma host | Darwin arm64, Python 3.12.12 (`.venv` del proyecto) |
| Naturaleza | Revisión externa, sólo lectura; sin corrección de código |
| Veredicto original | **CORRECTIVE-FIX-AND-RETRY** |

Este documento conserva íntegramente el resultado de la re-verificación
externa. No adjudica ni reinterpreta sus findings y no promueve ningún gate.

**Nota de continuidad.** Una revisión externa anterior de esta misma ronda fue
interrumpida por una restricción del harness antes de emitir informe. Este
informe no asume sus conclusiones: las reproduciones del estado provisional
(R12; hallazgos candidatos A y B) fueron reejecutadas de forma independiente
sobre el árbol congelado.

## Veredicto

**CORRECTIVE-FIX-AND-RETRY**

| Obligación | Resultado |
|---|---|
| R12 | **SATISFIED** |
| R13 | **NOT-SATISFIED** |
| R14 | **NOT-SATISFIED** |

R12 quedó firme bajo refutación independiente (replay obligatorio y ataques
adicionales, 27/27 verificaciones). R13 cae por un hallazgo material
reproducido (FIND-R13-A, P2) que reproduce la causa raíz aceptada de
CORR-M2-02 en forma desplazada. R14 cae por FIND-R14-A (P2): existe
comparación de fingerprints, pero no binding de autoridad de configuración.

## Identidad y alcance

- `HEAD` durante toda la sesión:
  `8c087be6276784046254fc3d144242eee6836e6e` (checkout detached; árbol
  limpio antes, durante y después; repositorio no modificado).
- MANIFEST-ROOT verificado con
  `shasum -a 256 docs/evidencia/manifest-m2-sha256.txt`:
  `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95`
  (coincidencia exacta).
- Preflight AN-KLA: `context status` sin diagnósticos.
- Dif correctivo confirmado: 11 archivos (6 `src/`, 5 `tests/`), conforme al
  paquete revisado; `contracts/` y `scripts/` sin cambios.
- Reproducciones adversariales ejecutadas en directorio temporal fuera del
  repositorio (`/var/folders/.../T/opencode/ektel-reverify2/`), con `sys.path`
  apuntando al árbol congelado; ningún archivo del repositorio fue creado ni
  alterado.

## R12 — SATISFIED (estado provisional confirmado; refutación fallida)

Replay obligatorio ejecutado de forma independiente:
`terminal inmediato → Started → handle_for(ref)`, **500/500 iteraciones,
`lost = 0`**, cero resultados defectuosos, slots finales = 0, registros
operacionales = 0, pending = 0 tras adquisición.

Ataques adicionales (27/27 verificaciones del script adversarial):

- **Terminal antes del retorno de `start()`**: host doble que entrega el
  traspaso dentro de `spawn`; la capability se conserva y `await_result`
  devuelve el stdout íntegro (`b"early"`); slot liberado por el vigilante.
- **Saturación de custodia pendiente**: con `max_concurrent_actions=2`, dos
  inicios sin adquirir, terminales entregados sin adquirir (slots/ops drenados,
  pending=2). El tercer inicio produce `capacity:no_handle_slot` **antes del
  CAS/spawn**; `spawns=2`; el token del rechazado queda sin consumir
  (`spent=2`); **ninguna capability prometida fue desalojada**; tras adquirir
  ambas custodias, el reintento con el **mismo token** produce `Started`.
- **Handle abandonado (sin adquirir) + terminal inmediato**: slot=0,
  registros=0, custodia pendiente acotada (=1), adquisición tardía entrega el
  resultado, doble `release` inofensivo.
- **Doble await / segundo consumidor**: primer `await_result` entrega
  exactly-once (`b"only-once"`); segundo y tercer await → ausencia honesta
  (`None`); `handle_for` repetido → `None`.
- **Acción sin terminal**: slot retenido honesto (=1); adquisición no libera
  slot; await con timeout → `None`; tras `deliver_absence` el slot se libera y
  el await posterior devuelve ausencia honesta, sin resultado fabricado.

No se observó crecimiento ilimitado ni eviction de capabilities prometidas.

**Nota de harness.** Dos fallos iniciales de la sección C/E del script fueron
defectos del propio harness (reuso de nonce en fixtures y comprobación sin
esperar al vigilante asíncrono), corregidos en el harness; el repositorio no
se modificó.

## R13 — NOT-SATISFIED

### FIND-R13-A — P2 — La autoridad de depósito es alcanzable desde referencias públicas ordinarias

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/application/start_service.py:109-155` (`_HandleRecord`,
  slot `_deposit_authority` y `deposit_once`), `:222-224` (`_acquired`),
  `:455-457` (`deposit_authority = object()`), `:516-519` (`_record_for`).
- **Claim afectado:** FIX-M2-R13.3/5/6; single terminal ownership del
  contenido; «sólo el coordinador acuñador puede realizar la transición
  terminal».
- **Pregunta de frontera aplicada:** `_nombre_privado` no se aceptó como
  frontera de autoridad por sí misma; la pregunta fue si un caller con
  **únicamente las referencias públicas normales** (la instancia
  `StartService` y el `ExecutionHandle` legítimo de `handle_for`) puede
  alcanzar la autoridad.
- **Reproducción 1 (recorrido del hallazgo candidato):**
  `record = svc._record_for(handle)` →
  `authority = record._deposit_authority` →
  `record.deposit_once(forged, authority)` → `True` →
  `svc.await_result(handle)`.
  Salida textual:
  ```text
  record alcanzable via _record_for: True
  autoridad de deposito legible: True (object)
  fake_deposit_accepted = True
  observed_stdout = b'forged-by-caller'
  ```
- **Reproducción 2 (ruta alternativa sin `_record_for`):**
  `svc._acquired.get(handle)` devuelve el mismo registro; forjado
  `b'forged-via-_acquired'` aceptado y entregado por `await_result`.
- **Reproducción 3 (desplazamiento del terminal real):** depósito falso
  `b'forged-first'` seguido de entrega del terminal real `b"REAL"` por el
  puerto legítimo: `await_result` entregó `b'forged-first'`; el resultado real
  se perdió. Exactly-once se preserva en contador, pero el **contenido** del
  terminal lo elige el caller.
- **Reproducción 4 (destrucción de capability):**
  `rec.close_without_result(rec._deposit_authority)` → `closed=True`; el
  terminal real entregado después nunca es recuperable (`await → None`).
- **Esperado:** un caller ordinario no puede obtener, reconstruir ni invocar
  la autoridad que realiza la transición terminal; `deposit_once` con
  autoridad que no sea la del vigilante → `False`.
- **Observado:** la "capability" es un sentinel `object()` almacenado en un
  slot alcanzable por traversal ordinario de atributos desde objetos que el
  caller posee legítimamente.
- **Causa raíz:** la frontera es convención de nombres, no incapacidad de
  falsificación. Reproduce la causa raíz aceptada de CORR-M2-02 («la autoridad
  de depósito está representada por una referencia ordinaria reutilizable»)
  en forma desplazada: el método público desapareció, pero la autoridad sigue
  siendo una referencia ordinaria reutilizable.
- **Consecuencia:** el caller puede fabricar el contenido del terminal
  (desplazando al real) o cerrar el registro destruyendo la capability
  prometida; «sólo el vigilante acuña» deja de ser cierto. Sin impacto wire,
  sin doble entrega, sin escape de procesos; severidad P2 análoga a
  CORR-M2-02.
- **Recomendación:** que la autoridad no resida en estado alcanzable desde
  referencias públicas del coordinador: closure retenida exclusivamente por el
  hilo vigilante (jamás almacenada en `_HandleRecord` ni en dict del
  servicio), o verificación de rol/identidad de hilo en la transición.
- Defensas que **sí** resistieron (sin hallazgo): autoridad de un solo uso
  (segunda transición con autoridad consumida → `False`), objeto copiado
  (`copy.copy` no recupera el registro; identidad débil por objeto), sentinel
  inforgeable por construcción (`object()` distinto → `False`), segundo
  consumidor (`handle_for` repetido → `None`; único consumo).

### FIND-R13-B — P3 — Handle forjado semi-construido filtra excepción en vez de rechazo documentado

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/application/start_service.py:572-574` (`await_result`),
  `:534-536` (`terminate`); `src/domain/execution_handle.py:41-46` (`__slots__`
  sin inicializar en construcción por `__new__`).
- **Reproducción:** `object.__new__(ExecutionHandle)` pasado a
  `await_result`/`terminate` →
  `AttributeError: 'ExecutionHandle' object has no attribute '_token'`.
- **Esperado:** rechazo documentado (`None` / `TerminationRejected`) para
  handles forjados.
- **Observado:** `isinstance(handle, ExecutionHandle)` acepta la instancia
  semi-construida y `authenticates_for` falla con excepción no controlada.
- **Causa raíz:** la validación de tipo no verifica inicialización completa
  antes de acceder a slots.
- **Consecuencia:** violación de robustez de frontera hostil; sin ganancia de
  autoridad ni corrupción de estado.
- **Recomendación:** capturar excepciones de autenticación o verificar
  inicialización (p. ej. `hasattr(handle, "_token")`) antes de usar el handle.

## R14 — NOT-SATISFIED

### FIND-R14-A — P2 — La declaración de Admission no está vinculada: fingerprint caller-asserted

- **Clase de evidencia:** REPRODUCIDO.
- **Ubicación:** `src/application/start_service.py:200/209/286-289/313-331`
  (`declared_config_fingerprint` como string del constructor y comparación
  interna); `src/application/admit.py:184-192`
  (`m2_config_fingerprint`, propiedad derivada de la config propia de
  Admission). Grep verificado: **ningún código de `src/` consume
  `AdmissionService.m2_config_fingerprint`**.
- **Claim afectado:** FIX-M2-R14.3/4/6/8; criterio de cierre «la declaración
  de Admission, la exigencia de Start y la acreditación del Host se comparan
  antes del CAS/spawn en toda composición admitida, incluidas las
  construcciones directas».
- **Reproducción (composición del hallazgo candidato B):**
  `AdmissionService(m2_config=A(termination_grace_ms=2000))`; `StartService(
  config=B(1500), declared_config_fingerprint=fp(B))`; host acreditado con
  `fp(B)`; `admit` → `start`. El caller afirmó `fp(B)` en la ruta que conecta
  Admission con Start. Salida textual:
  ```text
  Admission declara: 9b4424eb1b2ffe4f... (== fp(A): True)
  GuaranteePlan declarado por Admission: ['termination_grace_ms_configured=2000', ...]
  outcome=Started spawns=1 token_consumed=1
  ```
- **Esperado:** `rejected before CAS/spawn`; el token intacto;
  `declared == required == applied` autenticado contra la Admission que emitió
  el token.
- **Observado:** `Started`, `spawns=1`, `token_consumed=1`; el GuaranteePlan
  declaró gracia 2000 mientras el perfil aplicado era B (1500); composición
  incoherente silenciosa.
- **Causa raíz:** `declared_config_fingerprint` es **caller-asserted** en la
  frontera de construcción de `StartService`; nada autentica ese valor contra
  la autoridad (Admission) que declaró el perfil. El contraejemplo obligatorio
  2000/1500/500 pasa sólo porque el *test* actúa como integrador honesto
  inyectando `admission.m2_config_fingerprint`
  (`tests/unit/test_m2_config.py:286`).
- **Consecuencia:** un perfil declarado (2000) convive silenciosamente con
  otro aplicado (1500); la construcción directa de componentes permite
  composición incoherente silenciosa (violación de R14.8).
- **Recomendación:** transportar la acreditación por la ruta Admission→Start
  (portada en `Admitted`/`StartRequest`, derivada localmente de la config de
  Admission) y que Start compare **ese** valor —no uno suministrado por el
  integrador— con su config y el host.

### Pregunta arquitectónica — comparación sin binding

- **fingerprint comparison: EXISTE.** `_check_configuration_authority`
  compara triple (declarado == config de Start == propiedad del host) antes de
  revalidación, CAS y spawn. Confirmado por rechazo pre-CAS en: fingerprint
  omitido (`config:declared_fingerprint_missing`), falso (`"0"*64` →
  `config:declared_fingerprint_mismatch`), correcto de otro perfil (→
  `mismatch`), host divergente A/A/B y A/B/A (→
  `config:host_fingerprint_mismatch`), drift aplicado del host real
  (`PosixSupervisorHost` mutado post-construcción → rechazo, token sin
  consumir), host real del mismo perfil → admitido (coherente), configs
  distintas pero equivalentes → mismo fingerprint (determinismo canónico).
- **configuration authority binding: NO EXISTE.** El valor «declarado» no
  procede de la Admission que emitió el token: es un string que el integrador
  entrega a `StartService`. La composición Admission(A)/Start(B)/Host(B) con
  `fp(B)` afirmado por el caller se ejecuta sin rechazo.

## Regresión y evidencia adicional (G-M2-14)

- Darwin arm64, Python 3.12.12 (`.venv` del proyecto): **368 OK, 4 skips**
  (`unittest discover -s tests -t .`).
- `mypy --strict src`: **34 archivos, sin issues**.
- Golden vectors: `--check` exit 0, **91 vectores**, diff cero.
- Fuzz admisión (`scripts/fuzz_admision.py`): exit 0, sin fallos de oráculo.
- Fuzz start/revalidación (`scripts/fuzz_start_revalidation.py`):
  **2000 iteraciones**, semilla **20260909**, `crashes: []`,
  `divergencias: []`, `gate: OK`.
- Supervisores residuales: `pgrep -fl src.adapters.posix_supervisor` sin
  salida tras las corridas.
- Contraejemplos de `validity_bound`, doble await, doble release,
  indeterminación post-spawn, terminate/deadline y KILL del grupo: cubiertos
  por la suite verde (368) y reejercidos independientemente en el script R12
  (doble await/release, ausencia honesta).
- Árbol del revisor: limpio durante toda la sesión (`git status --porcelain`
  sin salida). Repositorio no modificado.

## Limitaciones declaradas

- **Linux aarch64 no reejecutado** en esta sesión: el entorno del revisor sólo
  disponía de Darwin arm64. La evidencia Linux de la ronda (368 OK, 1 skip)
  permanece como la declarada por el paquete correctivo, no re-verificada
  aquí.
- Las reproducciones adversariales usan los dobles deterministas del propio
  repositorio (`FakeProcessHost`), no procesos POSIX reales; la suite completa
  (368, con procesos reales) se reejecutó íntegra y en verde.
- Dos fallos iniciales del script R12 fueron defectos del harness (no del
  repositorio) y se corrigen en el propio harness antes del resultado final.

## Conclusión original

La ronda correctiva 2 materializó R12 de forma sólida (refutación fallida en
replay obligatorio, backpressure pre-spawn con token intacto, ausencia de
eviction y de crecimiento ilimitado) y fortaleció la matriz de rechazo de
configuración. Pero R13 conserva, desplazada, la causa raíz aceptada de
CORR-M2-02 —la autoridad de depósito es una referencia ordinaria alcanzable
desde referencias públicas— y R14 mantiene el configuration authority split:
la comparación de fingerprints existe, el binding con la autoridad de
configuración de Admission no.

Estado derivado de la revisión:

- G-M2-15: no conforme.
- M2: permanece abierto.
- M3: permanece bloqueado.
- HEAD final: `8c087be6276784046254fc3d144242eee6836e6e`.
- Árbol final: limpio.
