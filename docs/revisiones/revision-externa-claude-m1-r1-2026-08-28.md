# Revisión adversarial externa — M1-R1

**Fecha:** 2026-08-28. **Revisor:** Claude CLI en contextos frescos, modo de
sólo planificación. **Base:** `ddf8fa01f7752d12d60add144532c8043fa099f8`.
**Alcance:** working tree M1-R1; sin M2/M3, commit, push, tag o release.

Este registro resume ciclos reproducibles; no sustituye las salidas de pruebas
ni convierte una revisión intermedia en aprobación final.

## Ciclo 1 — FIX-AND-RETRY

1. Un `Deny` con `decision_id` inválido se degradaba a admisión en modo
   `optional`.
2. Un outcome hostil del replay store podía lanzar desde `__eq__` después de
   reservar el nonce.
3. `FileReplayStore` podía persistir un TTL entero no representable un segundo
   antes de la cota solicitada.

Correcciones: el `Deny` conserva fuerza negativa; outcomes comparados por
identidad de enum; TTL directo no representable devuelve `UNAVAILABLE`.

## Ciclo 2 — FIX-AND-RETRY

Los tres hallazgos del ciclo 1 quedaron corregidos. La revisión encontró una
familia adicional en la frontera `PolicyPort`:

1. doble lectura de `valid_until_wall` y `decision_id` permitía validar un
   valor y emitir otro;
2. campos o relojes numéricos hostiles podían propagar excepciones después de
   `evaluate()`;
3. un `Deny` podía degradarse a admisión `optional` si fallaba la segunda
   lectura monotónica;
4. el API directo del store propagaba excepciones de subclases numéricas;
5. el acta interna conservaba el conteo obsoleto de 145 pruebas.

Correcciones: clasificación por dataclass exacta, snapshot único de campos,
tipos numéricos exactos, conversión dentro de la frontera protegida y resolución
inmediata de señales negativas. El conteo se corrigió contra la suite real.

## Estado antes del ciclo final

- sondas hostiles dirigidas: tipadas y sin excepciones escapadas;
- Darwin: 150 pruebas OK, 3 skips Linux-only;
- `mypy==1.19.1 --strict src/`: 22 archivos limpios;
- fuzz contractual y de admisión: cero divergencias, fallos de oráculo o
  crashes;
- 91 vectores regenerados con diff cero;
- Linux aarch64: 150 pruebas OK, 0 skips; ambos fuzzes limpios y 91 vectores
  con diff cero;
- veredicto externo final: pendiente.

## Ciclo 3 — PROCEED

Claude no pudo iniciar este ciclo por límite de sesión. Un contexto fresco de
Kimi CLI ejecutó la revisión final de sólo lectura, sin aceptar las actas
anteriores como prueba. Reprodujo las sondas previas, verificó suite, mypy,
fuzzes, vectores, manifest e higiene, y no encontró defectos P0-P2 dentro de
M1-R1.

Hallazgo residual P3: `src/domain/capability.py::_finite_float()` acepta
subclases numéricas mediante `isinstance`; una llamada directa a
`verify_capability()` con `__float__` hostil puede propagar `RuntimeError`.
No existe ruta end-to-end desde `AdmissionService`: `_read_clock()` y la
configuración temporal exigen tipos exactos antes de invocar el dominio. Se
conserva como defensa en profundidad, no como bloqueo del paquete.

Comprobaciones independientes del ciclo:

- Darwin: 150 pruebas OK, 3 skips Linux-only;
- mypy 1.19.1 estricto: 22 archivos limpios;
- manifest: 12/12;
- fuzz contractual y de admisión: cero divergencias, fallos de oráculo o
  crashes;
- 91 vectores regenerados con diff cero;
- todos los hallazgos de los ciclos 1 y 2 bloqueados por sondas dirigidas;
- `git diff --check` y seis documentos no rastreados sin whitespace final;
- cero implementación productiva de M2/M3 y cero operación Git protegida.

**VEREDICTO FINAL EXTERNO: PROCEED.** No autoriza commit, push, tag, release,
M2 ni M3.
