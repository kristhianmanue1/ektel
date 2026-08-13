# ektel

**Estado:** sin código todavía. Este README documenta intención, no
implementación.

## Qué se pretende

El runtime de ejecución del ecosistema: el componente que corre acciones de
agentes de IA bajo compuertas mecánicas, no bajo confianza declarativa.

Un runtime necesita imponer, en el momento de la ejecución —no antes, no
después—:

- **Presupuesto acotado** (tokens, tiempo, costo) por acción o por tarea.
- **Capacidad expirable**: la autorización para actuar tiene ventana de
  validez y profundidad de delegación, validada en el punto de entrada.
- **Plazo de resolución**: toda acción termina —ejecutada o descartada— dentro
  de un tiempo declarado; no hay tareas que queden indefinidamente en el aire.

Estas tres son las únicas obligaciones que un runtime puede cumplir de forma
mecánica y verificable, sin depender de que el agente coopere. El resto de
gobernanza del ecosistema —qué puede hacer, con qué evidencia se acepta su
resultado— es de otros proyectos (Epistates, Praxis Dev); `ektel` sólo
ejecuta bajo las tres compuertas de arriba.

## Por qué el nombre

Del griego ἐκτελέω — llevar a cabo, ejecutar, completar. En griego moderno,
εκτέλεση es literalmente la palabra técnica para "ejecución" en informática:
correr un programa.

Se descartó **Chronos** (y su forma abreviada, mal formada, "Chronus"): nombra
sólo una de las tres compuertas —el tiempo— y colisiona con proyectos ya
existentes en el dominio de scheduling (Chronos de Mesos, entre otros).
`ektel` nombra lo que el componente **hace** —ejecutar bajo restricción—, no
una sola de las magnitudes que restringe.

## Relación con el resto del ecosistema

- Consume `task-card/v1` de Epistates como entrada.
- El canal de interrupción (A0) hoy es manual —la terminal de quien lo opera—
  hasta que exista `propylon` como dominio de ingreso independiente.
- No gobierna qué está permitido hacer; eso lo declara quien despacha la
  tarea. `ektel` sólo garantiza que, una vez despachada, no se salga de sus
  tres límites.

## Siguiente paso

Un esqueleto mínimo que ejecute una acción real bajo las tres compuertas,
antes que cualquier documento de diseño adicional.
