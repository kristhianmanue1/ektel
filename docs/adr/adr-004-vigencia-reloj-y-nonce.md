# ADR-004: Semántica de vigencia, reloj y nonce

**Estado:** borrador para consenso. No adoptado. No autoriza implementación.

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y el
criterio de adopción de la propuesta M0–M3 (§21).

**Contexto normativo:** propuesta §6.2 (admisión: firma, confianza, vigencia,
PoP, nonce/replay), §6.3 (reloj monotónico del supervisor), §18 (ADR-004
requerido antes de M1), §20 (decisión abierta: alcance y persistencia del
replay store). Decisiones vigentes: D2 (capacidad raíz expirable, no
delegable) y D3 (plazo efectivo truncado a `exp`).

## 1. Decisión propuesta

1. **Dos relojes con roles separados:**
   - **Reloj de pared (wall clock)** del host: única referencia para
     validar `nbf`/`exp` de la capacidad en admisión, porque la vigencia es
     una afirmación sobre tiempo civil compartida con el emisor.
   - **Reloj monotónico**: única referencia para plazos de supervisión,
     duraciones y precedencia deadline/presupuesto (propuesta §6.3); nunca
     se usa para interpretar claims de vigencia.
2. **Truncamiento (D3):** el plazo efectivo de ejecución es
   `min(deadline_solicitado, exp - now_wall)`; si `exp <= now_wall` la
   admisión rechaza como capacidad expirada. Una capacidad que expira
   durante la ejecución **no** interrumpe la ejecución en M0–M3; el
   resultado registra la vigencia al admitir y la transición se reporta
   como evento. (La interrupción a mitad de ejecución queda fuera: exige
   revocación activa, excluida por D6.)
3. **Tolerancia de skew declarada:** la validación de `nbf`/`exp` admite
   una tolerancia fija de despliegue (propuesta inicial: 30 s), registrada
   en el `GuaranteePlan`/evento de admisión. Supuesto declarado: el reloj
   de pared del host está disciplinado (NTP) y un administrador del host
   está fuera del modelo de amenaza (propuesta §12.2).
4. **Replay store durable y obligatorio:** los nonces consumidos se
   persisten antes de admitir (append con fsync de archivo y directorio,
   perfil `posix-fsync-dir/v1`, el mismo que ya usa AN-KLA en este
   repositorio). El store **sobrevive reinicios** del runtime; un nonce
   permanece reservado hasta `exp + tolerancia` de su capacidad.
   Semántica de reinicio: tras reiniciar, el store cargado sigue rechazando
   replays; no hay ventana de replay por reinicio.
5. **Fail-closed:** si el replay store no está disponible o no puede
   persistir, la admisión rechaza. No existe modo en memoria en despliegue;
   un store en memoria sólo se permite en pruebas.
6. **Ámbito del nonce:** único por `(emisor de capacidad, nonce)` dentro del
   despliegue; la colisión entre emisores distintos no es replay.

## 2. Motivación

D2 y D3 quedan formalmente cumplidas pero operativamente huecas si el replay
store es volátil: un reinicio del supervisor habilitaría replay de nonces
válidos, contradiciendo el modelo de amenaza de la propuesta (§12.1,
"replay dentro del ámbito de nonce"). La durabilidad del store es la pieza
que convierte D2/D3 en garantía real.

## 3. Alternativas consideradas

### A. Store durable con fsync + truncamiento a `exp` (propuesta)

A favor: cierra la ventana de replay por reinicio; coherente con el perfil
de durabilidad ya adoptado por el proyecto; semántica simple de auditar.
En contra: un fsync por admisión añade latencia (milisegundos en discos
locales; irrelevante frente al arranque de un proceso supervisado, medido
en 10–20 ms sólo de intérprete).

### B. Store en memoria + ventana temporal acotada

A favor: sin I/O en admisión.
En contra: **rechazada** — deja ventana de replay tras cada reinicio; para
cerrarla habría que rechazar toda capacidad emitida antes del arranque, lo
que rompe disponibilidad sin ganar seguridad real.

### C. Validación de vigencia contra reloj monotónico anclado

A favor: inmune a saltos de NTP durante la ejecución.
En contra: **rechazada como referencia de claims** — `nbf`/`exp` son
afirmaciones de tiempo civil del emisor; un reloj monotónico local no puede
interpretarlas. Se usa monotónico para lo que sí gobierna (plazos internos)
y se declara el supuesto de reloj disciplinado.

### D. Interrupción de la ejecución al expirar la capacidad

En contra: **aplazada** — exige revocación activa y semántica de
terminación por vigencia, fuera de M0–M3 (D6). El resultado declara la
vigencia al admitir; la expiración durante ejecución se registra como
evento observable, no como compuerta.

## 4. Consecuencias

- La admisión tiene una escritura durable síncrona en su camino crítico;
  M1 debe medirla y declararla en métricas (latencia de admisión,
  propuesta §16).
- El store necesita compactación o rotación por TTL (`exp + tolerancia`);
  sin ella crece sin límite. Obligación registrada para M1: recolección de
  nonces expirados.
- La tolerancia de skew es un parámetro de despliegue versionado, no una
  constante escondida; cambios de tolerancia no cambian el contrato v1.
- Un atacante con control del host puede manipular el reloj de pared: ya
  está fuera del modelo de amenaza (§12.2), pero la documentación pública
  debe nombrarlo como supuesto, no como garantía.

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | "Sin ventana de replay por reinicio" depende de que el fsync realmente preceda a la admisión; un crash entre persistir nonce y emitir decisión deja nonce consumido sin ejecución (denegación de servicio para ese nonce). | **Incorporada:** se acepta como comportamiento fail-closed deliberado: ante ambigüedad se prefiere falso replay rechazado sobre replay admitido; el emisor puede re-emitir con nonce nuevo. Documentado en §1.4. |
| A2 | Un emisor malicioso puede agotar el store con nonces de capacidades de larga vigencia. | **Incorporada:** M1 declara límite de tamaño del store y la admisión rechaza fail-closed al alcanzarlo; la mitigación fina (cuotas por emisor) queda fuera de M0–M3 como riesgo conocido de disponibilidad local. |
| A3 | La tolerancia de 30 s es un número sin evidencia. | **Incorporada parcialmente:** se declara valor inicial de despliegue ajustable y versionado, no verdad de plataforma; la evidencia de skew real del despliegue es tarea operativa posterior. |
| A4 | La expiración durante ejecución sin interrupción permite que una acción "sigua autorizada" con capacidad muerta. | **Refutada:** es la semántica exacta que D3 consensuó (truncamiento en admisión, no revocación); el resultado declara la vigencia al admitir y la traza registra la expiración. Cambiarlo exige reabrir D3 por consenso. |

## 6. Criterio de revisión

Reabrir si:

1. el despliegue real demuestra skew de reloj mayor que la tolerancia
   declarada;
2. se autoriza revocación activa o delegación de capacidades (M4+), lo que
   reabre D2/D3;
3. la latencia de fsync en el camino de admisión resulta incompatible con
   la carga objetivo medida.

## 7. Decisiones que este ADR no toma

- Algoritmo de firma y proof-of-possession → ADR-003.
- Estados terminales y precedencia completa → ADR-005.
- Durabilidad y recibos del AuditSink (distinto del replay store) → ADR-007.
