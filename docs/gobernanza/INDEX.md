# Índice de gobernanza — ektel

<!-- dureza: [C] índice operativo — se actualiza con registro al crear/cerrar decisiones -->

> Pre-flight de Directivas v0.2.0 §3.2: antes de ejecutar una instrucción
> del dueño con efecto en este repo, leer este índice. Una página, orden
> inverso temporal, sin contenido normativo (solo punteros).

## Decisiones activas (vigentes)

| Fecha | Decisión | Qué decide | Ruta |
|---|---|---|---|
| 28-08 | Aceptación ADR-012 | Diseño M2 fijado; **NO autoriza** implementar M2/M3 ni crear tags/releases | decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md |
| 28-08 | Cierre M1-R2 | Conformidad GuaranteePlan cerrada | decisiones/cierre-m1-r2-2026-08-28.md |
| 28-08 | Aceptación ADR-011 | Handoff admisión→start normativo | decisiones/aceptacion-adr-011-handoff-2026-08-28.md |
| 22-08 | **Cierre M1** | **Ningún tag ni release hasta M3 cerrado** (orden del dueño); sin push/PR/tag | decisiones/cierre-m1-2026-08-22.md |
| 22-08 | Autorización M1 | Alcance M1 | decisiones/autorizacion-m1-2026-08-22.md |

## ADRs (docs/adr/, 001–012)

| Núm | Título | Estado |
|---|---|---|
| 012 | Supervisión local M2 (topología, contratos) | aceptado 28-08 |
| 011 | Handoff admisión→start | aceptado 28-08 |
| 001–010 | Alcance, wire format, identidad, vigencia, etc. | ver docs/adr/ |

## Deuda documental abierta

| Qué | Dónde | Estado |
|---|---|---|
| Caracterización x86_64 real (puerta pre-producción, N12/ADR-006) | README | pendiente |
| Ampliación suite de caracterización (durabilidad bajo fallo, RSS) | README | pendiente |
| Tag `pre-consenso-v0.3` (14-08) obsoleto: main 41 commits adelante | git | sin decisión del dueño |
