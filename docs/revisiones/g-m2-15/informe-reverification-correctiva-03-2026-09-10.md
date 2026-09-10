# Re-verificación externa correctiva 3 — R15/R16

**Fecha:** 2026-09-10.
**Revisor:** agente independiente `/root/r15_r16_reverification`, mismo harness
Codex, modelo heredado sin override; conversación del implementador no transferida
(`fork_turns=none`). No se presenta como diversidad de familias de modelos.
**Procedencia:** respuesta final del revisor, preservada a continuación por el
agente ejecutor. El revisor no escribió archivos ni vio el paquete de resultados
del implementador para concluir. Encargo: inspección read-only del commit exacto,
contraste normativo y pruebas/sondas efímeras; no autoridad para cerrar gates.

## Informe del revisor

Veredicto: **PROCEED para la re-verificación correctiva R15/R16**, limitado al threat model ratificado. No identifico un finding bloqueante reproducido. Este veredicto no cierra G-M2-15 ni M2, ni habilita M3.

Identidad verificada independientemente:

- CORRECTIVE-REVIEW-ROOT: `f944493bc9872414daf3d46d7ae230adcbfcf42e`.
- Baseline: `dc3de184de495abe022c656fb8b947a1b976ed8f`.
- MANIFEST-ROOT: `b59553bcb6d4ab696357354ba63ffbae398609ea48426610b447d43bec660588`; todas sus entradas verificadas.
- AN-KLA: integración sin diagnósticos; integridad correcta, revisión 51.
- Árbol inicialmente limpio. Al terminar sólo aparece el paquete documental no rastreado anunciado por el ejecutor; no lo usé para concluir. No escribí código, pruebas, documentos ni memoria.

| Obligación | Resultado |
|---|---|
| R15 | SATISFIED dentro del modelo ratificado |
| R16 | SATISFIED dentro del modelo ratificado |
| R12/CAS, regresión focalizada | Sin regresión observada |
| R13 fuerte | Continúa NOT-SATISFIED / BLOCKED-BY-NORMATIVE-GAP |

R15: el writer se crea en `src/application/start_service.py:142` y llega al watcher interno; las tablas conservan el lector. Las superficies consumidoras no reciben depósito/cierre terminal ni un parámetro que permita suministrar un terminal autorizado. `_record_for` verifica pertenencia por identidad antes de autenticar, de modo que un handle incompleto externo no alcanza acceso a campos ausentes. Copias, tipos hostiles e instancias ajenas se rechazan. Timeout, receipt y abandono no sustituyen el terminal del Host.

Sonda propia efímera: 30 ciclos con handle copiado/incompleto, timeout inicial, `linearized_receipt()`, `release()`, dos consumidores concurrentes y entrega posterior del Host. Resultado: exactamente una entrega de `b"host-real"`, posteriores consumos vacíos, cero slots, custodia pendiente y registros operacionales; evidencia de emisión retirada. No usé introspección arbitraria como supuesto ataque contra R15.

R16: `AdmissionService.admit()` publica evidencia sólo después de completar la admisión; mantiene token completo → expiración/fingerprint en un registro serializado y acotado. Start exige pertenencia al Admission ligado y coteja emisión/Start/Host antes del CAS. El string legado del caller no participa en esa autoridad. Las pruebas A/B/B con caller declarando B, emisor ajeno del mismo perfil, ausencia de emisor, reinicio, saturación, expiración y concurrencia pasan. `unspent`/`unknown` conservan evidencia; `spent` la retira. Los parámetros de spawn del Host salen del snapshot de configuración, no de sus campos espejo.

Sonda propia adicional del lock: durante `consume_start_token`, una segunda admisión quedó deliberadamente bloqueada en PolicyPort sosteniendo el lock de Admission. El primer spawn ocurrió antes de liberar ese lock; posteriormente se completó la retirada de la primera emisión y se conservó la segunda. Confirma que no se interpone el lock entre CAS y spawn.

Observación operativa no bloqueante: ese mismo experimento confirma que la respuesta `Started` puede demorarse después del spawn mientras `_forget_issuance()` espera al lock ocupado por otra admisión. No contradice el orden ratificado ni demuestra pérdida del handle; sí limita cualquier futura afirmación de latencia de retorno acotada. Rutas: `src/application/admit.py:231` y `StartService._start_with_slot()`.

Verificación ejecutada:

```text
.venv/bin/python -B -m unittest
  tests.unit.test_m2_authority
  tests.unit.test_m2_config
  tests.unit.test_termination_semantics
  tests.integration.test_capacity_slots
  tests.integration.test_start_linearization
  tests.integration.test_start_concurrency

122 tests — OK — 15.519 s
```

Las fixtures actualizadas emiten mediante Admission real y comparan el token resultante; no vi registro prefabricado que omitiera la nueva condición. Las pruebas negativas de provenance llaman `start` directamente. Revalidación pura, ReplayStore, contratos, SpawnFrontier y fixture M1 no tienen cambios frente al baseline.

Limitaciones: no repetí suite completa ni caracterización Linux; el snapshot del Host se revisó estáticamente y mediante pruebas focalizadas existentes. Una primera ejecución con el `python3` del sistema —Python 3.9— falló por incompatibilidad de sintaxis evaluada existente; se repitió correctamente con Python 3.12 del proyecto. No atribuyo esos errores iniciales a R15/R16. No afirmo aislamiento ante código arbitrario del mismo intérprete.
