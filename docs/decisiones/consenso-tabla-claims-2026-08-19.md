# Registro de consenso — Tabla pública de claims/no-claims

**Fecha del acto:** 2026-08-19.

**Regla de autoridad:** la misma de los registros D1–D7 y ADR-001–009 —
cada decisión queda adoptada cuando la persona responsable la marca
explícitamente con dueño y fecha.

**Dueño:** Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com).

## Decisión

| # | Decisión | Resolución | Dueño | Fecha | Estado |
|---|---|---|---|---|---|
| Tabla §21.4 | `docs/claims-y-no-claims.md` — lenguaje público permitido sobre ektel M0–M3 (claims C1–C8 y C10; no-claims N1–N14 y N16) | Aceptar | Kristhian Manuel Jimenez Sanchez | 2026-08-19 | **aceptada** |

## Notas del acto

- La tabla se presentó en dos rondas: el borrador inicial fue revisado por
  un agente externo (Claude, 2026-08-19), cuyo veredicto exigió dos
  correcciones bloqueantes y una de lenguaje:
  - **B1:** C2 alineado con ADR-002 — HMAC-SHA256 sobre el texto base64 del
    payload (estilo JWS), no "sobre bytes transportados".
  - **B2:** C7 y ADR-007 corregidos por plataforma — en Darwin `fsync()` no
    vacía la caché del disco y el recibo `durable` exige
    `fcntl(F_FULLFSYNC)`; la supervivencia a corte de energía queda como
    supuesto declarado no testeable (N5). Caracterización de API en
    `tests/escape/test_host_characterization.py`.
  - **M1:** "identidad firmada" → "identidad autenticada (MAC)" en prosa
    pública; el campo `alg: HS256` se mantiene.
  - Faltantes estructurales incorporados: N1 y N14 nombran los claims que
    anulan si su supuesto cae; **N16** nuevo (presencia del `Allow`, no
    corrección de la política externa); nota de estado de evidencia
    (todos los claims son **P** hasta que su suite los falsifique).
- Veredicto preservado en
  `docs/revisiones/revision-externa-claude-tabla-claims-2026-08-19.txt`.
- La aprobación del dueño se dio en el canal del proyecto ("adelante") tras
  re-presentar la tabla corregida con el resumen de cambios. Ante duda, el
  dueño puede refutarla con un acto igual de explícito.
- El identificador C9 queda retirado (no reutilizado) y N15 reservado sin
  uso: la numeración no se compacta.

## Efecto

La tabla es el lenguaje público permitido sobre ektel M0–M3 y se versiona
con los contratos (regla de uso al pie de la tabla). Queda satisfecho el
requisito §21.4 del criterio de adopción. **Esto no autoriza M0**: la
autorización de M0 (propuesta §21.6) requiere además la especificación v1
fusionada (propuesta + ADR-001–009 con enmiendas R1, R3 y R5), que es el
siguiente acto documental.
