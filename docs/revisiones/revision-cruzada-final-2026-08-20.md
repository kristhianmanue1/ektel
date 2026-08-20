# Revisión cruzada final — ADR / tabla / especificación v1.2

**Fecha:** 2026-08-20. **Ejecutor:** agente mantenedor (Kimi Work), con el
repo como única fuente.
**Alcance:** consistencia interna post-enmiendas (B1–B8, C1–C6, D1–D5)
entre los ADR-001–009, la tabla pública y la especificación v1.2. No es una
revisión externa: es el último paso interno de la ruta de cierre antes del
consenso del dueño.

## Verificaciones ejecutadas

| Verificación | Método | Resultado |
|---|---|---|
| Valor `durable` eliminado del vocabulario de contrato | grep de `` `durable` `` en docs/ | **OK tras corrección**: los únicos remanentes son históricos (A3/A5 de ADR-007, anotados con el renombre; actas que citan el nombre anterior) |
| `flush_protocol_completed` presente en los 4 documentos normativos | grep | OK (ADR-007, tabla C7/N5, spec §11, acta v3) |
| Tipos de resultado por operación consistentes | grep de `AdmissionOutcome`/`StartOutcome`/`TerminationOutcome` en spec y ADR-005; renombre aplicado también en ADR-007/008 | OK |
| Dominios criptográficos cerrados | grep de `ektel/*/v1` | OK: exactamente `capability`, `pop`, `admission`, `termination`; ningún otro |
| `policy_degraded` declarado donde se usa | grep | OK (ADR-008, spec §9 y §10, acta v3) |
| `start_failed_indeterminate` con una sola semántica | grep | OK (ADR-003/004/005, spec §7.4/§8.3) |
| Referencias cruzadas internas de la spec | grep de `§x.y` | **2 defectos corregidos**: `§10.4` (subsección inexistente → §10) y `§7.4–7.5` (→ §7 puntos 4–5) |
| Numeración sin compactar | lectura de la tabla | OK: C8 y C9 retirados con nota; N15 con lápida; nota aclaratoria de referencias § añadida a la cabecera |
| Suite de caracterización | `python -m unittest discover -s tests/escape` | OK: 8 tests, 3 skips Linux-only |
| Estado git | `git status` | main empujado, worktree limpio |

## Hallazgos residuales (declarados, no bloqueantes)

1. Las filas de la tabla citan secciones `§` de la propuesta histórica; se
   declaró en la cabecera cómo resolverlas. Migrarlas a secciones de la
   especificación es limpieza editorial, no normativa.
2. Las filas A3/A5 de la ronda adversarial de ADR-007 citan el nombre
   antiguo del valor de recibo por fidelidad histórica, con anotación del
   renombre.
3. La autoridad de la especificación v1.2 **sigue pendiente de consenso**:
   este documento no la adopta; verifica que es internamente consistente y
   lista para ese acto.

## Dictamen

La especificación v1.2, los ADR-001–009 enmendados y la tabla pública son
**internamente consistentes** a la fecha. Se recomienda al dueño el acto de
consenso de la v1.2; tras él, el único requisito restante del criterio de
adopción (§21.6) es la autorización separada de M0.
