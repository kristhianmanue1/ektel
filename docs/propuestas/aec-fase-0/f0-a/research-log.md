# F0-A — Research Log

- **Fecha:** 2026-09-08.
- **Clasificación:** `PRIVATE-SANITIZED`.
- **Autoridad:** autorización explícita del maintainer de 2026-09-08 para F0-A
  únicamente.

## Registro

| Paso | Actividad | Resultado | Límite aplicado |
|---|---|---|---|
| RL-01 | Preflight AGENTS/AN-KLA | integración verificada; memoria leída como dato no confiable; sin write/checkpoint | AN-KLA no concede autoridad |
| RL-02 | Preflight Git | `main`; HEAD `6e688ab3ef4dd51251b9c401dcff49373daedace`; `origin/main` observado `7ce1b2a0ff116167774224d42605e6ebd0a411a9`; local +1; árbol con untracked preexistentes | sin rama/commit/push |
| RL-03 | Derivación externa | se fijó corpus de 12 fuentes principales, 0 secundarias | no se usó EKTEL como baseline universal |
| RL-04 | Tres familias | local process/container; remote execution/job; remote tool/API | examen superficial, no F0-C |
| RL-05 | Vocabulario | se separaron invocation/attempt/effect/evidence y authn/authz/enforcement | sin schema ni nombres definitivos |
| RL-06 | Threat Model | assets, actors, boundaries, attacker, assumptions, consecuencias y 20 amenazas | no se afirmó control implementado |
| RL-07 | Authority/Trust Model | roles, vector de assurance, binding chain y evidencia | no se eligió trust provider |
| RL-08 | Contraste EKTEL read-only | PolicyPort, timeout post-hoc, replay anticipado, frontera de prueba, request POSIX y profile mutable | cero cambios funcionales |
| RL-09 | Crítica independiente | dos agentes con contexto público y roles separados: standards/trust e interoperability/lifecycle | outputs son crítica, no evidencia independiente |
| RL-10 | Reconciliación root | convergencia contra H-common fuerte; desacuerdo H-profiles/H-family conservado como P2-02 | una sola reconciliación |
| RL-11 | Manifest/verificación | inventario, clasificación, digests y chequeos documentales | sin publicación |

## Preflight detallado

Los untracked preexistentes observados fueron:

- `docs/propuestas/Mandato-investigacion-Agent-Execution-Contract.md`;
- `docs/propuestas/aec-fase-0/` — contenía el mandato de esta investigación;
- `project-manifest.yaml`.

No se atribuyó propiedad ni se modificaron los dos artefactos externos al
perímetro. Los resultados nuevos se limitaron a `f0-a/` y `records/`.

## Reproducibilidad y limitaciones

- La fecha de consulta para el corpus es 2026-09-08.
- Se consultaron páginas públicas y archivos locales read-only; no se ejecutó
  código de fuentes externas ni se transmitió contenido privado del repo.
- La documentación viva puede cambiar; cada registro conserva la revisión o
  fecha disponible.
- No se realizaron pruebas multi-runtime, prototipos ni evaluación cuantitativa.
- El consenso entre modelos no cuenta como evidencia adicional; sólo expone
  desacuerdos y preguntas.
- El nombre comercial exacto de la instancia root no fue expuesto al artefacto;
  se registra como `GPT-5 Codex (root reconciler)` sin inventar build ID.
