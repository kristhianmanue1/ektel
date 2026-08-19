# ADR-006: Lenguaje y plataforma iniciales del runtime M0–M3

**Estado:** borrador para consenso. No adoptado. No autoriza implementación.

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y el
criterio de adopción de la propuesta M0–M3 (§21).

**Contexto normativo:** propuesta §13 (M0 exige ADR de lenguaje y plataforma),
§18 (ADR-006 requerido antes de M1), §20 (decisiones abiertas: lenguaje y
versión mínima, plataforma primaria de M1–M3).

## 1. Decisión propuesta

1. **Lenguaje inicial:** Python 3.12 (versión mínima 3.12), stdlib-only para
   el núcleo de M0–M3. Cero dependencias de terceros en dominio, puertos y
   supervisor.
2. **Plataforma primaria de M1–M3:** Linux aarch64, caracterizado
   únicamente en kernel 6.11.11-linuxkit (VM de Docker Desktop) con Python
   3.12.14. Cualquier otro kernel, distro o entorno de ejecución **no hereda
   garantías** sin re-ejecutar la suite pineada de `tests/escape/`.
3. **Plataforma secundaria:** Darwin arm64, caracterizada en macOS 26.5.2
   (build 25F84) con Python 3.12.12, con tabla de garantías degradada y
   explícita (ver §4). Un cambio de versión mayor de macOS exige
   re-caracterización.
4. **x86_64:** puerta de pre-producción, no de M1–M3. Ninguna afirmación de
   portabilidad x86_64 antes de caracterización en hardware o VM con
   virtualización completa.

## 2. Evidencia

| Evidencia | Resultado | Fuente |
|---|---|---|
| E1/E3 · `RLIMIT_AS` | Aceptado en Linux; rechazado en Darwin | `docs/evidencia/caracterizacion-linux-2026-08-18.md` |
| E2 · reparentado con padre terminado | Sin `PR_SET_CHILD_SUBREAPER` el CPU del nieto huérfano se pierde; con subreaper se recupera vía `wait4`. **Linux-only, sin mitigación conocida en Darwin** | mismo documento; `tests/escape/test_host_characterization.py` |
| Intento x86_64 vía Rosetta 2 | Inconcluso: `rosetta error: mmap_anonymous_rw mmap failed` es artefacto del traductor binario, no evidencia de kernel | mismo documento |
| Suite de caracterización | 7/7 OK en Linux 6.11.11-linuxkit aarch64 (Python 3.12.14, imagen pineada por digest); en macOS 26.5.2 arm64: 4 ejecutadas, 3 omitidas como Linux-only | `scripts/characterize-linux.sh`; corridas 2026-08-18 y 2026-08-19 |
| Arranque del intérprete | 10–20 ms por proceso en macOS 26.5.2 arm64 (5 mediciones, caché caliente, `python -c pass`) | medición local 2026-08-19 |

**Calificador del entorno Linux:** la caracterización corrió dentro de la VM
linuxkit de Docker Desktop, no en bare metal ni en una distro de producción.
Para las primitivas E1–E3 (rlimits, `wait4`, `prctl`) el riesgo de
divergencia es bajo, pero las garantías resultantes son de clase `enforced`
**sólo bajo ese entorno declarado**; kernels con configuración distinta
(p. ej. sin los CONFIG que linuxkit habilita) requieren evidencia propia.

Regla aplicada: la evidencia manda sobre la promesa narrativa (propuesta §2),
y la portabilidad no se infiere por analogía (registro D7a).

## 3. Alternativas consideradas

### A. Python 3.12 stdlib-only (propuesta)

A favor:

- La suite de caracterización E1–E3 ya existe en Python 3.12 y corre verde en
  la plataforma primaria; el lenguaje está validado empíricamente para las
  primitivas que M2 necesita (`fork`, grupos de proceso, `wait4`,
  `prctl` vía `ctypes`, reloj monotónico, señales).
- Parser JSON estricto, HMAC, hashes y firma sobre bytes transportados son
  stdlib pura; nada en M0–M3 exige dependencias externas.
- Cero dependencias reduce la superficie de cadena de suministro, coherente
  con el modelo de amenaza §12 y con el perfil de durabilidad ya usado en el
  proyecto (fsync directo, sin ORM ni frameworks).
- Arranque medido de 10–20 ms por acción supervisada; aceptable para cargas
  de procesos con plazo, inaceptable si un futuro M4+ exige alta frecuencia
  de acciones pequeñas. Criterio de revisión: §6.
- GIL irrelevante aquí: la supervisión es I/O y procesos, no cómputo
  concurrente en memoria.

En contra:

- Sin tipado estático obligatorio; se mitiga con `mypy --strict` en CI como
  herramienta de desarrollo (no del runtime) y contract tests contra
  vectores canónicos (M0). **Nota:** hoy no existe CI en el repositorio;
  esta mitigación es una obligación que M1 debe crear, no un hecho
  consumado.
- Stdlib no incluye validador de JSON Schema: la validación de wire schemas
  en runtime se escribe a mano (riesgo de validadores divergentes entre
  implementaciones) o se genera código. Mitigación: los vectores dorados
  canónicos de M0 son la fuente de verdad compartida y cualquier validador
  se prueba contra ellos; herramientas externas de validación pueden usarse
  en desarrollo sin entrar al runtime.
- `ctypes` (para `prctl`) es FFI dentro de stdlib: rompe parcialmente la
  pureza declarativa y una firma FFI incorrecta puede romper el supervisor.
  Se acepta acotado a llamadas sin punteros (`PR_SET_CHILD_SUBREAPER`) y
  cubierto por las pruebas de caracterización; la alternativa (módulo C
  propio) es una superficie mayor.

### B. Go

A favor: binario estático único, `os/exec` con grupos de proceso,
tipado estático, buen tooling de fuzzing.
En contra: rehace la suite de caracterización (la evidencia existente no se
transfiere); el ecosistema invita a dependencias; ninguna ventaja decisiva
para un supervisor fail-closed de un solo host en M0–M3.

### C. Rust

A favor: garantías de memoria, binario único, tipado fuerte en contratos.
En contra: costo de desarrollo más alto para cuatro hitos acotados; la
supervisión POSIX (`wait4`, `prctl`, señales) requiere `unsafe`/crates de
bajo nivel; rehace la evidencia. Candidato natural de re-evaluación si un
M4+ exige aislamiento fuerte o rendimiento.

## 4. Consecuencias

Positivas:

- M0 puede producir dos parsers de referencia independientes (criterio de
  salida) sin costo de portar la suite de caracterización.
- La matriz de garantías por plataforma nace con evidencia real, no vacía.

Negativas / aceptadas:

- **Darwin queda degradada por diseño:** en macOS, la magnitud
  "contabilidad de CPU multi-nivel" se declara `unsupported` (E2 no tiene
  mitigación conocida) y `RLIMIT_AS` no aplica. La tabla de garantías de M2
  debe reflejarlo como limitación declarada, no como test falsamente verde
  (criterio de salida M2).
- **x86_64 queda explícitamente sin afirmar.** Todo documento público debe
  absternerse de "multiplataforma" sin calificador (coherente con §12.2 de
  la propuesta).
- **Riesgo de plataforma de producción desconocida:** si el despliegue real
  resulta x86_64 (u otro kernel/distro), la evidencia aarch64-linuxkit no
  transfiere y M1–M3 habrían acumulado garantías en el entorno equivocado.
  Mitigación: definir la plataforma de despliegue antes de M2, o aceptar
  una re-caracterización completa como costo conocido.
- Un cambio futuro de lenguaje invalida parte de la evidencia de
  caracterización y exige nueva ronda E1–E3.

Interacción con decisiones vigentes:

- D4 (JSON estricto): stdlib `json` con `parse_constant` y límites
  rechazando NaN/Infinity y campos desconocidos satisface D4 sin
  dependencias.
- D7a (`route_mutable_unverified`): ninguna plataforma de M0–M3 ofrece
  apertura sin ventana TOCTOU dentro del alcance; el perfil de alta
  integridad sigue fuera, sin cambios.

## 5. Ronda adversarial 2026-08-19

Ronda sobre este ADR (no sobre la propuesta completa, que sigue pendiente
según §21.2 de la propuesta). Objeciones incorporadas o refutadas
explícitamente:

| # | Ataque | Resultado |
|---|---|---|
| A1 | "Linux aarch64 (kernel ≥ 6.x)" generalizaba desde un único kernel medido (6.11.11-linuxkit): promesa narrativa sin evidencia, violando la propia regla del ADR. | **Incorporada:** §1.2 ahora pinea kernel/entorno y niega herencia de garantías sin re-ejecución. |
| A2 | "Darwin arm64" no pineaba versión de macOS; la evidencia es macOS 26.5.2 específicamente. | **Incorporada:** §1.3 pinea versión y build, y exige re-caracterización ante cambio mayor. |
| A3 | El "Linux real" de la evidencia es la VM linuxkit de Docker Desktop, no bare metal ni distro de producción; los CONFIG del kernel pueden diferir. | **Incorporada:** calificador de entorno en §2; garantías `enforced` acotadas al entorno declarado. |
| A4 | El costo de arranque "~30–50 ms" era estimación sin fuente. | **Incorporada:** medición real 2026-08-19 (10–20 ms, macOS 26.5.2 arm64) en §2 y §3.A. |
| A5 | Stdlib-only deja la validación de wire schemas sin validador JSON Schema: riesgo de validadores caseros divergentes entre implementaciones. | **Incorporada:** consecuencia explícita en §3.A con mitigación por vectores dorados. |
| A6 | Si la plataforma de producción resulta x86_64, M1–M3 acumulan garantías en la arquitectura equivocada. | **Incorporada:** riesgo elevado a consecuencia explícita en §4 con mitigación (definir despliegue antes de M2). |
| A7 | `ctypes` para `prctl` es FFI: contradice parcialmente "stdlib-only puro" y una firma incorrecta rompe el supervisor. | **Refutada parcialmente:** la llamada requerida no usa punteros; la alternativa (módulo C propio) es superficie mayor. Se acepta `ctypes` acotado y testeado; queda documentado en §3.A. |
| A8 | `mypy --strict` se citaba como mitigación sin que exista CI en el repo. | **Incorporada:** §3.A la declara obligación que M1 debe crear, no hecho consumado. |

Ninguna objeción quedó abierta. La ronda adversarial sobre la **propuesta
M0–M3 completa** sigue pendiente y es requisito de adopción independiente.

## 6. Criterio de revisión

Este ADR debe reabrirse si:

1. aparece evidencia E1–E3 en x86_64 real que contradiga la tabla de
   garantías;
2. un M4+ autorizado exija aislamiento fuerte, multitenancy o rendimiento
   incompatible con Python;
3. la política de cadena de suministro del despliegue objetivo prohíba
   intérpretes en el host;
4. la plataforma de despliegue real se define y difiere del entorno
   caracterizado (kernel, distro o versión mayor de macOS).

## 7. Decisiones que este ADR no toma

- Formato de wire y canonicalización → ADR-002.
- Reloj de referencia para `nbf`/`exp` y replay store → ADR-004.
- Garantía mínima del AuditSink → ADR-007.
