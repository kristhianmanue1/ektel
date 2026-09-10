# Adjudicación final G-M2-15 y propuesta de pre-cierre M2

**Fecha:** 2026-09-10. **Naturaleza:** acto normativo/documental de adjudicación
solicitado por el dueño; no acto humano de cierre de M2.
**Resultado:** G-M2-01..15 = **15/15 CONFORMING** en el alcance ratificado.
**M2 sigue abierto**, preparado como **READY-FOR-HUMAN-M2-CLOSURE**.
M3 = **BLOCKED**. No se inicia implementación ni una nueva ronda correctiva.

## 1. Identidad y método

| Raíz congelada de entrada | Valor |
|---|---|
| HEAD documental; origin/main verificado | `6ee76934c126ff5201a9370e93e1c7c6d3b69885` |
| CORRECTIVE-REVIEW-ROOT | `f944493bc9872414daf3d46d7ae230adcbfcf42e` |
| MANIFEST-ROOT | `b59553bcb6d4ab696357354ba63ffbae398609ea48426610b447d43bec660588` |

Árbol limpio al comenzar; manifiesto y sus 98 entradas nuevamente verificados.
No hay diff de src/tests/scripts/contracts entre la raíz correctiva y el HEAD
documental. El commit de este acto sólo añade documentación y actualiza índices;
no sustituye la raíz de implementación ni requiere un manifiesto nuevo.

La adjudicación contrasta normas, findings reproducidos, código y evidencia
ejecutada contra esa implementación. No convierte memoria local en prueba.
Se reutilizan ejecuciones **de la misma implementación** identificada por hash,
no verdes de un árbol anterior; se añaden comprobaciones puntuales descritas
en §6. No se atribuyen al adjudicador nuevas suites completas ni otra revisión
externa. No se introducen código, tests funcionales, wire, schemas, IPC,
aislamiento, persistencia nueva, dependencias, tags ni releases.

## 2. Reconstrucción de la autoridad, anterior al resultado favorable

1. [Autorización M2](../../decisiones/autorizacion-m2-2026-09-09.md):
   alcance local y aditivo, contratos/revalidación protegidos; no autoriza M3/M4.
2. [ADR-011](../../adr/adr-011-handoff-admision-start.md) y
   [ADR-012](../../adr/adr-012-supervision-local-m2.md): CAS durable→spawn,
   supervisión POSIX, capacidad, deadlines y handoff; no sandbox general del
   intérprete coordinador. El supervisor POSIX existente no aísla al caller
   Python del estado del coordinador.
3. [Adjudicación post-Astra](adjudicacion-arquitectonica-r13-r14-2026-09-10.md),
   referencia `dc3de184de495abe022c656fb8b947a1b976ed8f`:
   no da por satisfecho R13; identifica el gap y solicita decisión humana.
4. [Ratificación humana R13-STRONG/R15/R16](../../decisiones/ratificacion-r13-strong-r15-r16-2026-09-10.md)
   §§1–3, anterior a la re-verificación favorable: excluye explícitamente el
   atacante arbitrario co-residente; autoriza el no-claim N20, R15 y R16.
   Sus enmiendas ya están en ADR-011/012 y
   [claims/no-claims](../../claims-y-no-claims.md). No fue una inferencia del
   implementador ni una concesión creada por este acto para obtener verde.
5. La tercera corrección y su re-verificación evalúan esa obligación ratificada,
   no la formulación fuerte rechazada. La solicitud humana actual autoriza
   adjudicar/preparar pre-cierre, pero reserva el cierre de M2 a otro acto.

**Trusted:** coordinador, Admission/Start internos autorizados, Host
autorizado/configurado y estado interno local operado por interfaces admitidas.
**Entradas hostiles:** requests, tokens, handles, fingerprints del caller,
tipos malformados/hostiles, concurrencia, secuencias abusivas y timeouts.
Una composición incoherente de componentes genuinos debe rechazarse; los fallos
normales de Host/ReplayStore siguen sometidos a manejo/reconciliación.

**Fuera de claim:** introspección/modificación arbitraria del intérprete,
sustitución arbitraria de componentes confiables, Host malicioso con autoridad
equivalente y extracción/modificación arbitraria de memoria. Que un objeto
hostil llegue a una API no autoriza invocar sus hooks arbitrarios ni convertirlos
en autoridad; esta exclusión no excusa excepciones públicas no controladas.

## 3. Adjudicación de R13-STRONG

**No es una garantía exigible de M2 bajo el threat model ya ratificado.**
Clasificación operativa: **KNOWN-LIMITATION / OUT-OF-THREAT-MODEL / NO-CLAIM**.
Provenance preservada: **BLOCKED-BY-NORMATIVE-GAP** para la propiedad fuerte;
R13 histórico permanece **NOT-SATISFIED**. Clasificar fuera de alcance no
implementa ni refuta la propiedad fuerte y no borra su falsación.

| Concepto | Garantía y límite |
|---|---|
| API encapsulation | No se entrega una operación consumidora de depósito/cierre terminal. No impide recorrer estado Python. |
| Capability discipline | El writer se distribuye sólo a la ruta interna prevista bajo composición confiable. No impide inspeccionar closures, frames u objetos con autoridad equivalente en el intérprete. |
| Security boundary | Tendría que impedir adquisición/modificación aunque el atacante ignore interfaces y controle código co-residente. No la proporcionan objetos Python ordinarios, sentinels, threads, closures o nombres privados. |

El contraejemplo histórico roba una autoridad legítima: no necesita falsificar
su valor. Desplazarla a otro objeto o closure no constituye aislamiento. R15
separa writer/lector **por interfaz**; no convierte `_foo` en security boundary.

Se conserva literalmente el no-claim humano:

> EKTEL M2 no proporciona aislamiento de seguridad frente a código Python
> arbitrario ejecutándose dentro del mismo proceso del coordinador ni garantiza
> que dicho código no pueda inspeccionar o modificar estado interno del runtime.

M2 protege las superficies y autoridades definidas por su contrato en ese
modelo. No extrapola R15 a aislamiento interproceso ni a código hostil
co-residente. Satisfacer la propiedad fuerte necesitaría una frontera efectiva
adicional; proceso/IPC gobernado/sandbox/permisos son posibilidades **no
diseñadas ni autorizadas aquí**, fuera de la corrección M2. La ubicación de una
obligación futura queda pendiente, no automáticamente en M3.

## 4. Started: orden no equivale a latencia de retorno

La [re-verificación 3](informe-reverification-correctiva-03-2026-09-10.md)
reprodujo contención de Admission: el spawn ocurre antes de liberar el lock,
pero la retirada posterior de evidencia puede demorar el retorno de `Started`.

ADR-011 §2.6 obliga al orden reloj final→CAS→spawn sin dependencia externa
intermedia y a producir Started ante spawn confirmado. Ni esa sección ni
ADR-012 fijan una cota de duración spawn→retorno de Started. Las cotas de
deadline y drenaje post-KILL no son una cota de esa llamada bajo contención.

**NO-CLAIM: bounded spawn→Started return latency.**

No se añade ni se suprime una cota temporal. Sigue vigente la custodia R12:
terminal rápido anterior al retorno no pierde el handle; el resultado existente
permanece recuperable por su vía admitida, con como máximo una entrega; no hay
doble handoff ni consumo adicional del token. La sonda de lock y las pruebas
de terminal inmediato aportan evidencia específica de esas propiedades.

No se promete recuperación durable tras caída, ni progreso de una llamada
contra una dependencia confiable que nunca retorne. La limitación de latencia
no excusaría pérdida de handle, fabricación de resultado, violación de CAS→spawn
o doble entrega: cualquiera de ellos reabriría el gate.

## 5. Obligaciones y adjudicación del expediente

| Obligación | Estado | Base |
|---|---|---|
| R12 | SATISFIED; preservada | Re-verificación 2; regresión 3 y sonda independiente de 30 ciclos, terminal anterior al retorno y custodia acotada. |
| R13 | NOT-SATISFIED histórico bajo formulación fuerte; obligación residual de interfaces SUPERSEDED por R15 | Findings R13-A/B reproducidos; adjudicación y ratificación. No se convierte retrospectivamente en SATISFIED. |
| R13-STRONG | KNOWN-LIMITATION / OUT-OF-THREAT-MODEL / NO-CLAIM; provenance BLOCKED-BY-NORMATIVE-GAP | Ratificación humana §1 y N20; §3 de este acto. |
| R14 | NOT-SATISFIED histórico; obligación correctiva SUPERSEDED por R16 | Fingerprint autodeclarado no probaba origen. El remedio histórico falló; la obligación actual se verifica como R16. |
| R15 | SATISFIED dentro del modelo ratificado | Writer no consumible, handles hostiles rechazados, ausencia/cierre/resultado diferenciados, transición única y entrega a lo sumo una; re-verificación 3 PROCEED. |
| R16 | SATISFIED dentro del modelo ratificado | Emisión reconocida→snapshot; A/B/B y emisor ajeno fallan pre-CAS; cota/lifecycle/reinicio; Host comprometido; re-verificación 3 PROCEED. |

R15 gobierna acceso a la transición terminal; R16, provenance de configuración.
Datos transportados por el caller no son evidencia de autoridad ni acceso a
operaciones autoritativas. Sus lifecycles permanecen separados. R16 reconoce
emisión efímera local, no identidad histórica universal; perderla falla cerrado,
sin inventar provenance desde token v1. Host commitment no prueba futuros
efectos exitosos del kernel.

### Cadena de evidencia, sin votación ni borrado

| Etapa preservada | Resultado y tratamiento actual |
|---|---|
| [Tres informes originales y sus identidades](README.md#informes-recibidos) | OpenAI GPT-5.6 Sol, Qwen y GLM 5.3 Flash sobre REVIEW-ROOT original `eb5590b37f5c84c8b59eb36d84ccd41dc81dd52e`. Todos FIX-AND-RETRY; restricciones de harness y exposición declarada de metadata conservadas. |
| [Reconciliación](reconciliacion-g-m2-15-2026-09-09.md) | Findings aceptados por evidencia, no mayoría. Los grupos P1 de vigencia, doble liberación y abandono originan R1/R2/R3; el resto origina R4..R11. |
| [Corrección 1](paquete-reverification-correctiva-g-m2-15-2026-09-09.md) / [re-verificación 1](informe-reverification-correctiva-01-2026-09-10.md) | R1/R2/R3/R5/R7/R8/R9/R10/R11 SATISFIED; R4/R6 no. Nuevo CORR-M2-01 P1 (custodia) y residuos P2; no se cerró el gate. |
| [Adjudicación 1](adjudicacion-reverification-01-2026-09-10.md) / [corrección 2](paquete-reverification-correctiva-02-g-m2-15-2026-09-10.md) | R12..R14 sustituyen los residuos correctivos, no la historia. |
| [Re-verificación 2](informe-reverification-correctiva-02-2026-09-10.md) | R12 SATISFIED; R13-A/P2, R13-B/P3 y R14-A/P2 reproducidos. No se ignoran por ser inferiores a P1. |
| [Adjudicación arquitectónica](adjudicacion-arquitectonica-r13-r14-2026-09-10.md) / [ratificación humana](../../decisiones/ratificacion-r13-strong-r15-r16-2026-09-10.md) | Gap fuerte y no-claim ratificados; R15/R16 autorizadas antes de corregir. Handle incompleto sigue siendo obligación dentro del modelo. |
| [Corrección 3](paquete-reverification-correctiva-03-g-m2-15-2026-09-10.md) / [re-verificación 3](informe-reverification-correctiva-03-2026-09-10.md) | PROCEED independiente para R15/R16; sin regresión R12/CAS observada. No equivale a tres familias repitiendo la tercera ronda: mismo harness/modelo heredado, contexto no transferido. |

**Respuesta a la pregunta P0/P1:** no se identifica actualmente un P0/P1
reproducible abierto dentro de los claims efectivos y el threat model M2
ratificado. Tampoco queda un residuo P2/P3 conocido exigible sin tratamiento:
la custodia, handle incompleto y provenance tienen evidencia favorable; la
intrusión arbitraria queda explícitamente fuera por decisión previa.

**G-M2-15 = CONFORMING**, como adjudicación técnica/documental para la propuesta
de pre-cierre, no como acto de cierre de M2. No es prueba de ausencia universal
de defectos. Un nuevo contraejemplo material exige reapertura, no ampliar
silenciosamente las exclusiones.

## 6. Reevaluación vigente de los quince gates

Bases: [criterios del paquete §5](../../propuestas/paquete-preparacion-m2-2026-08-28.md),
[enmienda conjuntiva G-M2-12](../../decisiones/enmienda-g-m2-12-2026-09-09.md),
ratificación R15/R16 y los paquetes/revisiones anteriores. La
[matriz del 09-09](../../evidencia/estado-evidencia-m2-2026-09-09.md)
se conserva histórica, incluido su addendum de reaperturas.

**E3** = suite final exacta de corrección 3: Darwin arm64 Python 3.12.12,
385 OK / 5 skips; Linux aarch64 clase V Python 3.12.14, 385 OK / 1 skip,
imagen por digest en el paquete. Incluye los módulos nombrados abajo.
**I3** = revisión independiente: 122 tests focalizados, sondas de 30 ciclos
y de contención; no repitió suites completas ni Linux.
**A** = comprobaciones adicionales de este acto, detalladas después de la tabla.

“Reabierto después” distingue reapertura formal del addendum de revisión
adicional por impacto. Cada fila se contrasta contra la implementación actual;
la ausencia de reapertura formal no dispensa reevaluación.

| Gate | Estado actual | Evidencia vigente | Reabierto después | Reevaluado |
|---|---|---|---|---|
| G-M2-01 | CONFORMING | E3: test_start_revalidation, test_m2_config; I3/R16 A-B-B, ausencia/otro issuer, tipos hostiles, cero CAS/spawn; fuzzers. | Sí: configuración/handles; R14→R16. | Sí: evidencia de emisión adicional, sin sustituir revalidación. |
| G-M2-02 | CONFORMING | E3: pureza en test_start_linearization; revalidation.py/ReplayStore sin cambio correctivo 3; lookup no readmite ni reemite. | No formal; impacto R16 revisado. | Sí: Admission sólo emite antes de start, no dentro de él. |
| G-M2-03 | CONFORMING | E3: OrdenTests y crash/linealización; I3 sonda de lock: spawn no espera Admission después del CAS. | No formal; impacto R16 revisado. | Sí: retiro de evidencia posterior al spawn; §4 no excusa alterar orden. |
| G-M2-04 | CONFORMING | E3: ReconciliacionTests; I3/R16: spent retira, unspent/unknown retienen, sin bypass de consumo. | No formal; ramas de retiro revisadas. | Sí: outcomes y condición estricta CONSUMED preservados. |
| G-M2-05 | CONFORMING | E3/I3: test_start_concurrency, spent tras reapertura; A: 5 carreras de 8 procesos con store real, 1 ganador/1 llamada spawn cada una. | Sí; evidencia literal multiproceso complementada aquí. | Sí: no confundir los 12 hilos existentes con procesos. |
| G-M2-06 | CONFORMING | E3: CrashAlrededorDelCasTests, SIGKILL real antes/después del CAS durable; R16 rechaza pérdida de provenance y conserva aserción spent. | Sí; reinicio sin handle/provenance. | Sí: fail-closed no reemplaza la prueba de durabilidad. |
| G-M2-07 | CONFORMING | E3: test_output_framing, prefijos, flood, crédito único, coordinador lento/caído, fórmulas y cierre forzado; A: RSS Darwin observable. | No formal; snapshot Host revisado. | Sí: parámetros salen del perfil comprometido; payload no es RSS. |
| G-M2-08 | CONFORMING | E3: test_no_hang y hostiles/escapes; procesos acotados; setsid declarado. | No formal; TERM/grupo revisados en correctivas. | Sí: no se extrapola a D-state ni sandbox. |
| G-M2-09 | CONFORMING | E3: test_deadline_math, test_termination_semantics y test_start_linearization; R1/R8 satisfechas por revisión 1. | Sí: vigencia/precedencia. | Sí: última muestra, empate y configuración comprometida preservados. |
| G-M2-10 | CONFORMING | E3/I3: test_termination_semantics, test_capacity_slots, test_m2_authority; R12/R15, handles copiados/incompletos/ajenos, abandono y carreras. | Sí: R4→R12/R13→R15. | Sí: evento de rechazo continúa pendiente M3, no se finge implementado. |
| G-M2-11 | CONFORMING | E3: test_supervisor_characterization, test_m2_config y CicloCompletoTests; R7/R9; subreaper Linux real, Darwin unsupported. | Sí: literals y TERM→KILL de grupo. | Sí: snapshot Host no altera topología/reap; no claim universal de descendientes. |
| G-M2-12 | CONFORMING | E3/I3: capacidad/terminal/cotas; diez criterios conjuntivos comprobados abajo; A: RSS. | Sí: criterios 5/7/9; R2/R3/R12/R15. | Sí: no doble liberación, custodia y evidencia R16 acotadas separadamente. |
| G-M2-13 | CONFORMING | E3: suites completas separadas Darwin/Linux del root actual; A completa RSS omitida Darwin. | No formal; nueva ejecución por cada candidato. | Sí: skips/degradaciones explícitos; sin extrapolar x86_64. |
| G-M2-14 | CONFORMING | E3: regresión M0/M1, mypy strict 34 archivos y fuzz; A: regeneración 91 vectores, diff cero; contratos/scripts sin diff desde revisión original. | Sí: regresión tras correctivas. | Sí: M1 sin m2_config preservado; no autoridad de promoción M3. |
| G-M2-15 | CONFORMING | Tres originales + reconciliación + tres ciclos correctivos/re-verificación + ratificación + I3 PROCEED + esta adjudicación. | Sí: permaneció correctivo hasta este acto. | Sí: diff y alcance revisados; no-claims explícitos, ningún P0/P1 conocido abierto dentro del modelo. |

### G-M2-12: conjunción, no compensación

1. Fórmula determinista: pruebas de configuración/cotas incluidas en E3.
2. Overflow: aritmética entera Python, fronteras y máximo analítico preservados.
3. Linealidad: casos n=1/64 y fórmulas literales; implementación de cotas sin cambio.
4. Empírico seguro: CotasDeCapacidadTests con procesos reales en E3.
5. Concurrencia: CarreraDeSlotsTests; límite no excedido.
6. Falta de slot: rechazo antes de consumo en CapacidadTests.
7. Liberación: handoff único, abandono, doble await/liberación y terminal inmediato;
   E3 e I3 reevalúan precisamente el mecanismo cambiado.
8. Indeterminado: RegresionSlotsTests y reconciliación preservan tratamiento.
9. Payload/RSS separados: pruebas explícitas más caracterización Linux E3 y
   comprobación Darwin A.
10. Claims contrastados: fórmulas de payload no se presentan como límite total de
    memoria; enmienda y no-claims permanecen. R16 añade evidencia acotada por N,
    no un diccionario ilimitado ni una cota total de RSS.

La cota máxima fue demostrada **analíticamente** y la implementación comprobada
**empíricamente a escala segura**. No se probó materialmente 16 GiB de payload.

### A: comprobaciones adicionales ejecutadas en este acto

- Manifiesto: hash anterior intacto; 98 entradas OK; diff de implementación
  nulo desde CORRECTIVE-REVIEW-ROOT. Contratos, scripts, workflows y
  pyproject.toml sin diff desde REVIEW-ROOT original. El puerto local ProcessHost
  sí evolucionó en las correctivas anteriores; no se presenta como intacto desde
  el original ni se confunde con cambio de wire/schema.
- Darwin: `.venv/bin/python -B -m unittest
  tests.escape.test_supervisor_characterization.CaracterizacionRssTests -v`:
  1 test OK, 2.641 s, sin skip, ejecutado con permiso para observar ps.
  No se convierte en una cota universal de RSS.
- Vectores: se ejecutó el generador vigente mediante runpy, cambiando únicamente
  su directorio OUT en memoria a TemporaryDirectory; `diff -ru` contra
  contracts/vectors/v1 dio cero. 91 vectores/7 grupos. El script no tiene
  `--check`: no se inventó ese modo ni se sobrescribieron los contratos.
- Multiproceso G-M2-05: sonda efímera reproducible en apéndice, sin editar tests.
  5/5 ciclos: 8 procesos, 1 Started, 1 llamada al Host, 7 cas:already_spent,
  spent verificado al reabrir FileReplayStore. Cada proceso crea su propia
  composición confiable y obtiene **su propia emisión reconocida del mismo
  token determinista de prueba**; no importa provenance perdida entre instancias.
  Store real compartido localmente; Host doble cuenta llamadas, no representa
  ocho procesos de carga reales. La supervisión/spawn real se cubre separadamente
  en E3. No prueba capability distribuida/cross-host.
- El primer intento de la sonda usó por error FileReplayStore como context manager
  (no soportado): TypeError del harness después de la carrera. Se descartó
  y repitió con close explícito; los cinco ciclos citados son de esa repetición.

Se preservan los ResourceWarning de subprocess de E3: los tests favorables no
demuestran ausencia universal de residuos. No hay en el expediente actual una
reproducción de fuga que invalide sus pruebas acotadas de recolección; un hallazgo
con identidad/proceso/condición reproducible obligaría a reabrir G-M2-08/11.
No se ocultan los skips ni las restricciones del revisor independiente.

## 7. Disposición y parada

```text
R12 = SATISFIED
R13 = NOT-SATISFIED (historical strong formulation)
R13-STRONG = KNOWN-LIMITATION / OUT-OF-THREAT-MODEL / NO-CLAIM
R13-STRONG.provenance = BLOCKED-BY-NORMATIVE-GAP
R14 = NOT-SATISFIED (historical; residual superseded by R16)
R15 = SATISFIED (ratified M2 threat model)
R16 = SATISFIED (ratified M2 threat model)
G-M2-15 = CONFORMING
G-M2-01..15 = 15/15 CONFORMING
M2 = OPEN
M2.preclosure = READY-FOR-HUMAN-M2-CLOSURE
M3 = BLOCKED
human_m2_closure = PENDING
```

READY-FOR-HUMAN-CLOSURE es estado de preparación, **no sinónimo de CLOSED**.
No queda una decisión humana pendiente sobre el no-claim R13 ya ratificado;
sí falta el acto humano separado de cierre M2. No se promueven aquí C5/C7,
audit_trail, eventos M3, tags ni releases.

Límites preservados: intérprete compartido sin security boundary; ausencia de
cota spawn→Started; pérdida de provenance tras reinicio falla cerrado;
compromiso Host no prueba efectos futuros del SO; escapes POSIX/degradaciones
de plataforma declarados; payload no es RSS; no prueba material de 16 GiB,
ni validación x86_64, ni ausencia universal de residuos.

Este acto termina con commit/push documental y comprobación de la identidad
remota. No inicia más construcción ni cierra M2.

## Apéndice — reproducción puntual G-M2-05

Ejecutar el siguiente cuerpo con `.venv/bin/python -B` desde la raíz congelada,
como sonda efímera; no forma parte de los tests funcionales ni crea infraestructura.
Sólo usa ficheros temporales del ReplayStore ya existente.

```python
import multiprocessing as mp, tempfile
from pathlib import Path
from src.adapters.replay_store_file import FileReplayStore
from src.domain.outcomes import Admitted
from src.domain.start_outcomes import Started
from tests.unit.helpers_m2 import FakeProcessHost, distinct_start_request, make_start_service
def worker(directory, barrier, queue):
    store = FileReplayStore(Path(directory))
    host = FakeProcessHost()
    svc = make_start_service(store=store, host=host)
    req = distinct_start_request(9001)
    issued = svc._admission.admit(req.action_request_wire)
    assert isinstance(issued, Admitted) and issued.admitted_action == req.admitted_action
    barrier.wait(20)
    out = svc.start(req)
    digest = host.spawns[0][0].identity_digest if host.spawns else None
    if isinstance(out, Started): host.deliver_absence(out.handle_ref)
    queue.put((type(out).__name__, len(host.spawns), getattr(out, "safe_detail", None), digest))
    store.close()
ctx = mp.get_context("fork")
for cycle in range(5):
    with tempfile.TemporaryDirectory(prefix="ektel-g05-") as directory:
        queue = ctx.Queue()
        barrier = ctx.Barrier(8)
        children = [ctx.Process(target=worker, args=(directory, barrier, queue)) for _ in range(8)]
        for child in children: child.start()
        outcomes = [queue.get(timeout=30) for _ in children]
        for child in children:
            child.join(20)
            assert child.exitcode == 0, child.exitcode
        assert sum(x[0] == "Started" for x in outcomes) == 1, outcomes
        assert sum(x[1] for x in outcomes) == 1, outcomes
        assert all(x[0] == "Started" or (x[0] == "StartFailed" and x[2] == "cas:already_spent") for x in outcomes), outcomes
        digest = next(x[3] for x in outcomes if x[3] is not None)
        reopened = FileReplayStore(Path(directory))
        assert reopened.start_token_status(digest) == "spent"
        reopened.close()
        queue.close()
        queue.join_thread()
        print("cycle", cycle+1, "8 processes; 1 Started; 1 spawn; 7 cas:already_spent; reopened spent", flush=True)
```
