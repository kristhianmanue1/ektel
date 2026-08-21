# ADR-010: Canonicalidad de base64url (bits residuales)

**Estado:** **aceptado** — decisión 🔒 firmada por el dueño el 2026-08-20:
**alternativa (a)** — rechazar base64url no canónico: bits residuales en cero,
verificado re-codificando. Firma comunicada en canal del agente tras revisión
y reproducción independiente de H1/H2 por Pinax.

**Origen:** doble NO-GO de las rondas externas de M0
(`/Users/krisnova/www/pinax/rondas/2026-08-20-m0-ektel-externas/sintesis-pinax.md`,
hallazgos bloqueantes 1 y 2 de Claude) e instrucción de corrección de
Pinax (`instruccion-agente-ektel-correccion-m0.md`, punto 1: brief antes que
código). Sometido a ronda adversarial pre-decisión propia (§4).

**Fecha:** 2026-08-20.

**Autor:** propuesta del agente mantenedor; requiere firma 🔒 del dueño.
Regla de gobernanza vigente: toda enmienda posterior al consenso de la v1.2
lleva acta explícita (`consenso-especificacion-v1-2-2026-08-20.md`).

## 1. El defecto, reproducido por este agente (no sólo reportado)

base64url codifica 6 bits por carácter. Cuando la longitud del binario no es
múltiplo exacto, el último carácter transporta **bits residuales** (2 bits
para la firma de 32 bytes: 43 chars × 6 = 258 bits, 256 útiles). RFC 4648 §3.5
exige que esos bits sean cero ("canonical"); decodificadores permisivos —
incluido `urlsafe_b64decode` de Python — los ignoran.

Consecuencia medida sobre `cap-valid-01` (snapshot 2026-08-20, clase L,
reproducción propia):

- **H1 — maleabilidad de firma:** flip de los 2 bits residuales del último
  carácter de `signature` → **ambos parsers aceptan** (`accept/ok`) con el
  **mismo `identity_digest`**
  (`a7ef9807…56cb`). Dos secuencias de bytes wire distintas, misma firma
  decodificada, mismo digest. Un antirreplay que hashee el sobre completo es
  evadible: la misma firma válida existe en 4 formas wire.
- **H2 — identidad como función del encoding:** demostrado a nivel de
  primitiva (payload de 13 bytes: `eyJ4IjoiMTIzNDU2In0` vs `…In3` decodifican
  a los mismos bytes; los digests difieren). Como `identity_digest` se computa
  sobre la **cadena** `phb64 + "." + plb64` (§6.5, correctamente — firmar lo
  que viaja), un emisor puede producir dos sobres igualmente válidos con el
  mismo contenido decodificado y **digests distintos**. El vector dorado
  actual no lo ejercita porque su payload (597 bytes) es múltiplo de 3 y no
  tiene bits residuales.

## 2. Alternativas

### (a) Rechazar base64url no canónico en el parser — **recomendada**

El verificador exige que los bits residuales sean cero en
`protected_header_b64`, `payload_b64` y `signature` (y en todo campo b64url de
los schemas, p. ej. `stdin_policy.data_b64`). Implementación: tras decodificar,
re-codificar y comparar byte a byte con la cadena recibida (`b64u(dec(s)) ==
s`); costo despreciable y local.

- **Consecuencias:** el conjunto de cadenas aceptadas por `(MAC, digest)`
  colapsa a una por contenido; H1 y H2 quedan cerrados por construcción.
  Antirreplay por hash del sobre vuelve a ser sano. Ningún emisor conforme
  (RFC 4648 canónico, como nuestro generador) se ve afectado.
- **Costos:** una regla más en el perfil byte-exacto (C2) y en los dos
  parsers; vectores nuevos (firma con flip residual → `bad_base64`; payload
  re-encodado no canónico con MAC válida → `bad_base64`).
- **Riesgo residual:** ninguno identificado para v1; los emisores no
  canónicos quedan fuera, que es exactamente lo que se quiere.

### (b) Normalizar antes de verificar — **rechazada**

Decodificar y re-codificar canónicamente, y verificar MAC/digest sobre la
forma normalizada.

- **Por qué no:** cambia *qué se firma* — rompe el invariante central de
  ADR-002/§5.2 ("se firma y verifica lo que viaja; nunca re-serializar").
  Introduce una transformación entre recepción y verificación, que es
  exactamente la clase de ambigüedad que C2 vino a eliminar. Si alguna vez
  dos normalizadores difieren, la identidad vuelve a ser inestable.

### (c) Canonicalidad sólo en el digest, no en el wire — **rechazada**

Aceptar cualquier encoding en el wire pero computar `identity_digest` sobre la
forma canónica.

- **Por qué no:** cierra H2 (digest estable) pero **deja H1 abierto**: la
  firma seguiría teniendo 4 formas wire aceptadas y el antirreplay por hash
  del sobre seguiría evadible. Además desdobla la regla (el MAC verifica lo
  viajado, el digest lo normalizado), creando dos nociones de identidad.

## 3. Propuesta

Adoptar **(a)** como enmienda al perfil byte-exacto v1 (C2): la regla
"base64url sin padding" pasa a ser "base64url sin padding **y canónico**
(bits residuales en cero; el receptor lo comprueba re-codificando)".
Texto a enmendar: especificación §5.2 (perfil C2) y, si se firma, esta
decisión se refleja en `contracts/schemas/v1` (patrón o nota), en ambos
parsers y en vectores dorados nuevos (clases: flip residual en `signature`;
payload no canónico con MAC correcta; `data_b64` no canónico).

Compatibilidad: M0 está en `experimental` y los vectores se regeneran; no hay
consumidores que romper. Es cambio de contrato v1 **dentro** del período
experimental autorizado, no envelope v2.

## 4. Ronda adversarial pre-decisión (propia, 2026-08-20)

- **A1 — "¿y si un emisor legado produce no-canónico?"** No existe emisor
  legado: M0 es experimental y ektel aún no tiene consumidores. El generador
  de referencia ya emite canónico (`urlsafe_b64encode` produce bits
  residuales en cero). Costo de la regla: cero migraciones.
- **A2 — "re-codificar para comparar es re-serializar, prohibido por
  §5.2".** No: la prohibición es re-serializar **para verificar el MAC**
  sobre bytes distintos de los viajados. Aquí el MAC y el digest siguen
  computándose sobre la cadena tal como viaja; la re-codificación es sólo un
  test de pertenencia al conjunto canónico, antes de cualquier uso. La
  verificación criptográfica no cambia de entrada.
- **A3 — "¿no basta con el patrón `^[A-Za-z0-9_-]*$`?"** No: el patrón excluye
  `=` pero admite los 4 valores del último carácter con bits residuales
  distintos de cero. La canonicalidad no es expresable por alfabeto; exige la
  comparación de la ronda A2. (Esto es lo que hoy hace aceptable el flip.)
- **A4 — "¿la firma necesita canonicalidad si nunca entra al digest?"** Sí:
  H1 no ataca el digest sino el antirreplay por hash del sobre completo y
  cualquier log/dedup que guarde bytes wire. Además, una regla uniforme
  (todo campo b64url canónico) es más simple de auditar que "canónico salvo
  la firma".
- **A5 — costo de (a) en los parsers:** una función de tres líneas y dos
  clases de vectores nuevas; sin dependencias (stdlib, ADR-006). La opción no
  elegida (b) sería irreversible en espíritu; (a) es relajable en una v2 si
  el mundo exterior lo exigiera (relajar es compatible hacia atrás; endurecer
  después no lo es).

**Retracciones:** ninguna; los cuatro contraargumentos se sostienen tras
verificarlos contra el código y la spec.

## 5. Decisión 🔒

- Dueño: firma comunicada en canal del agente · Fecha: 2026-08-20 ·
  Alternativa elegida: **(a) rechazar base64url no canónico** (bits residuales
  en cero, verificado re-codificando), con reproducción independiente de
  H1/H2 por Pinax antes de la firma.
