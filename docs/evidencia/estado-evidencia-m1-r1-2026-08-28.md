# Estado de evidencia local — M1-R1

**Fecha:** 2026-08-28. **Clase:** local, Darwin. **Base inicial:**
`ddf8fa01f7752d12d60add144532c8043fa099f8`.

Este documento registra una reproducción contemporánea del paquete de
corrección M1-R1 en Darwin y Linux aarch64. No sustituye las actas de cierre M1
ni extiende esos resultados a otras plataformas.

## Evidencia disponible al iniciar

- árbol limpio y `main == origin/main` en la base indicada;
- AN-KLA integrado; `context status` y `verify` sanos en revisión 30;
- el dossier efímero histórico
  `/private/tmp/ektel-m1-prep-20260822-01` ya no existía;
- el único run remoto del SHA actual no ejecutó pasos por límite de
  facturación/cupo de GitHub Actions; no es evidencia de regresión del código.

## Resultados reproducidos

| Gate | Resultado |
|---|---|
| Suite completa Darwin | 150 OK, 3 skips Linux-only |
| Suite completa Linux aarch64 | 150 OK, 0 skips; escape Linux 8/8 ejercitado |
| `mypy==1.19.1 --strict src/` | limpio, 22 archivos; ejecutado en Darwin |
| Fuzz contractual bytes | Darwin y Linux: 91 bases, 1547 mutaciones, 0 divergencias |
| Fuzz contractual semántico | Darwin y Linux: 19 bases accept, 172 mutaciones, 0 divergencias, 0 fallos de oráculo, 0 errores de base |
| Fuzz de admisión | Darwin y Linux: 2 bases, 63 mutaciones, 0 fallos de oráculo, 0 crashes, 0 errores de base |
| Regeneración de vectores | Darwin y Linux: 91 vectores, diff recursivo cero |
| Claims temporales extremos | `nbf`/`exp=10**1000`, cota derivada no finita y TTL no representable: rechazo tipado, 0 reservas parciales |
| G13 local nuevo | n=200; min 3.824 ms, p50 6.886 ms, p95 13.448 ms, max 22.933 ms, media 7.586 ms |
| Manifest del overlay | 12/12 archivos `OK` con `shasum -a 256 -c` |
| Higiene del diff | `git diff --check` limpio; documentos no rastreados sin whitespace final |
| Revisión externa final | Kimi CLI, contexto fresco: `PROCEED`; 0 P0-P2, 1 P3 de defensa en profundidad sin ruta desde `AdmissionService` |

Comandos canónicos:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python scripts/fuzz_diferencial.py
python scripts/fuzz_admision.py
EKTEL_VECTORS_OUT=<directorio-temporal> python scripts/generate-golden-vectors.py
git diff --check
```

Los documentos nuevos todavía no rastreados se revisan además con una búsqueda
explícita de whitespace final; `git diff --check` por sí solo no los incluye.

Para no alterar dependencias del proyecto, `mypy==1.19.1` se instaló en el
venv efímero `/private/tmp/ektel-mypy-1.19.1`. No se descargó mypy dentro de
Linux: la capa histórica que lo contenía ya no estaba disponible localmente;
ese gate Linux y el CI remoto permanecen pendientes.

## Reproducción Linux aarch64

- staging efímero = `git archive HEAD` de `ddf8fa01…` más los 14 archivos
  objeto de validación M1-R1; el acta
  externa generada por la revisión queda fuera del staging para evitar que su
  actualización posterior altere la identidad del código probado;
- digest combinado del inventario SHA-256 del staging:
  `69ef0a4f51f30e7458f12a06c3da1ef0164643f25a3116998053db3c6e687864`
  (rutas relativas; excluye este documento para evitar autorreferencia);
- manifest verificable del overlay intencionado:
  `docs/evidencia/manifest-m1-r1-sha256.txt`;
- imagen `python:3.12-slim-bookworm` fijada como
  `python@sha256:fa161ca9d626b475d504c439b943e295fbca9e2560b1be14654ade60e7d8d45a`;
- Docker server `linux/arm64`, contenedor `aarch64`, Python 3.12.14;
- corrida final como UID 10001, `--read-only`, `--network none`,
  `--cap-drop ALL`, `no-new-privileges`, fuente `/repo:ro` y tmpfs para `/tmp`;
- suite 150/150, 0 skips; fuzz contractual y de admisión sin fallos; vectores
  regenerados con diff cero. Las ocho pruebas `tests/escape` quedaron
  ejercitadas dentro de la suite completa.

La medición G13 contemporánea se ejecutó con el script versionado, store
durable real y 200 admisiones independientes. Es evidencia local clase L de
este diff, no una reconstrucción del dossier histórico ni una promesa de
plataforma:

```json
{"n":200,"min_ms":3.824416,"p50_ms":6.886292,"p95_ms":13.448208,"max_ms":22.933,"mean_ms":7.58588851}
```

## Límites de la evidencia

- El timeout del `PolicyPort` sólo detecta respuestas tardías; no cancela un
  adaptador bloqueado.
- El run remoto del SHA base falló antes de ejecutar pasos por estado de
  facturación/cupo. Darwin y el contenedor Linux no sustituyen CI remoto.
- Mypy 1.19.1 no se ejecutó dentro del contenedor Linux de este ciclo; sí quedó
  limpio sobre el mismo código en Darwin.
- El G13 nuevo es una medición distinta; no reconstruye el dossier histórico
  ausente ni permite atribuirle sus manifests originales.
- `verify_capability()` llamado directamente con una subclase numérica hostil
  puede propagar su excepción; `AdmissionService` exige tipos exactos antes de
  esa llamada, por lo que no existe una ruta end-to-end demostrada en M1-R1.
- No hubo commit, push, tag, release ni ejecución de M2/M3 en esta corrida.
