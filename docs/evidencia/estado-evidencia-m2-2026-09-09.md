# Estado de evidencia M2 — gates G-M2-01..15

**Fecha:** 2026-09-09. **Incrementos:** INC-M2-1 a INC-M2-5, más el cierre de
lagunas posterior. **Manifiesto:** `manifest-m2-sha256.txt`, regeneración
verificada con diff cero.

**Estado global: 13 gates verdes, 1 parcial declarado, 1 pendiente. M2 sigue
sin ser cerrable**, porque G-M2-15 exige revisión adversarial **externa** que
ninguna ronda propia sustituye.

## Corridas base

| Plataforma | Clase | Resultado | Evidencia |
|---|---|---|---|
| Darwin arm64 | L | **339 OK, 4 skips** | `caracterizacion-m2-darwin-2026-09-09.md` |
| Linux aarch64 (digest) | V | **339 OK, 1 skip** | `caracterizacion-m2-linux-2026-09-09.md` |

`mypy --strict src` limpio en 34 archivos (host). 91 vectores con diff cero.
Fuzz de admisión y de revalidación sin divergencias ni crashes en ambas.
Ningún supervisor huérfano tras las suites.

## Gates

| Gate | Estado | Evidencia |
|---|---|---|
| **G-M2-01** revalidación/configuración | verde | Matriz de tipos hostiles (`bool`, floats, subclases), `audit_mode=required` impide inicializar, fuzz de 3000 iteraciones sin divergencias |
| **G-M2-02** pureza | verde | Cero `reserve_nonce`, cero `PolicyPort.evaluate`, cero emisión de token; más comprobación estructural de la firma |
| **G-M2-03** linealización | verde | Reloj final → CAS → spawn; sólo `CONSUMED` cruza |
| **G-M2-04** reconciliación | verde | Matriz completa de ADR-011 §2.6, incluidos truthy y tipos ajenos |
| **G-M2-05** concurrencia/reinicio | verde | 12 hilos, un ganador, reinicio conserva `spent`, nunca doble spawn |
| **G-M2-06** crash | **verde** | Inyección **real por SIGKILL** antes y después de persistir el CAS sobre `FileReplayStore`: antes deja `unspent` y reconsumible, después deja `spent` durable e irreabrible. Sin handle fabricado. `os._exit` no se usó como modelo: SIGKILL no deja correr `atexit` ni buffers, que es lo que puede ocultar un fallo de durabilidad |
| **G-M2-07** salida | **verde** | Prefijo exacto, límites 0/máximo, multibyte, streams independientes, suma exacta, frames ≤64 KiB, coordinador lento y caído, `max_unacked ≤ 1` medido. **Cerrado**: `post_kill_forced_pipe_close=1` ejercitado directamente (exige KILL **y** descendiente escapado por `setsid`; un nieto en el grupo muere con él y la clave vale 0 legítimamente); cotas estable y de pico publicadas en el terminal y contrastadas contra el payload retenido real; RSS caracterizado, nunca como cota |
| **G-M2-08** no-hang | verde | Cinco clases de proceso hostil, todas acotadas; escape por `setsid` declarado |
| **G-M2-09** deadline | **verde** | Aritmética pura completa y TERM→KILL con procesos reales. **Cerrado**: `wall_sample_valid` extraída a dominio y probada —regresión, no finitos, tipos hostiles— y enlazada con `supervision_failed` |
| **G-M2-10** terminación | verde | Handle válido, forjado, cruzado, de otra acción, repetido, post-resultado, liberado. Evento de rechazo **pendiente M3**, no verde ficticio |
| **G-M2-11** recolección/plan | **verde** | **Cerrado**: se mide que el descendiente **observado** muere con el grupo y que el **escapado** sobrevive y se declara; el supervisor se recoge tras el terminal. Subreaper aplicado realmente en Linux, `unsupported` en Darwin |
| **G-M2-12** capacidad | **PARCIAL — tensión normativa declarada** | Cota respetada bajo carrera, sin gastar token, liberación en handoff, slot indeterminado observable y recuperable. Fórmulas confirmadas aritméticamente: 64 acciones a límites máximos dan **8 GiB + 8 MiB estables y 16 GiB + 8 MiB de pico**. Modelo lineal comprobado empíricamente a escala reducida (6 acciones × 256 KiB). **La corrida a escala máxima NO se ejecuta** — ver §Tensión |
| **G-M2-13** plataforma | verde | Suites separadas; skips y degradaciones declarados |
| **G-M2-14** regresión | verde | M1-R2, gates M0/M1, `mypy --strict`, vectores diff cero, fuzzers |
| **G-M2-15** frontera | **PENDIENTE** | El diff no toca schemas, workflows, dependencias, M3, x86_64, tag ni release. Falta la **revisión adversarial externa `PROCEED` sobre el código real** |

## Tensión normativa en G-M2-12 — enmienda de criterio propuesta

Existe un **borrador de enmienda de criterio** en
`docs/propuestas/borrador-enmienda-g-m2-12-2026-09-09.md`, que reevalúa la
evidencia existente contra un criterio de diez puntos y concluye que los diez
están cubiertos.

**Ese borrador no promueve el gate.** Mientras no exista acta humana de
enmienda, el estado es y permanece
`G-M2-12 = PARCIAL — tensión normativa declarada`. Tras la firma corresponde
rehacer la reevaluación contra el árbol vigente en ese momento.

## Origen de la tensión

G-M2-12 pide confirmar con **límites máximos** un pico de 16 GiB + 8 MiB de
payload. Dos hechos lo impiden, y ninguno es una excusa operativa:

1. el paquete M2 **§2.2 excluye expresamente** los tests de presión extrema;
2. el host de referencia tiene **16 GiB de RAM física**, de modo que la
   corrida no sería una medición sino un OOM.

La incompatibilidad es **normativa y previa al host**: seguiría existiendo en
una máquina con 512 GiB, porque §2.2 no excluye por falta de memoria sino por
**clase de prueba**. Por eso corresponde una enmienda de criterio y no una
excepción: el defecto está en el criterio, no en la implementación.

**Formulación obligatoria** mientras rija la exclusión de §2.2: la cota máxima
fue demostrada **analíticamente** y la implementación fue comprobada
**empíricamente a escala segura**. Queda prohibido declarar que «se probó
16 GiB».

No se marca verde por acumulación de pruebas parciales.

## Promoción de claims

Con G-M2-06, 07, 09 y 11 cerrados, **`C2-handoff`, `C3`, `C4` y la parte de
inicio de `C6` quedan en condiciones de promoverse**, pero **no se promueven
en este acto**: la promoción exige prueba citada **y** el cierre de M2, que
depende de G-M2-15 y de la resolución de G-M2-12.

`C5`, `C7` y `audit_trail` permanecen **P hasta M3**.

## Rondas adversariales propias

Dos, ambas del ejecutor y por tanto **sin acreditar independencia**:
`revision-adversarial-m2-inc1-3-2026-09-09.md` (11 hallazgos) y
`revision-adversarial-m2-fix-retry-2026-09-09.md` (4 sobre las correcciones).
Encontraron tres cuelgues y una pérdida silenciosa de datos. Eso mide su
utilidad, **no** su independencia.

## Qué falta para cerrar M2

1. resolver G-M2-12: aceptar la confirmación aritmética **con acta**, o
   autorizar la corrida a escala;
2. obtener la **revisión adversarial externa** sobre el diff real (G-M2-15);
3. resolver sus findings de forma explícita;
4. acta humana de cierre.

Hasta entonces, **M2 permanece abierto**.
