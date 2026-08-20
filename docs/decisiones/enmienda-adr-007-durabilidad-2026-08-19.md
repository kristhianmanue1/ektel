# Acta retroactiva de enmienda — ADR-007 (durabilidad por plataforma)

**Fecha del acta:** 2026-08-19.
**Regla de autoridad:** la misma de los registros anteriores — cada
enmienda queda adoptada cuando el dueño la marca explícitamente con fecha.

**Dueño:** Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com).

## Defecto reconocido

ADR-007 fue aceptado por el dueño dentro del acto ADR-001–009
(`consenso-adr-001-009-2026-08-19.md`, commit `fecf1b3`) y **modificado
después** (commit `d8cb9f6`) para aplicar el bloqueante B2 del veredicto
externo sobre la tabla de claims — sin acta de enmienda propia. La
modificación fue técnicamente correcta y verificada, pero el procedimiento
incumplió la disciplina de cadena de custodia que el proyecto exige. Este
acta lo regulariza retroactivamente y fija la regla.

## Enmienda regularizada

| # | Enmienda | Origen | Estado |
|---|---|---|---|
| E1 | ADR-007 punto 3: el recibo `durable` exige fsync de archivo y directorio; en Darwin `fsync()` no vacía la caché del disco y se requiere `fcntl(F_FULLFSYNC)`; la supervivencia a corte de energía es supuesto declarado no testeable (N5). El perfil `posix-fsync-dir/v1` de AN-KLA comparte la limitación en macOS (declarada, sin modificar AN-KLA). | Veredicto externo sobre tabla (Claude, 2026-08-19), B2 | **aplicada en `d8cb9f6`, regularizada por este acta** |
| E2 | ADR-007 ronda adversarial: ataque A5 añadido como «Incorporada». | mismo veredicto | **aplicada en `d8cb9f6`, regularizada por este acta** |

Evidencia: caracterización de API en
`tests/escape/test_host_characterization.py` (test renombrado después a
`test_flush_primitive_available` por la ronda B1–B8, acta transversal).

## Regla que nace de este defecto

**Toda modificación de un ADR o de la tabla pública posterior a su
consenso requiere acta de enmienda explícita con dueño y fecha, emitida en
el mismo commit o antes. Ninguna enmienda se aplica por edición silenciosa,
independientemente de su tamaño o corrección técnica.**

## Aprobación

| Resolución | Dueño | Fecha |
|---|---|---|
| Regularizar E1 y E2 y adoptar la regla de acta de enmienda | Kristhian Manuel Jimenez Sanchez | 2026-08-19 |
