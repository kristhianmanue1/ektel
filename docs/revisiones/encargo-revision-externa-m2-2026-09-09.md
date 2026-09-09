# Encargo de revisión adversarial externa — M2 (G-M2-15)

**Fecha:** 2026-09-09.
**Gate:** G-M2-15, que exige revisión adversarial **fresca** con veredicto
sobre el **código real**. Ninguna ronda propia del ejecutor la sustituye.
**Estado de M2:** abierto. Este encargo no lo cierra.

## 1. Identidad congelada

Todos los revisores trabajan sobre **exactamente la misma raíz**. Un revisor
que evalúe otro árbol no produce evidencia comparable.

| Qué | Valor |
|---|---|
| Commit (raíz congelada) | *se fija al publicar este encargo; ver §1.1* |
| Manifiesto | `docs/evidencia/manifest-m2-sha256.txt`, 95 entradas |
| MANIFEST-ROOT (sha256 del manifiesto) | `3e2110174ebe3b1365fdee0ed568675efa24c3cde67d696a040ff190d39524ae` |
| Cobertura del manifiesto | `src/`, `tests/`, `scripts/`, `contracts/`. **No** `docs/` |

### 1.1 Verificación exigida antes de empezar

Cada revisor **debe** comprobar por su cuenta, y declarar el resultado:

```bash
git rev-parse HEAD          # debe coincidir con la raíz congelada
git status --porcelain      # debe estar vacío
shasum -a 256 docs/evidencia/manifest-m2-sha256.txt   # MANIFEST-ROOT
```

Y regenerar el manifiesto para confirmar **diff cero**:

```bash
{ echo "# Manifiesto M2 — raiz congelada para la revision externa G-M2-15"
  echo "# Arbol del commit que contiene este archivo (padre: <padre>)."
  echo "# Cubre src/, tests/, scripts/ y contracts/. NO cubre docs/."
  find src tests scripts contracts/schemas contracts/vectors contracts/parsers \
    -type f \( -name '*.py' -o -name '*.json' -o -name '*.sh' \) \
    -not -path '*__pycache__*' | LC_ALL=C sort | xargs shasum -a 256
} | diff - docs/evidencia/manifest-m2-sha256.txt
```

Un revisor que no pueda reproducir el MANIFEST-ROOT **debe detenerse y
reportarlo**, no continuar sobre un árbol distinto.

## 2. Independencia

**Tres revisores de familias de modelo distintas**, como mínimo.

**Ningún revisor ve la respuesta de otro antes de emitir su primer veredicto.**
La reconciliación ocurre después, y no antes, de que los tres hayan emitido.

Precedente del proyecto: el gate externo de M0 se cerró con doble PROCEED de
Codex y Claude sobre el mismo MANIFEST-ROOT. Aquí se eleva a tres familias.

## 3. Material que recibe cada revisor

Idéntico para los tres:

| Qué | Ruta |
|---|---|
| Especificación M0–M3 v1.2 | `docs/especificacion/ektel-runtime-m0-m3-v1.md` |
| ADR-011 handoff admisión→start | `docs/adr/adr-011-handoff-admision-start.md` |
| ADR-012 supervisión local M2 | `docs/adr/adr-012-supervision-local-m2.md` |
| Autorización M2 | `docs/decisiones/autorizacion-m2-2026-09-09.md` |
| Alcance técnico §8 (45 rutas) | `docs/propuestas/alcance-tecnico-m2-2026-09-09.md` |
| Gates G-M2-01..15 | `docs/propuestas/paquete-preparacion-m2-2026-08-28.md` §5 |
| Estado de evidencia | `docs/evidencia/estado-evidencia-m2-2026-09-09.md` |
| Caracterización por plataforma | `docs/evidencia/caracterizacion-m2-{darwin,linux}-2026-09-09.md` |
| Claims y no-claims | `docs/claims-y-no-claims.md` |
| Manifiesto | `docs/evidencia/manifest-m2-sha256.txt` |
| Diff M2 completo | `git diff 4beb7ebe..<raíz congelada> -- src tests scripts` |
| Borrador de enmienda G-M2-12 | `docs/propuestas/borrador-enmienda-g-m2-12-2026-09-09.md` |

## 4. Obligaciones de falsación

Cada revisor debe **intentar falsificar**, como mínimo, estas dieciséis
propiedades. No basta con confirmar que las pruebas pasan: se pide construir el
caso que las rompa.

1. **Linealización CAS → spawn** — que algo distinto de `CONSUMED` cruce.
2. **Reconciliación** `spent`/`unspent`/`unknown` — que `unspent` autorice spawn
   directo, o que un indeterminado se degrade a determinado.
3. **Carreras de capacidad** — exceder `max_concurrent_actions`.
4. **Handles forjados o cross-instance** — autenticar uno que no debería.
5. **`terminate` / `await_result`** — receipt distinto en repetición, contacto
   al supervisor tras resultado, resultado fabricado.
6. **Deadlines** — plazo efectivo, empate duración/vigencia, plazo cero.
7. **TERM→KILL** — escapar del KILL, o que la gracia no se aplique.
8. **Backpressure** — más de un frame no confirmado por stream; pérdida de
   salida con coordinador vivo.
9. **Pipe escape** — cuelgue no acotado por pipes retenidos.
10. **Crash durability** — token reabierto tras `SIGKILL` post-CAS.
11. **Escapes `setsid`** — que se prometa lo que no se cumple.
12. **Divergencias Linux/Darwin** — comportamiento que difiera sin declararse.
13. **Regresiones M1** — cualquier prueba M1 que cambie de resultado
    (`SCOPE VIOLATION` por A-M2-3).
14. **Claims más fuertes que la evidencia** — especialmente payload presentado
    como límite de memoria, o gates parciales leídos como verdes.
15. **Ampliaciones no autorizadas de la TCB**.
16. **Violaciones del alcance M2** — rutas fuera del inventario de 45, tocar
    `contracts/`, schemas, workflows, o entrar en M3/M4.

### 4.1 Contexto que el revisor debe conocer, no para confiar sino para atacar

- Las **dos rondas propias** del ejecutor (`revision-adversarial-m2-inc1-3` y
  `revision-adversarial-m2-fix-retry`) hallaron quince defectos: tres cuelgues,
  una pérdida silenciosa de datos y una propiedad declarada sin acreditar. Que
  ya estén corregidos **no** es motivo para no reintentarlos: se pide verificar
  que las correcciones no reintrodujeron el problema por otra vía.
- **G-M2-12 está PARCIAL** y su enmienda es un **borrador sin firmar**. Un
  revisor que lo trate como verde está equivocado.
- Duplicación cosmética conocida: existen dos métodos llamados
  `test_las_cotas_publicadas_siguen_las_formulas` en
  `tests/integration/test_output_framing.py`, en clases distintas y probando
  cosas distintas (cotas de plazo y cotas de payload). No es copia-pega
  defectuosa; se declara para que no se reporte como tal.

## 5. Formato de cada hallazgo

| Campo | Contenido |
|---|---|
| **ID** | identificador estable dentro del informe |
| **Severidad** | P0 bloqueante · P1 material · P2 diferible · P3 cosmético |
| **Ubicación** | `archivo:línea` o evidencia citada |
| **Claim afectado** | qué promesa concreta queda falsificada |
| **Reproducción** | pasos o prueba que lo demuestran |
| **Consecuencia** | qué falla en la práctica |
| **Recomendación** | corrección propuesta |

Un hallazgo sin reproducción es una **hipótesis**, y debe marcarse como tal.

## 6. Veredicto

Cada revisor emite exactamente uno:

- **PROCEED**
- **FIX-AND-RETRY**
- **NO-GO**

**No hay votación por mayoría simple.** Un hallazgo material y reproducible
debe resolverse **aunque dos revisores hayan votado `PROCEED`**. La
reconciliación pondera evidencia, no cuenta votos — es el mismo criterio que
usó la reconciliación de AEC F0-A.

## 7. Después de la revisión

Si hay hallazgos:

1. corregir;
2. reejecutar los **gates afectados**;
3. reejecutar la **regresión completa** en ambas plataformas;
4. actualizar el manifiesto;
5. solicitar **re-verificación externa del diff correctivo**.

M2 sólo se cierra cuando concurren: G-M2-01..15 satisfechos · revisión externa
conforme · **cero hallazgos materiales abiertos** · acta humana de cierre.

## 8. Fuera de alcance de esta revisión

- **M3**: no se revisa ni se prepara. Permanece bloqueado hasta `M2 CLOSED`.
- **M4** / capability enforcement: Research Gate post-M3.
- **x86_64**: puerta de pre-producción (ADR-006/N12).
- Proponer **ampliaciones** de M2: un revisor puede señalar que algo falta
  según los gates vigentes, no pedir funcionalidad nueva.
