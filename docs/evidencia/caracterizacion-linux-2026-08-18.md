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
puede citarla como evidencia **L** de que Linux x86_64/aarch64 comparte al
menos el comportamiento base de `RLIMIT_AS` y `cutime/cstime` con lo
esperado, pero no puede declarar E1 resuelta hasta correr en x86_64 y sobre
el caso de padre terminado.
