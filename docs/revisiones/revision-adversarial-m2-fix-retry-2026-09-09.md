# Ronda adversarial simple — sobre el FIX-AND-RETRY de M2

**Fecha:** 2026-09-09.
**Objeto:** las correcciones de `cbd862c`, no el diff completo de M2.
**Ronda previa:** `revision-adversarial-m2-inc1-3-2026-09-09.md` (H1–H11).
**Naturaleza:** ronda **propia y simple** del ejecutor. No acredita G-M2-15.

**Veredicto: FIX-R1-R3-ANTES-DE-INC-M2-4.** Los once hallazgos previos están
corregidos y verificados. Las correcciones introdujeron **una degradación real
de promesa** y dos problemas de disciplina. Ninguno exige ampliar alcance.

## Verificación de los hallazgos previos

| Previo | Estado | Cómo se comprobó |
|---|---|---|
| H1 crédito bloqueaba el drenaje | corregido | El hijo termina y el terminal declara `credit_starved` |
| H2 espera de EOF ilimitada | corregido | Nieto que retiene pipes: terminal entregado, `forced_pipe_close` |
| H3 hijo huérfano tras terminar | corregido | `pgrep` confirma que el proceso ejecutado muere |
| H4 sin entrega incremental | corregido | La salida llega antes de que el hijo salga |
| H5 slot perdido en silencio | corregido | Observable y liberable por acto explícito |
| H6 registros sin purgar | corregido | `pending_actions` vuelve a cero |
| H7–H10 | corregidos | Pruebas de regresión propias |
| H11 propiedad no acreditada | corregido | `max_unacked_*` medido y acotado a 1 |

Sin procesos supervisores huérfanos tras la suite. 268 pruebas en dos corridas.

## Hallazgos nuevos

### R3 · Un coordinador **vivo pero lento** pierde salida que cabía · medio-alto

La corrección de H1 cambió «bloquearse para siempre» por «degradar a descarte a
los 2 s». Pero D-M2-1(a) habla de un coordinador que **deja de consumir**, no de
uno lento. `CREDIT_TIMEOUT_S` colapsa ambos casos.

**Verificado.** Coordinador vivo que confirma cada 3 s, límite pedido de
524 288 bytes: se entregaron **65 536** y se descartaron **458 752**. Es decir,
se perdió el **87 %** de una salida que cabía perfectamente en
`max_stdout_bytes`.

**Por qué importa.** D-M2-1(a) promete «conserva exactamente los primeros
`max_stdout_bytes`». Con un coordinador lento esa promesa deja de cumplirse, y
la única señal es `credit_starved` en el terminal. La corrección de H1 cambió un
cuelgue por una pérdida silenciosa de datos, que es más difícil de detectar.

**Corrección propuesta.** Distinguir *canal cerrado* —EOF, señal inequívoca de
que el coordinador no volverá— de *canal lento*, y descartar sólo en el primer
caso o tras una cota mucho mayor y **configurada**, no inventada.

### R1 · Constantes inventadas y fuera de la disciplina de configuración · medio

`CREDIT_TIMEOUT_S = 2.0` y `EOF_DRAIN_TIMEOUT_S = 3.0` **no derivan de ningún
documento normativo**: se comprobó por búsqueda en ADR-012, el paquete de
preparación M2 y la especificación. Además están **hardcoded**, mientras D-M2-3
somete toda cota temporal a configuración local validada con tipo exacto y rango
—`termination_grace_ms`, `post_kill_drain_ms`—.

Dos cotas de comportamiento observable escapan a esa disciplina y a su matriz de
validación de G-M2-01.

**Corrección propuesta.** Llevarlas a `M2Config` con rango y validación, o
derivarlas de `post_kill_drain_ms` donde corresponda.

### R2 · `forced_pipe_close` colisiona con la clave normativa · bajo

D-M2-3 congela la clave `post_kill_forced_pipe_close` (entero `0|1`) para el
cierre forzado **tras KILL**. El terminal publica `forced_pipe_close` (booleano)
para un hecho **distinto**: el cierre forzado tras agotar la espera de EOF sin
que haya habido KILL.

Nombres casi idénticos para hechos distintos invitan a que INC-M2-4 los
confunda o los fusione. Conviene renombrar el propio a algo inequívoco —por
ejemplo `eof_drain_forced_close`— antes de que exista el segundo.

### R4 · Detalles menores

- `_retained` se protege con `_handles_lock`, un lock cuyo nombre y propósito
  son otros. Dos invariantes distintos bajo un mismo cerrojo.
- Cuando `forced_pipe_close` es verdadero, los contadores del terminal se leen
  con los pumps posiblemente vivos: son valores **observados**, no totales. El
  código lo dice; ningún consumidor lo sabe todavía.

## Lo que esta ronda no cubre

Sigue siendo del ejecutor y sobre Darwin arm64. No hay revisión externa
(G-M2-15), ni medición en Linux, ni perspectiva ajena sobre el protocolo.

## Recomendación

Corregir **R3** y **R1** antes de INC-M2-4, porque INC-M2-4 introduce
`post_kill_drain_ms` y heredaría el desorden de cotas. **R2** es renombrado
barato y conviene hacerlo en el mismo acto. **R4** puede esperar.

Ninguna corrección requiere tocar `contracts/`, schemas ni ADR: no hay
`BLOCKED-BY-NORMATIVE-GAP`.
