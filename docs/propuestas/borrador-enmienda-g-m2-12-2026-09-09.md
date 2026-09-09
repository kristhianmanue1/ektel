# BORRADOR — enmienda de criterio del gate G-M2-12

> **NO ES UNA ENMIENDA VIGENTE.** Es un borrador para acto humano. Sin firma,
> **G-M2-12 permanece `PARCIAL — tensión normativa declarada`**. Este documento
> no es una excepción informal, ni un *waiver* silencioso, ni un cambio de
> código, ni una reducción retroactiva de evidencia.

**Fecha:** 2026-09-09.
**Naturaleza:** **enmienda de criterio de gate**.
**Estado de referencia:** `17da65e79a3606b898fa1b4bf451f26a7b122aab`.
**No altera:** implementación, alcance de M2, contratos, schemas ni ADR.

## 1. Por qué el criterio anterior era internamente incompatible

G-M2-12 exige, textualmente, «Tests con límites máximos confirman 8 GiB + 8 MiB
estables y pico de 16 GiB + 8 MiB de payload para 64 acciones».

El mismo paquete de preparación M2 que define ese gate excluye, en **§2.2**,
«tests peligrosos como fork bomb o **presión extrema**» del alcance de M2.

Ejecutar una corrida que materialice **16 GiB + 8 MiB de payload** es, por
definición, una prueba de presión extrema. **El paquete se contradice a sí
mismo**: pide como evidencia de un gate exactamente lo que excluye del alcance
dos secciones antes.

Esto no se descubrió por conveniencia al no poder ejecutarlo. Se descubrió al
intentar cerrarlo: el host de referencia tiene **16 GiB de RAM física**, de modo
que la corrida no habría sido una medición sino un OOM. Pero la incompatibilidad
es **normativa y previa al host**: seguiría existiendo en una máquina con 512 GiB,
porque §2.2 no excluye por falta de memoria sino por clase de prueba.

Por eso corresponde una **enmienda de criterio**, no una excepción: el defecto
está en el criterio, no en la implementación ni en la máquina.

## 2. Criterio propuesto

G-M2-12 se considera satisfecho **únicamente si se demuestran conjuntamente**
los diez puntos siguientes. La conjunción es estricta: fallar uno deja el gate
parcial, y **ninguno se compensa con otro**.

| # | Punto |
|---|---|
| 1 | Fórmula de cota máxima de payload demostrada por **prueba determinista** |
| 2 | **Ausencia de overflow** o comportamiento no definido en los límites permitidos |
| 3 | **Relación lineal** de la fórmula comprobada mediante casos de frontera |
| 4 | Comportamiento **empírico a escala ejecutable y segura** |
| 5 | `max_concurrent_actions` respetado bajo **concurrencia real** |
| 6 | **Ausencia de consumo de token** cuando no existe slot |
| 7 | **Liberación correcta** de capacidad |
| 8 | Comportamiento correcto ante **estado indeterminado** |
| 9 | **Separación explícita** entre cota de payload y RSS observado |
| 10 | **Ausencia de cualquier claim** que presente la fórmula de payload como límite de memoria del proceso |

**La prueba a 16 GiB no será requisito de M2** mientras permanezca vigente la
exclusión de presión extrema de §2.2.

### 2.1 Lenguaje obligatorio

Queda **prohibido** declarar que «se probó 16 GiB». La única formulación
admisible es:

> La cota máxima fue demostrada **analíticamente** y la implementación fue
> comprobada **empíricamente a escala segura**.

Cualquier documento, mensaje de commit o acta que se aparte de esa formulación
contradice esta enmienda.

## 3. Reevaluación de la evidencia existente

Mapeo del criterio propuesto contra la evidencia **ya existente** en
`17da65e`. No se creó evidencia nueva para esta enmienda: si un punto no
estuviera cubierto, correspondería declararlo, no fabricarlo.

| # | Evidencia | Ubicación |
|---|---|---|
| 1 | `test_limites_maximos_para_64_acciones` confirma **exactamente** `8 GiB + 8 MiB` estables y `16 GiB + 8 MiB` de pico; `test_formulas_literales` fija la forma de ambas fórmulas | `tests/unit/test_deadline_math.py` |
| 2 | `payload_bounds` opera sobre `int` de Python, de **precisión arbitraria**: el overflow es imposible por construcción, no por cota. Comprobado al máximo del schema (`67108864` por stream) y, adicionalmente, a `2**62` por stream con resultado exacto y sin envolvimiento | `src/domain/deadline.py`, `test_limites_maximos_para_64_acciones` |
| 3 | Frontera inferior `n=1` (`test_default_de_una_accion`) y superior `n=64` (`test_limites_maximos_para_64_acciones`); la linealidad se comprueba como igualdad `cota(n) == cota(1) * n`, no se asume | `tests/unit/test_deadline_math.py`, `tests/integration/test_capacity_slots.py` |
| 4 | `test_el_payload_retenido_se_ajusta_al_modelo_lineal`: **6 acciones × 256 KiB por stream con procesos reales**, inundando muy por encima del límite; el retenido real cabe en la cota publicada | `tests/integration/test_capacity_slots.py` |
| 5 | `test_carrera_no_excede_la_cota`: **16 hilos concurrentes**, la cota nunca se excede | `tests/integration/test_capacity_slots.py` |
| 6 | `test_falta_de_slot_no_gasta_token`: el token permanece reutilizable tras un rechazo por capacidad | `tests/integration/test_capacity_slots.py` |
| 7 | `test_fallo_pre_spawn_libera_el_slot`, `test_handoff_terminal_libera_el_slot`, `test_handle_abandonado_no_deja_registro_global` | `tests/integration/test_capacity_slots.py` |
| 8 | `test_h5_el_slot_retenido_por_indeterminacion_es_observable` y `test_h5_liberar_es_acto_explicito_y_recupera_capacidad`: el slot retenido es visible y su liberación es **acto explícito del operador**, nunca automática | `tests/integration/test_capacity_slots.py` |
| 9 | `test_las_cotas_no_son_cotas_de_rss`, `test_no_es_una_cota_de_rss` y `CaracterizacionRssTests`, que observa RSS por `/proc` en Linux y `ps` en Darwin y **se salta declarándolo** si no es observable | `tests/integration/test_output_framing.py`, `tests/unit/test_deadline_math.py`, `tests/escape/test_supervisor_characterization.py` |
| 10 | Búsqueda sobre `src/`, `docs/evidencia/` y las rondas adversariales de patrones que presenten payload o cotas como garantía de memoria o RSS acotado: **cero coincidencias**. La separación se declara explícitamente en el adaptador y en la evidencia | verificado por búsqueda el 2026-09-09 |

**Conclusión de la reevaluación:** los diez puntos están cubiertos por evidencia
preexistente. **Esto no promueve el gate**: la promoción exige la firma de §5.

## 4. Estado del gate hasta la firma

```
G-M2-12 = PARCIAL — tensión normativa declarada
```

Tras la firma, y **sólo si la reevaluación confirma los diez puntos**:

```
G-M2-12 = VERDE
```

La reevaluación posterior a la firma debe rehacerse contra el árbol vigente en
ese momento, no darse por hecha desde este borrador.

## 5. Qué falta para que esta enmienda exista

1. **decisión explícita del dueño**, transcrita fielmente;
2. **asiento y firma** con fecha y referencia de canal;
3. asentar el acta en `docs/decisiones/` y registrar el cambio de estado del
   gate en `docs/evidencia/estado-evidencia-m2-2026-09-09.md`.

## 6. Lo que esta enmienda NO hace

- no cambia implementación ni un solo byte de `src/`;
- no amplía el alcance de M2;
- no toca contratos, schemas ni ADR;
- no reduce retroactivamente evidencia ya exigida por otros gates;
- no autoriza M3;
- no sustituye la revisión adversarial externa de G-M2-15.

**Comprobación disponible:** el manifiesto `manifest-m2-sha256.txt` cubre
`src/`, `tests/`, `scripts/` y `contracts/`, pero **no** `docs/`. Que sus
digests permanezcan idénticos antes y después de esta enmienda es prueba
mecánica de que no cambió implementación.
