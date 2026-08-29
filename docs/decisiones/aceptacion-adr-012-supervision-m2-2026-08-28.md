# Acta — aceptación de ADR-012 y enmiendas previas a M2

**Fecha:** 2026-08-28.

**Autoridad:** el dueño respondió «adelante» en el canal de trabajo a la
solicitud concreta de aceptar D-M2-1(a), D-M2-2(a), D-M2-3, D-M2-4 y
D-M2-5(a), y redactar ADR-012 con sus enmiendas normativas. La misma
instrucción autorizó commit y push durante la sesión, con CI exclusivamente
local y administración de GitHub mediante `gh`.

## Decisión

Se acepta `docs/adr/adr-012-supervision-local-m2.md` y se incorpora a la
especificación M0–M3. Quedan fijados antes de cualquier código:

1. `AwaitedExecution` como portador local de resultado y bytes capturados, sin
   cambio wire;
2. coordinador runtime y supervisor dedicado por acción, con capacidad local
   exacta;
3. defaults, rangos, fórmulas y claves de medición temporal;
4. separación entre plan configurado y garantía realmente aplicada;
5. razón y receipt locales de terminación, idempotencia y reinicio; y
6. M2 con auditoría sólo opcional y rechazo de inicialización para `required`
   hasta M3.

La autoridad permite enmendar ADR-009, la especificación, la tabla de
claims/no-claims y los índices/documentos de estado necesarios para conservar
trazabilidad. No permite alterar schemas ni vectores wire.

La especificación corrige además un erratum editorial preexistente de la
aceptación ADR-011: expresa el cálculo conservador mediante
`ceil_exact_ms(now_wall)` y `remaining_validity_ms`, como ya exige ADR-011
§2.5. No es una decisión nueva de ADR-012 ni cambia el wire.

## Condición previa

M1-R2 quedó cerrado y publicado antes de este acto. Su prueba wire demuestra
que el `GuaranteePlan` emitido satisface el contrato v1; ADR-012 no reabre el
resto de M1 ni atribuye a ese plan valores efectivos que sólo existen en
`start`.

## Límite de autoridad

Esta aceptación es documental. **M2 sigue sin autorización de
implementación.** No permite crear código de `start`, procesos reales,
supervisores, IPC, handles, terminación o auditoría; tampoco M3, workflow
remoto, tag ni release.

Una autorización M2 posterior debe enumerar alcance, incrementos, DoD,
G-M2-01..15, plataformas, evidencia y stop rule. Un veredicto `PROCEED` sobre
este acto no cubre el futuro código.

## Verificación

El diff documental final requiere controles locales de consistencia y revisión
adversarial fresca. Sólo un resultado sin P0-P2 permite commit y push. Antes de
publicar se verifica administrativamente que `ci-m1` continúe deshabilitado;
después se comprueba que el SHA no tenga corridas remotas. Esta verificación es
detección del estado de GitHub, no una garantía a priori del documento.

El registro de rondas y gates queda en
`docs/revisiones/revision-adversarial-adr-012-2026-08-28.md`.
