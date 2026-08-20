# ADR-002: Wire format y canonicalización

**Estado:** **aceptado** — Kristhian Manuel Jimenez Sanchez (krisnova@hotmail.com), 2026-08-19. Normativo; aún no autoriza implementación por sí solo (la autorización de M0 es un acto separado, propuesta §21.6).

**Fecha:** 2026-08-19.

**Autor:** propuesta del agente mantenedor; requiere resolución y dueño según
`docs/decisiones/consenso-D1-D7-2026-08-18.md` (regla de autoridad) y el
criterio de adopción de la propuesta M0–M3 (§21).

**Contexto normativo:** propuesta §7 (contratos públicos como wire schemas
neutrales), §7.2 ("el descriptor transportado conserva los bytes necesarios
para verificar la firma sin reserialización ambigua"), §15 (versionado y
compatibilidad), §18 (ADR-002 requerido antes de M1). Decisión vigente D4:
descriptor JSON versionado y estricto, sin YAML ni campos desconocidos no
versionados.

## 1. Decisión propuesta

1. **Wire format v1:** JSON UTF-8, estricto. Se rechazan: NaN/Infinity,
   duplicados de clave, campos desconocidos (salvo extensión versionada
   explícita), tipos coercionados y documentos que excedan los límites de
   tamaño declarados por tipo.
2. **Firma sobre el texto base64 del payload, sin canonicalización
   (estilo JWS):** el sobre v1 tiene estructura fija de nivel superior
   `{payload_b64, signature, alg}`; la firma y el `identity_digest` se
   computan sobre la **cadena de caracteres base64 del payload tal como
   viaja** (los bytes ASCII de `payload_b64`), no sobre los bytes
   decodificados ni sobre el sobre completo. El receptor localiza la firma
   con un parseo superficial que no interpreta el payload, verifica
   **antes** de decodificar y nunca re-serializa para verificar.
   Razón (revisión externa 2026-08-19, F1): firmar los bytes decodificados
   admite maleabilidad del relleno base64 — cuatro sobres distintos byte a
   byte pueden decodificar al mismo payload — y firmar el sobre completo es
   circular. Firmar el texto base64 mata la maleabilidad, conserva
   verificar-antes-de-parsear y no necesita canonicalización. El decodificado
   base64 estricto (`validate=True` o equivalente) se mantiene como defensa
   en profundidad, ya no como pieza portante.
3. **Ningún esquema de canonicalización JSON (JCS u otro) entra en v1.** La
   canonicalización existe sólo como concepto interno de pruebas (vectores
   dorados), no como requisito del productor ni del verificador.
4. **Vectores dorados independientes del lenguaje:** cada wire type v1 tiene
   vectores válidos e inválidos (bytes + digest esperado + diagnóstico
   esperado) que todo parser de referencia debe consumir (criterio de
   salida de M0).
5. **Versionado:** cada wire type lleva `schema_version`; el núcleo rechaza
   versiones mayores desconocidas (propuesta §15).

## 2. Motivación

Toda la clase de problemas de canonicalización JSON (orden de claves,
espacios, normalización Unicode, representación de números) desaparece si la
firma cubre los bytes transportados. El canonicalizador es código confiable
adicional que puede diverger entre implementaciones; en v1 no es necesario
porque el productor es también el firmante y el descriptor viaja como un
solo documento autocontenido (propuesta §5: "descriptor de acción
autocontenido").

## 3. Alternativas consideradas

### A. Firma sobre el texto base64 del payload, estilo JWS (propuesta)

A favor:

- Cero código de canonicalización en la frontera de confianza.
- Verificación previa al parseo: un documento mal formado se rechaza por
  firma inválida o por parseo estricto, nunca se "interpreta" antes de
  verificar.
- Digest reproducible trivialmente en cualquier lenguaje (`sha256` de
  bytes), lo que hace los vectores dorados baratos y portables.

En contra:

- El productor debe conservar y transmitir los bytes exactos que firmó; un
  pipeline que pretty-printe o re-ordene invalida la firma. Es una
  disciplina del productor, documentada como requisito del contrato.
- No permite normalizar entradas semánticamente equivalentes: dos
  serializaciones distintas del mismo contenido son identidades distintas.
  Se acepta: la identidad vincula el descriptor concreto, no una clase de
  equivalencia.

### B. JCS (RFC 8785) u otra canonicalización JSON

A favor: tolera re-serialización intermedia.
En contra: introduce un canonicalizador como código crítico de seguridad en
cada implementación; las divergencias históricas entre implementaciones de
canonicalización son una fuente conocida de bypasses de firma. Rechazada
para v1; re-evaluable sólo si aparece un caso de uso con intermediarios que
re-serialicen.

### C. CBOR / MessagePack / Protobuf

A favor: binarios, tamaños menores, schemas más formales (protobuf).
En contra: contradicen D4 (JSON versionado, ya aceptada por consenso);
reabrir D4 requiere un acto de consenso nuevo, no este ADR.

## 4. Consecuencias

- `ActionRequest v1` viaja como documento único; `metadata_opaque` y la
  firma quedan dentro del mismo sobre bytes firmados.
- El parser estricto de M1 debe rechazar claves duplicadas; en Python
  stdlib esto exige `object_pairs_hook` con detección, no el parseo por
  defecto (que acepta duplicados silenciosamente). Obligación registrada
  para M1.
- Los límites de tamaño por tipo deben declararse en el schema v1; un
  documento que excede el límite se rechaza antes de parsear el cuerpo
  completo.
- Interacción con D7a: el digest del descriptor cubre la cadena base64
  firmada del descriptor, **no** el contenido del ejecutable referido por
  `command_absolute`; la ventana TOCTOU del artefacto sigue siendo riesgo
  reconocido no mitigado (registro D7a), sin cambios.

## 5. Ronda adversarial 2026-08-19

| # | Ataque | Resultado |
|---|---|---|
| A1 | Verificar firma antes de parsear exige que el sobre firme/verifique sin entender el contenido: ¿cómo se localiza la firma sin parsear? | **Incorporada:** el sobre v1 tiene estructura fija de nivel superior (`payload_b64`, `signature`, `alg`) localizable con un parseo superficial que no interpreta el payload. **Corregida por la revisión externa 2026-08-19 (F1):** la firma cubre la cadena base64 del payload tal como viaja (estilo JWS), no los bytes decodificados — la redacción original admitía maleabilidad de relleno base64, verificada en intérprete. |
| A2 | Base64 del payload añade ~33 % de tamaño. | **Refutada:** los descriptores son pequeños (KB) y los límites de tamaño ya están presupuestados; el costo no justifica un sobre binario nuevo. |
| A3 | Rechazo de claves duplicadas depende de cada parser; un parser laxo en otra implementación rompe la equivalencia. | **Incorporada:** los vectores dorados incluyen casos de claves duplicadas y todo parser de referencia debe rechazarlos para cumplir el criterio de salida de M0. |
| A4 | "Sin canonicalización" impide comparar identidades semánticas entre sistemas. | **Refutada:** la identidad de ejecución es del descriptor concreto; la comparación semántica pertenece a analítica fuera del núcleo. |

## 6. Criterio de revisión

Reabrir si:

1. aparece un intermediario legítimo que deba re-serializar el descriptor
   (reintroduciría canonicalización como propuesta separada);
2. un vector dorado resulta ambiguo entre dos parsers de referencia;
3. D4 se reabre por consenso.

## 7. Decisiones que este ADR no toma

- Algoritmo de firma, gestión de claves y confianza → ADR-003.
- Reloj de referencia para `nbf`/`exp` y replay store → ADR-004.
- Formato de recibo y firma del operador → ADR-007.
