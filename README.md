# ektel

**Estado:** preimplementación. Este README documenta intención corregida por
revisión adversarial, no una implementación ni garantías ya disponibles.

## Qué se pretende

Un runtime que separa del proceso ejecutado la admisión, la supervisión y el
brazo de terminación. Cada garantía debe declarar su fuerza y plataforma; no
se asume que todas sean límites duros.

El diseño investiga tres responsabilidades distintas:

- **Admisión autorizada:** descriptor y capacidad expirable validados antes de
  iniciar.
- **Ejecución restringida:** sólo para recursos que la plataforma realmente
  pueda imponer; una medición reactiva no se presenta como límite duro.
- **Resolución observada:** un supervisor vivo deja de esperar tras el plazo y
  dirige la terminación del grupo observado, sin prometer scheduler de tiempo
  real, muerte de procesos escapados ni reparación externa.

La evidencia actual en macOS refutó `RLIMIT_AS` como límite de memoria y
`RLIMIT_CPU` como freno no cooperativo. CPU/RSS por muestreo siguen siendo
observación best-effort con fallos silenciosos posibles. Tokens y costo sólo
son gobernables para llamadas que atraviesan una frontera mediada. La tabla y
las decisiones candidatas viven en
[`docs/consolidacion-para-consenso-2026-08-14.md`](docs/consolidacion-para-consenso-2026-08-14.md).

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
- No gobierna el éxito de negocio. La capacidad declara qué identidad de
  ejecución puede admitirse; el alcance efectivo depende de mecanismos que se
  especifican por separado.

## Siguiente paso

Llevar el candidato documental a consenso sobre alcance G0-first, capacidad
raíz, descriptor y estados. La caracterización autorizada ya cubre cuatro
casos seguros en Darwin; falta ejecutarla y ampliarla en Linux. Hasta entonces
no se promueven límites de recursos por acuerdo verbal.

La [propuesta de arquitectura M0–M3](docs/propuestas/propuesta-runtime-minimo-m0-m3-2026-08-17.md)
organiza ese posible primer ciclo sin autorizar todavía su implementación.
