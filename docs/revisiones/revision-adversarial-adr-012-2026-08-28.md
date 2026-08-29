# Revisión adversarial final — ADR-012 y enmiendas normativas

**Fecha:** 2026-08-28. **Revisor:** OpenCode con GLM-5.3-Flash, contexto
independiente y mandato de sólo lectura. **Base:**
`20b09e9d03030bd6a3ded51076d5e6e4c5167e43`.

## Ronda 1 — FIX

La primera ronda emitió `FIX` por un P2: la especificación §6.8 aún atribuía el
`ExecutionHandle` al «proceso supervisor» y lo invalidaba al reiniciarlo,
mientras ADR-003 ya enmendada y ADR-012 separaban al coordinador dueño del
handle del supervisor dedicado por acción.

También señaló cinco P3:

1. receipt indefinido para el primer `terminate` post-resultado;
2. falta de procedencia para el erratum de cálculo conservador de ADR-011;
3. redacción de CI como garantía previa, no verificación administrativa;
4. omisión de ADR-003 en el origen de ADR-012; y
5. caso no declarado `termination_grace_ms >= deadline_eff_ms`.

Se corrigieron el P2 y los cinco P3 antes del reintento.

## Ronda 2 — PROCEED

El reintento emitió **PROCEED, sin P0-P2**. Verificó:

- propiedad del handle e invalidación por reinicio coherentes en ADR-003,
  ADR-009/012 y especificación §6/§8/§12;
- receipt post-resultado linealizado en el handle, idempotente y sin contacto
  con el supervisor;
- erratum ADR-011 declarado como tal, no decisión nueva;
- procedimiento de CI corregido: comprobar `ci-m1` antes del push y verificar
  la ausencia de runs del SHA después;
- gracia igual o mayor al deadline con tiempo útil cero y TERM inmediato;
- salida local, framing, backpressure, fórmulas de memoria y propiedad del
  llamador;
- slots, topología, subreaper, deadline, plan frente a valores aplicados,
  claves de `measurements`, terminación y frontera M2/M3; y
- límites de autoridad: sólo documentación, sin implementación M2/M3 ni cambios
  wire/workflow.

La ronda dejó cuatro P3 informativos: glosa opcional en ADR-005, dos expresiones
algebraicamente equivalentes para `exp_ms`, una frase histórica ambigua del
paquete y firmas conservadas en archivos históricos. La frase activa del
paquete se desambiguó antes del recheck; los otros tres no cambian la norma.

## Gates locales reproducidos

- `git diff --check`: limpio;
- suite: 151 OK, 3 skips Linux-only en Darwin;
- mypy estricto: 22 archivos limpios;
- fuzz contractual: 91/1547/0 y 19/172/0/0;
- fuzz de admisión: 2/63/0 fallos de oráculo/0 crashes; y
- regeneración: 91 vectores, diff cero.

El registro no extiende el veredicto a una futura implementación M2. Tras
añadir este asiento y desambiguar el P3 activo se requiere un recheck focal
final antes del commit.
