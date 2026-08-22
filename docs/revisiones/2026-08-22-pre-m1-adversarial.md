# Ronda adversarial fresca — paquete pre-M1 (2026-08-22)

**Estado de este registro:** CERRADO — veredicto final `PROCEED` (ronda 6)
sobre el candidato v6. Los asientos de las seis rondas y el veredicto final
constan más abajo. Tras la emisión del PROCEED, el único cambio sobre el
artefacto fue este asiento (regla del encargo del Ejecutor, paso 7);
verificación final al pie.

**Artefacto revisado:** paquete pre-M1
(`docs/propuestas/paquete-preparacion-m1-2026-08-22.md` + índice de
`docs/propuestas/README.md` + este registro). Candidate congelado por
manifest SHA-256 antes de la ronda (ver `§Manifest`).

**Revisor:** Claude CLI autenticado (`claude -p`, `--permission-mode plan`),
proveedor/modelo distinto del autor (autor: OpenCode GLM 5.2). Sesión fresca,
sólo lectura, primera exposición al artefacto.

## Encargo de la revisión

Redactado para la ronda 1; la ronda 2 y siguientes añaden a estos blancos la
verificación de que los menores de la ronda anterior quedaron corregidos sin
defectos nuevos (los encargos íntegros de cada ronda viven en el dossier
efímero `/private/tmp/ektel-m1-prep-20260822-01/rondaN/encargo-revision.md`).

Revisión adversarial de sólo lectura sobre el diff final completo del
candidato. El revisor debe intentar **refutar**, con evidencia verificable
contra el repositorio (spec v1.2, ADR-001–010, actas, contratos, gate final
M0), los blancos:

1. **Autoridad:** que el paquete sea propuesta para decisión y no acto de
   autorización; que nada en él autorice M1/commit/push; que no resuelva por
   inferencia decisiones del dueño (D-P1–D-P4 deben quedar PENDIENTES).
2. **H6 `stdin_policy`:** tratamiento fiel de la deuda (acta §13, O-5):
   alternativas reales, recomendación razonada, consecuencias, contrato sin
   cambiar.
3. **O-1/O-3:** presentados como decisiones/gates de entrada sin fingir
   resueltos; fidelidad a los hallazgos del gate Claude.
4. **Criterios de salida:** conversión completa y verificable de los cuatro
   criterios M1 de spec §15 en gates; sin gates que no sean ejecutables ni
   criterios sin gate.
5. **Stop rules:** presentes, correctas, subordinadas a la stop rule del
   ciclo; rollback y definición de terminado coherentes.
6. **Alcance:** delimitación M1 fiel a spec §15/propuesta §13; nada de M2/M3
   o caracterización colándose; archivos/capas enumerados sin tocar nada hoy.
7. **Coherencia con v1.2:** citas y vocabulario conformes (§5.2/§5.6/§5.8/
   §6/§7/§8.2/§8.3/§9/§15; ADR-002/003/004/006/008; claims/no-claims); sin
   lenguaje público prohibido; sin promoción de claims P.
8. **Separación de caracterización:** x86_64/durabilidad bajo fallo/RSS por
   muestreo en carril separado, sin autorización implícita de M1.

Veredicto solicitado: `PROCEED` o `FIX-AND-RETRY` con bloqueantes concretos.

## Manifest

Candidato congelado antes de la ronda (SHA-256, `shasum -a 256`). Versión 6
del candidato, tras la corrección de los seis menores de la ronda 1, los
cinco de la ronda 2, los cuatro de la ronda 3, los tres de la ronda 4 y los
dos de la ronda 5 (asientos de las rondas más abajo, tras el veredicto
final):

```text
3dd4873fe898ee40f3b3e8945602170a138d4e641af66f7e1f5fb30af83bfd39  docs/propuestas/paquete-preparacion-m1-2026-08-22.md
0f262df97bd5406f037ae91e2f0b40e6b56b1e2102dd60aab0a015c999f1a975  docs/propuestas/README.md
```

(Las versiones previas del candidato: v1
`e1547d30…3818231` — ronda 1; v2 `215331a9…4d3ba8cc5e` — ronda 2; v3
`d989593d…f8a7a079` — ronda 3; v4 `d77cf74b…a12e5619` — ronda 4; v5
`4ae68aeb…81d1c2f` — ronda 5; el índice no cambió.)

Este registro (`docs/revisiones/2026-08-22-pre-m1-adversarial.md`) se excluye
de su propio manifest por diseño: es el destino del asiento post-revisión
(único cambio permitido sobre el candidato tras la ronda). El manifest auxiliar
completo de los tres archivos, con hash de este stub incluido, vive en el
dossier efímero `/private/tmp/ektel-m1-prep-20260822-01/`.

## Veredicto

**`PROCEED`** (ronda 6, confirmatoria final, sobre los hashes del candidato
v6: paquete `3dd4873f…bfd39`, índice `0f262df9…1a975`, stub
`c02419d3…29742`). Cero bloqueantes. Un menor editorial aceptado sin cambio
por la regla de cierre anunciada en el encargo de la ronda 6; observaciones
asentadas más abajo.

## Asiento de las rondas

Seis rondas, cada una con sesión fresca de Claude CLI (`claude -p`,
`--permission-mode plan`), proveedor/modelo distinto del autor (OpenCode GLM
5.2), sólo lectura. Encargos y veredictos íntegros en el dossier efímero
`/private/tmp/ektel-m1-prep-20260822-01/rondaN/`. Todas las rondas
verificaron primero la integridad del congelado (`shasum -a 256`), el estado
del árbol y los hechos fácticos (corpus 90/18 accept, fuzz bytes 1530/0 con
fingerprint `1c8412fe…640ddd89`, semántico 18/165/0/0/0, suite 20 tests/3
skips, commits `fba5a35`/`ecfde79`, MANIFEST-ROOT `47302f74…`, sin `.github/`,
`src/` sin código) con ejecución propia.

### Ronda 1 (candidato v1 `e1547d30…3818231`)

**Veredicto: `PROCEED`** — 8/8 blancos NO REFUTADOS, cero bloqueantes; seis
menores:

| # | Menor | Resolución |
|---|---|---|
| M-1 | G1/G4 confundían vocabularios (pedían «reason_code §8.2» para vectores con diagnóstico §5.6; la lista cerrada vive en §8.3) | Corregido en v2: capas separadas (contrato §5.6 / admisión §8.3) |
| M-2 | Stop rule 3 enunciaba la opción (α) de D-P4 como hecho | Corregido en v2: «la forma de compuerta que el dueño fije en D-P4» |
| M-3 | G3 anclaba «precedencia congelada (§4)» — §4 es Arquitectura | Corregido en v2: §5.6/§5.2 |
| M-4 | §1 omitía O-2 entre las observaciones del gate final | Corregido en v2 |
| M-5 | «token ya gastado (capability_rejected)» como negativo de admisión — es código de `StartFailed` | Corregido en v2: movido a `StartOutcome` |
| M-6 | Stop rules/Rollback/Terminado colgando de §8; ref. «(§2.1.8)» oscura | Corregido en v2: sección propia §9; «(§2.1, punto 8)» |

Observación aceptada con cambio: vehículo M1 de la degradación de política
pineado como condición del acto (incorporado en v3).

### Ronda 2 (candidato v2 `215331a9…4d3ba8cc5e`)

**Veredicto: `PROCEED`** — M-1..M-6 de la ronda 1 verificados corregidos;
cinco menores nuevos:

| # | Menor | Resolución |
|---|---|---|
| R2-1 | §1 citaba «uno clean-room, R5» sin la salvedad de independencia debilitada | Corregido en v3 |
| R2-2 | G9 congelaba conteos 18/165 sin salvedad D-P2 (insatisfacible si D-P2 se aprueba) | Corregido en v3: re-baseo declarado (91/19/bytes por corpus nuevo) |
| R2-3 | Entregable §15 M1 «replay store con semántica de reinicio» sin gate | Corregido en v3: **G16** nuevo; referencias G1–G16 |
| R2-4 | §4 enunciaba congelados como hecho normativo; punto 2 sin fuente | Corregido en v3: «se proponen… si el dueño las adopta»; salvedad explícita |
| R2-5 | Stub con referencia colgante («asiento de la ronda 1 más abajo») | Corregido en v3: nota de que los asientos se añaden tras el veredicto final |

Typos corregidos en v3 («inaccesible», «legales pero sospechosas»).

### Ronda 3 (candidato v3 `d989593d…f8a7a079`)

**Veredicto: `PROCEED`** — R2-1..R2-5 verificados corregidos; cuatro menores:

| # | Menor | Resolución |
|---|---|---|
| R3-M1 | «El árbol hoy está limpio en 43731b8» — falso al leerlo (3 archivos pendientes) | Corregido en v4: «no contiene trabajo de implementación…» |
| R3-M2 | «`__init__.py` vacíos» — tienen docstring | Corregido en v4: «de placeholder con docstring, sin código» |
| R3-M3 | Paso 7 del orden de admisión inerte en M1 sin declaración | Corregido en v4: nota (ADR-008 A3; matriz en M2/M3; acto puede fijar `audit_mode=optional`) |
| R3-M4 | G1 «todo vector inválido del corpus M0 (90)» — 18 son accept | Corregido en v4: «de veredicto reject… 18 de ellos accept» |

Observaciones accionables corregidas en v4: G4 cita §8.3+§6.6 con reserva
explícita (O-a); «si está configurado» en el paso 6 (O-b); re-baseo del fuzz
de bytes bajo D-P2 (O-d). Registradas sin cambio: O-c (atribución del
paréntesis de la autorización M0 bajo x86_64; sin consecuencia), O-e
(desfase 18-vs-20 tests del acta §13 M0 — defecto de la fuente, no del
paquete).

### Ronda 4 (candidato v4 `d77cf74b…a12e5619`)

**Veredicto: `PROCEED`** — correcciones R3 verificadas; tres menores:

| # | Menor | Resolución |
|---|---|---|
| R4-1 | G14 desplazaba el asiento del skew al resultado sin declarar que §7.3 lo sitúa en el evento (M3) | Corregido en v5: nota con remisión al patrón de §2.2 |
| R4-2 | «§6.2» sin desambiguar (spec vs propuesta) en dos puntos | Corregido en v5: «propuesta §6.2» |
| R4-3 | G4 sobreafirmaba «único código que encaja» | Corregido en v5: «el código que la letra asigna al caso vecino» |

Observación c corregida en v5 (G1 «si una entrada inválida cruza…»).
Registradas sin cambio: O-a (C3 duplicado en la nota de claims — defecto de
la fuente, citada fielmente), O-b («sink durable» adjetival, uso licenciado
por la propia spec §7.4).

### Ronda 5 (candidato v5 `4ae68aeb…81d1c2f`)

**Veredicto: `PROCEED`** — correcciones R4 verificadas; dos menores:

| # | Menor | Resolución |
|---|---|---|
| R5-m1 | Referencias desnudas que mezclaban espacios de numeración: «(§9)» y «(§7)» en §2.2, «§6.2» en el encabezado de G3 | Corregido en v6: «spec §9», «§7 de este paquete», «(propuesta §6.2)» |
| R5-m2 | D-P4 opción (β) sin declarar su costo de alcance | Corregido en v6: «roza M2: el inicio del grupo observado es entregable M2 (spec §15)…» |

Observaciones corregidas en v6: o-a (redundancia en G4), o-b («O-2 ya
cerrada» → formulación fiel del veredicto), o-d (§8.3 en el blanco 7 del
stub). Registrada sin cambio: o-c (el paquete no congela número de suite,
prudente ante el desfase 18-vs-20 de la fuente).

### Ronda 6 — confirmatoria final (candidato v6 `3dd4873f…bfd39`)

**Veredicto: `PROCEED`** — 8/8 blancos NO REFUTADOS con verificación por
ejecución propia (pytest 17 passed/3 skipped = 20 recolectados; fuzz
1530/0 y 18/165/0/0/0; recuento de corpus 90/18). Correcciones R5 verificadas
(R5-o-a «parcialmente aplicada»: la redundancia se redujo pero no desapareció
— sin error fáctico). El encargo de esta ronda anunció la regla de cierre:
menores no fácticos aceptados sin cambio. Quedan asentados:

- **m-1 (editorial, aceptado sin cambio):** redundancia residual en G4 — el
  paréntesis enuncia dos veces que §8.3 asigna `capability_rejected` al
  perdedor concurrente. Contenido fáctico correcto (verificado contra
  §8.3/§6.6 por el revisor).
- **o-a:** D-P4(β) cita «spec §15» por cadena normativa (la letra vive en
  propuesta §13 M2, adoptada por referencia) — correcto, anotado por higiene
  de citación.
- **o-b:** el título de §4 («invariantes no negociables») tiene registro más
  imperativo que el cuerpo, que se autolimita correctamente; anotado porque
  los títulos se citan fuera de contexto.
- **o-c:** «`__init__.py` de placeholder» en singular; son cuatro (sustancia
  correcta: cero código).
- **o-d (para el acto de autorización):** el archivo de clave del operador
  (spec §6.7, permisos `0600`) no tiene gate propio dentro del criterio 3
  (dependencias requeridas fail-closed): clave ausente/ilegible/inválida no
  está enumerada; `capability_rejected` la cubriría por defecto. El acto M1
  podría añadir la condición expresa a costo cero.

## Verificación final post-asiento

Tras escribir este asiento se re-verificó que `docs/propuestas/
paquete-preparacion-m1-2026-08-22.md` (`3dd4873f…bfd39`) y
`docs/propuestas/README.md` (`0f262df9…1a975`) permanecen byte-idénticos al
candidato v6 aprobado por la ronda 6, y que el único archivo modificado
respecto del congelado es este registro (asiento de las rondas y veredicto).
`git status` muestra exactamente los tres archivos del alcance; `git diff
--check` limpio; sin commit, sin push, sin escritura de memoria AN-KLA.
