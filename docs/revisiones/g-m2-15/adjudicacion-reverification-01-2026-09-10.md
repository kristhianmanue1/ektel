# G-M2-15 — adjudicación de re-verificación correctiva 1

## Metadata

| Campo | Valor |
|---|---|
| Acto | Adjudicación de la re-verificación externa del diff correctivo 1 |
| Fecha | 2026-09-10 |
| HEAD de entrada | `abefbeab9be7388c52481c7a769fa4927d8535a7` |
| CORRECTIVE-REVIEW-ROOT | `64409b6efed54973c26034cc593d7ed0c85b4d47` |
| MANIFEST-ROOT post-correctiva | `365c8a685e563611210cf69680f53cc9c7a32522e9ef5647f6f83ed786a9b470` |
| Informe adjudicado | `informe-reverification-correctiva-01-2026-09-10.md` |
| Veredicto recibido | **CORRECTIVE-FIX-AND-RETRY** |
| Naturaleza | Acto exclusivamente documental; no implementa correcciones |

Este acto adjudica CORR-M2-01..03, define la segunda ronda correctiva y
determina su encaje normativo. No modifica los informes originales, la
reconciliación inicial, FIX-M2-R1..R11 ni el informe adjudicado.

## 1. Historia preservada

La re-verificación correctiva 1 queda preservada con estos resultados
históricos, sin reinterpretación retroactiva:

| Obligación histórica | Resultado preservado |
|---|---|
| R1 | **SATISFIED** |
| R2 | **SATISFIED** |
| R3 | **SATISFIED** |
| R4 | **NOT-SATISFIED** |
| R5 | **SATISFIED** |
| R6 | **NOT-SATISFIED** |
| R7 | **SATISFIED** |
| R8 | **SATISFIED** |
| R9 | **SATISFIED** |
| R10 | **SATISFIED** |
| R11 | **SATISFIED** |

Las obligaciones residuales de R4 y R6 se trasladan respectivamente a R13 y
R14. CORR-M2-01, regresión introducida por la primera ronda correctiva, se
traslada a R12. Este traslado no cambia el resultado histórico de R1..R11.

## 2. Adjudicación de findings

### CORR-M2-01 — ACCEPTED-CONFIRMED — P1

**Finding:** pérdida prematura del `ExecutionHandle`.

**Causa raíz:** **acoplamiento incorrecto entre runtime-registry lifetime y
caller-capability lifetime.**

El terminal puede cerrar el proceso, liberar el slot y retirar el registro
operacional del runtime. No puede destruir la única vía por la cual el caller
adquiere la capability que `Started` prometió. La reproducción 500/500 del
informe constituye evidencia ejecutada suficiente para aceptar y confirmar el
finding y su severidad P1.

#### FIX-M2-R12 — Lifetime separation y adquisición durable del `ExecutionHandle`

La segunda ronda debe garantizar conjuntamente:

1. después de devolver `Started`, el caller puede obtener el
   `ExecutionHandle` correspondiente aunque la acción ya haya terminado;
2. una acción terminal inmediata no puede desalojar la capability antes de su
   adquisición;
3. liberar el slot no depende de conservar vivo el registro operacional;
4. conservar la capability o el resultado no mantiene ocupado el slot;
5. el resultado terminal permanece recuperable exactamente una vez conforme
   al contrato;
6. no se reintroducen doble handoff ni doble release corregidos por R2/R3; y
7. no existe crecimiento ilimitado sin una política explícita de lifecycle.

**Criterios de cierre.** Deben existir estados separados y observables para la
operación del runtime, la adquisición de la capability y la propiedad del
resultado. La transición terminal puede limpiar proceso, slot y registro
operacional, pero no la capability pendiente prometida. Toda retención previa a
la adquisición debe tener una política local explícita y acotada. Si la
garantía se preserva mediante una cota de registros, alcanzar la cota debe
producir backpressure o rechazo antes del spawn, nunca eviction de una
capability ya prometida. El cierre debe demostrar ausencia de doble entrega,
doble liberación y crecimiento no acotado.

**Contraejemplo obligatorio.** Repetir terminal inmediato seguido de
`handle_for(ref)` inmediatamente después de `Started`, por un mínimo de 500
iteraciones, con resultado `lost = 0`. Añadir una prueba en la que la acción
termine antes de que `start()` retorne.

### CORR-M2-02 — ACCEPTED-CONFIRMED — P2

**Finding:** depósito terminal todavía invocable por un llamador ordinario.

**Causa raíz:** **la autoridad de depósito está representada por una referencia
ordinaria reutilizable, no por una capability interna no falsificable.**

Las reproducciones de depósito falso, segundo depósito y objeto con datos
copiados confirman que la identidad pública del servicio no constituye una
frontera de autoridad. Se aceptan el finding y su severidad P2.

#### FIX-M2-R13 — Depósito terminal interno no invocable por caller

La segunda ronda debe garantizar conjuntamente:

1. ningún método público del `ExecutionHandle` permite al caller depositar un
   resultado;
2. ningún caller puede fabricar `AwaitedExecution` como terminal autorizado;
3. sólo el coordinador acuñador puede realizar la transición terminal;
4. el objeto depositado está tipado y validado;
5. un objeto copiado o forjado nunca obtiene autoridad por poseer datos
   equivalentes;
6. la autoridad no puede reconstruirse pasando una referencia pública a
   `StartService`;
7. tras el cierre operacional permanece suficiente estado o tombstone para
   impedir reutilización o segunda entrega; y
8. exactamente un resultado terminal puede ser consumido.

**Criterios de cierre.** La operación de depósito no debe formar parte de la
superficie pública del handle. La autoridad debe quedar exclusivamente en
estado privado del coordinador y ser inseparable de la identidad exacta del
objeto/registro acuñado. El tipo terminal se valida antes de la transición. La
linealización depósito-consumo deja un tombstone suficiente para rechazar toda
reutilización, sin volver a ocupar el slot ni crear retención ilimitada.

**Contraejemplos obligatorios.** Repetir depósito falso; depósito falso seguido
de terminal real; objeto distinto con datos/token copiados; segundo consumidor;
y handle legítimo después del cierre del registro operacional. Todos deben
preservar **single terminal ownership**.

### CORR-M2-03 — ACCEPTED-CONFIRMED — P2

**Finding:** la autoridad única de configuración sigue siendo optativa.

**Causa raíz:** **configuration authority split.**

`from_config()` copia correctamente un perfil cuando el integrador decide
usarlo, pero no impide componer Admission, Start y Host con perfiles distintos.
La ejecución reproducida con 2000/1500/500 confirma el finding y su severidad
P2.

#### FIX-M2-R14 — Autoridad única y verificable de configuración M2

La propiedad obligatoria es:

```text
declared configuration == start configuration == applied supervisor configuration
```

La segunda ronda debe garantizar conjuntamente:

1. `M2Config` continúa validada fail-closed;
2. existe una identidad o fingerprint canónica del perfil M2;
3. Admission declara esa identidad;
4. Start exige la identidad correspondiente;
5. ProcessHost/Supervisor expone o acredita la identidad/configuración que
   aplica;
6. toda divergencia falla antes del spawn;
7. `from_config()` puede permanecer, pero no es la única garantía; y
8. la construcción directa de componentes no permite una composición
   incoherente silenciosa.

**Criterios de cierre.** La identidad debe derivarse de la configuración local
validada completa y tener una representación canónica determinista. La
declaración de Admission, la exigencia de Start y la acreditación del Host se
comparan antes del CAS/spawn en toda composición admitida, incluidas las
construcciones directas. Un host que no pueda acreditar el perfil no adquiere
autoridad para ejecutar M2. No basta con observar después qué valor aplicó.

**Contraejemplo obligatorio.** Repetir exactamente:

```text
Admission grace = 2000
Start grace     = 1500
Host grace      = 500
```

El resultado requerido es `rejected before spawn`. Declarar finalmente 500 no
satisface la propiedad si Admission declaró 2000.

## 3. Análisis de gap normativo

### Resultado

| Obligación | Resultado de gap | Fundamento |
|---|---|---|
| R12 | **FIX-WITHIN-AUTHORIZED-M2** | `Started` ya contiene `handle_ref` y ADR-012 autoriza un `ExecutionHandle` local, opaco, ligado al coordinador. Separar el registro operacional del estado de adquisición/resultado es una corrección interna de `StartService`/`ExecutionHandle`. Puede acotarse con política local y backpressure anterior al spawn, sin añadir persistencia ni modificar wire. |
| R13 | **FIX-WITHIN-AUTHORIZED-M2** | La autoridad de terminación y handoff local ya pertenece al coordinador M2. Retirar el depósito de la superficie pública y linealizarlo en estado privado/tombstone interno no requiere capability distribuida, payload, schema ni persistencia nueva. |
| R14 | **FIX-WITHIN-AUTHORIZED-M2** | `M2Config` es configuración local ya autorizada. Su fingerprint y la acreditación obligatoria entre componentes pueden permanecer locales. Admission puede declarar la identidad en su interfaz/estado local M2 y el Host acreditarla antes del spawn, sin añadir campos a los documentos v1 ni alterar los literales congelados de ADR-012. |

**Determinación conjunta:** **R12..R14 = AUTHORIZABLE-WITHIN-M2**.

No se requiere cambiar `Started`, wire, schemas ni contratos congelados; no se
requiere persistencia durable ni una capability cross-host. `Durable` en R12
significa durable respecto del terminal y de la limpieza operacional dentro de
la instancia viva del coordinador; no promete sobrevivir a su reinicio. Una
implementación que necesitara ampliar esa semántica, modificar el wire o añadir
persistencia debe detenerse y declarar `BLOCKED-BY-NORMATIVE-GAP` antes del
cambio.

### Lifetimes que la segunda ronda debe separar

| Lifetime | Comienza | Evento que lo termina |
|---|---|---|
| `process lifetime` | spawn confirmado | terminal real y recolección conforme al supervisor |
| `slot lifetime` | reserva anterior al CAS | terminal/cierre definitivo verificado por la ruta única; o liberación pre-spawn determinada. La indeterminación conserva el slot hasta acto explícito |
| `runtime operational-record lifetime` | registro del spawn confirmado | handoff terminal completo, incluidos output y limpieza operacional |
| `caller capability lifetime` | capability acuñada para el `Started` confirmado | release/consumo por el caller, abandono tras la adquisición o reinicio del coordinador. Antes de adquirirla, la custodia pasa del coordinador al caller mediante `handle_for`; la política local debe acotar el número de capabilities pendientes con backpressure anterior al spawn, nunca mediante eviction de una ya prometida |
| `terminal-result lifetime` | depósito terminal único, después de completar el output | consumo exactamente una vez, release explícito o terminación de la capability conforme a su política declarada |

Estos lifetimes no son intercambiables. En particular, terminal del proceso no
equivale a consumo del resultado; liberar el slot no autoriza destruir la
capability; y conservar capability/resultado no autoriza mantener el slot.

## 4. Gates reabiertos

La reapertura es probatoria: no reescribe su historia, pero exige nueva
evidencia sobre el árbol de la segunda ronda.

| Gate | Obligaciones | Justificación |
|---|---|---|
| **G-M2-01 — revalidación/configuración** | R14 | Debe ampliarse la matriz fail-closed para identidad canónica, ausencia de acreditación y perfiles divergentes antes del spawn. |
| **G-M2-05 — concurrencia/reinicio** | R12, R13 | Los cambios de registros y tombstones afectan carreras, unicidad y semántica tras reinicio; deben conservar un único spawn/ganador y una sola propiedad terminal. |
| **G-M2-06 — crash** | R12, R13 | La nueva frontera post-spawn no puede inventar handles/resultados ni perder la capability prometida en los puntos de fallo ya cubiertos. |
| **G-M2-10 — terminación** | R12, R13 | Es el gate directo de handles válidos/forjados, destrucción, post-resultado, reinicio y carreras terminate/await. |
| **G-M2-11 — recolección/plan** | R14 | `GuaranteePlan` debe declarar el mismo perfil que Start exige y el supervisor acredita/aplica, conservando valores efectivos honestos. |
| **G-M2-12 — capacidad** | R12, R13, R14 | Debe probar slot independiente de capability/resultado, abandono sin registro operacional ilimitado, retención acotada y rechazo pre-spawn de composición incoherente. Se mantiene la enmienda aprobada de sus criterios. |
| **G-M2-14 — regresión** | R12, R13, R14 | Toda la regresión M0/M1/M2, tipos, vectores y fuzz debe permanecer verde después de cambios concurrentes y de configuración. |
| **G-M2-15 — frontera/revisión externa** | R12, R13, R14 | El nuevo diff debe permanecer dentro del alcance y recibir una nueva re-verificación externa conforme antes de proceder. |

Se revisaron expresamente G-M2-01, 05, 10, 12, 14 y 15 solicitados como
mínimo. Se añaden G-M2-06 porque R12/R13 alteran la frontera alrededor de spawn
y ausencia honesta, y G-M2-11 porque R14 afecta literalmente la relación entre
plan declarado y configuración aplicada. No se reabren G-M2-02, 03, 04, 07,
08, 09 ni 13 por su materia propia; siguen sujetos a G-M2-14 y a cualquier
evidencia de regresión que aparezca.

## 5. Criterios conjuntos de cierre de la segunda ronda

R12..R14 sólo pueden proponerse como satisfechas cuando, además de sus pruebas
específicas:

1. los contraejemplos originales y los aquí mandatados pasan sobre la ruta real;
2. la adquisición, el depósito, el consumo y la limpieza tienen puntos de
   linealización explícitos;
3. los cinco lifetimes están implementados y probados por separado;
4. no hay doble handoff, doble resultado, doble release, eviction prematura,
   slot liberado antes del terminal ni retención ilimitada silenciosa;
5. el perfil declarado/exigido/aplicado coincide y 2000/1500/500 se rechaza
   antes del spawn;
6. los gates reabiertos cuentan con evidencia nueva sobre el diff final;
7. la regresión completa y las plataformas se verifican sin convertir falta de
   evidencia en verde; y
8. una re-verificación externa fresca emite el veredicto exigido para G-M2-15.

## 6. Estado resultante

```text
corrective_round_1        = NOT-CONFORMING
reverification_1          = COMPLETE
adjudication_1            = COMPLETE
corrective_round_2        = REQUIRED
R12..R14                  = AUTHORIZABLE-WITHIN-M2
G-M2-15                   = CORRECTIVE-FIX-AND-RETRY
M2                        = OPEN
M3                        = BLOCKED
```

Este acto define obligaciones y confirma su encaje en el alcance; no autoriza
ni implementa R12..R14,
no regenera el MANIFEST-ROOT, no cierra G-M2-15 ni M2 y no inicia M3. El
siguiente acto, separado, podrá autorizar y ejecutar la segunda ronda
correctiva bajo estas obligaciones.
