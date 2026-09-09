"""Aritmética de vigencia y plazo — D-M2-3 y ADR-011 §2.5.

Puro: sin reloj propio. `now_wall` se inyecta.

Introducido en INC-M2-2 con el subconjunto anterior al CAS y **completado en
INC-M2-4** con la terminación graduada de D-M2-3.

Los instantes se exportan como **offsets relativos al inicio**, nunca como
instantes monotónicos: un valor monotónico no tiene significado fuera del
proceso que lo tomó.

`ceil_exact_ms` multiplica por 1000 el valor **racional exacto** del `float`
validado —vía `as_integer_ratio()`— y redondea **hacia arriba** con división
entera. Nunca redondea hacia abajo ni gana una fracción de milisegundo:
redondear a la baja regalaría tiempo de ejecución después de `exp`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
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


@dataclass(frozen=True)
class TimeBounds:
    """Cotas de D-M2-3, todas en milisegundos y relativas al inicio."""
    deadline_effective_ms: int
    termination_grace_ms: int
    applied_grace_ms: int
    useful_runtime_ms: int
    soft_termination_after_start_ms: int
    hard_deadline_after_start_ms: int


def compute_bounds(deadline_effective_ms: int,
                   termination_grace_ms: int) -> TimeBounds:
    """Fórmulas de D-M2-3.

        applied_grace_ms    = min(termination_grace_ms, deadline_eff_ms)
        useful_runtime_ms   = deadline_eff_ms - applied_grace_ms
        soft_termination_at = start_mono + useful_runtime_ms
        hard_deadline_at    = start_mono + deadline_eff_ms

    Una gracia mayor o igual que el plazo efectivo deja `useful_runtime_ms` en
    cero: el proceso recibe TERM de inmediato. No es un error, es la
    consecuencia declarada de configurar una gracia que no cabe.

    El plazo post-KILL **no amplía** el deadline de ejecución: sólo acota la
    latencia adicional de recolección de pipes antes de entregar el resultado.
    """
    if type(deadline_effective_ms) is not int or deadline_effective_ms <= 0:
        raise ValueError("deadline_effective_ms debe ser entero positivo")
    if type(termination_grace_ms) is not int or termination_grace_ms < 0:
        raise ValueError("termination_grace_ms debe ser entero no negativo")
    applied = min(termination_grace_ms, deadline_effective_ms)
    useful = deadline_effective_ms - applied
    return TimeBounds(
        deadline_effective_ms=deadline_effective_ms,
        termination_grace_ms=termination_grace_ms,
        applied_grace_ms=applied,
        useful_runtime_ms=useful,
        soft_termination_after_start_ms=useful,
        hard_deadline_after_start_ms=deadline_effective_ms,
    )
