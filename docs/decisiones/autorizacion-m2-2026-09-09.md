# Acta — autorización de M2 (supervisión)

**Fecha del acto:** 2026-09-09.

**Autoridad:** decisión explícita del dueño del proyecto, comunicada por canal
el 2026-09-09 y transcrita íntegramente en §1.

**Vinculación:** la autorización queda ligada específicamente al estado del
repositorio en el commit

```
4beb7ebe9127660c3c8671d02875b2ca1470a0a4
```

y a los artefactos de preparación contenidos o referenciados por él. Estado
verificado en el momento de asentar este acta: `HEAD == origin/main ==
4beb7ebe…`, árbol limpio, y digests SHA-256 coincidentes:

| Artefacto vinculado | SHA-256 |
|---|---|
| `docs/propuestas/borrador-autorizacion-m2-2026-09-09.md` (rev 2) | `c8ee83201237c16b6e0cf6a9c0f5185067bfc56f7505f3e5e7b765d5f94e4639` |
| `docs/propuestas/alcance-tecnico-m2-2026-09-09.md` (rev 2) | `d7363bac6ef1f3598720425d38e3787c5b3933167bb493f1c95e3531c6e203c2` |
| `docs/gobernanza/INDEX.md` | `7524257d3e86745e4d2535b8f37da64a3e17539600f3f9eec4721b87dd039870` |

Conforme al criterio de adopción de la especificación v1.2 §19 punto 6, cada
hito requiere su propia autorización. Este acta la registra para **M2**. M0
la obtuvo el 2026-08-20 y M1 el 2026-08-22. **M3 sigue sin autorizar.**

## 1. Transcripción fiel de la decisión del dueño

> **Autorización humana de M2 — EKTEL**
>
> Fecha: 2026-09-09
>
> Yo, como dueño del proyecto EKTEL, autorizo expresamente el inicio de la
> implementación de M2 — Supervisión, sujeto estrictamente al alcance,
> invariantes, gates, límites de autoridad, stop rules y condiciones de cierre
> definidos en el paquete documental congelado en:
>
> `4beb7ebe9127660c3c8671d02875b2ca1470a0a4`
>
> La autorización queda vinculada específicamente a ese estado del repositorio y
> a los artefactos de preparación contenidos o referenciados por dicho commit.
>
> **Alcance autorizado**
>
> Se autoriza exclusivamente la implementación de M2 conforme a:
>
> - especificación M0–M3 vigente;
> - ADR-011;
> - ADR-012;
> - paquete de preparación M2;
> - gates G-M2-01..15;
> - borrador de autorización M2 revisión 2;
> - alcance técnico §8 revisión 2;
> - resoluciones de alcance del 2026-09-09.
>
> Se adoptan expresamente las siguientes decisiones:
>
> - SpawnFrontier se preserva y aísla; no se retira durante M2;
> - `admit.py` sólo puede recibir una extensión aditiva compatible con M1;
> - cualquier regresión observable de M1 se trata inicialmente como
>   SCOPE VIOLATION;
> - la terminación M2 será local y opaca;
> - M2 no puede crear por su cuenta nuevos contratos wire para terminación;
> - la ubicación concreta de la revalidación entre domain/application puede
>   resolverla el desarrollador, pero su semántica permanece congelada;
> - M2 debe constituir una evolución monotónica respecto de las garantías
>   cerradas en M1.
>
> **Fuera de alcance**
>
> Esta autorización no concede autoridad para:
>
> - M3;
> - M4;
> - capability enforcement genérico;
> - sandboxing general;
> - aislamiento general de filesystem o red;
> - AEC universal;
> - integración específica con Ágora, Skopos o AN-KLA;
> - cambios de routing, memoria, plugins o delegación;
> - modificación no autorizada de contratos wire congelados;
> - tags;
> - releases;
> - preparación de alfa.
>
> F0-B permanece fuera del critical path de M2, pero no queda cancelado ni
> resuelto.
>
> **Condición de parada**
>
> Si durante M2 aparece una necesidad que exija:
>
> - ampliar el alcance congelado;
> - modificar contratos wire fuera de autorización;
> - reabrir garantías cerradas de M1;
> - introducir capability enforcement;
> - introducir sandboxing;
> - resolver un vacío normativo no previsto;
>
> el agente debe detener ese incremento y devolver:
>
> `BLOCKED-BY-NORMATIVE-GAP`
>
> o la condición equivalente prevista por la gobernanza.
>
> No debe resolver unilateralmente el vacío.
>
> **Obligaciones de cierre**
>
> La autorización de construcción no constituye aprobación del código.
>
> M2 sólo podrá cerrarse después de:
>
> - satisfacer G-M2-01..15;
> - regresión completa de M1;
> - evidencia reproducible;
> - validación en las plataformas previstas;
> - revisión adversarial multiagente sobre el diff real;
> - resolución explícita de findings;
> - acta humana de cierre.
>
> Un PROCEED documental previo no cubre el código futuro.
>
> **Decisión**
>
> **AUTORIZO M2.**
>
> El agente puede comenzar la implementación dentro de esta frontera y
> únicamente dentro de ella.
>
> Esta autorización queda ligada al commit:
>
> `4beb7ebe9127660c3c8671d02875b2ca1470a0a4`
>
> Cualquier cambio posterior a los artefactos normativos o de alcance requiere
> nueva revisión y, cuando corresponda, nueva autorización humana.

## 2. Fuentes normativas adoptadas por referencia

Este acta no reescribe su contenido; lo adopta:

- especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2, §8.0
  handoff y autorización de `terminate`, §12 supervisión enmendada por
  ADR-012, §15 M2, §19.6);
- `docs/adr/adr-011-handoff-admision-start.md`;
- `docs/adr/adr-012-supervision-local-m2.md`;
- `docs/propuestas/paquete-preparacion-m2-2026-08-28.md` (§2 alcance, §4
  invariantes, §5 gates y DoD, §6 incrementos, §7 capas);
- gates **G-M2-01..15**;
- `docs/propuestas/borrador-autorizacion-m2-2026-09-09.md` (revisión 2);
- `docs/propuestas/alcance-tecnico-m2-2026-09-09.md` (revisión 2), del que se
  adopta el inventario de **45 rutas** (32 nuevas, 13 existentes; 38
  modificables o nuevas, 5 preservadas no modificables, 2 consumidas sin
  cambios);
- resoluciones de alcance del 2026-09-09, transcritas en §1.

El borrador de la revisión 2 queda **sustituido como candidato operativo** por
este acta y se conserva en `docs/propuestas/` como provenance. No se reescribe
ni se elimina.

## 3. Decisiones adoptadas expresamente

| # | Decisión | Efecto operativo |
|---|---|---|
| A-M2-1 | `SpawnFrontier` se preserva y **aísla**; no se retira durante M2 | Quedan intactos y deben seguir pasando sin modificación `src/ports/spawn_frontier.py`, `src/adapters/spawn_frontier_counter.py`, `tests/unit/helpers_m1.py`, `tests/adversarial/test_fuzz_admision.py` y `tests/adversarial/test_policy_spawn_frontier.py` (20 pruebas). La frontera M2 se implementa en paralelo con `src/ports/process_host.py`. Retirar un símbolo M1 de los re-exports de `ports/__init__.py` o `adapters/__init__.py` es `SCOPE VIOLATION` |
| A-M2-2 | `src/application/admit.py` sólo admite **extensión aditiva** compatible con M1 | Se preservan semántica, decisiones de admisión, diagnósticos y su orden, comportamiento fail-closed, `PolicyPort`, contratos wire y regresión M1 completa |
| A-M2-3 | Toda **regresión observable de M1** se trata inicialmente como `SCOPE VIOLATION` | Se detiene ese incremento hasta demostrar documentalmente que el cambio estaba autorizado. Prohibido reinterpretar una regresión como adaptación implícita de M1 a M2 |
| A-M2-4 | La terminación M2 es **local y opaca** | Handle/capability local conforme a ADR-012; receipt opaco, local, no durable y sin MAC; `capability_rejected` como único reason code de rechazo |
| A-M2-5 | M2 **no puede crear por su cuenta** nuevos contratos wire para terminación | `termination-token-payload` permanece congelado sin capa productora. Si el incremento demuestra que hace falta: detener y declarar `BLOCKED-BY-NORMATIVE-GAP` |
| A-M2-6 | La **ubicación** de la revalidación entre domain y application la resuelve el desarrollador; su **semántica permanece congelada** | Cero `PolicyPort` nuevo, cero `reserve_nonce`, cero emisión de token nuevo; determinismo y pureza acreditados por G-M2-02 |
| A-M2-7 | M2 es **evolución monotónica** respecto de las garantías cerradas en M1 | Agregar funcionalidad M2 no concede autoridad para invalidar evidencia M1 |

## 4. Límites de autoridad

**Autorizado:** implementar M2 en las capas y rutas enumeradas por el alcance
técnico §8 revisión 2; pruebas `unit`, `integration`, `adversarial` y `escape`;
fuzz y scripts necesarios; CI **local** y configuración de desarrollo para
`mypy --strict`; documentación de implementación, rondas y evidencia; commits
locales por avance.

**No autorizado** (transcripción de §1): M3 · M4 · capability enforcement
genérico · sandboxing general · aislamiento general de filesystem o red · AEC
universal · integración específica con Ágora, Skopos o AN-KLA · routing,
memoria, plugins o delegación · modificación no autorizada de contratos wire
congelados · tags · releases · preparación de alfa.

**F0-B** permanece fuera del critical path de M2, **no cancelado ni resuelto**.

## 5. Condición de parada

Si durante M2 aparece una necesidad que exija ampliar el alcance congelado,
modificar contratos wire fuera de autorización, reabrir garantías cerradas de
M1, introducir capability enforcement o sandboxing, o resolver un vacío
normativo no previsto: **detener ese incremento** y devolver
`BLOCKED-BY-NORMATIVE-GAP` o la condición equivalente prevista por la
gobernanza. **No resolver unilateralmente el vacío.**

## 6. Obligaciones de cierre

**La autorización de construcción no constituye aprobación del código.** Un
`PROCEED` documental previo no cubre el código futuro (ADR-012 §5).

M2 sólo podrá cerrarse tras: satisfacer G-M2-01..15 · regresión completa de M1
· evidencia reproducible · validación en las plataformas previstas (Darwin
arm64 clase L y Linux aarch64 con imagen fijada por digest, clase V, probadas
por separado) · **revisión adversarial multiagente sobre el diff real** ·
resolución explícita de findings · **acta humana de cierre**.

El cierre de M2 no abre por sí mismo un ciclo de publicación ni autoriza M3.

## 7. Estado

**M2 autorizado; implementación no iniciada en este acto.** Este acta registra
la decisión del dueño y sus condiciones; no afirma avance, entrega ni evidencia
de implementación alguna. **M3 sigue sin autorizar** (especificación §19.6).

## 8. Firma y asiento

- **Decisión:** dueño del proyecto EKTEL, por canal, 2026-09-09. Transcripción
  íntegra en §1.
- **Vinculación:** commit `4beb7ebe9127660c3c8671d02875b2ca1470a0a4`, verificado
  contra `HEAD`, `origin/main`, árbol limpio y los tres digests SHA-256 de la
  cabecera.
- **Asiento documental:** agente, 2026-09-09. El asiento transcribe la
  decisión; no la crea ni la amplía.

**Cláusula de vigencia:** cualquier cambio posterior a los artefactos
normativos o de alcance requiere nueva revisión y, cuando corresponda, nueva
autorización humana.
