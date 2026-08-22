# Acta — estado post-M1: gates, decisiones asentadas y bloqueo de cierre

**Fecha:** 2026-08-22. **Autoridad:** orden de implementación M1
(`autorizacion-m1-2026-08-22.md` + adendas R1 y final); el encargo INC-5
autoriza «documentación de implementación, rondas y cierre M1».

**Estado honesto al cierre del ciclo: M1 implementado y CERRADO** (acta
`cierre-m1-2026-08-22.md`; bloqueo G15-Linux resuelto — ver actualización).
Sin push. La auditoría adversarial integral del Controlador sobre el rango
M1 precede al commit de cierre (método de la orden).

> **ACTUALIZACIÓN (2026-08-22, orden G15-Docker):** el bloqueo G15-Linux
> quedó **RESUELTO** con la evidencia
> `docs/evidencia/g15-linux-aarch64-m1-2026-08-22.md`; el cierre fue
> registrado en `docs/decisiones/cierre-m1-2026-08-22.md`. El texto
> original del bloqueo se conserva abajo como historia.

## Gates G1–G16 (evidencia por gate)

| Gate | Evidencia (test/gate, conteos) | Estado |
|---|---|---|
| G1 suite negativa | `tests/contract/test_golden_vectors.py`: corpus **91/19 accept** contra AMBOS parsers (veredicto+diagnóstico+digest exactos); capa de admisión: `tests/unit/test_admit_pipeline.py` (rechazos §8.3 por entrada inválida) | VERDE (clase L) |
| G2 prohibición de spawn | `tests/adversarial/test_policy_spawn_frontier.py`: zoo congelado de 14 inválidos → **0 cruces** (spy D-P4-α); `tests/adversarial/test_fuzz_admision.py::test_g2_cero_cruces_tras_fuzz` | VERDE |
| G3 orden/precedencia | `test_admit_pipeline.py`: dobles causas (stdin+MAC rota→malformed; MAC+expirada→cripto; binding+PoP rota→binding; replay+Deny→replay) — regla 2 final | VERDE |
| G4 negativos cripto | `tests/unit/test_capability_pop.py` (MAC rota, alias ADR-010 con bits residuales, exp≤nbf, expirada/no-vigente con skew, key_id inactivo, PoP rota/digest/nonce) + capa de contrato del corpus (signature≠43, alg, typ, schema_version — 6 grupos) | VERDE |
| G5 identidad determinista | digests del corpus (91) reproducidos por ambos parsers; `test_crypto_keyid.py` (fórmula §6.5; key_id cruzado con `index.json`) | VERDE |
| G6 dependencia caída | `tests/integration/test_replay_store_file.py`: corrupto-arranque→excepción propia; corrupto-posterior/fsync fallido/lleno (con vivos)/cerrado → `AdmissionRejected capability_rejected retryable`, nunca `Admitted` | VERDE |
| G7 política | `tests/adversarial/test_policy_spawn_frontier.py`: required×{nulo, Deny, Indeterminate, Allow expirado, tardío}→rechazo; Allow válido→recibo; optional→`policy_degraded` declarada; A2 bloqueada por tipo (no-vacuo, demostrado) | VERDE |
| G8 fuzz admisión | `scripts/fuzz_admision.py` + `tests/adversarial/test_fuzz_admision.py`: **2 bases, 63 mutaciones, 21 clases, 0 fallos de oráculo, 0 crashes, 0 errores de base**; fingerprint bases `795c3a96…e8ee3`; SENSIBILIDAD demostrada (divergencia artificial, ERROR COMÚN, crash — el gate los detecta) | VERDE |
| G9 regresión M0 | suite completa **130 OK / 3 skips**; regeneración de vectores **diff cero**; fuzz de contrato congelado: bytes **91/1547/0**, semántico **19/172/0/0/0**, fingerprint corpus `0d4d11fe…7ede7` | VERDE |
| G10 claves duplicadas | ADR-002 vía parser importado (object_pairs_hook); `test_admit_pipeline::test_descriptor_clave_duplicada` → `malformed_descriptor` con `duplicate_key` en safe_detail | VERDE |
| G11 TTL/límite | `test_replay_store_file`: `collect_expired` explícito + recolección oportunista antes del límite; `max_nonces` (A2) → UNAVAILABLE sin expulsar vivos | VERDE |
| G12 CI mypy | `.github/workflows/ci-m1.yml` (mypy --strict + suite + regen + ambos fuzz) y `mypy.ini`; `python3 -m mypy --strict src/` → **limpio, 22 archivos**. Nota honesta: sin push el pipeline no corre; existe y es ejecutable local (ADR-006 A8) | VERDE (artefacto) |
| G13 latencia | `scripts/medir_latencia_admision.py` (n=200, reloj monotónico, store durable real con fsync por admisión, Darwin arm64/APFS, clase L): **min 3.48 ms · p50 6.70 ms · p95 8.05 ms · max 14.65 ms** — la escritura durable síncrona es visible por diseño (ADR-004). Evidencia: dossier efímero `g13-latencia.json` | MEDIDA (L) |
| G14 skew versionado | `Admitted.skew_tolerance_s` (vehículo M1 en el resultado; el evento es M3); valor por defecto **30 s** (§7.3, ADR-004 A3), parámetro de despliegue | VERDE |
| G15 plataforma | **Darwin arm64 (macOS 26.5.2 build 25F84, Python 3.12.12): suite completa ejecutada, clase L.** **Linux aarch64 (2026-08-22, orden G15-Docker): RESUELTO** — contenedor Debian 12/Python 3.12.14, imagen por digest, 130 OK/0 skips con Linux-only ejercitadas (`docs/evidencia/g15-linux-aarch64-m1-2026-08-22.md`), clase V | **VERDE (L+V)** |
| G16 reinicio del store | `test_replay_store_file::test_g16_*` (4 pruebas): instancia NUEVA contra el mismo directorio durable (archivo real); replays de nonces y tokens gastados siguen rechazados; nonce nuevo = admisión nueva (digest distinto); estado en disco inspeccionado | VERDE |

## ~~BLOQ de cierre — G15-Linux~~ (RESUELTO 2026-08-22; historia)

La plataforma primaria de M1–M3 es **Linux aarch64** (ADR-006, §14 de la
spec). La suite completa M0+M1 **no se ha ejecutado en Linux aarch64**:
este ciclo opera sin push y sin infraestructura autorizada (la VM linuxkit
de Docker Desktop usada en M0 no está disponible en esta sesión de
trabajo). Conforme a la orden (secuencia, paso 7): **no se finge**. El
estado final honesto es «M1 implementado; cierre ABIERTO por G15-Linux».
Condición de cierre: ejecutar la suite completa (más la caracterización
pinesada) en Linux aarch64 con Python 3.12 y conservar la evidencia (clase
V o L según entorno), o decisión expresa del dueño que reaplaze la
plataforma primaria.

## Decisiones de diseño asentadas (INC-3/INC-4; sin código nuevo)

1. **Mapping §5.6→§8.3:** diagnósticos de la capa de contrato del
   descriptor → `malformed_descriptor`; de la capacidad y la PoP →
   `capability_rejected` (la PoP autentica la posesión de la capacidad).
   Replay store no disponible → `capability_rejected` +
   `retryable=True` + safe_detail `replay_store_unavailable`
   (infraestructura transitoria; vocabulario cerrado §8.3, sin código
   nuevo).
2. **Canonicalidad de campos anidados** (p. ej. alias del
   `protected_header_b64` del sobre dentro del ActionRequest): la aserta
   el schema exterior M0 (§5.8) → `malformed_descriptor`; la letra de la
   regla 2 final archiva «canonicalidad» bajo `capability_rejected` para
   el sobre COMO objeto superior. Clasificación documentada y congelada
   por el oráculo del fuzz (clase `cap_alias`).
3. **`stdin_policy` `empty` + `sha256(b"")` admitido** (forma esencial
   `{kind}` con digest de bytes vacíos): lectura forzada por el corpus
   dorado (`areq-valid-01`); `empty`+`data_b64` y sha discordante →
   `malformed_descriptor` (H6 cerrado en la capa de admisión).
4. **Zeroization no garantizable en Python** (regla 3 final): declarada
   como límite en `src/adapters/operator_key.py`.
5. **`collect_expired`** es contrato de MANTENIMIENTO (usa reloj de pared
   real dentro del store), no de decisión de admisión; sin hilo de fondo
   en M1.
6. **GaranteePlan honesto:** garantías v1 (`runtime_supervision`,
   `output_bounds`, `audit_trail`) declaradas `unsupported` hasta que
   M2/M3 las opere con evidencia (spec §9: lo aplicado, no lo solicitado).
7. **`SpawnFrontier`** es protocolo instrumental (D-P4-α): sin
   implementación productiva, sin API `start`; cero primitivas de proceso
   en `src/` (grep verificado por rondas adversariales).

## Fuzz de admisión (detalle)

Bases: 2 (`empty`/`inline`, capacidades coherentes del generador de
prueba, verificadas `Admitted` antes de mutar). 21 clases × 3 pasadas =
63 mutaciones; oráculo por mutación (veredicto + reason_code exactos);
crash = fallo del gate, nunca excepción propagada. Congelado en
`tests/adversarial/test_fuzz_admision.py` (bases 2 / 63 / fingerprint
`795c3a962546b0fcae01271233bf85e9900a116f5cce7a8ba3132894b3ee8ee3`;
re-basable por diseño si cambia el corpus de bases).

## Manifiesto efímero

Los manifests por incremento (INC-2 corpus; INC-3 src+unit; INC-4
adapters+integration+adversarial; INC-5 en su reporte) y la evidencia
detallada (G13: `g13-latencia.json`) viven en
`/private/tmp/ektel-m1-prep-20260822-01/m1-implementacion/` (fuera del
repo, orden paso 5). El Controlador los consolidará en su reporte final.
