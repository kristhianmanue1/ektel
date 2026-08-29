# Acta — aceptación de ADR-011: handoff de admisión hacia `start`

**Fecha:** 2026-08-28.

**Autoridad:** decisión explícita del dueño, Kristhian Manuel Jimenez Sanchez
(`krisnova@hotmail.com`), comunicada por el canal de trabajo el 2026-08-28.
El dueño respondió «adelante» a la solicitud concreta de aceptar ADR-011 sin
autorizar todavía M2. Esta acta registra esa aceptación con ese límite; no
convierte una autorización documental en permiso de implementación.

## Objeto

El dueño acepta
`docs/adr/adr-011-handoff-admision-start.md` y la incorpora a la especificación
normativa del runtime mínimo M0–M3. La decisión sustituye conceptualmente la
firma incompleta `start(AdmittedAction)` por el tipo local experimental:

```text
StartRequest {
  admitted_action: str,
  action_request_wire: bytes
}

start(StartRequest) -> StartOutcome
```

`start` deberá revalidar de forma pura el token y el `ActionRequest`, construir
un plan inmutable desde esa instantánea y exigir coherencia exacta con los
campos del token antes de cualquier efecto. No repetirá la reserva de nonce,
no reevaluará `PolicyPort` y no emitirá otro token.

La aceptación incorpora también el orden normativo de efectos definido en la
ADR: recibo previo `flush_protocol_completed` cuando la auditoría sea
obligatoria; nueva muestra de reloj y cálculo conservador del plazo; CAS de
consumo; y sólo después cruce de la frontera de proceso. El resultado ambiguo
del CAS se reconcilia conservadoramente y nunca habilita replay.

## Garantía adoptada y límites

La garantía v1 es **equivalencia ejecutable revalidada**, no identidad
byte-a-byte del `ActionRequest` exterior. El token no liga todos los bytes del
request ni `metadata_opaque`; tampoco resuelve el TOCTOU de una ruta mutable.
El `Allow` del `PolicyPort` es una decisión válida en el instante de admisión,
no una lease continua hasta el spawn.

Ektel no persistirá por esta decisión una copia adicional del comando, entorno
o stdin, ni prometerá recuperación autónoma del descriptor tras reiniciar. Si
en el futuro se exige identidad byte-a-byte o un handoff entre procesos/red,
serán necesarios un contrato wire y una versión criptográfica propios.

## Enmiendas normativas autorizadas por este acto

Este acto autoriza únicamente:

- marcar ADR-011 como aceptada y normativa;
- incorporar su decisión en
  `docs/especificacion/ektel-runtime-m0-m3-v1.md`, conservando
  `schema_version` v1 porque `StartRequest` es un tipo local experimental;
- completar la genealogía de ADR-010/ADR-011 y actualizar el estado ya
  registrado de M0/M1 como hitos cerrados, sin alterar que M2/M3 requieren
  autorización propia;
- precisar C2 y añadir el no-claim N17 en
  `docs/claims-y-no-claims.md`;
- actualizar las referencias históricas de
  `docs/propuestas/propuesta-handoff-admision-m2-2026-08-28.md` y
  `docs/propuestas/README.md`; y
- corregir en la lista normativa de `ActionRequest` la referencia editorial
  `deadline` a su nombre contractual existente `deadline_ms`.

## Límites de autoridad y stop rule

Este acto **no autoriza** M2 ni M3; código de producción; cambios en schemas o
wire contracts; cambios en el token o replay store; creación de procesos,
supervisión o AuditSink; tag o release; ni activación de CI remoto.

La construcción de M2 requiere una tarjeta separada con alcance, DoD,
evidencia, revisión adversarial y autorización explícita del dueño. Hasta que
exista ese acto, ADR-011 rige como diseño normativo pendiente de implementación
y sus afirmaciones sobre `start` no se promueven a evidencia verificada.

## Verificación del acto

El diff documental final debe superar comprobaciones locales de consistencia y
una revisión adversarial fresca con resultado `PROCEED`. Commit y push sólo
publican el acto normativo; no amplían sus límites ni disparan CI remoto.
