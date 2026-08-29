# ADR-012: Contrato local y topología de supervisión M2

**Estado:** **aceptado y normativo** — Kristhian Manuel Jimenez Sanchez
(`krisnova@hotmail.com`), 2026-08-28, mediante
`docs/decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md`.

Esta aceptación resuelve D-M2-1(a), D-M2-2(a), D-M2-3, D-M2-4 y D-M2-5(a).
No autoriza implementar M2/M3, crear procesos, cambiar schemas wire, activar CI
remota, crear tags ni publicar releases.

**Fecha:** 2026-08-28.

**Origen:** ADR-003, ADR-005, ADR-007, ADR-009, ADR-011 y
`docs/propuestas/paquete-preparacion-m2-2026-08-28.md`. M1-R2 cerró antes el
defecto de conformidad del `GuaranteePlan`; esta ADR fija las decisiones que
una autorización M2 futura no podrá improvisar en código.

## 1. Problemas resueltos

1. `ExecutionResult v1` declara truncamiento y descarte, pero no transporta
   stdout/stderr.
2. ADR-009 no fijaba topología, capacidad, valores temporales ni alcance de
   subreaper.
3. El `GuaranteePlan` se emite antes de conocer el deadline efectivo; no puede
   afirmar valores que sólo se aplican durante `start`.
4. `TerminationReason` y el receipt local carecían de semántica cerrada.
5. M2 precede a M3, mientras `audit_mode=required` depende del `AuditSink` y
   de eventos que pertenecen a M3.

## 2. Decisiones

### 2.1 D-M2-1(a): salida capturada en una API local

El wire `ExecutionResult v1` no cambia. La API local experimental adopta:

```text
AwaitedExecution {
  result: ExecutionResult,
  stdout: bytes,
  stderr: bytes
}

await_result(ExecutionHandle) -> AwaitedExecution
```

Cada stream conserva exactamente su prefijo hasta `max_stdout_bytes` o
`max_stderr_bytes`; después continúa drenando y descarta. Los flags de
truncamiento son por stream y `discarded_bytes` es la suma exacta de los dos
contadores. Los buffers no se escriben en replay store, logs, receipts ni
disco por efecto de M2.

El supervisor de acción transfiere frames ordenados de máximo 65 536 bytes por
stream al coordinador runtime, con crédito y confirmación que permiten como
máximo un frame no confirmado por stream. Libera cada frame confirmado y no
retiene una segunda copia completa. La cota estable de payload dentro del
runtime, antes de materializar los `bytes`, es:

```text
max_stdout_bytes + max_stderr_bytes + 2 * 65536
```

El pico de materialización puede ser:

```text
2 * (max_stdout_bytes + max_stderr_bytes) + 2 * 65536
```

por acción, más overhead de objetos, pipes y kernel que se caracteriza pero no
se declara como cota exacta de RSS. Si el coordinador deja de consumir, el
supervisor sigue drenando al hijo hasta los prefijos retenidos, descarta el
exceso y, si el canal se cierra, solicita terminación best-effort del grupo.

Cuando el resultado terminal y la salida pasan al `ExecutionHandle`, el slot se
libera. Retener handles terminados conserva memoria atribuida al llamador y no
queda cubierta por `max_concurrent_actions`; `await_result` transfiere esa
propiedad al `AwaitedExecution`. No se promete cero copias fuera del runtime ni
una cota global sobre payloads que el llamador conserve.

### 2.2 D-M2-2(a): coordinador y supervisor por acción

Un coordinador runtime, dueño de handles y slots, crea un proceso supervisor
dedicado por acción. El supervisor queda fuera del grupo ejecutado y crea para
éste un grupo propio con una primitiva POSIX equivalente a
`subprocess.Popen(..., process_group=0)`, sin `preexec_fn`.

Sólo el supervisor de acción puede activar `PR_SET_CHILD_SUBREAPER` en Linux;
su alcance es por proceso supervisor, no global al coordinador. Darwin conserva
la contabilidad multi-nivel como `unsupported`. EOF del canal del coordinador
solicita terminación best-effort, sin prometer muerte universal, recuperación
ni resultado.

La configuración local exacta es `max_concurrent_actions: int`, con `bool`
rechazado, default 1 y rango 1..64. El coordinador reserva un slot antes de
cualquier efecto irreversible. Sin slot devuelve
`StartFailed(reason_code=start_failed)`, no consume el token y permite un
reintento explícito. El slot se libera en fallo pre-spawn o en el handoff
terminal al handle.

Con límites wire máximos, una acción permite 128 MiB + 128 KiB estables y un
pico de payload de 256 MiB + 128 KiB. Sesenta y cuatro acciones permiten 8 GiB
+ 8 MiB estables y un pico de 16 GiB + 8 MiB, más overhead no acotado
exactamente. El rango es capacidad, no promesa de RSS bajo.

### 2.3 D-M2-3: tiempos, reloj y declaraciones de garantía

Configuración local exacta:

| Parámetro | Default | Rango | Semántica |
|---|---:|---:|---|
| `termination_grace_ms` | 2000 | 0..60000 | TERM→KILL; 0 es KILL directo. |
| `post_kill_drain_ms` | 1000 | 1..10000 | espera acotada de EOF tras KILL. |

Se rechazan `bool`, floats, tipos hostiles y valores fuera de rango durante la
inicialización. Para cada inicio:

```text
applied_grace_ms = min(termination_grace_ms, deadline_eff_ms)
useful_runtime_ms = deadline_eff_ms - applied_grace_ms
soft_termination_at = start_mono + useful_runtime_ms
hard_deadline_at = start_mono + deadline_eff_ms
```

Si `deadline_eff_ms == 0`, `start` devuelve
`StartFailed(reason_code=capability_rejected)` antes del CAS y sin spawn.
Si `termination_grace_ms >= deadline_eff_ms > 0`, la gracia aplicada se limita
al deadline, `useful_runtime_ms=0` y TERM comienza en `start_mono`; KILL sigue
acotado por `hard_deadline_at`. Es un perfil legal y deliberadamente sin tiempo
útil previo a la terminación cooperativa.

Esta ADR enmienda ADR-009: el `GuaranteePlan` emitido por admisión declara la
configuración, fórmula, topología y solicitud de subreaper; no declara como
aplicado un valor todavía desconocido. `guarantees_applied` declara gracia,
tiempo útil y subreaper realmente aplicados. En `assumptions`, el plan usa en
este orden entradas ASCII `clave=valor`:

1. `termination_grace_ms_configured=<int>`;
2. `useful_runtime_formula=deadline_eff_ms-applied_grace_ms`;
3. `supervisor_scope=per_action_process`; y
4. `subreaper_requested=<0|1>`.

El resultado usa, en este orden cuando correspondan:

1. `termination_grace_ms_applied=<int>`;
2. `useful_runtime_ms=<int>`; y
3. `subreaper_applied=<0|1>`.

La implementación futura debe probar valores, orden y ausencia. Si se exige
que el plan contenga valores aplicados, debe detenerse y versionar contrato; no
se muta retrospectivamente el resultado de admisión.

El mapa wire abierto `measurements` usa estas claves locales congeladas:

- `deadline_effective_ms`;
- `termination_grace_ms`;
- `useful_runtime_ms`;
- `soft_termination_after_start_ms`;
- `hard_deadline_after_start_ms`;
- `post_kill_drain_elapsed_ms`;
- `post_kill_forced_pipe_close` (`0|1` entero);
- `stdout_discarded_bytes`; y
- `stderr_discarded_bytes`.

`discarded_bytes` conserva la suma. Los offsets son relativos al inicio; no se
exportan instantes monotónicos. `finished_at_wall` y
`duration_monotonic_ms` terminan al recoger el proceso principal. El drenaje
post-KILL sólo acota latencia adicional de entrega y no amplía el deadline; al
vencer cierra pipes y marca el cierre forzado.

La última muestra de pared válida previa al CAS fija la vigencia restante y se
proyecta conservadoramente a monotónico. Ninguna muestra posterior extiende el
plazo. Una muestra final no finita o regresiva produce, si el supervisor aún
puede hacerlo, `supervision_failed/supervision_failure` sin fabricar tiempos.
`deadline_validity_exhausted` gana cuando la vigencia restante pre-CAS es menor
o igual que `deadline_ms`; en empate gana vigencia. Esta regla es propia de
ADR-012 y no reinterpreta la precedencia general de ADR-005.

### 2.4 D-M2-4: terminación local e idempotencia

V1 local sólo admite `TerminationReason.OPERATOR_REQUESTED`, sin detalle
arbitrario. `TerminationAccepted.receipt` es un identificador opaco local: no
es receipt de AuditSink, no tiene MAC ni claim de durabilidad y nunca se
registra completo.

Mientras la acción está viva, el primer `terminate` autenticado se linealiza en
el supervisor de acción y el coordinador guarda el receipt en el propio
`ExecutionHandle`. Si el resultado terminal ya estaba almacenado cuando llega
el primer `terminate`, el coordinador genera y guarda atómicamente el receipt,
devuelve `TerminationAccepted` y no contacta al supervisor; es un no-op
idempotente que no reclasifica el resultado. Repetir con ese objeto dentro de
la misma instancia devuelve el mismo receipt. Al desaparecer el último handle
desaparecen receipt y metadatos; no existe registro global.

Reiniciar el coordinador invalida todos sus handles. Perder sólo el supervisor
de acción produce ausencia o fallo honesto según la fase, no cambia la identidad
de instancia. Un handle forjado, cruzado o de otra instancia devuelve
`TerminationRejected(capability_rejected)`. En carrera, gana el primer hecho
observado; en empate de observación gana deadline conforme a ADR-005.

### 2.5 D-M2-5(a): frontera de auditoría entre M2 y M3

M2 sólo admite `audit_mode=optional`; `audit_trail` permanece `unsupported`.
Configurar `audit_mode=required` antes de M3 impide inicializar el servicio,
antes de solicitudes y sin consumir tokens. M2 no crea `RuntimeEvent`,
`AuditSink`, receipts ni un sustituto.

Esto no satisface ni elimina las obligaciones de C5/C7: los eventos y su
evidencia quedan pendientes de M3, incluidos rechazos de `terminate`. Cuando
M3 active `required`, conserva el orden de ADR-007/011:
`flush_protocol_completed` → nueva muestra de reloj → CAS → spawn.

## 3. Alternativas rechazadas

- `ExecutionResult v2` con stdout/stderr: exige migración wire prematura.
- Descartar toda salida: contradice la captura acotada adoptada.
- Threads dentro de un supervisor global: globalizan subreaper y carreras de
  `waitpid`, y amplían el blast radius.
- Receipt de terminación durable o razón extensible: requieren contrato nuevo.
- Coautorizar una rebanada M3: mezcla hitos y fabricaría claims de evidencia.

## 4. Consecuencias y no-claims

- `AwaitedExecution`, handles, receipts de terminación y configuración son
  locales y experimentales; no cambian `schema_version` v1.
- `max_concurrent_actions` acota slots activos, no memoria histórica retenida
  por el llamador ni RSS exacto.
- El deadline describe una transición de un supervisor vivo, no scheduler de
  tiempo real ni muerte universal.
- D-state, `setsid`, double-fork, muerte del supervisor y control del host
  conservan los no-claims existentes.
- M2 no promueve C5, C7 ni `audit_trail`; M3 sigue separado.

## 5. Gates para una autorización M2 futura

La implementación debe satisfacer G-M2-01..15 del paquete de preparación,
incluidos revalidación pura, CAS, crash, framing/backpressure, memoria,
deadline, terminación, capacidad, plataformas separadas, regresión M1-R2 y
revisión adversarial final. Un `PROCEED` documental no cubre ese futuro diff.

## 6. Stop rule

Esta ADR fija diseño normativo pero no concede autoridad de construcción. No
crear `start`, procesos, IPC, supervisores, handles productivos, salida,
terminación ni auditoría M2/M3 hasta una autorización posterior con alcance,
DoD y gates propios. No cambiar schemas/workflows ni crear tag o release por
efecto de esta aceptación.
