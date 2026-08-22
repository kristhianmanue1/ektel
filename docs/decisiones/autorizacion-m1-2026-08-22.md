# Acta — autorización de M1

**Fecha:** 2026-08-22.
**Autoridad:** decisión explícita del dueño comunicada por canal (2026-08-22)
y transcrita en la orden
`/private/tmp/ektel-m1-prep-20260822-01/ORDEN-AUTORIZACION-IMPLEMENTACION-M1.md`
(«Orden del dueño — aceptar D-P1..D-P4 y autorizar implementación de M1»),
**ampliada el mismo día por adenda autorizada del dueño**
(`ADDENDA-AUTORIZACION-M1-PINAX-R1.md`), que incorpora el FIX-AND-RETRY de
la ronda adversarial independiente de Pinax R1
(`RONDA-ADVERSARIAL-PINAX-DECISIONES-M1.md`) y **sustituye las formulaciones
ambiguas correspondientes de la orden inicial**; la ronda R2 final
(`RONDA-ADVERSARIAL-PINAX-R2-FINAL.md`) formuló F1–F4; y la **adenda final
autorizada del dueño**
(`ADDENDA-AUTORIZACION-M1-PINAX-R2-FINAL.md`) incorpora íntegramente esa
ronda R2, **levanta las pausas** (F1/F2 pasan a ser sus reglas autorizadas
1 y 2), **autoriza F3/F4** (sus reglas 3 y 4) y **cierra las rondas Pinax**
de decisión M1. M1 sigue autorizado dentro de sus límites; M2/M3,
caracterización y push siguen prohibidos.
Conforme al criterio de adopción de la especificación v1.2, §19 punto 6: cada
hito requiere su propia autorización. Este acta la registra para **M1**.

## Objeto

El dueño acepta las recomendaciones del paquete pre-M1
(`docs/propuestas/paquete-preparacion-m1-2026-08-22.md`, con ronda adversarial
propia cerrada en `docs/revisiones/2026-08-22-pre-m1-adversarial.md`) y
**autoriza la implementación de M1 (admisión)** conforme a ese paquete y a la
especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md` (v1.2, §15
M1), con las condiciones expresas siguientes.

## Condiciones expresas

### Plano (a) — condiciones originales de la orden (transcripción breve)

1. **D-P1 = (a):** coherencia de `stdin_policy.kind` en la capa de admisión
   M1. No reabrir el wire contract M0. **[Sustituida en su formulación por la
   adenda, regla 1 — ver plano (b).]**
2. **D-P2 = (i):** añadir `tout-valid-accepted`, regenerar el corpus y
   re-congelar conteos/fingerprints con todos los gates M0 verdes.
   **[Ampliada por la adenda, regla 4 — ver plano (b).]**
3. **D-P3:** rechazar **NUL** en `command_absolute` y `cwd` en la capa de
   admisión. TAB y `U+0085` permanecen admitidos mientras no haya evidencia
   para prohibirlos; documentar este límite, no presentarlo como omisión.
   **[Sustituida en su formulación por la adenda, regla 2 — ver plano (b).]**
4. **D-P4 = (alpha):** compuerta de spawn instrumental/contabilizada; ningún
   proceso real ni supervisión en M1. **[Precisada por la adenda, regla 5 —
   ver plano (b).]**
5. **Condición adicional:** clave de operador ausente, ilegible o inválida
   debe fallar cerrado y tener gate propio, usando el vocabulario normativo
   existente. Si esto exige un código nuevo o contradice la spec, detenerse y
   volver al dueño; no inventar contrato. **[Perfil fijado por la adenda,
   regla 3 — ver plano (b); la cláusula BLOQ subsiste para lo no decidido.]**

### Plano (b) — texto operativo vigente

El texto operativo vigente es la **adenda R1 (reglas 1–5, transcripción fiel
a continuación)** **más** la **adenda final (reglas 1–4, transcripción fiel
en la sección «Reglas finales autorizadas»)**. Relación explícita entre
ambas: la regla 1 final precisa la regla 3 R1 (clave) en lo de
`key_id`/`deployment_salt`; la regla 2 final fija la precedencia de la regla
1 R1 (stdin) por capa; las reglas 3–4 finales precisan la regla 3 R1 (carga
segura de la clave) y la regla 2 R1 (D-P3, representabilidad).

**Adenda R1 — reglas autorizadas (transcripción fiel):**

1. **D-P1 ampliada — stdin ligado byte a byte a la capacidad**
   - `empty`: sólo `{kind:"empty"}`; bytes efectivos `b""`; digest efectivo
     SHA-256 de bytes vacíos; debe coincidir con
     `action_binding.stdin_policy_digest`.
   - `inline_b64`: exige `data_b64` canónico y `sha256`; se decodifica; el
     campo `sha256` debe coincidir con los bytes decodificados y el mismo
     digest debe coincidir con `action_binding.stdin_policy_digest`.
   - Cualquier discordancia: `malformed_descriptor`, antes de PoP, replay y
     cualquier frontera de inicio.
   - Regla semántica M1; no modificar el schema/wire contract M0.
2. **D-P3 ampliada — representabilidad del futuro execve**
   - Rechazar NUL en `command_absolute`, `cwd`, cada elemento de `args`, y
     nombres/valores de `env_allowlist_values`.
   - Nombre de entorno no vacío y sin `=`.
   - TAB y U+0085 permanecen admitidos y se documentan como límite consciente.
3. **Perfil de clave del operador M1**
   - archivo regular, sin symlink, propiedad del usuario efectivo;
   - modo exacto `0600`;
   - contenido exacto: 32 bytes crudos;
   - carga única al inicializar; sin rotación en caliente en M1;
   - cualquier ausencia, ilegibilidad, tipo, dueño, modo o longitud incorrectos
     impide inicializar el servicio fail-closed;
   - no convertir ese defecto de despliegue en `AdmissionRejected` ni inventar
     `reason_code`.
4. **D-P2 y trazabilidad**
   - Añadir `tout-valid-accepted`, regenerar corpus/conteos/fingerprint y gates.
   - Crear evidencia/manifest nuevos para el artefacto resultante.
   - El doble PROCEED M0 histórico conserva alcance exclusivo sobre su manifest
     original; no reescribir ni sobre-extender ese dossier.
5. **D-P4 — frontera sin M2**
   - Spy/test double exclusivamente de pruebas para demostrar cero cruces ante
     inválidos.
   - Cero `subprocess`, `fork`, `exec`, proceso real, API `start`, ProcessHost o
     supervisión en el runtime de producción M1.

## Reglas finales autorizadas (adenda final, 2026-08-22)

Transcripción fiel de «Reglas finales autorizadas» de la adenda final del
dueño (`ADDENDA-AUTORIZACION-M1-PINAX-R2-FINAL.md`); levantan las pausas F1/F2
(que pasan a ser estas reglas 1 y 2) y autorizan F3/F4 (reglas 3 y 4):

1. **Sal de despliegue y `key_id`**
   - `deployment_salt` es un parámetro de configuración de exactamente 32
     bytes; no es secreto, pero es estable por despliegue.
   - `key_id = sha256(deployment_salt || operator_key).hexdigest()[:16]`, hex
     minúscula.
   - Cambiar clave o sal exige reinicio y reemisión de capacidades.
   - Los vectores históricos conservan su sal literal de prueba y su evidencia
     no se reescribe.
2. **Orden y diagnósticos**
   - incoherencia interna de `stdin_policy` (shape, base64, `sha256` vs bytes)
     → `malformed_descriptor`;
   - canonicalidad/MAC/header/payload/vigencia inválidos de la capacidad →
     `capability_rejected`;
   - tras autenticar la capacidad, cualquier discordancia del descriptor con
     `action_binding`, incluido digest efectivo de stdin →
     `capability_rejected`;
   - después se verifican PoP, replay y política.
3. **Carga segura de clave**
   - abrir con `O_NOFOLLOW`; validar con `fstat` del descriptor abierto;
   - archivo regular, `st_uid == geteuid`, permisos `0o600`;
   - leer exactamente 32 bytes y comprobar EOF;
   - fallo de cualquier condición impide inicializar el servicio;
   - declarar como límite que Python no garantiza zeroization de todas las
     copias en memoria.
4. **Representabilidad de strings de ejecución futura**
   - además de reglas NUL/`=`, aplicar `os.fsencode` a `command_absolute`,
     `cwd`, cada argumento y nombres/valores del entorno;
   - `UnicodeEncodeError` → `malformed_descriptor`;
   - TAB y U+0085 siguen permitidos cuando son representables.

**Cierre de decisión (transcripción de la adenda final):** D-P2 y D-P4
permanecen autorizadas según la adenda R1. No se requieren más rondas Pinax
sobre estas decisiones. Continúa el método fijado por el dueño: adversarial
propia del Ejecutor antes de avances y adversarial propia del Controlador
sólo al cierre integral; mismos dos agentes OpenCode; commits locales
permitidos; sin push.

## Límites de autoridad

**Autorizado** (transcripción de la orden):

- registrar el acto de autorización M1 con las decisiones anteriores;
- implementar únicamente M1 en `src/{domain,application,ports,adapters}`;
- pruebas `unit/contract/integration/adversarial`, fuzz/scripts necesarios;
- D-P2 en generator/corpus/artefactos derivados de `contracts/`;
- CI y configuración de desarrollo necesarias para `mypy --strict`;
- documentación de implementación, rondas y cierre M1;
- commits locales por avance y cierre, gobernados por el Controlador.

**No autorizado** (transcripción íntegra de la orden):

- push, PR, tag, release;
- M2: procesos reales, grupos, supervisión, deadline/kill, salida;
- M3: RuntimeEvent/AuditSink durable;
- x86_64, crash-consistency de dispositivo o RSS por muestreo;
- cambios normativos silenciosos en spec/ADR/wire contracts fuera de D-P2;
- dependencias runtime nuevas (M1 permanece stdlib-only);
- usar memoria o relaciones del ecosistema como autoridad.

El método de trabajo del ciclo (incrementos, gates por avance, adversarial
propia del Ejecutor, auditoría integral del Controlador al cierre) es el
transcrito en la orden; su detalle operativo vive en el dossier del ciclo.

## Estado

**M1 autorizado; implementación no iniciada en este acto.** Este acta
registra la decisión del dueño y sus condiciones; no afirma avance, entrega
ni evidencia de implementación alguna. **M2 y M3 siguen sin autorizar**
(especificación §19.6); la stop rule del ciclo permanece intacta.

## Firma y asiento

- **Decisión:** dueño, por canal (2026-08-22); ampliada por adenda autorizada
  del dueño el mismo día (2026-08-22) y cerrada por adenda final autorizada
  del dueño (2026-08-22).
- **Transcripciones de referencia:** orden del dueño
  (`ORDEN-AUTORIZACION-IMPLEMENTACION-M1.md`), adenda autorizada
  (`ADDENDA-AUTORIZACION-M1-PINAX-R1.md`) y adenda final autorizada
  (`ADDENDA-AUTORIZACION-M1-PINAX-R2-FINAL.md`), todas en el dossier del
  ciclo; origen: rondas adversariales independientes de Pinax R1
  (`RONDA-ADVERSARIAL-PINAX-DECISIONES-M1.md`, FIX-AND-RETRY H1–H5) y R2
  final (`RONDA-ADVERSARIAL-PINAX-R2-FINAL.md`, F1–F4; D-P2/D-P4
  confirmadas), incorporadas por las adendas y cerradas por la final.
- **Asiento documental:** Ejecutor OpenCode (sesión
  `ektel-opencode-ejecutor-pre-m1-01`), por encargo del Controlador
  (`ektel-opencode-controlador-pre-m1-01`), incrementos INC-1, INC-1-R2 e
  INC-1-R3 del protocolo del ciclo M1. El asiento transcribe la decisión; no
  la crea ni la amplía.

## Evidencia de soporte

- Paquete pre-M1: `docs/propuestas/paquete-preparacion-m1-2026-08-22.md`
  (ronda adversarial de seis rondas `PROCEED`:
  `docs/revisiones/2026-08-22-pre-m1-adversarial.md`).
- Especificación v1.2, §15 M1 y §19 punto 6.
- Orden del dueño: `ORDEN-AUTORIZACION-IMPLEMENTACION-M1.md` (2026-08-22).
- Adenda autorizada del dueño: `ADDENDA-AUTORIZACION-M1-PINAX-R1.md`
  (2026-08-22), con origen en `RONDA-ADVERSARIAL-PINAX-DECISIONES-M1.md`
  (ronda R1, H1–H5).
- Adenda final autorizada del dueño:
  `ADDENDA-AUTORIZACION-M1-PINAX-R2-FINAL.md` (2026-08-22); incorpora la
  ronda R2 final (`RONDA-ADVERSARIAL-PINAX-R2-FINAL.md`, F1–F4) y cierra las
  rondas Pinax de decisión M1.
