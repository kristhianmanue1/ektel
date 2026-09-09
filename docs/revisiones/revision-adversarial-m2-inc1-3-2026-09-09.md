# Ronda adversarial propia — M2, incrementos INC-M2-1 a INC-M2-3

**Fecha:** 2026-09-09.
**Alcance revisado:** el diff real de M2 hasta `ffde780` (commits `68d4afb`,
`ab456ea`, `ffde780`), bajo el acta `autorizacion-m2-2026-09-09.md`.
**Naturaleza:** ronda **propia del ejecutor**, no verificación independiente.
Por sí sola **no** acredita G-M2-15, que exige revisión adversarial **externa**
sobre el diff real, ni sustituye la revisión multiagente que el acta impone
antes del cierre.

**Veredicto: FIX-BEFORE-INC-M2-4.** Tres hallazgos de severidad alta y una
propiedad declarada pero no acreditada. Ninguno exige ampliar el alcance ni
tocar contratos: **no** hay `BLOCKED-BY-NORMATIVE-GAP`.

## Método

Se buscó falsificar las promesas del propio código, no confirmarlas. Cada
hallazgo alto o medio se **verificó ejecutando**, no por lectura. Las sondas
son efímeras y no se versionan; su resultado se transcribe aquí.

Sesgo declarado: quien escribió el código escribe esta ronda. Los hallazgos que
requieren una perspectiva ajena —diseño del protocolo de frames, modelo de
amenaza del canal local, elección de topología— **no** están cubiertos.

## Hallazgos altos

### H1 · El crédito bloquea el drenaje · `posix_supervisor.py`

D-M2-1(a) es explícito: «Si el coordinador deja de consumir, el supervisor
**sigue drenando** al hijo hasta los límites ya retenidos, descarta el exceso
y, al cerrarse el canal, aplica la terminación best-effort de D-M2-2.»

`_StreamPump.run()` hace `self._credit.acquire()` **antes** de emitir. Si el
coordinador deja de confirmar, el pump queda bloqueado y **deja de leer** del
hijo. El comportamiento implementado es el contrario del normado.

**Verificado.** Coordinador que lee un frame y deja de ackear: a los 6 s el
supervisor sigue vivo y bloqueado, sin entregar terminal ni descartar.

**Consecuencia.** Un coordinador lento o caído bloquea al hijo contra un pipe
lleno. G-M2-07 exige exactamente el caso «coordinador lento/caído» y hoy no lo
cubre ninguna prueba.

**Corrección propuesta.** Crédito con espera acotada; al agotarse, pasar a modo
descarte contando bytes, y al cerrarse el canal solicitar terminación
best-effort del grupo.

### H2 · Espera de EOF no acotada con pipes retenidos por descendientes

El supervisor hace `join()` de los pumps y luego `child.wait()`. Los pumps
terminan sólo con EOF. Un nieto que hereda y **retiene** los pipes impide el
EOF aunque el proceso principal haya salido: el supervisor no entrega frame
terminal **nunca**.

**Verificado.** Hijo que lanza un nieto durmiente y sale de inmediato:
`await_terminal(8 s)` devuelve `None`, sin terminal.

**Consecuencia.** G-M2-08 exige «procesos que … mantienen pipes en
descendientes … toda prueba acotada termina». Hoy no termina. La cota
`post_kill_drain_ms` que resolvería esto pertenece a INC-M2-4, pero el cuelgue
existe **ya** y no debe quedar latente.

### H3 · `request_termination` deja al hijo huérfano y vivo

`PosixSupervisorHost.request_termination` llama a `process.terminate()` sobre
el **supervisor**. Matar al supervisor no termina el grupo del proceso
ejecutado: lo deja huérfano y corriendo. D-M2-2(a) manda solicitar
«terminación best-effort **del grupo**».

**Verificado.** Tras `request_termination`, el supervisor queda terminado y el
proceso ejecutado sigue vivo; hubo que matar su grupo a mano.

**Consecuencia.** La operación hace lo contrario de lo que su nombre promete:
convierte una terminación solicitada en un escape garantizado. Es más grave que
no implementarla, porque un llamador razonable la creería efectiva.

**Corrección propuesta.** Señalizar al supervisor por el canal —cierre de
stdin— para que él aplique la terminación del grupo del hijo, y sólo después
recolectar al supervisor.

## Hallazgos medios

### H4 · `read(n)` no drena de forma incremental

`_StreamPump` usa `source.read(FRAME_MAX_BYTES)`. `BufferedReader.read(n)`
bloquea hasta reunir `n` bytes **o EOF**; no devuelve lo disponible.

**Verificado.** Un hijo que escribe 4 bytes, hace `flush` y duerme 5 s:
`read(65536)` devuelve tras **5,0 s**; `read1(65536)` devuelve tras **0,0 s**.

**Consecuencia.** No hay entrega incremental: la salida de un proceso longevo
no llega hasta que termina. El alcance autorizado dice «stdout/stderr
**drenados continuamente**». Además amplifica H2 y deja el control de flujo por
crédito prácticamente sin ejercitar. La memoria sigue acotada, así que no es
alto por sí solo.

**Corrección propuesta.** `read1`.

### H5 · Fuga permanente de slot en la rama indeterminada de `spawn`

En `StartService._spawn`, una excepción opaca del host produce
`start_failed_indeterminate` y **deliberadamente** no libera el slot, porque
podría existir un proceso vivo. La decisión es correcta, pero **no existe
ninguna ruta de recuperación**: ese slot queda ocupado para siempre y la
capacidad del coordinador decrece de forma monótona.

**Consecuencia.** Con `max_concurrent_actions=1`, una sola indeterminación deja
el runtime permanentemente sin capacidad. Hoy no hay prueba que lo cubra.

**Corrección propuesta.** Registrar la acción indeterminada con su handle_ref
para que la reconciliación posterior pueda liberarla, o declarar explícitamente
la degradación en la documentación del perfil de despliegue. No inventar una
liberación automática: eso rompería la razón por la que se retiene.

### H6 · `_actions` y `_handles` crecen sin límite

`PosixSupervisorHost._actions` nunca se purga. `StartService._handles` sólo se
purga en `await_result`. Una acción nunca aguardada retiene su registro, sus
buffers y su entrada de diccionario.

**Consecuencia.** Contradice el espíritu de D-M2-2(a): «abandonar el último
referente al handle libera resultado y metadatos **sin mantener un slot o
registro global**». Hoy el registro global sí se mantiene.

## Hallazgos bajos

| ID | Defecto | Dónde |
|---|---|---|
| H7 | Un `ExecutionHandle` ya liberado sigue autenticando: `terminate` tras `await_result` contacta al supervisor en vez de ser no-op. `_released` se escribe pero no participa en ninguna decisión | `execution_handle.py`, `start_service.py` |
| H8 | `_read_clock` usa `value == value`, que sólo descarta `NaN`: acepta infinito. Se salva aguas abajo por `math.isfinite`, pero es defensa frágil y asimétrica con el resto del código | `start_service.py` |
| H9 | La escritura del plan puede lanzar `BrokenPipeError` fuera de `SpawnRejected`; un fallo **determinado y pre-proceso** se degrada a indeterminado | `posix_supervisor.py` |
| H10 | `_reconcile` compara `status == "unspent"` en vez de exigir tipo exacto, mientras el resto del módulo compara por identidad | `start_service.py` |

## Hallazgo sobre la evidencia, no sobre el código

### H11 · Propiedad declarada y no acreditada · **un solo frame no confirmado por stream**

D-M2-1(a) y G-M2-07 exigen acreditar «máximo uno no confirmado por stream». El
campo `SupervisedAction.unacked_peak` existe **y nunca se actualiza**; ninguna
prueba mide la propiedad. El mensaje del commit de INC-M2-3 la menciona entre
los gates ejercitados.

**Corrección obligatoria.** O se instrumenta y se prueba, o se retira la
afirmación. Un campo muerto que sugiere una medición inexistente es peor que su
ausencia: invita a leer como acreditado lo que no lo está.

## Informativo

- `deadline.validity_exhausted` está definida y sin uso; su consumidor llega en
  INC-M2-4. Aceptable, pero conviene no acumular superficie sin consumidor.
- `_write_frame` y `_read_frame` están tipados como `object` con
  `type: ignore`, lo que anula la comprobación estática justo en la frontera de
  parseo. Preferible un `Protocol` mínimo.
- `verify_invocation_proof` se importa dentro de la función con una
  justificación débil; no hay circularidad que lo exija.

## Lo que esta ronda NO cubre

- Revisión **externa** e independiente sobre el diff real (G-M2-15).
- Perspectiva de seguridad ajena sobre el canal local y su modelo de amenaza.
- Plataforma Linux: todo lo verificado aquí corrió en Darwin arm64. El
  comportamiento de subreaper y de la recolección multinivel **no** está medido
  en esta ronda.
- Gates de INC-M2-4 e INC-M2-5, no implementados.

## Recomendación

**FIX-BEFORE-INC-M2-4.** H1, H2 y H3 son fallos de comportamiento contra
cláusulas normativas ya adoptadas, no ampliaciones de alcance: corregirlos cae
dentro de la autorización vigente. H11 debe resolverse antes de que ningún
documento vuelva a listar esa propiedad como ejercitada.

Ninguna corrección propuesta requiere tocar `contracts/`, schemas, ADR ni
ampliar el modelo de amenaza.
