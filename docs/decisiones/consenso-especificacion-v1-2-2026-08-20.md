# Acta — consenso de la especificación ektel runtime mínimo M0–M3, v1.2

**Fecha:** 2026-08-20.
**Autoridad:** consenso explícito del dueño, conforme al §0 de la propia
especificación y a su criterio de adopción (§19, que recoge la propuesta
histórica §21; la especificación vigente no tiene §21).

## Objeto

El dueño declara alcanzado el consenso sobre
`docs/especificacion/ektel-runtime-m0-m3-v1.md` en su **versión 1.2
(2026-08-20)**. A partir de este acta, la especificación deja de ser
«candidata» y rige como fuente normativa única del runtime mínimo M0–M3, con
la prevalencia definida en su §0.

## Cobertura de las enmiendas post-consenso (Y-6)

Los ADR-001 a ADR-009 fueron aceptados el 2026-08-19
(`consenso-adr-001-009-2026-08-19.md`). Con posterioridad a ese consenso se
aplicaron dos rondas de enmienda transversal:

- `enmienda-transversal-b1-b8-2026-08-19.md` (ronda Codex B1–B8);
- `enmienda-transversal-v3-2026-08-20.md` (ronda Codex C1–C6 + verificación
  Claude D1–D5), que regeneró la especificación a v1.2.

Este acta declara explícitamente que los ADR **002, 003, 004, 005, 007, 008 y
009**, enmendados tras el consenso del 2026-08-19, quedan **cubiertos por el
presente consenso** en su texto vigente a la fecha. Ninguna enmienda posterior
al 2026-08-19 queda fuera del acto.

Nota de trazabilidad (Y-6): el hallazgo original identificaba las enmiendas de
ADR-005, ADR-007 y ADR-008 en el rango `fecf1b3` → `82f7a19` (renombre
`durable` → `flush_protocol_completed`, tipos de resultado por operación, C8
retirado). La verificación contra las dos actas de enmienda muestra que el
conjunto real enmendado post-consenso es el superset arriba listado; este acta
cubre el superset completo, que incluye los tres ADR señalados por Y-6.

Queda asentada la regla de gobernanza ya practicada: **toda enmienda
posterior a este consenso requiere su propio acta explícita**; no hay
enmiendas tácitas.

## Base de la decisión

- Dictamen de revisión cruzada final ADR/tabla/especificación:
  `docs/revisiones/revision-cruzada-final-2026-08-20.md`.
- Tabla pública de claims/no-claims, consensuada el 2026-08-19
  (`consenso-tabla-claims-2026-08-19.md`) y verificada contra la v1.2 en la
  revisión cruzada.
- Acta de divergencia P0–P3 (`divergencia-p0-p3-m0-m3-2026-08-19.md`), que
  sigue vigente: ektel no implementa P0–P3 literalmente.

## Lo que este consenso NO autoriza

- No autoriza por sí mismo la implementación de M0; esa autorización se
  otorga por acta separada (`autorizacion-m0-2026-08-20.md`).
- No autoriza M1, M2 ni M3.
- No modifica la stop rule ni promueve límites de recursos por acuerdo
  verbal.
