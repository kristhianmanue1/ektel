# Estado de evidencia M2 — gates G-M2-01..15

**Fecha:** 2026-09-09. **Incrementos cubiertos:** INC-M2-1 a INC-M2-5.
**Manifiesto:** `manifest-m2-sha256.txt` (98 entradas, regeneración
verificada con diff cero).

**Estado global: M2 NO cerrable.** 8 gates en verde, 6 parciales y 1
pendiente. Este documento existe para que las lagunas sean visibles, no para
declarar un cierre que la evidencia no sostiene.

## Corridas base

| Plataforma | Clase | Resultado | Evidencia |
|---|---|---|---|
| Darwin arm64 | L | 314 OK, 4 skips | `caracterizacion-m2-darwin-2026-09-09.md` |
| Linux aarch64 (digest) | V | 314 OK, 1 skip | `caracterizacion-m2-linux-2026-09-09.md` |

`mypy --strict src` limpio en 34 archivos (host). 91 vectores con diff cero.
Fuzz de admisión y de revalidación sin divergencias ni crashes en ambas
plataformas.

## Gates

| Gate | Estado | Evidencia y laguna |
|---|---|---|
| **G-M2-01** revalidación/configuración | **verde** | `test_start_revalidation`, `test_m2_config`, `fuzz_start_revalidation` (3000 iter., 0 divergencias). Matriz de tipos hostiles incluida `bool`, floats y subclases; `audit_mode=required` impide inicializar |
| **G-M2-02** pureza | **verde** | Spy con cero `reserve_nonce`, cero `PolicyPort.evaluate`, cero emisión de token; además comprobación estructural de que la firma no admite puertos |
| **G-M2-03** linealización | **verde** | Reloj final → CAS → spawn; sólo `CONSUMED` cruza |
| **G-M2-04** reconciliación | **verde** | Matriz completa de ADR-011 §2.6, incluidos valores truthy y estados de otro tipo |
| **G-M2-05** concurrencia/reinicio | **verde** | 12 hilos con el mismo token contra `FileReplayStore` real: un ganador, reinicio conserva `spent`, nunca doble spawn |
| **G-M2-06** crash | **PARCIAL** | Cubierto alrededor del spawn y la no reapertura del token. **Falta** la inyección de crash **antes y después de persistir el CAS**, que el gate exige explícitamente |
| **G-M2-07** salida | **PARCIAL** | Prefijo exacto, límites 0/máximo, multibyte, streams independientes, `discarded_bytes` como suma, frames ≤64 KiB, coordinador lento y caído, y `max_unacked ≤ 1` medido. **Falta**: `post_kill_forced_pipe_close=1` no se ejercita de forma directa, y **no se midió** la cota estable ni el pico de materialización de las dos fórmulas de D-M2-1, ni la caracterización de RSS |
| **G-M2-08** no-hang | **verde** | Cinco clases de proceso hostil; todas acotadas. Escape por `setsid` comprobado y **declarado**, no mitigado |
| **G-M2-09** deadline | **PARCIAL** | Aritmética pura completa y TERM→KILL con procesos reales. **Falta**: la ruta de **muestra de pared inválida o regresiva** está implementada pero **no probada** con reloj falso |
| **G-M2-10** terminación | **verde** | Handle válido, forjado, cruzado entre instancias, de otra acción, repetición con el mismo objeto, post-resultado sin contactar al supervisor, handle liberado. El evento de rechazo queda **marcado pendiente M3**, no verde ficticio |
| **G-M2-11** recolección/plan | **PARCIAL** | Grupo propio verificado por `getpgid`; subreaper aplicado realmente en Linux y `unsupported` declarado en Darwin; `GuaranteePlan` y `guarantees_applied` probados. **Falta**: la **recolección de descendientes observados** no está medida como tal |
| **G-M2-12** capacidad | **PARCIAL** | Cota respetada bajo carrera de 16 hilos, sin gastar token por falta de slot, liberación en handoff, sin registro global, y slot retenido por indeterminación observable y recuperable. **Falta**: la confirmación con **límites máximos** —8 GiB + 8 MiB estables y pico de 16 GiB + 8 MiB para 64 acciones— **no se ejecutó**; exigiría memoria que este host no tiene |
| **G-M2-13** plataforma | **verde** | Suites separadas en Darwin arm64 y Linux aarch64 con imagen fijada por digest; skips y degradaciones declarados |
| **G-M2-14** regresión | **verde** | M1-R2 cerrado, gates M0/M1 verdes, `mypy --strict`, vectores diff cero, fuzzers sin divergencias |
| **G-M2-15** frontera | **PENDIENTE** | El diff no toca schemas, workflows, dependencias runtime, M3, x86_64, tag ni release. Pero **falta la revisión adversarial externa `PROCEED` sobre el código real**, que ninguna ronda propia puede sustituir |

## Promoción de claims

`C2-handoff`, `C3`, `C4` y la parte de inicio de `C6` **no se promueven
todavía**: su promoción exige prueba citada y G-M2-06, G-M2-07, G-M2-09,
G-M2-11 y G-M2-12 siguen parciales.

`C5`, `C7` y `audit_trail` permanecen **P hasta M3**. `audit_mode=optional`
evita el bloqueo por durabilidad pero **no elimina** la obligación de emitir el
evento, incluido el `capability_rejected` de un `terminate` inválido.

## Rondas adversariales propias

Dos, ambas del ejecutor y por tanto **sin acreditar independencia**:

- `revision-adversarial-m2-inc1-3-2026-09-09.md` — 11 hallazgos, corregidos;
- `revision-adversarial-m2-fix-retry-2026-09-09.md` — 4 hallazgos sobre las
  correcciones, corregidos.

Ambas encontraron defectos reales de comportamiento, incluidos tres cuelgues y
una pérdida silenciosa de datos. Eso mide su utilidad, **no** su independencia.

## Qué haría falta para cerrar M2

1. cerrar las seis lagunas de los gates parciales, o **autorizar
   explícitamente** su exclusión con acta;
2. obtener la **revisión adversarial externa** sobre el diff real (G-M2-15);
3. resolver sus findings de forma explícita;
4. acta humana de cierre.

Hasta entonces, **M2 permanece abierto**.
