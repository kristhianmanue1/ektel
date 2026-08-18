# Evidencia — caracterización Linux vía contenedor desechable

**Fecha:** 2026-08-18T16:36:43Z.

**Estado de evidencia (consolidación §2.1):** **L** — ejecución local única,
en una sola ronda, en un solo entorno. No es **V** (no está conservada como
prueba automática en CI) ni **R** (no se ha reproducido en una segunda
implementación o entorno independiente).

**No sustituye** la corrida Darwin registrada en
[consolidación §9.1](../consolidacion-para-consenso-2026-08-14.md); la
complementa.

## Cómo reproducir

```sh
scripts/characterize-linux.sh
```

El script fija la imagen por digest (no por tag flotante) para que la corrida
sea reproducible byte a byte del entorno, aunque el contenido del `python:3.12-slim`
en Docker Hub cambie después.

## Entorno exacto de esta corrida

| Campo | Valor |
|---|---|
| Motor | Docker Desktop 28.5.1, daemon en macOS (backend `linuxkit`) |
| Imagen | `python@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a` |
| SO del contenedor | Debian GNU/Linux 13 (trixie) |
| Kernel | Linux 6.11.11-linuxkit |
| **Arquitectura** | **aarch64** — no x86_64 |
| Intérprete | Python 3.12.14 |
| Aislamiento | `--rm`, repo montado `:ro`; el contenedor no persiste tras salir |

## Resultado

Comando: `python3 -m unittest discover -s tests/escape -v`.

5 de 5 pruebas: **OK**. Incluye, por primera vez en este repositorio,
ejecución exitosa de `test_linux_cutime_cstime_capture_reaped_children`
(antes en estado `N` — no ejecutado).

## Qué mueve esto (E1–E3) y qué no

| Puerta empírica | Efecto de esta corrida |
|---|---|
| E1 · plataforma | Confirma comportamiento base en Linux aarch64. **No** decide plataforma primaria: falta x86_64 y el kernel real de despliegue si difiere de 6.11. |
| E2 · CPU | `cutime+cstime` del padre superviviente sí recupera CPU de 8 hijos breves ya recogidos (caso simple). **No** cubre el caso de padre también terminado ni reparentado — sigue en `N`. |
| E3 · memoria | `RLIMIT_AS` se acepta en Linux (`accepted`), contraste directo con el rechazo (`rejected`) observado en Darwin — confirma la fila correspondiente de la tabla en consolidación §5. RSS por muestreo sigue sin caracterizar aquí; esta suite no lo prueba. |
| E4 · lenguaje | Sin cambio. Esta corrida no es evidencia a favor ni en contra de ningún lenguaje del runtime — solo ejecuta la suite de caracterización, que ya declaraba poder vivir en Python independientemente del lenguaje final. |

## Huecos que quedan abiertos explícitamente

- **Arquitectura:** aarch64 vía virtualización de Apple Silicon, no x86_64.
  Si la plataforma de despliegue objetivo es x86_64, esta corrida no cubre
  ese caso y debe repetirse ahí antes de tratarlo como evidencia suficiente
  para ADR-006.
- **Kernel de producción:** 6.11.11-linuxkit es el kernel de la VM de Docker
  Desktop, no necesariamente el kernel del entorno de despliegue real.
- **Padre muerto / reparentado:** el caso de `cutime/cstime` cuando el padre
  también termina (no solo los hijos) sigue sin prueba conservada. La
  consolidación §5.4 ya señalaba este mecanismo como candidato, no como
  reparación general.
- **Casos peligrosos excluidos por diseño:** fork bomb, D-state, presión
  extrema de memoria y muerte deliberada del proceso de pruebas siguen fuera
  de esta suite (ver tests/escape/README.md); requieren entorno desechable
  con autorización específica adicional, no solo un contenedor Docker
  estándar.

## Siguiente paso propuesto para ADR-006

Esta corrida es insumo, no cierre. ADR-006 (plataforma y lenguaje iniciales)
puede citarla como evidencia **L** de que Linux aarch64 comparte al menos el
comportamiento base de `RLIMIT_AS` y `cutime/cstime` con lo esperado, pero no
puede declarar E1 resuelta hasta correr en x86_64 real y sobre el caso de
padre terminado.

## Intento de x86_64 vía emulación (mismo día) — resultado inconcluso

Se intentó cerrar el hueco de arquitectura corriendo la misma imagen (mismo
digest) con `docker run --platform linux/amd64`. Docker Desktop resuelve esto
con Rosetta 2 (traducción binaria de Apple), no con hardware ni con QEMU.

**Resultado:** 4 de 5 pruebas OK. `test_rlimit_as_platform_semantics` no
produjo `accepted`/`rejected`: el subproceso murió con
`rosetta error: mmap_anonymous_rw mmap failed, size=1000` antes de imprimir
nada.

**Diagnóstico:** no es evidencia sobre el kernel Linux x86_64. Rosetta
necesita mapear memoria propia para su traducción JIT; el `RLIMIT_AS` de
128 MiB que el test aplica al propio intérprete es suficientemente estrecho
para chocar con esa necesidad de Rosetta antes de que el `try/except` de
Python llegue a ejecutarse. Confirmado reproduciendo el mismo `setrlimit`
aislado, fuera de la suite, con el mismo resultado.

**Conclusión honesta:** la emulación x86_64 de Docker Desktop en Apple
Silicon (vía Rosetta) **no es un sustituto válido** para este test
específico. Los otros 4 casos sí corrieron sobre código traducido y no
muestran el mismo problema, pero como el binario entero pasa por Rosetta,
tampoco se tratan aquí como evidencia fuerte de comportamiento nativo
x86_64 — quedan registrados como dato adicional de bajo peso, no como cierre
de E1. El hueco de arquitectura sigue abierto: hace falta x86_64 real
(hardware o VM con virtualización completa, no traducción binaria) para
tratarlo como evidencia comparable a la corrida aarch64 de arriba.

## Caso de padre muerto en reparentado (E2) — cerrado con hipótesis confirmada

Se añadieron dos pruebas nuevas a `tests/escape/test_host_characterization.py`
para cubrir el hueco explícito señalado arriba: qué pasa con el CPU de un
hijo cuando el proceso que lo supervisaba muere **antes** de hacer `wait()`
sobre él (reparentado, no el caso simple ya cubierto de padre vivo).

**Hipótesis probada:** sin ningún mecanismo adicional, ese CPU es
irrecuperable para la línea de proceso original; con
`prctl(PR_SET_CHILD_SUBREAPER)` en un ancestro vivo, ese ancestro se vuelve
el nuevo padre del huérfano en el momento del reparentado y sí puede
recuperar su CPU completo vía `wait()`/`RUSAGE_CHILDREN`.

**Resultado (misma corrida, Linux 6.11.11-linuxkit aarch64, 2026-08-18):**

| Prueba | Resultado |
|---|---|
| `test_orphaned_grandchild_cpu_is_lost_without_subreaper` | OK — CPU del huérfano (~0.3s de cómputo) no aparece en `RUSAGE_CHILDREN` del proceso raíz; éste solo reap-ea a su hijo directo (el supervisor caído), no al nieto huérfano. |
| `test_subreaper_recovers_orphaned_grandchild_cpu` | OK — con `PR_SET_CHILD_SUBREAPER=1`, el huérfano se reparenta al proceso raíz mismo; `os.wait4(-1, 0)` lo recoge directamente y su CPU sí se contabiliza. |

Suite completa tras el cambio: **7 de 7 OK** (antes 5 de 5).

**Qué mueve esto en E2:** el hueco deja de ser "sin probar" y pasa a ser
"probado y con mitigación conocida". Si el diseño de ektel supervisa
procesos con más de un nivel de profundidad (un supervisor que a su vez
lanza hijos), **cualquier componente vivo destinado a contabilizar CPU debe
declararse subreaper** (`prctl(PR_SET_CHILD_SUBREAPER)`) antes de lanzar esa
jerarquía, o aceptar explícitamente que el CPU de huérfanos por caída de un
nivel intermedio es una pérdida de contabilidad conocida, no un bug latente.

**Qué NO prueba esto:** `PR_SET_CHILD_SUBREAPER` es Linux-only (no existe en
Darwin); si el runtime debe soportar macOS en algún punto, este mecanismo no
está disponible ahí y el hueco de padre-muerto persiste sin mitigación
conocida en esa plataforma. Tampoco prueba el caso con más de un nivel de
reparentado (huérfano de huérfano) ni con múltiples subreapers anidados.
