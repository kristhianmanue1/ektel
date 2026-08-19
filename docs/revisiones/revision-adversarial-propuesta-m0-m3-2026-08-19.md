# Ronda adversarial sobre la propuesta M0–M3 (completa)

**Fecha:** 2026-08-19.

**Objeto:** `docs/propuestas/propuesta-runtime-minimo-m0-m3-2026-08-17.md`
(sha256:eb915f37a32e5b11cd12bd349f27a56181abac5ff5b28da6b1f36a6b514e6329).

**Requisito que satisface:** §21.2 del criterio de adopción ("una ronda
adversarial intente romper fronteras, contratos e invariantes") y §21.3
("las objeciones se incorporen o refuten explícitamente"). Las rondas
anteriores (2026-08-14) cubrieron la consolidación, no este documento.

**Método:** revisión estática del documento contra sus propios invariantes,
contrastada con la evidencia E1–E3 y con los ADR-001 a ADR-008 redactados
el mismo día. No se ejecutó código.

**Declaración de contexto:** la ronda la ejecuta el agente mantenedor, no un
revisor independiente; no acredita independencia (frontera de confianza del
proyecto: "una ronda adversarial sin contexto declarado no acredita
independencia"). Una ronda externa sigue siendo recomendable antes de
autorizar M0.

## Resultados

Leyenda: **incorporada** (ya resuelta por un ADR de 2026-08-19, se cita) ·
**refutada** (el diseño ya la cubre; se explica) · **abierta** (requiere
enmienda a la propuesta; texto propuesto incluido).

### R1 · `terminate()` no declara control de autorización — **abierta**

§7.1 expone `terminate(ActionId, TerminationReason)` sin decir quién puede
invocarlo. Tal cual está escrito, cualquier llamador que conozca un
`action_id` podría terminar la acción de otro flujo del mismo despliegue.

Enmienda propuesta a §7.1: "`terminate` exige la misma capacidad raíz
vigente y el `action_id` ligado a ella; una terminación no autorizada se
rechaza como `capability_rejected` y se registra como evento". Asignación:
anotar en la propuesta al formalizarla como especificación; no requiere ADR
nuevo (es aplicación directa de D2).

### R2 · Valores de entorno en la identidad firmada — **incorporada**

`env_allowlist_values` viaja en claro dentro del descriptor firmado: un
secreto en el entorno quedaría en el descriptor, en logs y en la identidad.
Resuelto en ADR-003 §4: el descriptor no debe contener secretos y los
eventos registran el entorno sólo por digest o forma redactada (§10.3.4).

### R3 · `output_limits` sin mecanismo declarado — **abierta**

§7.2 declara `output_limits` y §6.3 "captura acotada de salida", pero ninguna
sección dice cómo se acota (bucle de lectura con truncamiento, límite de
archivo, `RLIMIT_FSIZE`). La revisión de `sandbox.py` de Argos
(`docs/revisiones/revision-argos-sandbox-2026-08-19.md`, F7) muestra el
costo real de este hueco: captura ilimitada = bomba de memoria del
supervisor, y en Darwin ni `RLIMIT_AS` está disponible como red.

Enmienda propuesta a §6.3: "la captura se implementa con bucle de lectura
acotado y truncamiento declarado (`stdout_truncation`/`stderr_truncation`);
no se usa `RLIMIT_FSIZE` como mecanismo primario por no estar caracterizado
(E-gates)". Asignación: M2.

### R4 · La cadena hash no impide rollback del sink — **refutada**

Un sink que reescribe su historia re-encadena los digests y la cadena
verifica. Correcto y ya declarado: §10.3.5 dice que la cadena detecta
modificación pero no prueba completitud ni almacenamiento externo; ADR-007
§5 lo repite como no-claim. El sink es componente del operador, dentro de la
frontera de confianza. El anclaje externo es criterio de revisión de ADR-007.

### R5 · "Dos parsers de referencia" pueden ser ambos del mismo autor — **abierta**

El criterio M0 ("vectores consumibles por al menos dos implementaciones
independientes o dos parsers de referencia") no define "independiente"; con
ADR-006 (Python) ambos parsers serían Python y podrían compartir hasta el
autor, haciendo la independencia nominal.

Enmienda propuesta a §13 (M0): "al menos uno de los dos parsers de
referencia se escribe desde el schema y los vectores, sin leer el código del
otro (clean-room); la independencia de lenguaje queda como ideal, no como
requisito de M0, dado ADR-006". Asignación: al cerrar M0.

### R6 · Replay de `admitted_action` tras reinicio — **incorporada**

Un `admitted_action` válido no consumido podría reutilizarse tras reiniciar
el runtime si el consumo sólo viviera en memoria. Resuelto en ADR-003 §6 +
ADR-004 §1.4: el consumo se registra durable junto al nonce, antes de
emitir la admisión, y sobrevive reinicios.

### R7 · Skew de reloj entre emisor y verificador — **incorporada**

`nbf`/`exp` contra reloj de pared del host admiten manipulación NTP y skew.
Resuelto en ADR-004 §1.1/§1.3: wall clock con tolerancia declarada para
vigencia, monotónico para plazos, supuesto de reloj disciplinado declarado
como no-claim.

### R8 · Acciones concurrentes intercalan eventos en el sink — **refutada**

`sequence` es monotónica por acción, no global (§10.3.1), y la causalidad
usa `causal_parent_ids` (§10.3.2), no el orden de llegada. La intercalación
no rompe ningún invariante declarado. Nada que corregir.

### R9 · `opaque_policy_context_ref` como canal lateral — **refutada**

El PolicyPort podría recibir contexto opaco que el núcleo no inspecciona,
canalizando entradas de decisión no declaradas. Es intencional: el núcleo
no interpreta política (§6.4) y el contenido opaco nunca alimenta decisiones
del núcleo (§7.2, `metadata_opaque`). La rendición de cuentas de esa entrada
pertenece al contrato del adaptador, no a ektel. Documentado como frontera,
no como hueco.

### R10 · Latencia de admisión puede consumir el deadline — **refutada**

El plazo efectivo se computa en admisión contra `exp` (ADR-004) y el
deadline de ejecución lo gobierna el reloj monotónico del supervisor desde
el inicio del proceso, no desde la recepción del descriptor. No hay doble
descuento oculto.

### R11 · Garantías multi-nivel de CPU en Darwin — **incorporada**

La tabla de garantías por plataforma podría presentar paridad Linux/Darwin
que la evidencia E2 contradice. Resuelto en ADR-006 §1.3/§4: Darwin declara
`unsupported` la contabilidad CPU multi-nivel (sin `PR_SET_CHILD_SUBREAPER`
equivalente conocido) y `RLIMIT_AS` no aplica.

### R12 · Stop rule sin dientes técnicos — **refutada**

La parada tras M3 es social, pero los contratos v1 no tienen dónde colgar
routing, memoria ni delegación (D6), y toda extensión exige versión mayor de
schema (§15.7). El scope creep tendría que romper dos gobernanzas a la vez.
Ver también ADR-001 A3.

## Síntesis

| Resultado | Cantidad | Ítems |
|---|---|---|
| Incorporadas (vía ADR 2026-08-19) | 5 | R2, R6, R7, R11 + (R4 confirmada como no-claim) |
| Refutadas | 5 | R4, R8, R9, R10, R12 |
| Abiertas con enmienda propuesta | 3 | R1, R3, R5 |

Las tres abiertas son enmiendas de redacción a la propuesta (§7.1, §6.3 y
§13-M0), ninguna invalida el diseño. Se recomienda aplicarlas cuando la
propuesta se promueva a especificación, y una ronda adversarial **externa**
antes de autorizar M0 (esta ronda no acredita independencia).
