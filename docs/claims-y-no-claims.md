# Claims y no-claims de ektel M0–M3

**Estado:** borrador para consenso, junto con los ADR-001 a ADR-008.
**Fecha:** 2026-08-19. **Requisito:** §21.4 del criterio de adopción.

Esta tabla es el lenguaje público permitido sobre ektel. Todo documento,
README o integración que afirme algo fuera de "Claims" o niegue algo de
"No-claims" contradice la gobernanza del proyecto. Las clases de garantía
(`enforced` / `reactive` / `observed` / `unsupported`) son las de la
propuesta §8.

## Claims (lo que M0–M3 sí afirmará, una vez implementado y probado)

| # | Claim | Clase / base |
|---|---|---|
| C1 | Toda acción mal formada, no autorizada o con capacidad inválida, expirada o reutilizada se rechaza antes de iniciar cualquier proceso (fail-closed en admisión). | Diseño: §6.2, ADR-003/004 |
| C2 | La autorización queda vinculada a la ejecución mediante identidad firmada (HMAC-SHA256 sobre bytes transportados) y admisión de un solo uso, durable tras reinicio. | ADR-002/003/004 |
| C3 | El proceso se ejecuta bajo un supervisor separado con reloj monotónico, plazo, terminación dirigida del grupo observado y salida acotada con truncamiento declarado. | §6.3; plataforma: ADR-006 |
| C4 | Todo resultado es tipado y distingue terminación técnica de éxito de negocio; `executed` nunca significa éxito. | ADR-005 |
| C5 | Toda transición observada dentro de la frontera intenta emitir un RuntimeEvent; todo fallo reconocido queda como brecha explícita o ausencia declarada, nunca rellenado. | §10, ADR-007 |
| C6 | Con `policy_mode=required`, ninguna acción inicia sin `Allow` del PolicyPort configurado. | ADR-008 |
| C7 | Con auditoría obligatoria, el inicio falla cerrado si el evento previo no logra recibo `durable` (fsync de archivo y directorio). | ADR-007 |
| C8 | La cadena de eventos por digest detecta modificación posterior. | §10.3.5 |
| C10 | Los contratos v1 son versionados, estrictos y verificables contra vectores dorados. | ADR-002 |

*(La contabilidad de CPU se retiró de Claims por la revisión externa
2026-08-19, F7: es una magnitud que el producto no gobierna —clase
`observed` en el mejor caso— y v1 excluye `budget_exceeded`. Permanece
registrada como evidencia E1/E2 y en la tabla de garantías por plataforma,
no como claim de producto. El identificador C9 queda retirado, no
reutilizado.)*

## No-claims (lo que ektel NO afirma)

| # | No-claim | Origen |
|---|---|---|
| N1 | Ektel **no garantiza la identidad del binario ejecutado**: con `route_mutable_unverified`, el contenido de `command_absolute` puede cambiar entre admisión e inicio (TOCTOU reconocido, no mitigado en v1). | D7a, ADR-003 |
| N2 | No hay aislamiento de filesystem ni de red, ni contención preventiva de CPU/RSS. | §4, D6 |
| N3 | No hay ejecución multitenant ni defensa contra código hostil con control del host; kernel comprometido y escape por `setsid`/double-fork están fuera del modelo. | §12.2, ADR-001 |
| N4 | `deadline_exceeded` no promete scheduler de tiempo real ni muerte universal de descendientes: describe la transición registrada por un supervisor vivo. | §8 regla 4 |
| N5 | En Darwin (macOS) la contabilidad de CPU multi-nivel es `unsupported` (sin mitigación conocida de huérfanos) y `RLIMIT_AS` no aplica. | Evidencia E2/E1, ADR-006 |
| N6 | Si el supervisor muere, hay ausencia de resultado: ektel no inventa estado ni lo reconstruye. | §11, ADR-005 |
| N7 | La cadena de eventos no prueba autoría, completitud, orden global ni almacenamiento externo; los recibos v1 son verificables sólo localmente (sin firma asimétrica). | §10.3.5, ADR-007 |
| N8 | Las capacidades y recibos v1 no son verificables por terceros ni aportan no-repudio (HMAC simétrico del operador). | ADR-003 |
| N9 | Ektel no emite ni avala conformidad CAGF (A0–A10); cualquier conformidad la declara, si acaso, el adaptador externo bajo su propio contrato. | §9.2, ADR-008 |
| N10 | Ektel no enruta conversaciones, no selecciona tareas, no tiene memoria, plugins, presupuestos de tokens ni delegación de capacidades. | §4, D6 |
| N11 | Ektel no audita acciones que eviten su frontera (canales directos, procesos ajenos, estado externo no mediado). | §10.1 |
| N12 | Ninguna afirmación de portabilidad x86_64 hasta caracterización en hardware o VM real; la evidencia actual cubre Linux aarch64 (linuxkit) y Darwin arm64 (macOS 26.5.2). | ADR-006 |
| N13 | El replay store y la admisión asumen reloj de pared disciplinado (NTP) y tolerancia declarada; un administrador del host está fuera del modelo de amenaza. | ADR-004 |
| N14 | Ektel no protege su almacén ni su clave contra el proceso supervisado más allá de la separación de escritura por diseño; la protección de rutas y permisos es del despliegue. | ADR-001 A2, ADR-003 A1 |

## Regla de uso

Afirmar un no-claim como claim, o un claim antes de que su criterio de
salida esté probado, es un defecto de documentación que se corrige antes de
cualquier publicación. Esta tabla se versiona con los contratos: un cambio
incompatible crea versión mayor (propuesta §15).
