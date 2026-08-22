# Propuesta de intercambio documental: escrubery ⇄ ektel

**Estado:** no vinculante — espera consenso del dueño y queda pendiente de
cualquier adopción posterior. **Fecha:** 2026-08-22, fecha de origen declarada
por escrubery para esta propuesta y su censo; corregida en ektel el
2026-08-21 por orden del dueño (el nombre de archivo conserva la fecha de
origen).
**Autoría:** redactada por agente (opencode/GLM-5.2, sesión del Mediador de
escrubery), revisada por el Mediador; corregida en ektel por el Ejecutor
autorizado del dueño (orden «persistir propuesta escrubery ⇄ ektel»).
**Declaración de independencia:** escrubery y ektel comparten dueño (el
Mediador humano); el consenso aquí pedido no es entre partes independientes.
**Alcance de este acto:** intercambio documental propuesto (cita informativa
unilateral de ektel hacia escrubery y un aporte de vocabulario ofertado
unilateralmente). No modifica especificación, ADRs, contratos ni claims de
ektel. Se somete a ronda adversarial de ektel si se admite.

## 0. Autorización y procedencia

El dueño/orquestador humano autorizó este acto: dio a un agente de escrubery
acceso de lectura a ektel y permiso para dejar esta propuesta, porque los
proyectos del ecosistema deben empezar a conocer a sus pares. División de
roles declarada por el dueño: AN-KLA aporta continuidad/memoria; Skopos
observación/lectura; escrubery caracterización de mecanismos CLI; ektel
control de acciones; Pinax cataloga relaciones declaradas. Conocer a un par
**no crea autoridad, dependencia, adopción ni equivalencia de garantías**
entre los repositorios.

## 1. Quién propone y qué aporta

[escrubery](https://github.com/kristhianmanue1/escrubery) es un servicio de
inteligencia sobre CLIs y modelos de IA. Es un **repositorio privado y
versionado**, accesible a participantes autorizados del ecosistema; no a
terceros anónimos. Con fecha declarada 2026-08-22 registró su primer **censo
Harness–Runtime Assurance** ([permalink al commit 6ce8efa](https://github.com/kristhianmanue1/escrubery/blob/6ce8efa/docs/investigacion/hra/reporte-censo-2026-08-22.md)),
conservado aquí como referencia versionada: el permalink identifica la
versión exacta citada y no afirma acceso público. Según el propio reporte de
escrubery —cifras declaradas por esa parte, no verificables desde ektel por
ser repositorio privado—, el censo cubre 5 CLIs principales × 8 normas; cada
celda clasificada con evidencia citable (URL+fecha, con hash cuando la fuente
es estable) o marcada `pendiente` (fail-closed), con Fase 1 en 20 de 40
celdas con evidencia y 20 pendientes. El método está documentado en ese
repositorio, según escrubery, y es reproducible por participantes autorizados
(verificador fail-closed incluido); no se afirma que sea público para
lectores externos.

Nota: en la taxonomía de escrubery, el token «N9» es un gate modificador —
capa el peldaño máximo de una fila — no una primitiva de frontera. Ese token
pertenece a la taxonomía de escrubery y no guarda relación con el no-claim
N9 del registro `docs/claims-y-no-claims.md` de ektel (no emisión ni aval de
conformidad CAGF); la coincidencia de forma es casual.

## 2. Mapeo G0–G5 ⇄ L1–L4 (analogía informativa, no normativa)

El vocabulario normativo de ektel es el de la [especificación M0–M3
v1.2](../especificacion/ektel-runtime-m0-m3-v1.md) (§9) y sus claims
consensuados: exclusivamente `enforced/reactive/observed/unsupported`. Los
términos G0–G5, el eje F-R/F-S/F-M y los estados de leyenda de esa
consolidación (P/V/N/D/I y variantes) proceden de la
[consolidación 0.3](../consolidacion-para-consenso-2026-08-14.md) —candidata
y no vinculante— y se usan aquí sólo como **analogías informativas** de esa
consolidación; ninguna fila de este mapeo constituye equivalencia de
garantías ni sustituye al vocabulario normativo. G mide compuertas de
admisión/ejecución en un supervisor de procesos; L mide dónde vive una norma
en la pila agéntica.

| ektel (consolidación 0.3 §2; analogía informativa) | escrubery (taxonomía L1–L4) | Nota de mapeo |
|---|---|---|
| G0 admisión (fail-closed antes de iniciar) | L4 enforzada | criterio afín: determinista, fuera del modelo. G0 enforza la autorización del descriptor; ektel no confina fs/red (no-claim N2 de ektel). Estado ektel: P (propuesta, leyenda 0.3) |
| G1 límite preventivo en la frontera | L4 | sujeto a los límites documentados del mecanismo |
| G2 reactivo con sobreconsumo acotado | sin peldaño exacto | G2 observa **y termina** (contención reactiva acotada); L3 solo detecta. La escala L no tiene peldaño para contención reactiva — mismo tipo de hueco que el eje F (§3) |
| G3a transición eventual | sin peldaño exacto | L3 exige registro no suprimible; la latencia de G3a no tiene cota dura |
| G3b observación best-effort | sin peldaño exacto | G3b puede perder eventos; L3 los exige persistentes |
| G4 servicio mediado | sin peldaño directo | la escala L no mide mediación de servicio; G4 es diseño de frontera, no peldaño |
| G5 declaración | L1 declarada | — |

**Qué podría aportar a ektel:** el censo inventarió mecanismos de frontera
de 5 CLIs (sandbox de SO, deny-lists pre-ejecución, gate N9 de su taxonomía)
con evidencia por mecanismo, según escrubery, consultable por participantes
autorizados del ecosistema. Para decisiones sobre qué envolver (G4), podría
servir como referencia con procedencia. No afirmamos que resuelva las
necesidades de ektel.

## 3. Aporte ofertado por ektel hacia escrubery: el eje F-R/F-S (oferta unilateral)

La escala L1–L4 de escrubery no distingue **modo de fallo**: un mecanismo
que falla ruidosamente (F-R) es cualitativamente distinto de uno que falla
en silencio (F-S, o mixto F-M). Esta sección es una **oferta unilateral de
ektel hacia escrubery** — poner a disposición de su corpus v1 el eje F
completo (F-R/F-S/F-M), vocabulario originado en la consolidación 0.3 de
ektel (candidata, no vinculante). No registra adopción, crédito ni acto
bilateral alguno: cualquier registro recíproco (cita cruzada, acta de
crédito) queda diferido hasta que escrubery documente su propia adopción en
su repositorio; sólo entonces podrá documentarse en ambos repos con
evidencia recíproca. El hallazgo del propio mapeo acompaña la oferta: la
contención reactiva de G2 tampoco tiene peldaño en L — ambos vocabularios
presentan un hueco análogo, sin que exista aún acto de intercambio alguno.

## 4. El nicho que esta propuesta NO ocupa (no-competencia)

En conversaciones de diseño (aún no documentadas en el corpus de escrubery)
se ha considerado un posible "wrapper de agente conversacional": inyección
de memoria al arranque, medición de tokens sosteniendo la credencial,
composición de los mecanismos que el censo inventarió. **Eso no es ektel y
no pretende serlo.** ektel se propone gobernar acciones discretas bajo
restricción, con identidad autenticada (MAC, HMAC-SHA256 — C2); la
supervisión bajo restricción es materia de M1–M3, hoy sin autorizar. El
wrapper envolvería el bucle conversacional de un CLI. Son fronteras
distintas. Si ambos existieran algún día, el wrapper podría delegar la
ejecución de acciones a ektel — diseño futuro, no compromiso.

## 5. Preguntas para el consenso

1. ¿Acepta ektel el mapeo §2 como cita informativa unilateral de ektel hacia
   escrubery (no normativa)?
   El vocabulario canónico queda fijado de antemano: el de la especificación
   v1.2 (`enforced/reactive/observed/unsupported`); G0–G5 y F-R/F-S/F-M se
   leerían sólo como analogías de la consolidación 0.3 candidata.
2. ¿Desea ektel dejar constancia de la oferta unilateral del eje F (§3)?
   Todo crédito o acto bilateral queda diferido hasta que escrubery registre
   su propia adopción con evidencia recíproca.
3. ¿Le sirve que una futura ficha `assurance/ektel` (cuando M1–M3 tenga
   suites y estados V de la leyenda 0.3) use la escala L con el eje F? En
   todo caso, la ficha sería registro informativo y no desplazaría al
   vocabulario normativo de la v1.2; su elaboración queda condicionada a la
   autorización separada de M1–M3, hoy inexistente. Nota de encaje: la escala
   se diseñó para harnesses con un modelo dentro; para ektel, el "modelo"
   sería el llamador — la ficha declararía ese ajuste.

## 6. No-claims de esta propuesta

- No afirma que ektel adopte nada; solo ofrece el intercambio.
- No afirma adopción, crédito ni acto bilateral sobre el eje F: §3 es una
  oferta unilateral que sólo escrubery podrá consumar registrando su propia
  adopción; hasta entonces no hay reciprocidad que documentar.
- No representa compromiso de escrubery de construir el wrapper (§4).
- No propone modificar especificación, ADRs, contratos ni claims de ektel.
- No activa M1, M2 ni M3: siguen sin autorizar; toda mención a M1–M3 es
  condicional.
- No crea dependencia, autoridad, adopción ni equivalencia de garantías
  entre escrubery y ektel; conocer a un par (§0) no genera vínculo
  normativo alguno.
- El mapeo §2 es analogía informativa; G0–G5, F-R/F-S/F-M y los estados de
  la leyenda (P/V/N/D/I) pertenecen a la consolidación 0.3 candidata y no
  sustituyen al vocabulario normativo de la especificación v1.2.
