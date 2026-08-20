# Acta — autorización de M0

**Fecha:** 2026-08-20.
**Autoridad:** autorización explícita del dueño, conforme al criterio de
adopción de la especificación v1.2, **§19 punto 6** (que recoge la propuesta
histórica §21; la especificación vigente no tiene §21), sobre la especificación
consensuada en `consenso-especificacion-v1-2-2026-08-20.md`.

## Objeto

Se autoriza la ejecución de **M0** de la especificación
`docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2), con el alcance
cerrado que sigue.

## Alcance autorizado

1. **Wire schemas v1** — los tipos de cable con `schema_version` v1 definidos
   por la especificación, con perfil criptográfico byte-exacto (HS256,
   base64url sin padding, dominios `ektel/{capability,pop,admission,termination}/v1`;
   HKDF prohibido en v1).
2. **Vectores dorados** — juego de vectores de prueba byte-exactos para los
   wire types v1, como artefacto de conformidad.
3. **Dos parsers de referencia**, uno de ellos **clean-room** (R5): el segundo
   parser se escribe a partir de la especificación y los vectores, sin leer la
   implementación del primero.

La API de M0 se etiqueta **`experimental`** en código y documentación; no hay
compromiso de estabilidad en este hito.

## Restricciones

- **No se autoriza M1, M2 ni M3.** Cada hito posterior requiere su propia
  autorización.
- **La stop rule no se toca.** Cualquier propuesta de modificarla va por acta
  de enmienda explícita.
- El vocabulario contractual vigente es el de la v1.2
  (`flush_protocol_completed`, outcomes por operación, dos CAS,
  `ExecutionHandle` local/opaco/no serializable); las implementaciones de M0
  no reintroducen términos retirados (`durable`, C8, C9, N15).
- Los no-claims de la tabla pública siguen vigentes y no se promueven por
  acuerdo verbal; la ampliación de caracterización (Y-1, Y-2) es trabajo
  pendiente, no parte de M0 salvo que se autorice aparte.

## Evidencia de soporte

- Consenso v1.2: `consenso-especificacion-v1-2-2026-08-20.md`.
- Caracterización Linux de la suite vigente (8/8, snapshot 2026-08-20,
  **clase L** — ejecución local única, no V ni R):
  `docs/evidencia/caracterizacion-linux-2026-08-20.md`.
