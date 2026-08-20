# Claims y no-claims de ektel M0–M3

**Estado:** **consensuada por el dueño el 2026-08-19**, tras aplicar el
veredicto externo
(`docs/revisiones/revision-externa-claude-tabla-claims-2026-08-19.txt`), y
**enmendada con acta** por la ronda correctiva B1–B8
(`docs/decisiones/enmienda-transversal-b1-b8-2026-08-19.md`) y por la
segunda ronda externa C1–C6/D1–D5 del 2026-08-20
(`docs/decisiones/enmienda-transversal-v3-2026-08-20.md`).
Actas: `docs/decisiones/consenso-tabla-claims-2026-08-19.md`,
`docs/decisiones/enmienda-transversal-b1-b8-2026-08-19.md` y
`docs/decisiones/enmienda-transversal-v3-2026-08-20.md`.
**Fecha:** 2026-08-20. **Requisito:** §21.4 del criterio de adopción.

Esta tabla es el lenguaje público permitido sobre ektel. Todo documento,
README o integración que afirme algo fuera de "Claims" o niegue algo de
"No-claims" contradice la gobernanza del proyecto. Las clases de garantía
(`enforced` / `reactive` / `observed` / `unsupported`) son las de la
propuesta §8. Las referencias de la forma `§x.y` se resuelven contra la
propuesta histórica
(`docs/propuestas/propuesta-runtime-minimo-m0-m3-2026-08-17.md`) o la
especificación v1.2, según el contexto de cada fila.

## Claims (lo que M0–M3 sí afirmará, una vez implementado y probado)

| # | Claim | Clase / base |
|---|---|---|
| C1 | Toda acción mal formada, no autorizada o con capacidad inválida, expirada o reutilizada se rechaza antes de iniciar cualquier proceso (fail-closed en admisión). | Diseño: §6.2, ADR-003/004 |
| C2 | La autorización queda vinculada **al descriptor admitido y a la ruta declarada** mediante identidad autenticada (MAC): HMAC-SHA256 sobre `protected_header_b64 + "." + payload_b64` tal como viaja (estilo JWS, `alg` autenticado), y admisión de un solo uso, durable tras reinicio. **No** se vincula a la identidad del contenido finalmente ejecutado (ver N1). | ADR-002/003/004 |
| C3 | El proceso se ejecuta bajo un supervisor separado con reloj monotónico, plazo, terminación dirigida del grupo observado y salida acotada con truncamiento declarado. | §6.3; plataforma: ADR-006 |
| C4 | Todo resultado es tipado y distingue terminación técnica de éxito de negocio; `executed` nunca significa éxito. | ADR-005 |
| C5 | Toda transición observada dentro de la frontera intenta emitir un RuntimeEvent; todo fallo reconocido queda como brecha explícita o ausencia declarada, nunca rellenado. | §10, ADR-007 |
| C6 | Con `policy_mode=required`, ninguna acción inicia sin `Allow` del PolicyPort configurado. | ADR-008 |
| C7 | Con auditoría obligatoria, el inicio falla cerrado si el evento previo no logra recibo `flush_protocol_completed` (antes `durable`; renombrado por D1). El protocolo es fsync de archivo y directorio; en Darwin (macOS) `fsync()` no vacía la caché del disco y se requiere `fcntl(F_FULLFSYNC)`. `flush_protocol_completed` significa "protocolo de plataforma completado bajo supuestos declarados": el orden del protocolo y la recuperación tras crash del escritor **sí son testeables** (nivel 1: SIGKILL del escritor; nivel 2: dm-flakey en Linux — ambos se validan en M3); la supervivencia a un **corte físico real** no es testeable sin hardware (nivel 3, supuesto declarado; ver N5). | ADR-007 |
| C10 | Los contratos v1 son versionados, estrictos y verificables contra vectores dorados. | ADR-002 |

*(C8 queda **retirado** por la segunda revisión externa 2026-08-20 (C3):
la formulación "enlaces rotos respecto de un head confiable" no tenía
interfaz implementable en v1 — no existe puerto `TrustedHeadStore` ni
`verify_chain`. La cadena de eventos aporta diagnóstico de consistencia
interna y eso queda declarado en N7; la verificación contra head confiable
externo es propuesta v2. El identificador C8 no se reutiliza.)*

*(La contabilidad de CPU se retiró de Claims por la revisión externa
2026-08-19, F7: es una magnitud que el producto no gobierna —clase
`observed` en el mejor caso— y v1 excluye `budget_exceeded`. Permanece
registrada como evidencia E1/E2 y en la tabla de garantías por plataforma,
no como claim de producto. El identificador C9 queda retirado, no
reutilizado.)*

*(Estado de evidencia — taxonomía §2.1 de la consolidación: hoy todos los
claims son **P** (propuesta de diseño). Ninguno es V/L hasta que la suite
del hito correspondiente lo ejecute y conserve la prueba: C1–C4 y C10 con
la suite M1 (admisión y wire), C3 y C5–C7 con M2/M3 (supervisión y
auditoría). La prueba que falsaría cada claim es el test de esa suite que
ejerce la transición prometida y comprueba el rechazo, recibo o estado
contrario; un claim que sobrevive su suite pasa a V y esta nota se
actualiza por claim, no en bloque.)*

## No-claims (lo que ektel NO afirma)

| # | No-claim | Origen |
|---|---|---|
| N1 | Ektel **no garantiza la identidad del binario ejecutado**: con `route_mutable_unverified`, el contenido de `command_absolute` puede cambiar entre admisión e inicio (TOCTOU reconocido, no mitigado en v1). Si este supuesto cae, la identidad del descriptor sigue autenticada (C2 en parte), pero la vinculación al artefacto realmente ejecutado queda anulada. | D7a, ADR-003 |
| N2 | No hay aislamiento de filesystem ni de red, ni contención preventiva de CPU/RSS. | §4, D6 |
| N3 | No hay ejecución multitenant ni defensa contra código hostil con control del host; kernel comprometido y escape por `setsid`/double-fork están fuera del modelo. | §12.2, ADR-001 |
| N4 | `deadline_exceeded` no promete scheduler de tiempo real ni muerte universal de descendientes: describe la transición registrada por un supervisor vivo. | §8 regla 4 |
| N5 | En Darwin (macOS) la contabilidad de CPU multi-nivel es `unsupported` (sin mitigación conocida de huérfanos), `RLIMIT_AS` no aplica, y `fsync()` no vacía la caché del disco — el recibo `flush_protocol_completed` exige `F_FULLFSYNC` (disponibilidad de la primitiva caracterizada en `tests/escape/`). Sólo la supervivencia a un **corte físico real** (nivel 3) no es testeable sin hardware; el orden del protocolo y la recuperación tras crash del escritor sí lo son (niveles 1–2, M3). | Evidencia E2/E1, ADR-006, ADR-007 |
| N6 | Si el supervisor muere, hay ausencia de resultado: ektel no inventa estado ni lo reconstruye. | §11, ADR-005 |
| N7 | La cadena de eventos por digest aporta en v1 **diagnóstico de consistencia interna únicamente**: no prueba autoría, completitud, orden global ni almacenamiento externo, y un atacante que reescribe todo el almacén puede recalcularla (no existe puerto de head confiable en v1 — es propuesta v2). Los recibos v1 no llevan MAC ni firma. | §10.3.5, ADR-007 |
| N8 | Las capacidades usan HMAC simétrico del operador: no son verificables por terceros ni aportan no-repudio. Los **recibos v1 no llevan MAC ni firma** — son acuses estructurales del sink, no objetos autenticados; un recibo autenticado es propuesta v2. | ADR-003, ADR-007 |
| N9 | Ektel no emite ni avala conformidad CAGF (A0–A10); cualquier conformidad la declara, si acaso, el adaptador externo bajo su propio contrato. | §9.2, ADR-008 |
| N10 | Ektel no enruta conversaciones, no selecciona tareas, no tiene memoria, plugins, presupuestos de tokens ni delegación de capacidades. | §4, D6 |
| N11 | Ektel no audita acciones que eviten su frontera (canales directos, procesos ajenos, estado externo no mediado). | §10.1 |
| N12 | Ninguna afirmación de portabilidad x86_64 hasta caracterización en hardware o VM real; la evidencia actual cubre Linux aarch64 (linuxkit) y Darwin arm64 (macOS 26.5.2). | ADR-006 |
| N13 | El replay store y la admisión asumen reloj de pared disciplinado (NTP) y tolerancia declarada; un administrador del host está fuera del modelo de amenaza. | ADR-004 |
| N14 | Ektel no protege su almacén ni su clave contra el proceso supervisado más allá de la separación de escritura por diseño; la protección de rutas y permisos es del despliegue. Si la **clave** se filtra, se anulan **en silencio** C1 y C2: un atacante fabrica capacidades válidas e inicios indistinguibles. C7 **no** cae por la clave — exige además comprometer o evadir el AuditSink (corrección de la segunda revisión externa, 2026-08-20). Si el **almacén** es reescrito por completo, la cadena deja de detectarlo (los recibos v1 no llevan MAC: no se "fabrican", se reescriben). | ADR-001 A2, ADR-003 A1, ADR-007 |

*(N15 queda **reservado sin uso**: la numeración de no-claims no se compacta, igual que C9 y C8 en Claims. Ningún no-claim fue retirado en silencio.)*

| N16 | Ektel afirma la **presencia** de un `Allow` del PolicyPort, no la corrección de la política externa. El núcleo **sí** valida el sobre de respuesta (forma, `decision_id`, vigencia `valid_until` contra reloj de pared con tolerancia declarada, recepción dentro del timeout) y convierte un `Allow` expirado o tardío en rechazo cuando el puerto es requerido; lo que **no** valida es que el adaptador decida bien ni que su política sea justa — eso es del adaptador, bajo su propio contrato (pareja de C6). | ADR-008 |

## Regla de uso

Afirmar un no-claim como claim, o un claim antes de que su criterio de
salida esté probado, es un defecto de documentación que se corrige antes de
cualquier publicación. Esta tabla se versiona con los contratos: un cambio
incompatible crea versión mayor (propuesta §15).
