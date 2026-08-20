# Encargo de revisión externa — contratos M0 (vectores dorados y parsers)

**Fecha:** 2026-08-20.
**Para:** Codex CLI y Claude CLI (una ronda cada uno, hallazgos numerados
propios con retracciones declaradas — criterio F5).
**Objeto:** primera pasada de M0 (commit `33da6f8`): wire schemas v1, 31
vectores dorados, dos parsers de referencia (uno clean-room).

## Qué revisar (en orden)

1. **Fidelidad a la norma.** Cada regla implementada en
   `contracts/parsers/` debe tener respaldo en
   `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2) §5, §6, §8.3, y
   cada regla normativa de esas secciones debe estar implementada o
   declarada fuera de alcance. Buscar: reglas inventadas (sobre-implementación)
   y reglas normativas ausentes (sub-implementación).
2. **Perfil criptográfico byte-exacto (C2).** Verificar a mano al menos un
   vector: recomputar MAC e `identity_digest` de `cap-valid-01` con la clave
   de prueba de `contracts/vectors/v1/index.json` y comparar byte a byte.
   Comprobar el orden obligatorio (MAC antes de decodificar), dominios
   `ektel/{capability,pop,admission,termination}/v1`, base64url sin padding,
   ausencia de HKDF.
3. **Calidad adversarial de los vectores.** ¿Qué caso inválido falta que un
   receptor real encontraría? (p. ej. unicode en campos ASCII, números con
   decimales, `exp` < `nbf`, sobre con campos reordenados, MAC correcta pero
   `typ` cruzado entre dominios). Proponer vectores nuevos concretos.
4. **Independencia clean-room (R5).** Contrastar los dos parsers: si ambos
   comparten un mismo error de interpretación, la independencia es ilusoria.
   Señalar cualquier divergencia latente que los 31 vectores no capturen.
5. **Vocabularios cerrados.** Contrastar enums de schemas contra §8.3 y la
   tabla `docs/claims-y-no-claims.md`: ningún código/estado de más ni de
   menos; `budget_exceeded` ausente.

## Qué NO revisar

- No hay runtime que revisar (M1+ no autorizado).
- No reabrir decisiones cerradas (stop rule, vocabulario contractual,
  retiradas C8/C9/N15, divergencia P0–P3).
- La revisión cruzada final de la spec es documento interno ya declarado;
  no es objeto aquí.

## Formato de respuesta

Hallazgos numerados con severidad (bloqueante / menor / nota), evidencia
comprobable contra el repo, y retracciones explícitas si un hallazgo propio
no se sostiene. En español. Toda métrica citada como snapshot fechado.

## Estado verificado al emitir este encargo

- `main@33da6f8`, worktree limpio (snapshot 2026-08-20, clase L).
- Suite completa: `python -m unittest discover -s tests` → 10 tests OK
  (3 skips Linux-only en Darwin).
- 31 vectores en 6 grupos; ambos parsers coinciden en veredicto, diagnóstico
  y digest para todos los vectores.
- Generador determinista: doble corrida byte-idéntica.
