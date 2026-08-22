# Acta de enmienda — criterio de adopción §19.6: estado de M1

**Fecha:** 2026-08-22.
**Autoridad:** autorización de M1 del dueño
(`autorizacion-m1-2026-08-22.md`, con adendas R1 y final) — la orden
autoriza «documentación de implementación, rondas y cierre M1», incluida la
actualización factual de estado.
**Regla aplicada:** toda enmienda posterior al consenso lleva acta explícita
(`consenso-especificacion-v1-2-2026-08-20.md`). **Patrón:** E1 de
`enmienda-adopcion-19-6-y-cita-tabla-2026-08-20.md`.

## Enmienda

### E1. Especificación v1.2, §19 punto 6: «cumplido para M0» → incluye M1

Tras la autorización de M1 (`autorizacion-m1-2026-08-22.md`), el punto 6
del criterio de adopción registra también la autorización e implementación
de **M1 únicamente**. El estado honesto al cierre del incremento final de
implementación (INC-5) es: **M1 implementado; cierre ABIERTO por
G15-Linux** (la suite no se ha ejecutado en la plataforma primaria Linux
aarch64 — ver `estado-post-m1-2026-08-22.md` para el bloqueo exacto). El
texto nuevo mantiene que **M2 y M3 requieren autorización separada**. No se
altera ningún otro punto del criterio.

**Naturaleza:** actualización de estado factual de un criterio cuyo
cumplimiento (de autorización, no de cierre) ya ocurrió por acto separado;
no cambia obligaciones normativas.

## Lo que esta enmienda NO hace

- No declara M1 «cerrado»: el cierre queda pendiente de G15-Linux y de la
  auditoría adversarial integral del Controlador (orden M1, método).
- No autoriza M2–M3 ni toca la stop rule.
- No promueve claims por sí misma: la promoción conservadora (con evidencia
  M1 exacta) vive en `docs/claims-y-no-claims.md` por claim, con nota de
  plataforma y clase de evidencia.

## Verificación

- Regresión completa M0+M1 en verde tras el cambio (snapshot 2026-08-22,
  clase L, Darwin arm64): 130 tests OK + 3 skips Linux-only.
- Consistencia cruzada: `autorizacion-m1-2026-08-22.md` (fuente),
  especificación §19.6 (estado) y `estado-post-m1-2026-08-22.md` (gates)
  mutuamente coherentes.
