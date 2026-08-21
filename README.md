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

La especificación M0–M3 v1.2 alcanzó consenso el 2026-08-20
(`docs/decisiones/consenso-especificacion-v1-2-2026-08-20.md`) y M0 quedó
autorizado con alcance cerrado
(`docs/decisiones/autorizacion-m0-2026-08-20.md`). La caracterización de
plataforma ya se ejecutó en Darwin (5 tests + 3 skips Linux-only) y en Linux
(8/8, `docs/evidencia/caracterizacion-linux-2026-08-20.md`). **M0 en curso** (snapshot 2026-08-20): `contracts/` contiene los wire
schemas v1, 90 vectores dorados y dos parsers de referencia (uno clean-room,
R5), corregidos tras la doble NO-GO externa (acta
`docs/decisiones/enmienda-correccion-m0-2026-08-20.md`, ADR-010) y por tres
rondas FIX-AND-RETRY de Pinax (semántica `pattern` Draft 2020-12, campos
cerrados por schema, fuzz diferencial versionado bytes+semántico con oráculo,
bases accept y fingerprint congelado, validación externa estratificada); el
hito NO
se cierra hasta la re-verificación externa. Sigue pendiente la **ampliación**
de la suite de caracterización: durabilidad bajo fallo y RSS por muestreo.
Hasta entonces no se promueven límites de recursos por acuerdo verbal.

La [especificación M0–M3](docs/especificacion/ektel-runtime-m0-m3-v1.md)
gobierna ese primer ciclo; M1 y posteriores no están autorizados.
