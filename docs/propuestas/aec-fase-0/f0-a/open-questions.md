# F0-A — Cuestiones abiertas y pendientes

- **Estado:** cierre F0-A.
- **Clasificación:** `PRIVATE-SANITIZED`; no autorizada para transmisión o
  publicación por esta etiqueta.

## P1 — bloqueantes de F0-A

**Ninguno.** El corpus, vocabulario, Threat Model, Authority/Trust Model,
paradigmas, registros y manifest existen. No queda un defecto que invalide esos
entregables dentro de F0-A.

## P2 — materiales, diferidos por fase

| ID | Cuestión | Por qué no invalida F0-A | Fase natural si se autoriza |
|---|---|---|---|
| P2-01 | ¿El núcleo candidato preserva una decisión operacional además de correlación e incertidumbre? | F0-A sólo construye base epistemológica | F0-B, anti-trivialidad |
| P2-02 | ¿H-profiles conserva suficiente semántica común o H-family describe mejor el resultado? | el desacuerdo independiente está documentado y requiere diseño comparado | F0-B |
| P2-03 | ¿Cuál es la máquina mínima de lifecycles y cardinalidad de attempts? | términos y diferencias ya están definidos | F0-B |
| P2-04 | ¿Cómo se representa binding profile -> admission -> attempts -> outcome sin TOCTOU? | threat/authority model identifica el requisito | F0-B |
| P2-05 | ¿Qué predicados de assurance son verificables y por qué verifier/trust anchor? | el vector está definido, no su schema | F0-B |
| P2-06 | ¿Qué outcome algebra evita colapsar cache, partial, cancel y efecto ambiguo? | el problema se documentó sin elegir wire format | F0-B |
| P2-07 | ¿Cómo se declara TCB de forma comparable sin una escala lineal engañosa? | no es necesario para completar el modelo de roles | F0-B/F0-D |
| P2-08 | ¿Qué perfiles maximizan distancia semántica y qué casos se fijan antes de probar? | el mandato reserva el stress test | F0-C |
| P2-09 | ¿Puede un adaptador conservar las garantías o sólo envolver divergencias? | controles negativos están definidos | F0-C |
| P2-10 | ¿Qué versión estable de MCP usar ante la evolución 2025-06-18 -> RC 2026-07-28? | F0-A registró exactamente la versión usada y el cambio como backlog | F0-B/F0-C |
| P2-11 | ¿Cómo modelar revocación durante un intento y efectos supervivientes? | threat model cubre stale/revocation/cancel race | F0-B |
| P2-12 | ¿Qué claims pueden producir terceros sin convertirlos en parte excesiva del TCB? | authority model distingue producer/verifier/relying party | F0-B/F0-D |

## P3/backlog no material para cierre

- comparar NIST RATS RFC 9334 con el evidence model;
- evaluar in-toto Statement/Bundle como posible envelope, no como outcome;
- seguir la estabilización de MCP Tasks y autorización 2026;
- evaluar límites/cost budgets en inferencia remota;
- revisar requisitos legales o sectoriales sólo bajo mandato específico;
- considerar object capabilities como alternativa a bearer OAuth sin asumir
  equivalencia.

## Stop

Ningún pendiente autoriza trabajo adicional. F0-B, F0-C y F0-D permanecen no
autorizadas; no se ha creado AEC Core ni wire format.
