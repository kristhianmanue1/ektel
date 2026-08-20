# Acta de divergencia — ektel adopta M0–M3, no P0–P3 literal

**Fecha del acta:** 2026-08-19.
**Origen:** hallazgo estratégico de la revisión externa de Codex
(`docs/revisiones/revision-externa-codex-espec-2026-08-19.txt`, sección
«Divergencia estratégica respecto del encargo inicial»).

**Dueño:** Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com).

## Declaración

**Ektel no implementará P0–P3 literalmente.** Adopta el ciclo M0–M3 con la
frontera de la especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md`
y las divergencias explicitadas abajo. La nomenclatura P0–P8 se reserva a
CAGF (propuesta §1; `MANIFIESTO-DEL-ORIGEN.md` y disposición N22 del
repositorio CAGF).

## Divergencias frente al encargo original

| Encargo original (P0–P3) | Decisión adoptada en ektel | Dónde quedó normativo |
|---|---|---|
| Routing / despacho de acciones | **Excluido.** El routing pertenece a un gateway o despachador externo; ektel recibe un descriptor autocontenido. | No-objetivos (§3 de la especificación), N10 |
| `before_action` / `after_action` como interfaz principal | **Descartados como semántica principal** (parecen callbacks, no contratos de estado); un adaptador los traduce a `PolicyPort.evaluate` + flujo de eventos. | §8 de la especificación |
| Auditoría obligatoria para todas las acciones (P3) | **Por perfil de despliegue:** `audit_mode ∈ {optional, required}` declarado; con `required` es fail-closed. | ADR-008, §9 y §11 de la especificación |
| Gobernanza CAGF integrada | **CAGF fuera del núcleo:** adaptador externo del PolicyPort; conversiones por nombre prohibidas; el núcleo no nombra axiomas CAGF. | ADR-008 |

## Motivo

El encargo original describía una capa con responsabilidades de gateway,
gobernanza y evidencia. La consolidación y las rondas adversariales
mostraron que fundirlas en un solo runtime producía claims inflados e
incomprobables. La frontera M0–M3 es deliberadamente menor para que cada
claim sea falsable por una suite.

## Efecto

Esta divergencia es una decisión adoptada, no un descuido documental.
Cualquier re-convergencia hacia P0–P3 (routing, hooks como interfaz
principal, auditoría universal obligatoria, CAGF embebido) requiere
propuesta y acto de consenso nuevos — está cubierta por la stop rule de M3.

## Aprobación

| Resolución | Dueño | Fecha |
|---|---|---|
| Adoptar la divergencia declarada | Kristhian Manuel Jimenez Sanchez | 2026-08-19 |
