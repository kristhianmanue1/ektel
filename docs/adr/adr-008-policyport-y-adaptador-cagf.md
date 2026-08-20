# ADR-008: Frontera del PolicyPort y adaptador CAGF

**Estado:** **aceptado** — Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com), 2026-08-19. Normativo; aún no autoriza implementación por sí solo (la autorización de M0 es un acto separado, propuesta §21.6).

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Contexto normativo:** propuesta §5 (reglas de dependencia), §6.4
(PolicyPort), §9 (política externa y futura integración CAGF), §19 (riesgo:
"CAGF se vuelve dependencia de producto"). Decisión abierta que resuelve:
si PolicyPort es omitible o requerido por perfil de despliegue (§20).

## 1. Decisión propuesta

1. **El contrato del puerto (§9.1) se adopta tal cual:**
   `PolicyPort.evaluate(PolicyEvaluationRequest) -> PolicyDecision` con
   tres decisiones tipadas (`Allow`, `Deny`, `Indeterminate`) y la regla:
   `Indeterminate` se trata como rechazo cuando la política sea obligatoria.
   **División de validación (ronda correctiva 2026-08-19, B7):** la
   *corrección* de la política es del adaptador, pero la validación del
   **sobre de respuesta** es del núcleo: forma del `PolicyDecision`,
   `decision_id` presente, vigencia (`valid_until` contra el reloj de
   pared con la tolerancia declarada de ADR-004) y recepción dentro del
   timeout de la llamada — medido con **reloj monotónico** (ADR-004: los
   plazos nunca usan reloj de pared; la vigencia sí, por ser afirmación
   civil compartida con el emisor). Un `Allow` expirado o recibido fuera de
   plazo se
   convierte en `Indeterminate` — y por tanto en rechazo cuando el puerto
   sea requerido. Aceptar un `Allow` ya expirado sería una decisión del
   núcleo, no «corrección de política externa».
2. **Omitible o requerido es propiedad del perfil de despliegue declarado,
   no una flag opaca:** el despliegue publica un *deployment profile* con
   `policy_mode ∈ {absent, optional, required}` y
   `audit_mode ∈ {optional, required}`. El perfil se incluye en
   `deployment_claims` dentro de `PolicyEvaluationRequest` y se declara en
   la documentación del despliegue. Con `policy_mode=required`, un
   PolicyPort ausente, indisponible o `Indeterminate` rechaza la admisión
   (fail-closed, §11). Con `absent`, la admisión no invoca el puerto y el
   resultado lo declara. **Con `optional`, `Indeterminate` o puerto
   indisponible es fail-open declarado** (segunda revisión externa
   2026-08-20): la admisión prosigue y emite el evento
   `policy_degraded` — si `audit_mode=required`, ese evento es obligatorio
   y su fallo rechaza el inicio (ADR-007 punto 4); la degradación nunca es
   silenciosa.
3. **Los contract tests corren contra el puerto nulo y contra uno falso**
   (M1 y M3): el núcleo se prueba completo sin CAGF, demostrando por
   construcción que CAGF no es dependencia.
4. **Las conversiones prohibidas del adaptador CAGF (§9.2) se adoptan como
   norma:** una capacidad local no es conformidad A9; un log local no es
   auditoría constitucional; un proceso terminado no es satisfacción de A0;
   una decisión individual no es verificación A2/A4; hooks no son
   gobernanza end-to-end A10. El adaptador puede traducir, nunca inflar.
5. **El núcleo no conoce CAGF:** ningún tipo, campo, código de error ni
   documento del núcleo nombra axiomas CAGF. La palabra "CAGF" aparece
   sólo en adaptadores y documentación de integración.
6. **`policy_receipt`** lo produce el puerto y viaja en
   `AdmissionOutcome.policy_receipt?` (ADR-007, D7b absorbida).

## 2. Motivación

El riesgo estructural histórico de este ecosistema es que la gobernanza de
negocio se infiltre en el runtime y lo convierta en dependencia de CAGF. El
puerto hexagonal ya estaba diseñado; lo que faltaba era resolver si la
política es omitible — y resolverlo como *perfil declarado* evita que el
comportamiento fail-closed dependa de una flag de arranque invisible.

## 3. Alternativas consideradas

### A. Perfil de despliegue declarado (propuesta)

A favor: verificable (el perfil está en `deployment_claims` y en la
documentación); testeable (tres modos, contract tests por modo); honesto
(el resultado declara qué modo operó).
En contra: un perfil mal configurado como `absent` desactiva la política.
Mitigación: el perfil es decisión del operador (dentro de su autoridad,
ADR-001) y el resultado siempre declara el modo; no hay modo oculto.

### B. PolicyPort siempre requerido

En contra: haría imposible probar o usar el núcleo sin política, y CAGF (o
un sustituto) se volvería dependencia de facto. Rechazada.

### C. PolicyPort siempre omitible (fail-open)

En contra: un despliegue con gobernanza obligatoria no tendría cómo
garantizarla; contradice §6.4. Rechazada.

## 4. Consecuencias

- M1 entrega el puerto nulo y un adaptador de prueba; M3, un adaptador de
  política falso para contract tests. Ninguno menciona CAGF.
- Un futuro adaptador CAGF es un repositorio/paquete separado con su
  propio contrato y su propia declaración de conformidad; ektel no emite
  claims CAGF (no-claim público).
- La tabla claims/no-claims incluye: "ektel con `policy_mode=required`
  garantiza que ninguna acción inicia sin decisión `Allow` del puerto
  configurado; no garantiza que esa política sea CAGF-conforme".

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | `deployment_claims` es autodeclarado por el propio despliegue: un despliegue puede mentir sobre `policy_mode`. | **Refutada:** el despliegue es el operador, que está dentro de la frontera de confianza (ADR-001); la afirmación no es para defenderse del operador sino para que el resultado sea auditable. Un campo autodeclarado no eleva autoridad (frontera de confianza del proyecto). |
| A2 | Un adaptador puede mutar la solicitud antes de evaluarla y el núcleo no lo vería. | **Incorporada:** la solicitud al puerto se construye desde la identidad ya validada y es inmutable por contrato (§6.4 ya lo exige); se añade a los contract tests: el adaptador de prueba debe intentar mutarla y el núcleo debe ignorar cualquier mutación (evalúa su propia copia). |
| A3 | Tres modos × dos modos de auditoría = matriz de despliegue que multiplica tests. | **Refutada:** 3×2=6 combinaciones, todas enumerables en la matriz M2/M3; es el costo correcto de que el fail-closed sea verificable. |

## 6. Criterio de revisión

Reabrir si: CAGF ratifica un contrato que requiera campos nuevos en
`PolicyEvaluationRequest` (→ versión de contrato, no edición); o si un
despliegue real demuestra que el perfil declarado es insuficiente.

## 7. Decisiones que este ADR no toma

- El contrato CAGF ratificado ni la semántica de axiomas → CAGF.
- Recibo y durabilidad del `policy_receipt` → ADR-007.
