# Adjudicación arquitectónica post-Astra — R13/R14

**Fecha:** 2026-09-10. **Naturaleza:** adjudicación documental; no construcción.
**Autoridad de este acto:** encargo explícito del dueño por canal para analizar,
crear este documento, actualizar el README del expediente y hacer commit/push
exclusivamente documental. No autoriza implementar, modificar contratos
congelados, promover gates ni iniciar M3.

## 1. Identidad, evidencia y método

| Referencia de entrada | Identidad verificada |
|---|---|
| HEAD documental | `7f7742708e34e0783e4bd86b4cdb7ac004278876` |
| MANIFEST-ROOT vigente | `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95` |
| Manifiesto | `docs/evidencia/manifest-m2-sha256.txt` |
| Re-verificación preservada | [Informe correctivo 2](informe-reverification-correctiva-02-2026-09-10.md) |

HEAD coincidía con `origin/main` consultado directamente antes de editar; árbol
inicial limpio. Se verificaron el SHA-256 del manifiesto y sus entradas. El
manifiesto cubre implementación, contratos, scripts y tests; no estos documentos.
AN-KLA: integración sin diagnósticos e integridad correcta, revisión 51; el
checkpoint recuperado en la consulta antecedente es histórico y no sustituye
esta evidencia. No se escribe memoria en este acto.

La consulta arquitectónica Astra de la conversación antecedente es una hipótesis
razonada, no autoridad automática ni revisión independiente de este nuevo acto.
Se contrastó con código y documentos actuales. No se reejecutaron sondas ni suites
funcionales: los resultados dinámicos siguientes se atribuyen al informe
preservado; la comprobación propia es estática y normativa.

| Evidencia | Observación y adjudicación |
|---|---|
| FIND-R13-A, informe §R13 | REPRODUCIDO: `_record_for(handle)` / `_acquired.get(handle)` permiten obtener `_deposit_authority` y depositar un falso terminal o cerrar anticipadamente. ACCEPTED-CONFIRMED; no refutado por cambiar el threat model. |
| `src/application/start_service.py`, `_HandleRecord`, `_watch_terminal`, `_record_for` | El mismo registro conserva el secreto y las operaciones que éste autoriza. Unforgeability por identidad no demuestra confinement. |
| FIND-R13-B, informe §R13 | REPRODUCIDO: handle parcialmente construido filtra excepción. ACCEPTED-CONFIRMED; sigue siendo defecto de frontera pública dentro de R15. |
| FIND-R14-A, informe §R14 | REPRODUCIDO: Admission A / Start B / Host B / caller declara B produce Started, spawn y consumo. ACCEPTED-CONFIRMED. |
| `start_service.py`, constructor y `_check_configuration_authority` | `declared_config_fingerprint` proviene del caller; las comparaciones funcionan pero no acreditan al emisor. |
| `admit.py`, `admit` / `m2_config_fingerprint`; `domain/admission_token.py` | Admission deriva su configuración y GuaranteePlan, pero el token v1 no contiene el perfil M2 ni identifica un evento de emisión por sí solo. |
| `adapters/posix_supervisor.py`, `config_fingerprint` / `spawn` | Se cotejan campos operativos con el perfil; el payload se prepara después del CAS. La futura corrección debe ligar el compromiso pre-CAS al snapshot usado efectivamente. |

Fuentes normativas contrastadas:

- [ADR-001](../../adr/adr-001-alcance-y-modelo-de-amenaza.md): alcance local, exclusión de aislamiento fuerte y separación de escritura por diseño.
- [ADR-011](../../adr/adr-011-handoff-admision-start.md), §§2.1–2.3, 2.6–2.7 y 3: handoff existente, revalidación, CAS, reinicio y alternativas aplazadas.
- [ADR-012](../../adr/adr-012-supervision-local-m2.md), §§2.1–2.5 y 4: ownership, configuración frente a valores aplicados, handles y no-claims.
- [Especificación](../../especificacion/ektel-runtime-m0-m3-v1.md), §§8, 12, 13 y 17; [claims/no-claims](../../claims-y-no-claims.md), C2–C4, N3, N6, N14, N17–N19.
- [Autorización M2](../../decisiones/autorizacion-m2-2026-09-09.md), A-M2-2/3/6/7 y §§4–6; [alcance técnico](../../propuestas/alcance-tecnico-m2-2026-09-09.md), §6.2: extensión aditiva de M1 y stop rules.
- [Paquete M2](../../propuestas/paquete-preparacion-m2-2026-08-28.md), gates G-M2-01..15; [adjudicación anterior](adjudicacion-reverification-01-2026-09-10.md), FIX-M2-R13/R14.

## 2. Resolución R13 fuerte

**R13-STRONG = BLOCKED-BY-NORMATIVE-GAP** bajo el threat model exacto:
`arbitrary Python code executing inside the same coordinator process`.

| Concepto | Alcance |
|---|---|
| API encapsulation | El consumidor no recibe operaciones públicas de depósito/cierre terminal. |
| Capability discipline | Las referencias con autoridad se entregan sólo a componentes previstos, bajo las restricciones de acceso asumidas. |
| Security boundary | Impide obtener o modificar autoridad aun ignorando interfaces y usando introspección/modificación arbitraria. |

Las tres propiedades no son equivalentes. Python ordinario compartido permite
las dos primeras como arquitectura de interfaces; no constituye la tercera.
Funciones y closures exponen estado; los frames permiten inspeccionar ejecución;
la modificación de clases, funciones o estado puede eludir el sentinel en lugar
de robarlo. Cambiar nombres, usar name mangling, trasladar el secreto a una
closure, comprobar un thread o esconder una cola no separa permisos del runtime.
Base técnica: [modelo de datos de Python](https://docs.python.org/3/reference/datamodel.html#user-defined-functions),
[`sys._current_frames`](https://docs.python.org/3/library/sys.html#sys._current_frames)
y [PEP 578, límites del sandboxing](https://peps.python.org/pep-0578/#why-not-a-sandbox).
La conclusión arquitectónica se deriva de esas capacidades, no de un supuesto
de que todo objeto de cualquier runtime sea necesariamente introspectable.

Demostración del gap: decisión terminal, estado y verificador comparten el dominio
del atacante; éste puede modificar ese dominio; las restricciones M2 no permiten
añadir el mecanismo que lo impediría. Aislamiento de proceso/runtime, IPC gobernado
o separación efectiva de permisos/capabilities serían una frontera adicional.
No se diseña ni introduce aquí. Su ubicación futura queda pendiente: **no se
adjudica a M3**. ADR-001 remite históricamente aislamiento a una propuesta futura;
este acto no activa ni adjudica M4.

El gap de la claim fuerte no es un fracaso que otro sentinel pueda corregir.
Tampoco absuelve el defecto concreto de distribución de referencias ni el fallo
de validación de handles. Se conserva **R13 = NOT-SATISFIED bajo su formulación
fuerte**. La determinación histórica «R13 AUTHORIZABLE-WITHIN-M2» no se reescribe:
este acto limita prospectivamente su lectura, sin convertirla en evidencia de
seguridad frente al intérprete hostil.

No-claim propuesto para ratificación normativa:

> EKTEL M2 no proporciona aislamiento de seguridad frente a código Python
> arbitrario ejecutándose dentro del mismo proceso del coordinador ni garantiza
> que dicho código no pueda inspeccionar o modificar estado interno del runtime.

Esta precisión no elimina garantías de validación pública, concurrencia,
linealización, rechazo de falsificaciones ni conservación de R12.

## 3. Threat model para R15/R16

**Trusted:** composición/bootstrap autorizado, coordinador EKTEL, componentes
internos Admission/Start, Host autorizado y configurado, y estado interno bajo
uso de interfaces admitidas. El ReplayStore conserva sus contratos y modos de
fallo; llamarlo parte de la infraestructura confiable no autoriza asumir éxito
de I/O ni eliminar reconciliación. No se redefine PolicyPort como infalible.

**Entradas no confiables:** requests, tokens inválidos o ajenos, handles copiados,
incompletos o forjados, fingerprints del caller, tipos hostiles en fronteras,
secuencias abusivas, concurrencia, abandono y timeouts. Componer componentes
genuinos con perfiles incompatibles sigue dentro de los casos que deben rechazarse.

**Fuera de claim:** introspección/modificación arbitraria del mismo intérprete,
extracción o modificación de memoria, sustitución maliciosa del Host o del código
con autoridad equivalente, y sandboxing del coordinador. No basta declarar
«sin introspección arbitraria» y después permitir recorrer registros privados:
esa operación queda fuera del modelo limitado, sin negar la reproducción R13.

Las interfaces admitidas incluyen toda ruta pública de construcción y consumo
aceptada en producción. Deben inventariarse antes de implementar; no se permite
reclasificar retrospectivamente una ruta pública como interna para hacer pasar
una prueba. Los puntos de inyección de dependencias de confianza deben quedar
identificados; recibir una property con el nombre esperado no acredita un Host.

## 4. FIX-M2-R15 — Terminal writer separation bajo threat model M2

**R15 = AUTHORIZABLE-WITHIN-M2. No implementada ni satisfecha.** Obligación nueva,
limitada, que sustituye la tarea correctiva residual de interfaz; no renombra R13
ni lo marca satisfecho. Su adopción normativa y construcción siguen pendientes.

Objetivo: bajo composición confiable y consumidores que usan interfaces admitidas,
el consumidor no puede suministrar, depositar ni cerrar autoritativamente el
resultado terminal. La transición pertenece al coordinador/writer interno.

Requisitos conjuntivos:

1. ExecutionHandle no ofrece depósito público.
2. Ninguna API consumidora acepta un terminal fabricado como autorizado.
3. Ninguna API consumidora permite cierre terminal autoritativo, incluida ausencia.
4. El writer recibe el handoff del Host confiable; no de un callback del caller.
5. Existe un único punto de transición terminal, linealizado: **como máximo una**
   transición; exactamente una cuando el writer vivo observa un desenlace
   definitivo conforme al contrato. No se promete liveness tras perderlo.
6. Como máximo un resultado puede consumirse; exactamente una transferencia si
   existe resultado disponible y un consumidor elegible completa su adquisición.
   Abandono o ausencia no fabrican una entrega para cumplir «exactamente uno».
7. Ausencia definitiva, cierre, resultado disponible, consumo y timeout de espera
   se distinguen. Timeout no equivale a ausencia terminal ni cierra la operación.
8. El caller no recibe una referencia destinada a ejercer la operación writer.
9. Ninguna ruta pública permite desplazar el terminal real por uno fabricado.
10. Handle copiado, parcialmente construido, cross-instance o inválido produce
    rechazo controlado, nunca excepción no documentada.
11. R12 se conserva: lifetimes, custodia, tombstones, consumo y slots permanecen
    separados; no reaparecen pérdida del handle prometido ni retención ilimitada.
12. No se afirma resistencia a introspección Python arbitraria.

`terminate` legítimo puede solicitar terminación conforme a ADR-012; no concede
al caller el derecho de decidir o inyectar el terminal. Abandono y timeout tampoco
son esa autoridad. La validación del terminal y la diferenciación de estados se
mantienen aunque ya no exista un sentinel accesible.

| Contraejemplo obligatorio | Oráculo |
|---|---|
| Depósito por cada superficie pública documentada/admitida | Operación inexistente o rechazo controlado; ningún cambio terminal. |
| Cierre anticipado por superficie consumidora | Ninguna transición autoritativa; preservar terminación legítima best-effort. |
| Terminal falso seguido/concurrente con terminal real | El falso no desplaza ni bloquea la entrega legítima. |
| Handle copiado, incompleto, cruzado o inválido | Rechazo contractual, sin excepción no documentada; cubre FIND-R13-B. |
| Terminal + abandono + timeout + dos consumidores | Como máximo una transición y una entrega; sin doble liberación ni fuga de R12. |
| Extracción por privados/closures/frames | Límite reconocido del modelo fuerte; no presentar exclusión como ataque resistido. |

## 5. Adjudicación R14 y FIX-M2-R16 — Admission issuance provenance binding

**R14 = NOT-SATISFIED. Viabilidad arquitectónica: FIX-WITHIN-AUTHORIZED-M2
bajo el modelo local delimitado. R16 = AUTHORIZABLE-WITHIN-M2.** No equivale a
permiso de construcción: las condiciones normativas de §9 siguen pendientes.

Sí puede conservarse evidencia efímera producida por Admission, sin cambiar
wire/schema ni el par existente de StartRequest. Asociación exigida:

```text
token emission -> recognized Admission issuer -> configuration snapshot/fingerprint
```

La raíz confiable fija quién puede emitir para esta instancia. Admission deriva
el perfil del mismo snapshot validado que produjo GuaranteePlan y registra la
asociación internamente al emitir. El caller sólo transporta token y request;
no declara emisor, perfil ni asociaciones. «No sustituible» se entiende frente
a interfaces admitidas, no frente a modificación arbitraria del intérprete.

Flujo obligatorio, todo binding anterior al CAS/spawn:

1. Admission opera con snapshot validado A.
2. La admisión produce la emisión T; su publicación utilizable en M2 requiere
   que la evidencia local esté comprometida en memoria.
3. El dominio confiable conserva `T -> issuer-local -> fingerprint(A)`.
4. Caller transporta T y el request por el handoff existente.
5. Start resuelve T contra evidencia de su instancia y preserva la revalidación
   pura de ADR-011; el lookup no reevalúa PolicyPort ni reserva nonce.
6. Compara el perfil de esa emisión con el snapshot requerido por Start.
7. Comprueba el compromiso de configuración del Host confiable contra ese snapshot.
8. Sólo coincidencia completa permite continuar con la secuencia vigente de
   capacidad, reloj, CAS y spawn. Ausencia, ambigüedad o divergencia rechazan antes
   de `consume_start_token`; el intento no cambia el estado previo del token.

El contraejemplo A/B/B con caller declarando B devuelve A del registro autorizado
o ausencia si T es ajeno. En ambos casos rechaza antes del CAS. Una referencia
a Admission B no demuestra que B emitió T. Una factory es útil, pero no suficiente
sin pertenencia de emisión y comprobación obligatoria en construcciones directas.

Prohibido: API pública `register(token, caller_supplied_fingerprint)`, overwrite
silencioso, usar sólo `action_id`, aceptar un fingerprint del caller como provenance,
o inferir historia perdida. Tampoco se sustituye la revalidación del descriptor
por este registro: no guarda comando, entorno ni stdin ni afirma igualdad de los
bytes completos del request, que ADR-011 no acredita.

Identidad: el índice debe ligar la representación autenticada inequívoca del token
completo, no campos parciales ni JSON exterior incidental. Si usa hash, debe
resolver colisiones/comparaciones sin atribuir una emisión distinta. Un token v1
determinista no distingue dos eventos con los mismos campos y clave: dentro de la
instancia se exige emisión reconocida única o repetición idempotente del mismo
vínculo, sin nueva autoridad; cualquier asociación incompatible se rechaza. No
hay claim de origen histórico universal frente a emisiones idénticas externas
con las mismas claves. Exigir esa distinción sin nueva evidencia sería otro gap.

No se necesita autenticidad criptográfica nueva. Fingerprint acredita igualdad
de contenido; provenance identifica al productor; authority binding acredita
que éste podía crear la asociación; identidad local distingue objetos registrados
de copias bajo el modelo asumido. MAC/firma sólo autentican respecto de una clave
protegida y no vuelven veraz a un Host ni protegen contra el intérprete hostil.
Se conserva la criptografía existente del token; no se crea otro envelope.

## 6. Lifecycle acotado de evidence-of-issuance

Decisión de diseño candidata para autorización: capacidad de evidencia
**N = max_concurrent_actions** del snapshot validado existente (1..64), en un
contador independiente de slots de ejecución y de handles pendientes. No añade
parámetro a M2Config ni modifica su fingerprint. Es una cota conservadora de
admisiones M2 pendientes, no una promesa de throughput; ampliarla requerirá
adjudicar su presupuesto. No dimensionarla por número de resultados retenidos.

| Etapa | Regla obligatoria de la corrección propuesta |
|---|---|
| Creación | Reservar plaza en la ruta M2 antes de publicar una emisión que requiera evidencia. Admission es el productor del vínculo. Un fallo de admisión libera la reserva; el commit local precede a entregar Admitted utilizable. |
| Saturación | Fail-closed en la composición M2 antes de emitir una admisión sin respaldo. No desalojar evidencia vigente para admitir otra. La ruta M1 sin M2 permanece intacta. La ubicación del control y su outcome existente requieren ratificación de §9 antes de implementar. |
| Lookup | Sólo lectura/validación para Start; referencia fijada durante el intento y contada contra N. No releer configuración mutable después de aprobar. Desconocido, expirado, ambiguo o divergente: rechazo pre-CAS. |
| Expiración | Retener hasta fin de vigencia estricta de start (`now_wall >= exp`, sin extenderla por skew) salvo consumo confirmado. Un intento en curso mantiene su snapshot fijado hasta resolver; el reloj inválido no habilita inicio ni exige crecimiento ilimitado. |
| Fallo anterior al CAS o CAS confirmado unspent | Mantener evidencia válida para reintento hasta expiración. No gastarla durante la comprobación de configuración. |
| CAS CONSUMED / ALREADY_SPENT / reconciliación spent | No habilitar otro inicio. Puede liberar la plaza de emisión al concluir su transferencia a la operación; el ReplayStore mantiene la defensa durable de replay. Intentos concurrentes ya fijados siguen sometidos al mismo CAS. |
| CAS incierto / reconciliación unknown | Conservar evidencia hasta expiración o resolución sin reintento automático. No transformar evidencia en permiso de spawn; conservar las reglas vigentes de indeterminación y slots. |
| Resultado terminal | No se necesita conservar el registro de emisión por retención del resultado. R15/R12 poseen su estado y tombstone; su consumo no reabre emisión ni token. |
| Reinicio | La evidencia desaparece. El token/request solos no reconstruyen el perfil histórico: fail-closed para inicio sin evidencia. Ninguna escritura durable ni repoblación por el caller. `spent` del ReplayStore sigue durable. |

La cuenta incluye reservas e intentos fijados; carreras no pueden superar N.
Un intento bloqueado puede consumir capacidad, pero no justificar crecimiento
ilimitado. La futura implementación debe demostrar cierre/liberación en sus rutas
de fallo. Los nombres de estados de esta tabla son conceptuales, no un schema
nuevo ni diseño impuesto de clases.

No se añade un requisito de éxito después de reinicio. ADR-011 §2.7 formula
posesión de token/request como condición necesaria, no una garantía explícita de
aceptación suficiente. Sin embargo, introducir esta condición local afecta la
semántica observable del handoff y requiere ratificación, no una reinterpretación
implícita del contrato. Si se exige aceptar tokens previos sin evidencia y probar
su perfil original a la vez, **BLOCKED-BY-NORMATIVE-GAP**: el perfil no está en el
token v1, la memoria se perdió y no se permite persistir ni cambiar wire.

El registro no sustituye por un objeto local el handoff aplazado en ADR-011 §3.A,
ni crea el store durable del descriptor rechazado en §3.B, ni recupera por
`action_id` desde base externa (§3.D). Esta distinción muestra viabilidad técnica;
no autoriza ampliar por analogía el permiso estrecho de `admit.py`.

## 7. Host y contraejemplos R16

Antes del CAS se verifica **Host configuration commitment**, no **future OS
effect**. El Host confiable debe usar el snapshot comprometido para preparar los
parámetros de ejecución, sin defaults alternativos ni relecturas mutables que
divergan. No se exige un efecto de kernel futuro como prueba pre-CAS. ADR-012
distingue gracia configurada de `min(grace, deadline_eff)` y subreaper solicitado
de disponible/aplicado; la igualdad de perfiles no elimina esas transformaciones.

| Contraejemplo obligatorio | Oráculo |
|---|---|
| Admission A / Start B / Host B / caller afirma B | Cero CAS, cero spawn; token sin consumo por el intento. |
| A/B/C; Host sin compromiso o con perfil divergente | Rechazo pre-CAS, también en construcción directa. |
| Token ajeno a la factory o supuesto Admitted reconstruido | Ninguna provenance por semejanza de datos/referencia a otro Admission. |
| Registro público, overwrite, colisión o misma emisión con otro perfil | Ninguna asociación incompatible aceptada; no inventar cuál fue el emisor. |
| Mutación normal de configuración entre check y spawn | Snapshot estable o rechazo anterior al CAS; ninguna divergencia operativa silenciosa. |
| Capacidad N y N+1, expiración concurrente, error de admisión | Cota real; no emisión M2 sin evidencia prometida ni desalojo silencioso. |
| Pre-CAS fallido, CAS unspent/spent/unknown, dos starts | Reintento y reconciliación vigentes; ningún consumo anticipado de evidencia ni doble spawn. |
| Reinicio con token previamente emitido y aún vigente | Ausencia local: fail-closed; no inferir el perfil desde Start/Host/caller. |
| Terminal retenido/abandonado tras CAS | Evidencia no retenida por el handle; R12 y límites preservados. |
| Host malicioso declara A y aplica B | Fuera del trusted set: no contabilizar un fingerprint como defensa contra ese código. |

## 8. Diseños y ataque propio

| Propiedad | A — mínimo M2 | B — robusto M2 | C — frontera futura |
|---|---|---|---|
| Estructura | Writer por interfaz, evidencia efímera, snapshots, checks pre-CAS | Núcleo propietario de emisión/terminal, fachadas y flujo interno serializado | Aislamiento efectivo proceso/runtime y permisos/capabilities |
| R13 fuerte | No | No | Requiere frontera efectiva; no diseñada ni acreditada aquí |
| R15 | Viable | Viable | No evaluado como corrección M2 |
| R16 | Viable bajo condiciones de este acto | Viable bajo las mismas condiciones | Necesita contrato propio |
| Caller y coordinador en mismo proceso | Sí | Sí | No, o runtime efectivamente aislado |
| Wire/schema nuevos | No | No | Posible/necesario según frontera; ADR-011 exige wire versionado al cruzar procesos |
| M3 | No | No | No asignado a M3 |
| Resistencia a introspección arbitraria | No | No | Sólo con aislamiento efectivo, no por mover un watcher |
| Coste | Bajo/medio | Medio | Alto y fuera del acto |

Ataque a A: intentar obtener writer por handle/record, cerrar por timeout,
presentar emisión de A a B o sobrescribir evidencia. Debe fallar por las
interfaces admitidas. Buscar closures/frames lo vence bajo R13 fuerte: se declara
el límite, no se presenta el ataque como resistido.

Ataque a B: recuperar núcleo por fachada, inyectar `deposit`/`register` por cola
genérica o ejecutar callbacks del caller con autoridad writer. Si alguna interfaz
lo permite, se rechaza B por desplazar el mismo defecto. Serialización no es
autenticación. No se exige implementar B para resolver A.

Ataque a C: falsificar IPC o modificar el resultado autoritativo que siga viviendo
con el caller. Otro proceso por sí solo no basta. Este señalamiento de frontera
no diseña IPC, sandbox, identidad ni permisos y no inicia trabajo futuro.

Recomendación: A como mínimo candidato, sujeto a §9. R15 gobierna acceso a la
transición; R16 gobierna provenance de configuración. La raíz común es confundir
datos transportados, evidencia del emisor y acceso autoritativo. En R13 la
capability era legítima pero filtrada; en R14 la declaración era caller-asserted.
No fusionar sus lifecycles ni usar el estado terminal como almacén de emisiones.

## 9. Decisiones normativas pendientes y stop rules

**HUMAN-NORMATIVE-DECISION-REQUIRED.** Este encargo autoriza la adjudicación y su
publicación, no adopta automáticamente cambios en contratos congelados. La
autorización M2 §8 exige nueva revisión y, cuando corresponde, autorización humana
para cambios normativos/de alcance. Deben ratificarse antes de construir:

1. No-claim de intérprete compartido, threat model y sustitución prospectiva de la
   obligación fuerte por R15, conservando R13 no satisfecha y el gap.
2. Evidencia local adicional para Start, fail-closed tras pérdida/reinicio,
   identidad de emisión inequívoca, capacidad N y saturación M2.
3. Encaje exacto de la creación/reserva de evidencia en la extensión aditiva de
   Admission: outcome existente, orden de diagnósticos y ausencia de regresión
   M1. No inventar un reason code ni modificar el pipeline congelado al implementar.
4. Nueva autorización separada de corrective_action_3 con archivos, DoD y gates.

Documentos exactos que deben enmendarse posteriormente mediante acto normativo
autorizado; **ninguno se modifica ahora**:

| Documento | Sección/objeto de la actualización posterior |
|---|---|
| `docs/adr/adr-001-alcance-y-modelo-de-amenaza.md` | Modelo §1.2 y consecuencias: precisión expresa del intérprete compartido, sin ampliar aislamiento. |
| `docs/claims-y-no-claims.md` | No-claim explícito (identificador a ratificar, sin reutilizar retirados), alcance de C2/C4 y distinción replay durable/provenance efímera. |
| `docs/especificacion/ektel-runtime-m0-m3-v1.md` | §§8, 12 y 13: condición local del handoff, ownership terminal y threat model; sincronizar lenguaje normativo público. |
| `docs/adr/adr-011-handoff-admision-start.md` | §§2.1–2.3, 2.7 y consecuencias: lookup local adicional, reinicio y conservación de revalidación/CAS; sin nuevo campo wire. |
| `docs/adr/adr-012-supervision-local-m2.md` | §§2.1, 2.3, 2.4 y 4: writer/consumidor, snapshot y no-claim; preservar terminación y ausencia honesta. |
| `docs/propuestas/alcance-tecnico-m2-2026-09-09.md` | §6.2 e inventario: aclarar extensión de emisión M2 y límites de Admission; preservar baseline histórica mediante enmienda referenciada. |
| `docs/propuestas/paquete-preparacion-m2-2026-08-28.md` | Gates G-M2-01/02/05/06/10/11/12/14/15: integrar criterios R15/R16, sin promoverlos por documentación. |

La decisión humana debe asentarse en un acta nueva de `docs/decisiones/`, ligada
a esta adjudicación y a la autorización de M2; no reescribir la transcripción
histórica de `autorizacion-m2-2026-09-09.md` ni los informes previos. Si la revisión
determina incompatibilidad con una garantía M1 congelada o necesidad de otro
contrato, detener ese incremento como **BLOCKED-BY-NORMATIVE-GAP**. Viabilidad
arquitectónica no significa permiso para resolver tal incompatibilidad en código.

## 10. Estado resultante y límite de cierre

```text
architectural_adjudication = COMPLETE / DOCUMENTARY-ONLY
R12 = SATISFIED
R13 = NOT-SATISFIED
R13-STRONG = BLOCKED-BY-NORMATIVE-GAP
R14 = NOT-SATISFIED
R15 = AUTHORIZABLE-WITHIN-M2
R16 = AUTHORIZABLE-WITHIN-M2
normative_ratification = HUMAN-NORMATIVE-DECISION-REQUIRED
corrective_action_3 = PENDING-AUTHORIZATION

G-M2-15 = CORRECTIVE-FIX-AND-RETRY
M2 = OPEN
M3 = BLOCKED
```

R15/R16 no están implementadas, verificadas ni satisfechas. El gap fuerte queda
registrado; su exclusión de una obligación de cierre necesita ratificación, no
desaparición del finding. R14 permanece no satisfecha hasta evidencia futura.
R12 se conserva según re-verificación 2, no por una nueva ejecución en este acto.

DoD documental: sólo este archivo y README del expediente; informe correctivo 2,
src, tests, scripts, contratos, manifiesto y documentos normativos intactos;
enlaces y diff verificados; commit/push documental con SHA remoto comprobado.
No se ejecutan suites funcionales para atribuir verde nuevo. Después de publicar
estos documentos, detenerse. Ninguna promoción de gate, cierre de M2 ni inicio M3.
