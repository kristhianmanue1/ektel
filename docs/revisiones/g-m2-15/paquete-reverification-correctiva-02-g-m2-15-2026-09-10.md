# Paquete de re-verificación externa — ronda correctiva 2 (R12..R14)

**Fecha:** 2026-09-10.
**Destinatario:** re-verificación externa correctiva de G-M2-15.
**Pregunta:** ¿FIX-M2-R12..R14 quedaron realmente satisfechas sin reintroducir
defectos de R1..R11, crear regresiones materiales ni ampliar M2?

## 1. Identidades congeladas

| Qué | Valor |
|---|---|
| Referencia normativa de autorización | `3d06a30c3087ab0780cdc6b5cdcf3f16270097d0` |
| Commit de implementación correctiva 2 | `273d09be488d9315e68e140d4553837944c1fd1f` |
| MANIFEST-ROOT anterior | `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470` |
| MANIFEST-ROOT post-correctiva 2 | `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95` |
| Manifiesto | `docs/evidencia/manifest-m2-sha256.txt` |
| CORRECTIVE-REVIEW-ROOT 2 | El commit documental que contiene este paquete y el manifiesto; su SHA se fija al publicar el asiento |

El hash del manifiesto se obtiene con:

```text
shasum -a 256 docs/evidencia/manifest-m2-sha256.txt
```

Sus entradas deben reproducirse íntegramente con:

```text
shasum -a 256 -c docs/evidencia/manifest-m2-sha256.txt
```

## 2. Diff exacto a revisar

```text
git diff 3d06a30c3087ab0780cdc6b5cdcf3f16270097d0..273d09be488d9315e68e140d4553837944c1fd1f -- src tests scripts contracts
```

El diff contiene **11 archivos**: 6 de `src/`, 5 de `tests/`, 0 de `scripts/`
y 0 de `contracts/`. No añade rutas ni toca wire, schemas, M3, M4,
capabilities cross-host, persistencia durable ni sandboxing general.

```text
src/adapters/posix_supervisor.py
src/application/admit.py
src/application/config.py
src/application/start_service.py
src/domain/execution_handle.py
src/ports/process_host.py
tests/integration/test_capacity_slots.py
tests/integration/test_start_linearization.py
tests/unit/helpers_m2.py
tests/unit/test_m2_config.py
tests/unit/test_termination_semantics.py
```

## 3. FIX-M2-R12 — implementación y falsificación requerida

### Implementación

- Se separan el slot, el registro operacional, la custodia pendiente de
  adquisición, la capability adquirida y el resultado terminal.
- `_operations` sólo vive durante la espera/cierre operacional.
- `_pending_handles` conserva fuertemente la capability prometida hasta la
  primera adquisición por `handle_for(ref)`, aunque el terminal ya haya
  llegado.
- La custodia pendiente tiene una cota independiente igual al perfil de
  capacidad M2. Saturarla produce `capacity:no_handle_slot` antes de CAS y
  spawn; no existe eviction de una capability prometida.
- Tras adquirir, el estado terminal queda ligado débilmente a la identidad
  exacta del handle. Retener el handle/resultado no conserva el slot ni el
  registro operacional; abandonar el handle permite liberar el estado.
- El vigilante terminal sigue siendo la única ruta que libera el slot.

### Pruebas nuevas/actualizadas

- `test_terminal_inmediato_no_pierde_capability_500_iteraciones`: mínimo 500
  iteraciones, `lost = 0`.
- `test_terminal_antes_de_que_start_retorne_conserva_capability`.
- `test_capabilities_pendientes_tienen_backpressure_pre_spawn`: saturación sin
  CAS/spawn y reintento con el mismo token.
- Replays de handle abandonado, slot liberado por terminal, doble
  `await_result` y doble release.

### Preguntas adversariales

El revisor debe intentar terminal antes/durante/después del retorno de
`start()`, adquisición tardía, nunca adquirir, saturación concurrente y
abandono después de adquirir. Debe comprobar por separado que:

- `lost = 0` en el replay de 500;
- slots y registros operacionales vuelven a cero tras el terminal;
- la custodia pendiente queda acotada;
- la saturación rechaza antes del spawn y no consume el token; y
- capability/resultado retenidos no retienen slot.

## 4. FIX-M2-R13 — implementación y falsificación requerida

### Implementación

- `ExecutionHandle` ya no expone `deposit_terminal_result`,
  `store_terminal_result`, espera ni extracción terminal.
- `_HandleRecord` es estado privado del coordinador, separado del objeto
  público.
- Cada spawn acuña una autoridad de depósito por identidad de objeto que sólo
  recibe el vigilante; pasar una referencia pública a `StartService` no la
  reconstruye.
- Depósito y cierre sin resultado exigen esa autoridad y la consumen.
- El depósito acepta únicamente un `AwaitedExecution` exacto que contenga
  `ExecutionResult` exacto y buffers `bytes` exactos.
- `take_once()` linealiza un único consumidor; el estado débil conserva el
  tombstone mínimo mientras vive la capability legítima.
- `terminate` y `await_result` exigen tanto autenticación criptográfica como
  identidad exacta del handle adquirido.

### Pruebas nuevas/actualizadas

- ausencia de cualquier método público de depósito en el handle;
- depósito falso tipado con autoridad inventada, tipo falso y cierre falso,
  seguidos por terminal real recuperable;
- objeto distinto con identidad/token copiados;
- validación del tipo terminal y consumo de un solo uso de la autoridad;
- segundo consumidor, handle forjado, cross-instance y otra acción;
- terminate post-resultado y tras consumo sin reabrir efectos.

### Preguntas adversariales

El revisor debe repetir depósito falso, falso seguido de real, objeto copiado,
segundo depósito y segundo consumidor. Debe intentar usar únicamente objetos
públicos entregados al caller. Ninguna ruta debe producir doble resultado,
desalojar al handle legítimo, contactar indebidamente al host ni liberar dos
veces el slot.

## 5. FIX-M2-R14 — implementación y falsificación requerida

### Implementación

- `M2Config.fingerprint` calcula SHA-256 de una representación ASCII
  canónica, versionada y de orden fijo del perfil validado completo.
- `AdmissionService.m2_config_fingerprint` acredita localmente el perfil M2
  que declara, sin añadirlo al wire ni alterar los assumptions congelados.
- `StartService` exige un fingerprint declarado válido y lo compara con su
  perfil y con la acreditación vigente del Host en cada `start`, antes de
  revalidación, CAS o spawn.
- `ProcessHost` expone `config_fingerprint`; `spawn` recibe el fingerprint
  esperado del coordinador.
- `PosixSupervisorHost` acredita el perfil completo del que derivan sus
  valores aplicados, detecta drift antes del CAS mediante su propiedad y
  vuelve a comprobarlo en la frontera de spawn.
- `from_config()` permanece, pero la comparación ya no depende de que el
  integrador elija esa ruta.

### Pruebas nuevas/actualizadas

- fingerprint determinista, canónico, hexadecimal y sensible al perfil;
- Admission con/sin perfil M2;
- host sin acreditación;
- divergencia Start/Host;
- drift de valores aplicados tras construcción, rechazado antes del CAS;
- contraejemplo exacto Admission/Start/Host = 2000/1500/500, con cero spawn y
  token sin consumir;
- host real compuesto desde el mismo perfil y mediciones aplicadas iguales a
  las declaradas.

### Preguntas adversariales

Repetir exactamente 2000/1500/500. Probar fingerprint ausente, malformado,
copiado de otro perfil y Host cuya propiedad o valores aplicados cambien tras
la construcción. Toda divergencia debe fallar antes de consumir el token o
crear proceso. No aceptar como conformidad que el resultado sólo declare el
valor finalmente aplicado.

## 6. Lifetimes implementados

| Lifetime | Inicio | Cierre |
|---|---|---|
| Proceso | spawn confirmado | terminal real y recolección del supervisor |
| Slot | reserva pre-CAS | handoff/cierre terminal único; pre-spawn determinado; indeterminación sólo por acto explícito |
| Registro operacional | registro post-spawn | handoff completo, output incluido, o cierre definitivo |
| Capability del caller | acuñación post-spawn | adquisición y ownership del caller; release/consumo/abandono o reinicio del coordinador |
| Resultado terminal | depósito interno tipado | consumo único, release/abandono o fin de la capability |

El terminal no destruye la custodia pendiente; la adquisición no ocupa slot;
la retención del resultado no conserva el registro operacional.

## 7. Evidencia de regresión final

| Verificación | Resultado |
|---|---|
| Suite completa Darwin arm64, Python 3.12.12 | **368 OK, 5 skips** dentro del sandbox; el quinto es RSS no observable por falta de enumeración de procesos |
| Suite completa Linux aarch64 clase V | **368 OK, 1 skip**; imagen `python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`, read-only, sin red, no root |
| `mypy --strict src` | 34 archivos, sin issues |
| Golden vectors | 91, `--check`, diff cero |
| Fuzz admisión | 63 mutaciones, 0 fallos de oráculo, 0 crashes |
| Fuzz start/revalidación | 2000 iteraciones, semilla 20260909, 0 crashes, 0 divergencias, gate OK |
| Supervisores residuales | `pgrep -fl src.adapters.posix_supervisor` sin salida tras las corridas |
| Manifiesto | todas las entradas `OK`; contracts y scripts sin cambios |

La suite emitió los `ResourceWarning` de procesos todavía vivos durante GC ya
observados y declarados antes de esta ronda. No quedó supervisor residual al
cierre. Darwin no se presenta como una corrida exacta de 4 skips: la
limitación de RSS del sandbox se conserva expresamente.

Los replays ejecutados incluyen doble await, doble release, handle abandonado,
terminate/await, indeterminación post-spawn, vigencia, causalidad del primer
hecho y KILL del grupo con líder ya terminado.

## 8. Gates y estado

Este paquete aporta evidencia nueva para G-M2-01, G-M2-05, G-M2-06, G-M2-10,
G-M2-11, G-M2-12 y G-M2-14. **No promueve G-M2-15**: ese gate exige la
re-verificación externa sobre el árbol congelado.

```text
corrective_round_2 = IMPLEMENTED
R12..R14           = IMPLEMENTED / PENDING-EXTERNAL-REVERIFICATION
G-M2-15            = CORRECTIVE-FIX-AND-RETRY
M2                 = OPEN
M3                 = BLOCKED
```

La siguiente acción autorizable es exclusivamente la re-verificación externa
correctiva 2. Sólo `CORRECTIVE-PROCEED` permite pasar a un asiento posterior de
conformidad; este paquete no cierra ningún gate.
