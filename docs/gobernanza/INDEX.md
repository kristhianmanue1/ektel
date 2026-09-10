# Índice de gobernanza — ektel

<!-- dureza: [C] índice operativo — se actualiza con registro al crear/cerrar decisiones -->

> Pre-flight de Directivas v0.2.0 §3.2: antes de ejecutar una instrucción
> del dueño con efecto en este repo, leer este índice. Una página, orden
> inverso temporal, **sin contenido normativo (solo punteros)**. Ante
> discrepancia entre este índice y un documento normativo, manda el documento.

**Estado del ciclo:** M0 y M1 cerrados (incluidas M1-R1 y M1-R2).
**M2 AUTORIZADO e IMPLEMENTADO, pero ABIERTO**: los cinco incrementos están
completos; **G-M2-01..15 = 15/15 CONFORMING** según adjudicación final.
**READY-FOR-HUMAN-M2-CLOSURE**, sin cierre humano todavía. R15/R16 SATISFIED;
R13 fuerte es known limitation/no-claim ratificado, con provenance del gap intacta.
**M3 no comienza hasta `M2 CLOSED`** por acta humana.
Ningún tag ni release hasta que M3 cierre.

## Decisiones activas (vigentes)

| Fecha | Decisión | Qué decide | Ruta |
|---|---|---|---|
| 10-09 | **Adjudicación final G-M2-15 / pre-cierre** | 15/15 CONFORMING; R15/R16 satisfechas en modelo ratificado; R13 fuerte fuera de claim, gap histórico preservado; M2 aún OPEN y listo para acto humano separado | revisiones/g-m2-15/adjudicacion-final-pre-cierre-m2-2026-09-10.md |
| 10-09 | **Ratificación R13-STRONG/R15/R16** | No-claim de intérprete compartido; autoriza R15/R16, evidencia local acotada y fail-closed tras pérdida; sin cerrar M2 ni iniciar M3 | decisiones/ratificacion-r13-strong-r15-r16-2026-09-10.md |
| 09-09 | **Enmienda G-M2-12** | Reconoce la incompatibilidad normativa del criterio original —exigía 16 GiB de payload que §2.2 excluye como presión extrema— y adopta **diez criterios conjuntivos**. Tras reevaluación individual, **G-M2-12 = VERDE**. Prohíbe afirmar que se probó materialmente 16 GiB. **NO** cierra M2 ni sustituye G-M2-15 | decisiones/enmienda-g-m2-12-2026-09-09.md |
| 09-09 | **Autorización M2** | **M2 AUTORIZADO**, ligado al commit `4beb7ebe…`. Adopta A-M2-1..7 (SpawnFrontier aislar; `admit.py` aditivo; regresión M1 = SCOPE VIOLATION; terminación local y opaca; sin wire nuevo; semántica de revalidación congelada; evolución monotónica). **NO autoriza** M3, M4, tags ni releases | decisiones/autorizacion-m2-2026-09-09.md |
| 08-09 | **Cierre F0-A** (AEC) | Veredicto `F0-A-CLOSED`; stop decision expresa: **NO autoriza F0-B/C/D**, no adopta AEC, no modifica el estado funcional de EKTEL | propuestas/aec-fase-0/f0-a/f0-a-verdict.md |
| 28-08 | Aceptación ADR-012 | Diseño M2 fijado; **NO autoriza** implementar M2/M3 ni crear tags/releases | decisiones/aceptacion-adr-012-supervision-m2-2026-08-28.md |
| 28-08 | Cierre M1-R2 | Conformidad GuaranteePlan cerrada | decisiones/cierre-m1-r2-2026-08-28.md |
| 28-08 | Aceptación ADR-011 | Handoff admisión→start normativo | decisiones/aceptacion-adr-011-handoff-2026-08-28.md |
| 22-08 | **Cierre M1** | **Ningún tag ni release hasta M3 cerrado** (orden del dueño); sin push/PR/tag | decisiones/cierre-m1-2026-08-22.md |
| 22-08 | Autorización M1 | Alcance M1 | decisiones/autorizacion-m1-2026-08-22.md |

## Documentos de preparación — no son decisiones

Deliberación y alcance. **Por sí solos no conceden autoridad de construcción**;
la autoridad de M2 vive exclusivamente en el acta de autorización. Se conservan
en `propuestas/` como provenance y no se reescriben.

| Fecha | Documento | Qué es | Ruta |
|---|---|---|---|
| 09-09 | Alcance técnico M2 (§8) — **rev 2** | Inventario de 45 rutas (32 nuevas, 13 existentes): 38 modificables/nuevas, 5 preservadas no modificables, 2 consumidas sin cambios. **Adoptado por referencia** por el acta de autorización M2 | propuestas/alcance-tecnico-m2-2026-09-09.md |
| 09-09 | Borrador acta autorización M2 — **rev 2** | **Sustituido como candidato operativo** por `decisiones/autorizacion-m2-2026-09-09.md`; se conserva como provenance | propuestas/borrador-autorizacion-m2-2026-09-09.md |
| 09-09 | Borrador enmienda G-M2-12 | **Sustituido** por `decisiones/enmienda-g-m2-12-2026-09-09.md`; se conserva como provenance | propuestas/borrador-enmienda-g-m2-12-2026-09-09.md |

## Ciclo M2 — evidencia y revisiones

| Qué | Estado | Ruta |
|---|---|---|
| **Expediente G-M2-15** | CONFORMING tras adjudicación final; matriz vigente 15/15 y preparación para cierre humano, no M2 CLOSED | revisiones/g-m2-15/ |
| Encargo de revisión externa (G-M2-15) | 3 familias, misma raíz, sin verse antes del primer veredicto; sin mayoría simple | revisiones/encargo-revision-externa-m2-2026-09-09.md |
| Estado histórico de evidencia por gate | Baseline 14 verdes/1 pendiente y addendum de reaperturas; matriz vigente en adjudicación final, no verde heredado | evidencia/estado-evidencia-m2-2026-09-09.md |
| Caracterización Darwin arm64 (clase L) | 339 OK, 4 skips | evidencia/caracterizacion-m2-darwin-2026-09-09.md |
| Caracterización Linux aarch64 (clase V) | 339 OK, 1 skip | evidencia/caracterizacion-m2-linux-2026-09-09.md |
| Manifiesto — identidad de implementación | R15/R16: `MANIFEST-ROOT b59553bc…`, 98 entradas; paquete de revisión identifica el commit exacto | evidencia/manifest-m2-sha256.txt |
| Ronda adversarial propia sobre INC-M2-1..3 | 11 hallazgos, corregidos | revisiones/revision-adversarial-m2-inc1-3-2026-09-09.md |
| Ronda adversarial propia sobre el FIX-AND-RETRY | 4 hallazgos, corregidos | revisiones/revision-adversarial-m2-fix-retry-2026-09-09.md |

Las dos rondas son **propias del ejecutor**: hallaron defectos reales pero **no
acreditan independencia** y no satisfacen G-M2-15.
| 28-08 | Paquete preparación M2 | Deliberación, invariantes y gates G-M2-01..15; **no es autorización** | propuestas/paquete-preparacion-m2-2026-08-28.md |

## Expediente AEC (Agent Execution Contract)

Investigación sobre un contrato neutral de ejecución agéntica que **no debe
depender de EKTEL**. F0-A cerrada; **F0-B, F0-C y F0-D permanecen no
autorizadas** y cada una exige un acto humano separado.

| Qué | Ruta |
|---|---|
| Mandato operativo vigente de F0-A | propuestas/aec-fase-0/MANDATO-F0-A.md |
| Veredicto de cierre (`F0-A-CLOSED`) | propuestas/aec-fase-0/f0-a/f0-a-verdict.md |
| Corpus, vocabulario y modelos de confianza | propuestas/aec-fase-0/f0-a/ |
| Cuestiones abiertas (0 P1, 12 P2 diferidos) | propuestas/aec-fase-0/f0-a/open-questions.md |
| Registros de corrida multimodelo | propuestas/aec-fase-0/records/ |
| Mandato original (sustituido, se conserva como provenance) | propuestas/Mandato-investigacion-Agent-Execution-Contract.md |

**Clasificación:** `PRIVATE-SANITIZED` — no autoriza transmisión ni
publicación. Única excepción: `f0-a/execution-paradigms.md`, marcado
`PUBLISHABLE` como candidato.

**Relación con M2:** no existe dependencia normativa demostrada entre F0-B y
M2. Esto **no** significa que `H-family` haya prevalecido; F0-A la mantiene
sólo como inclinación provisional, con `H-profiles` aún abierta.

## ADRs (docs/adr/, 001–012)

| Núm | Título | Estado |
|---|---|---|
| 012 | Supervisión local M2 (topología, contratos) | aceptado 28-08 |
| 011 | Handoff admisión→start | aceptado 28-08 |
| 001–010 | Alcance, wire format, identidad, vigencia, etc. | ver docs/adr/ |

## Deuda documental abierta

| Qué | Dónde | Estado |
|---|---|---|
| Ambigüedad de fuente normativa: README §29 remite la tabla de garantías a la consolidación 14-08, autodeclarada «no vinculante», mientras el manifiesto declara normativa la especificación v1.2 | README.md, project-manifest.yaml | pendiente |
| Caracterización x86_64 real (puerta pre-producción, N12/ADR-006) | README | pendiente |
| Ampliación suite de caracterización (durabilidad bajo fallo, RSS) | README | pendiente |
| Tag `pre-consenso-v0.3` → `ffdd566` (14-08): fijó el corpus previo al consenso D1–D7 (precondición §11.1 ya cumplida); hoy no apunta a nada vigente | git | sin decisión del dueño: conservar como marcador histórico o borrar |
| Memoria AN-KLA sin respaldo: `.an-kla/` está en `.gitignore` y no viaja en git | .gitignore | sin decisión del dueño |

<!--
Nota de mantenimiento: no se registra aquí el número de commits que el tag
pre-consenso-v0.3 lleva de retraso. Un contador se desactualiza con cada
commit y ya indujo una cifra falsa (decía 41 cuando eran 45). Para obtenerlo
en el momento: git rev-list --count pre-consenso-v0.3..HEAD
-->
