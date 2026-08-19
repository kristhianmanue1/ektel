# ADR-007: Durabilidad, recibos y fail-closed del AuditSink

**Estado:** borrador para consenso. No adoptado. No autoriza implementación.

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y §21 de
la propuesta M0–M3.

**Contexto normativo:** propuesta §6.5 (AuditSink), §10 (eventos e
invariantes), §11 ("respuesta desconocida del AuditSink"), §18. **Absorbe
D7b** (retirada del lote de consenso): `policy_receipt` vive en
`AdmissionDecision v1` (§7.4), no en `ExecutionIdentity v1` (§7.3); este ADR
lo formaliza sin acto de consenso adicional, como mandata la nota del
registro D1–D7. Decisión abierta que resuelve: garantía mínima exigida al
AuditSink y formato de recibo (propuesta §20).

## 1. Decisión propuesta

1. **Contrato del AuditSink v1:**

   ```text
   AuditSink.append(RuntimeEvent) -> AppendOutcome
   AuditSink.query(event_id) -> EventStatus
   ```

   `AppendOutcome` distingue exactamente cinco casos (propuesta §6.5):
   `durable`, `accepted_undemonstrated`, `rejected`, `unavailable`,
   `unknown_after_timeout`. Un `append()` exitoso no equivale a durabilidad.

2. **`query` es parte del contrato, no opcional.** La reconciliación tras
   `unknown_after_timeout` (§11: "no reintentar sin clave idempotente;
   reconciliar por `event_id`") es imposible sin una lectura por id. Todo
   sink conforme implementa `query(event_id)` con respuestas `present` /
   `absent` / `unknown`. Esta operación faltaba en §6.5 y este ADR la añade
   al contrato.

3. **Garantía mínima del sink durable de referencia (M3):** append con
   fsync de archivo y directorio antes de emitir recibo `durable` (perfil
   `posix-fsync-dir/v1`, el mismo adoptado por AN-KLA en este repositorio).
   Sinks que no puedan demostrar durabilidad sólo pueden emitir
   `accepted_undemonstrated`.

4. **Fail-closed:** cuando el despliegue declare auditoría obligatoria, un
   evento previo al inicio que no logra recibo `durable` rechaza el inicio
   (propuesta §10.3.3 y §11). La pérdida del sink *después* de iniciar
   produce brecha explícita (`audit_gap_detected` o ausencia declarada);
   nunca se rellena retrospectivamente (§10.3.6).

5. **Recibo v1:** `{receipt_version, event_id, event_digest,
   previous_event_digest, sink_identity, received_at_wall,
   durability_class}`. La cadena por `previous_event_digest` detecta
   modificación; **no prueba** autoría, completitud, orden global ni
   almacenamiento externo (§10.3.5).

6. **Firma del operador sobre recibos: aplazada.** Coherente con ADR-003
   (HMAC simétrico, un operador): firmar un recibo con la misma clave que
   lo emite no añade garantía verificable por terceros. Los recibos v1 son
   verificables localmente (digest + cadena); la firma asimétrica llega, si
   acaso, con la v2 criptográfica (ADR-003 §6).

7. **D7b formalizada:** `policy_receipt` es campo opcional de
   `AdmissionDecision`, producido por el PolicyPort (ADR-008); nunca forma
   parte de la identidad firmada del artefacto. La separación dominio vs.
   política (propuesta §5) queda así cerrada.

## 2. Motivación

Sin `query`, la semántica de `unknown_after_timeout` era declarativa pero
inimplementable sin acoplar al sink concreto. Y sin una garantía mínima de
durabilidad, "auditoría obligatoria" sería una etiqueta sobre un buffer en
memoria.

## 3. Alternativas consideradas

### A. Sink con fsync + query + recibos de cadena (propuesta)

A favor: durabilidad demostrable en POSIX local; reconciliación real;
coherente con la disciplina de durabilidad ya adoptada por el proyecto.
En contra: fsync en el camino de admisión (ya aceptado en ADR-004) y por
evento; el costo se declara en métricas (§16).

### B. Sink en memoria con snapshot periódico

En contra: una ventana de pérdida equivale a brecha silenciosa; contradice
§10.3.3. Permitido sólo como sink de pruebas (M3 lo exige como adaptador
falso), nunca como referencia durable. Rechazada para despliegue.

### C. Anclaje externo de la cadena (transparencia, terceros)

En contra: exige firma asimétrica y servicio externo; fuera del modelo de
amenaza de M0–M3 (ADR-001). Criterio de revisión §6.

## 4. Consecuencias

- M3 entrega dos sinks: memoria (pruebas) y referencia durable (fsync),
  ambos conformes al mismo contrato con `query`.
- El resultado referencia `last_event_receipt` (§7.5) y la brecha se
  reporta en el resultado o en el siguiente evento durable, o permanece
  como ausencia (§10.3.6) — sin cambios, ya normativo.
- No-claim público heredado: "la cadena de eventos detecta alteración pero
  no prueba completitud ni autoría; los recibos v1 son verificables sólo
  localmente".

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | `query` por `event_id` permite a un sink mentiroso decir `present` sin tenerlo: el recibo no es prueba. | **Incorporada:** `query` es para reconciliación operativa, no para verificación; la verificación es `verify_receipt` contra digest y cadena. Un sink malicioso está fuera del modelo (es componente del operador). |
| A2 | fsync por evento puede colapsar throughput de eventos. | **Refutada parcialmente:** M0–M3 emiten decenas de eventos por acción, no miles por segundo; si una carga real lo contradice, el batching con recibo agregado es propuesta v2, no relajación silenciosa. |
| A3 | Un `append` que devuelve `durable` pero miente (fsync falló y el sink no lo notó) es indetectable. | **Refutada:** la honestidad del sink es responsabilidad del adaptador del operador; ektel declara la clase devuelta, no audita el disco del sink. Ya cubierto por "accepted_undemonstrated" para sinks que no pueden demostrar. |
| A4 | `received_at_wall` del sink es reloj no confiable y rompe orden global. | **Incorporada:** el recibo declara que su timestamp es wall del sink, sin orden global; el orden causal lo dan `sequence` y `causal_parent_ids` (§10.3.1–2), no el reloj. |

## 6. Criterio de revisión

Reabrir si: se adopta firma asimétrica (v2 criptográfica, ADR-003 §6); una
carga medida exige batching; o un despliegue requiere anclaje externo de la
cadena.

## 7. Decisiones que este ADR no toma

- Esquema completo de RuntimeEvent y tipos mínimos → propuesta §10.2 (ya
  normativo tras adopción; no se reabre aquí).
- Política de retención y rotación del almacén del operador → despliegue,
  fuera de M0–M3.
