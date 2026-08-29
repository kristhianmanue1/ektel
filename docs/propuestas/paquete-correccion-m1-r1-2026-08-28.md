# Paquete de corrección M1-R1

**Fecha:** 2026-08-28. **Base auditada:**
`ddf8fa01f7752d12d60add144532c8043fa099f8` (`main == origin/main` al
iniciar). **Naturaleza:** corrección defensiva dentro de M1; no es un nuevo
hito ni una autorización de M2/M3.

## Problema confirmado

La implementación cerrada de M1 aceptaba algunos valores que no pertenecen
al dominio temporal o al contrato del puerto:

- un reloj de pared `NaN` podía eludir una comparación de vigencia;
- `policy_timeout_s=NaN` hacía inoperante el límite post-hoc;
- `collect_expired(inf)` podía eliminar nonces aún vigentes;
- claims autenticados `nbf`/`exp` con enteros no representables como `float`
  podían propagar `OverflowError` en vez de producir rechazo tipado;
- un `Allow` con campos inválidos podía admitirse y una respuesta desconocida
  podía terminar en `AssertionError`;
- una excepción ordinaria del adaptador de política escapaba sin resultado
  tipado.
- una respuesta desconocida del replay store podía caer implícitamente por el
  camino de éxito.

No se atribuye a esos casos una vía remota demostrada: los relojes, la
configuración y el adaptador son dependencias del host. Sí son violaciones
fail-closed en una frontera de seguridad y deben corregirse antes de ampliar
el runtime.

## Corrección aplicada

1. La configuración temporal se valida al construir el servicio: timeout
   finito y positivo; tolerancia finita y no negativa; relojes invocables.
2. Toda lectura de reloj usada por admisión debe ser numérica, finita y no
   booleana. Una lectura inválida produce rechazo seguro y tipado.
3. Las comparaciones de vigencia evitan aritmética `int` arbitrario ↔ `float`;
   toda cota derivada debe permanecer finita. El TTL entregado al store nunca
   puede redondearse antes del `exp` autenticado.
4. El tiempo monotónico no puede retroceder. Un plazo inválido o tardío se
   trata como política no disponible.
5. `PolicyPort` queda como frontera no confiable: excepciones ordinarias,
   tipos desconocidos y respuestas positivas o indeterminadas inválidas se
   convierten en `policy_unavailable` en modo required o degradación explícita
   en optional. Un objeto `Deny` conserva fuerza negativa aunque su
   `decision_id` sea malformado: degradarlo en optional convertiría una señal
   negativa explícita en admisión. Sólo las dataclasses exactas del contrato
   se clasifican como decisión; sus campos se capturan una vez y se valida el
   snapshot antes de construir un recibo.
6. El replay store rechaza configuración/TTL inválidos y
   `collect_expired()` valida el reloj antes de mutar estado.
7. La aplicación sólo continúa si el replay store devuelve exactamente
   `RESERVED`, comparado por identidad de enum; excepción, `UNAVAILABLE` o
   tipo desconocido fallan cerrados sin ejecutar igualdad del adaptador.

## Semántica preservada

- El nonce se reserva antes de consultar política y continúa quemado ante
  fallo, rechazo o excepción del puerto. Es la semántica conservadora de
  ADR-004; esta corrección no introduce reintentos reutilizando identidad.
- El timeout del puerto sigue siendo una comprobación **post-hoc**. No
  interrumpe una llamada bloqueada; aislamiento/cancelación dura exige una
  decisión de adaptador separada y no se implementa aquí.
- Esta corrección define el dominio técnico finito/representable, pero no
  inventa un máximo operativo de skew o timeout. La tolerancia sigue siendo
  configuración declarada del operador conforme a ADR-004; fijar un techo
  normativo requiere una decisión del perfil de despliegue.
- No se añaden primitivas de proceso, `start`, supervisión, `AuditSink`, red,
  wake, publicación ni release.

## Definition of Done ejecutable

- pruebas unitarias de configuración y reloj inválidos;
- claims temporales autenticados enormes sin excepción ni reserva parcial;
- pruebas adversariales para respuestas malformadas, excepción, regresión
  monotónica y segundo reloj de pared inválido;
- pruebas de integración que demuestran no mutación con reloj de
  mantenimiento inválido;
- suite completa, fuzz contractual, fuzz de admisión, regeneración de
  vectores con diff cero y `git diff --check`;
- revisión adversarial fresca del artefacto final.

La evidencia reproducida del cierre original no se reescribe. En particular,
el dossier efímero de G13 ya no está disponible y sus cifras históricas no se
presentan como una medición nueva.
