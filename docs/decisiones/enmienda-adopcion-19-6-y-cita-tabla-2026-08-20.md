# Acta de enmienda — criterio de adopción §19.6 y cita de la tabla pública

**Fecha:** 2026-08-20.
**Autoridad:** autorización explícita del dueño (2026-08-20, "queda autorizado
el push y cumplimiento").
**Regla aplicada:** la asentada en
`consenso-especificacion-v1-2-2026-08-20.md` — toda enmienda posterior al
consenso lleva acta explícita.

## Enmiendas

### E1. Especificación v1.2, §19 punto 6: «pendiente» → «cumplido para M0»

Tras la autorización de M0 (`autorizacion-m0-2026-08-20.md`), el punto 6 del
criterio de adopción deja de estar pendiente **para M0 únicamente**. El texto
nuevo registra la autorización con su acta y mantiene que M1–M3 requieren
autorización separada. No se altera ningún otro punto del criterio.

**Naturaleza:** actualización de estado factual de un criterio cuyo
cumplimiento ya ocurrió por acto separado; no cambia obligaciones normativas.

### E2. Tabla pública, cabecera: precisión de la cita «§21.4»

`docs/claims-y-no-claims.md` citaba «§21.4 del criterio de adopción» sin
indicar el documento. Se precisa que remite a la **propuesta histórica** §21.4,
recogida en la especificación v1.2 §19 punto 4. Cambio editorial de
procedencia; no se toca ningún claim ni no-claim.

## Lo que esta enmienda NO hace

- No promueve ningún no-claim ni amplía la caracterización (durabilidad bajo
  fallo, RSS por muestreo siguen pendientes).
- No autoriza M1–M3 ni toca la stop rule.
- No reabre el consenso de la v1.2: opera sobre estado factual posterior a él.

## Verificación

- Suite `tests/escape` en verde tras el cambio (snapshot 2026-08-20, clase L):
  8 tests, 5 OK + 3 skips Linux-only en Darwin.
- Consistencia cruzada: los actas `autorizacion-m0-2026-08-20.md` (fuente del
  cumplimiento) y la especificación §19 quedan mutuamente coherentes.
