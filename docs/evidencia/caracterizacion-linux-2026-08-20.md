# Evidencia — caracterización Linux, suite vigente completa (8/8)

**Fecha:** 2026-08-20.

**Estado de evidencia (consolidación §2.1):** **L** — ejecución local, en una
sola ronda, en un solo entorno. No es **V** (no está conservada como prueba
automática en CI) ni **R** (no se ha reproducido en una segunda implementación
o entorno independiente).

**Relación con el acta anterior:** complementa y actualiza
[caracterizacion-linux-2026-08-18.md](caracterizacion-linux-2026-08-18.md).
Aquella corrida registró 7/7 de la suite entonces vigente; ésta ejecuta la
suite vigente completa de **8 tests, incluidas las tres Linux-only** que en
Darwin quedan en `skip`:

- `test_linux_cutime_cstime_capture_reaped_children` (/proc cutime/cstime);
- `test_orphaned_grandchild_cpu_is_lost_without_subreaper`;
- `test_subreaper_recovers_orphaned_grandchild_cpu` (PR_SET_CHILD_SUBREAPER).

## Cómo reproducir

```sh
scripts/characterize-linux.sh
```

El script fija la imagen por digest (no por tag flotante), de modo que la
corrida es reproducible byte a byte del entorno.

## Entorno exacto de esta corrida

| Campo | Valor |
|---|---|
| Motor | Docker Desktop en macOS (backend `linuxkit`) |
| Imagen | `python@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a` |
| SO del contenedor | Debian GNU/Linux 13 (trixie) |
| Kernel | Linux 6.11.11-linuxkit aarch64 |
| Python | 3.12.14 |

## Resultado

```text
Ran 8 tests in ~2.5s
OK
```

**8/8 OK, cero `ResourceWarning`.** Durante la primera corrida del día se
detectó un `ResourceWarning` por un pipe `stdout` sin cerrar en
`test_linux_cutime_cstime_capture_reaped_children`; se corrigió en
`tests/escape/test_host_characterization.py` (cierre explícito del pipe en el
`finally`) y la corrida registrada en este acta es la posterior al fix,
verificada con `grep -c ResourceWarning` = 0 sobre el log completo.

La suite Darwin del mismo commit corre 5 tests + 3 `skip` (los Linux-only),
sin warnings (`-W error::ResourceWarning`).

## Lo que este acta NO afirma

- No afirma niveles 1–2 de durabilidad de `flush_protocol_completed` en Linux;
  la caracterización de flush aquí es de disponibilidad de la primitiva, no de
  durabilidad bajo fallo.
- No afirma medición de RSS por muestreo; sigue pendiente (Y-2).
- No afirma cobertura de CI; la corrida es local y manual (clase L).

La ampliación de la suite (durabilidad bajo fallo, RSS por muestreo) sigue
pendiente como Y-1 / Y-2 y no se promueve por acuerdo verbal.
