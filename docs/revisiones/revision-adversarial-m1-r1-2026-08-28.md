# Revisión interna previa — corrección M1-R1

**Fecha:** 2026-08-28. **Objeto:** diff local sobre
`ddf8fa01f7752d12d60add144532c8043fa099f8`. **Clase:** revisión interna del
artefacto en construcción; no sustituye la revisión adversarial fresca del
artefacto final. **Autoridad:** correcciones M1; sin autoridad para M2/M3,
commit, push o release.

## Preguntas adversariales y resultado

| Ataque | Evidencia | Resultado |
|---|---|---|
| `NaN`, infinidades, booleanos o entero desbordante como configuración/reloj | unitarias y adversariales; entero `10**1000` incluido | Bloqueado antes de admitir o mutar estado |
| `nbf`/`exp` autenticados enormes | pruebas de dominio y pipeline con `10**1000` | sin `OverflowError`; TTL no representable rechaza antes del store |
| Segundo reloj de pared inválido tras un `Allow` | prueba adversarial con `NaN` | `policy_unavailable`, nunca `Admitted` en required |
| Reloj monotónico regresivo | prueba 10 → 9 | respuesta descartada como puerto no disponible |
| `Allow` con id/timestamp inválidos | pruebas con id vacío/no-string, `NaN` y entero extremo | respuesta no adquiere autoridad |
| Tipo de decisión desconocido | adaptador devuelve un diccionario | resultado tipado, sin `AssertionError` |
| Excepción ordinaria del adaptador | adaptador lanza detalle sensible | required rechaza; optional degrada; no filtra detalle |
| Mantenimiento con tiempo inválido | `collect_expired()` contra nonce vivo | excepción safe antes de mutación; nonce permanece reservado |
| TTL/configuración inválidos del store | pruebas de integración | fail-closed |
| Store devuelve `None` o lanza excepción | prueba unitaria de frontera | sólo `RESERVED` continúa; lo demás rechaza tipado |
| Corrección introduce proceso real/M2 | búsqueda de primitivas en `src/` y revisión del diff | no hay implementación productiva de `start`, fork, spawn o subprocess |
| La propuesta pre-M2 confunde digest de capacidad con bytes del request | dos requests distintos producen el mismo digest/token | afirmación retirada; borrador M2 separado y pendiente |

## Objeciones que sobreviven

1. El timeout del puerto es post-hoc: una llamada que nunca regresa todavía
   puede bloquear admisión. Resolverlo requiere decidir aislamiento,
   cancelación, recursos y semántica de proceso/hilo del adaptador.
2. La especificación exige calcular `deadline_eff` en admisión, pero el token
   M1 no transporta descriptor ni deadline solicitado. El handoff a `start`
   requiere una decisión previa; se documentó una opción, no se corrigió por
   inferencia.
3. Linux aarch64 se reprodujo sobre staging identificado, con 150/150 y los
   fuzzes/vectores verdes; mypy dentro de Linux y CI remoto siguen pendientes.
   El único run del SHA base quedó bloqueado antes de pasos por
   facturación/cupo, por lo que no prueba ni regresión ni éxito.
4. El nonce sigue quemado después de un fallo del puerto. Es deliberadamente
   conservador y coherente con ADR-004, aunque reduce disponibilidad.

## Estado de esta revisión

**READY_FOR_EXTERNAL_REVIEW.** El diff final pasó 150 pruebas en Darwin
(3 skips Linux-only) y Linux aarch64 (0 skips), mypy 1.19.1 en Darwin, ambos
fuzzes y regeneración de 91 vectores con diff cero. El veredicto `PROCEED`
permanece pendiente de una revisión adversarial fresca con procedencia
identificada; esta revisión interna no la sustituye.

Este estado no reabre ni recierra M1, no autoriza M2/M3, no promueve claims de
plataforma y no autoriza commit, push, tag o release.
