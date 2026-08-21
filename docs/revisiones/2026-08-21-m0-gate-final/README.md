# Evidencia del doble gate externo final de M0 (2026-08-21)

Persistencia documental del gate de cierre contractual de M0, autorizada
por el dueño tras el doble PROCEED oficial. **No es acta normativa nueva**
(no reabre nada): es el registro durable de la evidencia que sustentó el
cierre, commit `fba5a35` (cierre) sobre `afb1801` (base del paquete).

## Qué contiene este directorio

| Archivo | Contenido | Procedencia |
|---|---|---|
| `ARTIFACT.txt` | Identidad del artefacto congelado: MANIFEST-ROOT `sha256:47302f74d89abae5ba88654b6f8b626fda1f9b4ee81d967553faa45719592786` (27 archivos: 21 tracked M + 6 untracked del paquete, sobre `main@afb1801`) | dossier efímero del gate |
| `manifest-sha256.txt` | Los 27 hashes SHA-256 archivo a archivo del artefacto revisado por AMBOS revisores | ídem |
| `codex-verdict.md` | Veredicto oficial Codex: **PROCEED**, cero hallazgos (observaciones de sandbox anotadas en el propio documento) | ídem |
| `claude-verdict.md` | Veredicto oficial Claude: **PROCEED** consolidado, 5 frentes NO REFUTADOS, ~420 corridas hostiles propias, hallazgos O-1..O-6 no bloqueantes; incluye su declaración de contaminación del venv (revertida) y la declaración literal de no-recuperabilidad de la lista histórica 307/79 | ídem |

Excluidos de esta persistencia (por orden): prompts de las rondas,
stderr, logs, diffs de trabajo y cualquier otro artefacto efímero.

## Cadena de la secuencia de gates (resumen)

1. Rondas internas (fix-and-retry ×3 + micro) → paquete H1–H3.
2. Gate oficial ronda 1: Codex PROCEED · Claude FIX-AND-RETRY
   (H1–H6; informe en el dossier, no persistido aquí por orden de
   alcance).
3. M0-FAR-CLAUDE-01: corrección de H1–H5 + deuda H6 + ronda interna
   (bloqueante RecursionError → fix) → artefacto congelado
   `47302f74…`.
4. Gate oficial ronda 2 (mismo manifest): **Codex PROCEED (0 hallazgos)
   · Claude PROCEED (consolidado)** → doble PROCEED sobre hashes
   idénticos.
5. Auditoría mecánica read-only del índice → commit `fba5a35`
   (27 archivos exactos) → **cierre contractual de M0 aceptado**.

## Reglas vigentes que este registro no altera

- La lista histórica de divergencias 307/79 **no es recuperable** y no
  se reconstruyó (declaración literal de Claude en su veredicto).
- M0 cerrado contractualmente; M1+ **sin autorización**.
- Los relevos operativos (`CONTEXTO-RELEVO-2026-08-20.md`,
  `ADDENDA-CONTEXTO-RELEVO-2026-08-21.md`) permanecen fuera del repo
  versionado, sin modificar.
