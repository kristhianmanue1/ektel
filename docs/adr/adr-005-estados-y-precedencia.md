# ADR-005: Estados, precedencia y ausencia de resultado

**Estado:** **aceptado** — Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com), 2026-08-19. Normativo; aún no autoriza implementación por sí solo (la autorización de M0 es un acto separado, propuesta §21.6).

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Contexto normativo:** propuesta §7.5 (ExecutionResult), §11 (semántica de
fallos), §13 (criterio M2: precedencia determinista). Decisión vigente: **D5**
(estados de §7.5 sin `budget_exceeded` por defecto; precedencia plazo →
presupuesto).

## 1. Decisión propuesta

1. **D5 se formaliza sin cambios de sustancia.** El vocabulario cerrado de
   estados de `ExecutionResult v1` es exactamente:
   - antes de iniciar: `admission_rejected`, `capability_rejected`,
     `start_failed`;
   - después de iniciar: `executed`, `deadline_exceeded`, `terminated`,
     `supervision_failed`.
2. **`budget_exceeded` no existe en v1.** Sólo podrá añadirse en una versión
   posterior para una magnitud cuyo mecanismo esté clasificado y probado en
   la plataforma objetivo (propuesta §7.5); nunca como comodín de una
   observación incompleta.
3. **Precedencia fija:** deadline observado precede a presupuesto y a toda
   otra compuerta; una orden externa aceptada produce `terminated` sólo si
   precede al deadline observado. La precedencia es determinista y testeable
   (criterio M2).
4. **Ausencia honesta de resultado:** si el supervisor muere, no hay
   resultado y no se inventa estado (propuesta §11). Un observador externo
   sólo puede afirmar ausencia de evidencia, nunca un estado presumido.
5. **`executed` no significa éxito.** Significa que el proceso observado
   terminó sin que una compuerta de ektel produjera otro estado. El éxito
   de negocio pertenece al llamador; ektel nunca lo declara.
6. **Códigos cerrados y versionados:** estados y `cause_code` no se
   reutilizan ni se redefinen; ampliarlos crea versión de schema (propuesta
   §15.4).
7. **Cada resultado declara sus garantías aplicadas:** `guarantees_applied`
   refleja lo que realmente operó (con su clase), no lo solicitado; la
   discrepancia entre solicitado y aplicado es visible en el resultado
   (propuesta §7.5, §8 regla 1).

## 2. Motivación

La confusión entre terminación técnica y éxito de negocio, y entre
observación y garantía, son las dos fuentes históricas de claims inflados
en runtimes. El vocabulario cerrado + precedencia explícita + ausencia
honesta son la defensa contractual contra ambas.

## 3. Alternativas consideradas

### A. Vocabulario cerrado §7.5 + precedencia fija (propuesta)

A favor: deterministico, testeable, enumerable en vectores dorados;
cubre todos los fallos de la tabla §11 sin huecos ni solapes.
En contra: rigidez — un fallo no clasificado no tiene dónde caer.
Mitigación: `supervision_failed` es el sumidero honesto *post-inicio* y los
fallos de admisión tienen `reason_code` cerrado propio; no se improvisan
estados en runtime.

### B. Estados extensibles por despliegue

En contra: dos despliegues producirían resultados incomparables y la
compatibilidad de vectores (M0) sería inverificable. Rechazada.

### C. Modelar `budget_exceeded` ya, deshabilitado

En contra: un estado reservado invita a activarlo sin evidencia; D5 lo
descartó explícitamente. Rechazada.

## 4. Consecuencias

- Todo consumidor puede pattern-matchear el vocabulario completo; no hay
  `else` semántico.
- La muerte del supervisor es observable sólo como ausencia; los
  despliegues que necesiten detectarla requieren watchdog externo, fuera de
  M0–M3 (§12.2 de la propuesta).
- `deadline_exceeded` describe la transición registrada por un supervisor
  vivo: no promete scheduler de tiempo real ni muerte universal de
  descendientes (propuesta §8 regla 4); la contabilidad de descendientes
  escapados es `unsupported` en Darwin (ADR-006, evidencia E2).

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | Con vocabulario cerrado, una carrera deadline/terminate simultánea es ambigua. | **Incorporada:** la precedencia se decide sobre el registro del supervisor (qué observó primero el reloj monotónico), y M2 exige test de carrera determinista; en empate de observación, gana `deadline_exceeded` por regla fija documentada. |
| A2 | `supervision_failed` como sumidero puede tragarse fallos que merecían estado propio. | **Refutada parcialmente:** es el precio de un vocabulario cerrado; la mitigación es que `cause_code` (también cerrado pero más fino) distingue las causas sin abrir el enum de estados. |
| A3 | "Ausencia de resultado" es indistinguible de "resultado perdido" para el llamador. | **Incorporada:** el llamador recibe del `ExecutionHandle` únicamente lo que el supervisor emitió; si el supervisor muere, la ausencia se declara como tal en la API (`await_result` no fabrica timeout sintético) y el último recibo conocido (`last_event_receipt`) es la frontera de lo afirmable. |

## 6. Criterio de revisión

Reabrir si una magnitud de presupuesto obtiene mecanismo clasificado y
probado (E-gates) — habilitaría `budget_exceeded` en v2 — o si una carrera
real de la suite M2 no puede hacerse determinista.

## 7. Decisiones que este ADR no toma

- Reloj que gobierna el deadline → ADR-004 (monotónico).
- Qué eventos acompañan cada transición → ADR-007 y propuesta §10.
