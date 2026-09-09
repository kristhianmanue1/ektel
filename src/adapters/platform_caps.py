"""Capacidades de plataforma del supervisor — ADR-012 D-M2-2(a), ADR-006.

Declara qué puede hacer realmente **esta** plataforma, para que
`GuaranteePlan`/`guarantees_applied` no prometan más de lo medido (spec §9:
una observación best-effort no se presenta como límite duro).

**`PR_SET_CHILD_SUBREAPER` es Linux-only.** Sin él, el CPU y la recolección de
un nieto huérfano —cuyo padre inmediato murió sin `wait()`— son irrecuperables
para el proceso raíz, que sólo reap-ea a su hijo directo. En Darwin **no hay
mitigación conocida**: la contabilidad multi-nivel queda `unsupported`, y eso
se declara, no se disimula.

Sólo el **supervisor de acción** puede activarlo (D-M2-2(a)): hacerlo global
en el coordinador convertiría en global un efecto que debe ser por acción.

`ctypes` para `prctl` es la **única excepción parcial declarada** de ADR-006 al
núcleo stdlib-only.

API EXPERIMENTAL (spec §16). stdlib-only + ctypes declarado.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

#: `PR_SET_CHILD_SUBREAPER` en <linux/prctl.h>.
PR_SET_CHILD_SUBREAPER = 36

MULTILEVEL_SUPPORTED = "supported"
MULTILEVEL_UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class PlatformCaps:
    """Capacidades observadas. `subreaper_available` es una propiedad de la
    plataforma; `subreaper_applied` sólo puede afirmarlo el supervisor que lo
    activó realmente."""
    platform: str
    subreaper_available: bool
    multilevel_accounting: str

    @property
    def declares_multilevel(self) -> bool:
        return self.multilevel_accounting == MULTILEVEL_SUPPORTED


def detect() -> PlatformCaps:
    """Capacidades de la plataforma actual. No activa nada."""
    platform = sys.platform
    if platform.startswith("linux"):
        return PlatformCaps(platform=platform, subreaper_available=True,
                            multilevel_accounting=MULTILEVEL_SUPPORTED)
    # Darwin y cualquier otra: sin mitigacion conocida.
    return PlatformCaps(platform=platform, subreaper_available=False,
                        multilevel_accounting=MULTILEVEL_UNSUPPORTED)


def set_child_subreaper() -> bool:
    """Activa `PR_SET_CHILD_SUBREAPER` en **este** proceso.

    Devuelve si quedó realmente aplicado. Un fallo no se convierte en
    excepción: la ausencia de la garantía se declara, no se finge.
    """
    # Se deriva de `detect()` y no de `sys.platform` directo: el análisis
    # estático fija `sys.platform` al de la máquina que analiza y daría el
    # resto por inalcanzable.
    if not detect().subreaper_available:
        return False
    try:
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        result = libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)
        return bool(result == 0)
    except Exception:
        return False
