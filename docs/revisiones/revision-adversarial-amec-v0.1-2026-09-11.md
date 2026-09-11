# Revisión adversarial — Agent Memory Enforcement Contract v0.1 (AMeC)

**Fecha:** 2026-09-11. **Revisor:** OpenCode con GLM-5.3-Flash, contexto
independiente, mandato de análisis y revisión adversarial del borrador
`docs/propuestas/Agent Memory Enforcement Contract v0.1.md`. **Alcance:** sólo
documentación; sin cambios al contrato ni a implementación.

El objeto se declara `EXPERIMENTAL`, derivado de evidencia real (Prime Agent ×
AN-KLA, DSH × AN-KLA) y pendiente de revisión adversarial (su §47, paso 1). Esta
revisión ataca el contrato como texto normativo: consistencia interna,
falsabilidad de sus propiedades y huecos explotables por un modelo adversarial
que controla su propio output pero no el host.

Clasificación: P0 anula una propiedad central; P1 hueco explotable; P2
subespecificación que impide implementar o falsar consistentemente; P3
informativo.

## Veredicto

**APROBADO CON CORRECCIONES.** Sin P0: el núcleo axiomático (§2) es coherente y
las separaciones que proclama resisten el ataque directo. Cinco P1, todos
cerrables con enmiendas textuales. Los P1 de procedencia de policy,
canonicalización y bootstrap con store vacío deben resolverse **antes** de
congelar el subconjunto MEC para M2/M3 (§47, paso 4), porque condicionan qué
puede exigirse por contrato.

## Lo que resiste el ataque

- La clasificación explícita de ambigüedad (MEC-23) y su justificación
  experimental (§24) cierran el error clásico de reportar `failed` tras un
  commit real.
- La separación proposal/plan/commit con authority ceilings (MEC-14…16) elimina
  la auto-elevación silenciosa como categoría.
- `UNKNOWN → MATERIAL` (MEC-08) es el default correcto y su invalidación por
  cambio de inventario (MEC-33) evita garantías zombis.
- MEC-29 (un crash casual no es enforcement) anticipa la objeción obvia.
- El esquema de falsabilidad §44 (`precondition → attack → policy decision →
  effect/non-effect → external verification`) es aplicable tal cual.

## P1 — huecos explotables

### P1-1 Procedencia e integridad de la policy (hueco en MEC-01/02)

MEC-01 ordena la carga; MEC-02 identifica la generación. Ninguno restringe
**quién autoriza o modifica el origen de la policy** ni exige verificar su
integridad en cada arranque. Ataque: un agente con capability material de
escritura edita el archivo de policy o el flag de perfil antes de un reinicio;
el runtime carga lealmente una policy debilitada de generación propia. La
lección Prime Agent (§36) señala exactamente ahí y el contrato no cierra el
hueco de procedencia.

Enmienda mínima: `policy_source_digest` verificado contra canal fuera del
alcance del modelo en cada boot; mismatch → modo diagnóstico restringido
(alinear con MEC-32).

### P1-2 Canonicalización ausente: MEC-19/20 sin serialización definida

El binding por digest es ambiguo sin regla de serialización canónica (claves
duplicadas, unicode, flotantes, whitespace). Dos representaciones del «mismo»
proposal pueden producir digests distintos (falso `STALE`, DoS de replan) o un
digest idéntico con contenido distinto si el hash se calcula sobre proyección
parcial. El principio §2 `HASH ≠ SIGNATURE` reconoce el límite, pero el
contrato no exige la condición previa. Falta además: rechazo de campos
desconocidos y versión de schema en proposal/plan, para que una evolución
posterior no introduzca campos de autoridad en silencio (ataque a MEC-14 «no
debe contener campos que concedan authority», que sólo cubre el schema inicial).

Nota de contexto EKTEL: ADR-002 (wire format y canonicalización) y ADR-010
(base64url) ya resuelven esto localmente; el contrato portable debería exigirlo
como propiedad, no dejarlo a la implementación.

### P1-3 Paradoja de bootstrap con store vacío (MEC-04/28)

El contrato no distingue «memoria inexistente» de «memoria no disponible».
Recovery obligatorio + fail-closed bloquea el arranque legítimo de un proyecto
sin store: crear la memoria es un efecto material, y todo efecto material
exige memoria recuperada. Contrato de AN-KLA coincidente: no inicializar sin
habilitación explícita.

Enmienda mínima: estado `FIRST_RUN` con cápsula mínima, o excusa explícita
requiriendo autoridad humana registrada (MEC-18) para la creación inicial.

### P1-4 Autoridad humana sin acotación de alcance (MEC-18)

«Registrar evidencia correspondiente» no obliga a que la evidencia humana esté
ligada a (acción, scope, revisión, ventana temporal) ni a canal fuera de banda.
Ataques clásicos que el texto actual no excluye: aprobación blanket («sí a
todo») reutilizada como consentimiento universal; «human said yes» capturado
del propio canal del modelo y presentado como evidencia.

### P1-5 Downgrade de perfil sin atestación (§34, complemento de MEC-33)

La garantía se liga al inventario pero no al perfil: un runtime puede anunciar
P4 y ejecutar P1. Falta binding y registro del `profile_effective`, verificable
externamente según §44. MEC-30 ya registra `runtime version` y `policy
generation`; añadir el campo cierra el hueco casi sin coste.

## P2 — subespecificaciones

1. **MEC-03 sin grafo de transiciones legales.** ¿`DEGRADED → WORKING` tras
   recovery? ¿`CLOSED_INCOMPLETE` terminal o reabrible? Sin grafo, las
   implementaciones divergen y la conformidad se vuelve incomparable.
2. **MEC-02 sin clase de mecanismo de revocación.** Pull por invocación, lease
   con TTL o push tienen costes incompatibles; declarar la clase mínima
   aceptable y cómo demostrarla en la prueba §44.
3. **MEC-06 sin parámetros de retry.** «Retry acotado» sin techo ni backoff;
   bajo contención, R1==R2 degenera en tormenta `DEGRADED`. Corolario: el
   fail-closed de MEC-28 convierte la disponibilidad de memoria en SPOF;
   inducir escrituras concurrentes es un ataque de liveness contra trabajo
   material ajeno. Declararlo como tradeoff explícito, no dejarlo implícito.
4. **MEC-09 presupone observabilidad del efecto.** «Failed write without
   effect → no dirty» no es decidible en efectos remotos (un timeout ¿mutó el
   servidor?). MEC-23 reconcilia sólo commits de memoria. Falta protocolo de
   reconciliación por capability o regla conservadora declarada (unknown →
   dirty) con su coste de liveness aceptado.
5. **MEC-16 permite «reducir» sin reason code.** Un runtime puede elegir siempre
   la rama silenciosa. Exigir reason code obligatorio en las tres ramas.
6. **MEC-24 «cuando sea viable» sin criterio.** Escape hatch que debilita la
   reconciliación de MEC-23. Definir viabilidad (mismo host, store accesible,
   presupuesto acotado).
7. **MEC-32 «no debe crear normalmente».** El «normalmente» vuelve opcional el
   requisito. Fail-closed duro: sin policy obligatoria cargada, cero
   capabilities materiales, también en modo diagnóstico.
8. **Matriz MEC×perfil ausente.** §34 define perfiles y §35 el subconjunto
   EKTEL, pero sin mapeo perfil→MECs el criterio §44 no es aplicable. Riesgo:
   declarar conformidad P3 implementando sólo MEC-14.
9. **MEC-30 sin tamper-evidence ni binding decisión→regla.** MEC-29 exige
   demostrar que el `DENY` vino de policy, pero el log no incluye
   `policy_rule_id` ni protección de integridad (append-only, hash-chain o
   superficie fuera del alcance del modelo).

## P3 — informativo

1. Fronteras de identidad de subagentes indefinidas (pid, agent-id lógico,
   sesión): MEC-11/12 requieren saber qué es «un agente» para aislarlo.
   Aclarar además que el hijo deriva autoridad de sus propias observaciones
   mediadas; la lectura literal de MEC-12 sugiere que un hijo nunca podría
   escribir memoria.
2. MEC-13 «fronteras de policy distintas» carece de criterio mínimo falsable.
3. MEC-17 lista `timestamp` sin requisito de fuente de reloj (contexto EKTEL:
   ADR-004 ya norma vigencia, reloj y nonce).
4. Fan-out de subagentes sin tope: MEC-26 cubre liveness de cierre, no de
   spawning (DoS de recursos).
5. MEC-05 «selected records» sin criterios de selección: la flag untrusted
   cubre confianza del contenido, no sesgo de selección manipulable vía la
   propia memoria.
6. Tensión §4.3/§46: el mediador debe interpretar respuestas de memoria
   (MEC-27) sin «controlar su semántica interna». Operacionalizar con
   contratos de reason codes, no con parsing libre.
7. Contexto EKTEL para el gap analysis (§47, paso 2): ADR-005 (estados y
   precedencia) es el análogo natural de la corrección P2-1; ADR-007
   (receipts) cubre parte de MEC-17/30; ADR-008 (PolicyPort/adaptador CAGF) y
   ADR-011 (handoff admisión/start) son los puntos de anclaje para MEC-01/07.
   El P1-2 ya tiene solución local (ADR-002/010) que puede promoverse a
   requisito del contrato.

## Conclusión

El contrato es una destilación honesta de las campañas de origen y su regla
final preserva la separación que importa. No es aún congelable: resolver P1-1,
P1-2 y P1-3 antes de seleccionar el subconjunto MEC para M2/M3; P1-4 y P1-5
antes de cualquier prueba de autoridad humana o de perfil. Los P2 pueden ir al
paquete de enmiendas v0.2 sin bloquear el gap analysis.
