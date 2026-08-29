# Propuestas de arquitectura

Esta carpeta contiene propuestas no vinculantes para la evolución de ektel.
Una propuesta describe opciones, contratos y criterios de decisión; no
autoriza por sí sola implementación, publicación ni cambios al contrato del
proyecto.

## Propuestas activas

- [Runtime mínimo M0–M3 y puerto de gobernanza](propuesta-runtime-minimo-m0-m3-2026-08-17.md)
  — arquitectura de admisión, supervisión y evidencia con integración de
  gobernanza por adaptador externo.
- [Intercambio documental escrubery ⇄ ektel](propuesta-intercambio-escrubery-2026-08-22.md)
  — propuesta entre pares, no vinculante y sin autoridad: cita informativa
  unilateral de ektel hacia escrubery (analogía G0–G5 ⇄ L1–L4, sin valor
  normativo frente a la especificación v1.2) y oferta unilateral del eje F;
  pendiente de cualquier adopción posterior, incluida la recíproca de
  escrubery. Fuente: repositorio privado y versionado, citado por permalink
  como referencia versionada.
- [Paquete de preparación para la decisión sobre M1](paquete-preparacion-m1-2026-08-22.md)
  — propuesta **no vinculante** para que el dueño decida sobre M1 (admisión):
  delimitación, criterios de salida convertidos en gates, decisiones D-P1–D-P4
  (H6 `stdin_policy`, O-1, O-3, compuerta de spawn) con recomendación razonada
  y pendientes de firma, carril de caracterización separado y stop rules.
  **No autoriza M1 ni implementación alguna**; la decisión del dueño
  (D-P1..D-P4 aceptadas; M1 autorizado con condiciones expresas) quedó
  registrada en
  [../decisiones/autorizacion-m1-2026-08-22.md](../decisiones/autorizacion-m1-2026-08-22.md)
  (2026-08-22); ampliada por adenda autorizada del dueño el mismo día (el
  acta la referencia). La ronda adversarial sobre el paquete se registra en
  [../revisiones/2026-08-22-pre-m1-adversarial.md](../revisiones/2026-08-22-pre-m1-adversarial.md).
- [Paquete de corrección M1-R1](paquete-correccion-m1-r1-2026-08-28.md)
  — endurecimiento fail-closed de relojes, configuración temporal, respuesta
  del `PolicyPort` y mantenimiento del replay store. No cambia el cierre de
  M1 ni autoriza M2/M3.
- [Borrador separado: handoff admisión → M2](propuesta-handoff-admision-m2-2026-08-28.md)
  — fuera del paquete M1-R1; compara identidad byte-a-byte, descriptor canónico
  y revalidación semántica sin convertir el token actual en permiso suficiente
  ni iniciar M2. Su alternativa de reenvío con revalidación se desarrolla en
  [ADR-011 aceptada](../adr/adr-011-handoff-admision-start.md), normativa por
  [acta propia](../decisiones/aceptacion-adr-011-handoff-2026-08-28.md), pero
  todavía sin autoridad para implementar M2.
