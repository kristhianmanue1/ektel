"""Aritmética de vigencia y plazo — D-M2-3 y ADR-011 §2.5.

Puro: sin reloj propio. `now_wall` se inyecta.

**Introducido en INC-M2-2 con el subconjunto que el orden de ADR-011 §2.6
exige antes del CAS**: `ceil_exact_ms`, `remaining_validity_ms` y
`deadline_eff_ms`. Las cotas de terminación graduada
(`applied_grace_ms`, `useful_runtime_ms`, `soft_termination_at`,
`hard_deadline_at`) pertenecen a INC-M2-4 y todavía no viven aquí.

`ceil_exact_ms` multiplica por 1000 el valor **racional exacto** del `float`
validado —vía `as_integer_ratio()`— y redondea **hacia arriba** con división
entera. Nunca redondea hacia abajo ni gana una fracción de milisegundo:
redondear a la baja regalaría tiempo de ejecución después de `exp`.
"""
from __future__ import annotations

import math
from typing import Optional


def ceil_exact_ms(now_wall: float) -> Optional[int]:
    """Milisegundos exactos redondeados hacia arriba, o `None` si el valor no
    es representable."""
    if type(now_wall) is not float or not math.isfinite(now_wall):
        return None
    numerator, denominator = now_wall.as_integer_ratio()
    return -((-numerator * 1000) // denominator)


def remaining_validity_ms(exp_wall: int, now_wall: float) -> Optional[int]:
    """`exp*1000 - ceil_exact_ms(now)`. `None` si no es representable."""
    if type(exp_wall) is not int:
        return None
    now_ms = ceil_exact_ms(now_wall)
    if now_ms is None:
        return None
    return exp_wall * 1000 - now_ms


def deadline_eff_ms(requested_deadline_ms: int, exp_wall: int,
                    now_wall: float) -> Optional[int]:
    """`min(deadline_ms, remaining_validity_ms)`.

    Devuelve `None` cuando no es representable **o no es positivo**: ADR-011
    §2.5 exige rechazar **antes de consumir** el token; iniciar un proceso sin
    vida útil gastaría el token para nada.
    """
    if type(requested_deadline_ms) is not int:
        return None
    remaining = remaining_validity_ms(exp_wall, now_wall)
    if remaining is None:
        return None
    effective = min(requested_deadline_ms, remaining)
    return effective if effective > 0 else None


def validity_exhausted(requested_deadline_ms: int, remaining_ms: int) -> bool:
    """Causa `deadline_validity_exhausted` (D-M2-3): se fija cuando la
    vigencia restante fue **menor o igual** que la duración pedida. En empate
    **gana vigencia**, explícitamente."""
    return remaining_ms <= requested_deadline_ms
