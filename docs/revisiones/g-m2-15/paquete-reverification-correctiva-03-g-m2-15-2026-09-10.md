# Paquete de re-verificación — tercera corrección R15/R16

**Fecha:** 2026-09-10. **Estado del candidato:** IMPLEMENTED /
PENDING-EXTERNAL-REVERIFICATION al emitir el candidato. No adjudica gates.
**Resultado posterior:** [re-verificación independiente 3](informe-reverification-correctiva-03-2026-09-10.md)
PROCEED para R15/R16 dentro del threat model ratificado; se conservan sus límites.

## 1. Raíces exactas

| Identidad | Valor |
|---|---|
| Baseline documental/adjudicación | `dc3de184de495abe022c656fb8b947a1b976ed8f` |
| CORRECTIVE-REVIEW-ROOT | `f944493bc9872414daf3d46d7ae230adcbfcf42e` |
| MANIFEST-ROOT anterior | `9a2e3d52ad0c807335bc6f0a9cc8384a337c0784f4e91f124542aaba60080c95` |
| MANIFEST-ROOT candidato | `b59553bcb6d4ab696357354ba63ffbae398609ea48426610b447d43bec660588` |
| Entradas del manifiesto | 98; src, tests, scripts y contracts |

El commit de revisión contiene implementación, acta ratificada, enmiendas de
alcance/no-claim y manifiesto. Este paquete se añade después, exclusivamente
documental: no cambia la raíz que debe revisar otro agente.

```sh
git diff dc3de184de495abe022c656fb8b947a1b976ed8f f944493bc9872414daf3d46d7ae230adcbfcf42e -- src tests
shasum -a 256 docs/evidencia/manifest-m2-sha256.txt
shasum -a 256 -c docs/evidencia/manifest-m2-sha256.txt
```

## 2. Autoridad y alcance

[Decisión humana](../../decisiones/ratificacion-r13-strong-r15-r16-2026-09-10.md):
ratifica gap R13 fuerte y no-claim N20, autoriza R15/R16 y fail-closed sin
provenance tras reinicio. No autoriza cierre G-M2-15/M2 ni inicio M3.
La [adjudicación](adjudicacion-arquitectonica-r13-r14-2026-09-10.md) y el
[informe 2](informe-reverification-correctiva-02-2026-09-10.md) se conservan intactos.

Cambian cuatro archivos productivos: `application/admit.py`,
`application/start_service.py`, `domain/execution_handle.py` y
`adapters/posix_supervisor.py`. No cambia wire/schema, dependencia runtime,
IPC, topología de procesos, persistencia, ReplayStore, revalidación pura ni
SpawnFrontier. Tampoco cambian scripts ni fixtures/pruebas M1 protegidas.

## 3. Comportamiento corregido

R15: las tablas y handles conservan vista consumidora sin depósito/cierre.
El writer local es retenido por el watcher y linealiza resultado o ausencia;
finalización repetida no reclasifica. Rechazo por identidad exacta antes de
autenticar handles incompletos; tipos de timeout no finitos, hostiles o fuera
de rango no escapan como excepciones. No se afirma seguridad ante introspección.

R16: `AdmissionService.admit` produce evidencia interna token completo →
expiración/perfil bajo el emisor ligado al Start. No existe registro público.
`admission_service` es dependencia de composición; una referencia a otro emisor
no acredita el token. `declared_config_fingerprint` legado es ignorado como
autoridad. Ningún Start sin evidencia puede cruzar CAS/spawn.

La cota N usa `max_concurrent_actions`, sin nuevo campo de configuración.
Admission M2 serializa comprobación/emisión y rechaza saturación antes del nonce.
M1 sin M2 conserva su pipeline. Expiración libera entradas; reintento pre-CAS,
unspent y unknown retienen evidencia válida; consumed/spent la retiran. Retirada
tras spawn para no introducir el lock de Admission entre CAS y creación. R12
conserva su lifecycle separado. Un nuevo Start no hereda emisiones del anterior,
incluso si se reutiliza el mismo objeto Admission. El Host prepara sus parámetros
desde el mismo snapshot comprometido, sin prometer éxito futuro del kernel.

## 4. Evidencia ejecutada por el implementador

Resultados del candidato final, no de las corridas exploratorias anteriores:

| Comprobación | Resultado |
|---|---|
| Darwin arm64, Python 3.12.12, suite completa | 385 tests; OK; 5 skips; 112.467 s |
| Linux aarch64 clase V, Python 3.12.14, suite completa | 385 tests; OK; 1 skip; 118.616 s |
| `mypy --strict src` | 34 archivos; sin issues |
| Fuzz Admission, ambas plataformas | 2 bases, 63 mutaciones efectivas, cero fallos/crashes/errores de base |
| Fuzz revalidación, ambas plataformas | 1000 iteraciones, semilla 20260909, cero crashes/divergencias; gate OK |
| R15/R16 + concurrencia sobre store real | 20 tests; OK |
| Manifiesto e invariantes de alcance | 98 entradas verificadas; rutas protegidas sin diff; `git diff --check` correcto |

Linux: imagen local fijada
`python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`,
repo read-only, sin red, sin privilegios, UID 10001, `/tmp` efímero.
Los skips se conservan como skips; no equivalen a cobertura de la otra plataforma.
Las suites imprimieron ResourceWarning de subprocess todavía vivo en dos puntos;
también aparecieron en las corridas previas a la última revisión local. No se
presenta OK como prueba de ausencia universal de procesos residuales. No se ejecutó
caracterización x86_64 ni se afirma RSS bajo o prueba material de 16 GiB.

Reproducción en host:

```sh
.venv/bin/python -B -m unittest discover -s tests -t .
.venv/bin/mypy --strict src
.venv/bin/python -B scripts/fuzz_admision.py --iteraciones 500
.venv/bin/python -B scripts/fuzz_start_revalidation.py --iteraciones 1000
```

El fuzzer Admission reporta 63 mutaciones efectivas; el argumento 500 no se
presenta como 500 casos ejecutados. La suite nueva es
`tests/unit/test_m2_authority.py` (17 pruebas), más las regresiones M2 adaptadas.

Las fixtures actualizadas emiten por Admission M2 real y comprueban que el token
coincide con el request preparado; nunca insertan fingerprints en el registro.
Los tests negativos de provenance llaman Start directamente. En reinicio, el
diagnóstico pasa a ausencia de evidencia pre-CAS; se conserva además la aserción
explícita de `spent` durable en FileReplayStore. No se debilita esa garantía para
adaptar el nuevo diagnóstico.

## 5. Preguntas para el revisor

1. ¿Una superficie consumidora todavía entrega writer, admite terminal falso o
   cierra por timeout/abandono? ¿Se conservan rechazo controlado y R12?
2. ¿A/B/B con caller afirmando B llega a CAS? ¿Otro Admission genuino basta sin
   evidencia de emisión? ¿Algún constructor ofrece bypass?
3. ¿Cota, expiración, reinicio, concurrencia y reconciliación retienen exactamente
   lo necesario sin nueva persistencia ni pérdida del snapshot autorizado?
4. ¿El compromiso del Host procede del snapshot usado, bajo el trusted set
   ratificado? No exigir aislamiento de código malicioso excluido por N20.
5. ¿Las adaptaciones de fixtures preservan oráculos de R12/CAS y no ocultan el
   fallo mediante registro público o reemisión implícita en producción?

La re-verificación debe declarar raíz, ejecución propia, limitaciones y hallazgos.
La suite del implementador no es su veredicto. No modificar el candidato durante
la revisión ni convertir un PROCEED de revisión en cierre humano del gate.

```text
R12 = SATISFIED (evidencia previa; regresión ejercitada)
R13 = NOT-SATISFIED
R13-STRONG = BLOCKED-BY-NORMATIVE-GAP
R14 = NOT-SATISFIED (histórico)
R15/R16 = IMPLEMENTED / EXTERNAL-REVERIFICATION-PROCEED
G-M2-15 = CORRECTIVE-FIX-AND-RETRY
M2 = OPEN
M3 = BLOCKED
```
