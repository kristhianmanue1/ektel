"""Resultados de `start` — vocabulario wire v1 congelado (spec §8.3, ADR-005).

Unión discriminada `StartOutcome = Started | StartFailed`, con el mismo
vocabulario que `contracts/schemas/v1/start-outcome.schema.json`. Este módulo
**consume** ese contrato; no lo redefine ni lo amplía. M2 no crea schemas ni
vectores nuevos (acta de autorización M2, §4).

`capability_rejected` es código legítimo de `StartFailed`: lo exige §7.4 (el
perdedor de un `start` concurrente) y §8.3 enmendado lo reconoce.

`start_failed_indeterminate` conserva la incertidumbre epistemológica: se usa
cuando el runtime **no puede determinar** si el token quedó consumido o si un
proceso llegó a existir. No se convierte en éxito ni en fallo determinado
(ADR-011 §2.3, invariante 4 del paquete M2).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

#: Único reason code de rechazo por forma, cripto, vigencia o coherencia.
REASON_CAPABILITY_REJECTED = "capability_rejected"
#: Fallo de una dependencia pre-inicio requerida; el token sigue sin gastar.
REASON_START_FAILED = "start_failed"
#: Indeterminación real: no se sabe si el token se gastó o si hubo proceso.
REASON_START_FAILED_INDETERMINATE = "start_failed_indeterminate"

START_FAILURE_REASONS = frozenset({
    REASON_START_FAILED,
    REASON_START_FAILED_INDETERMINATE,
    REASON_CAPABILITY_REJECTED,
})

#: Cota del schema wire para `safe_detail` (maxLength 512).
MAX_SAFE_DETAIL = 512


@dataclass(frozen=True)
class Started:
    """`start` creó el proceso. `handle_ref` es la correlación wire (16 hex);
    el `ExecutionHandle` real es local, opaco y no serializable (ADR-012)."""
    handle_ref: str

    def __post_init__(self) -> None:
        if type(self.handle_ref) is not str or len(self.handle_ref) != 16:
            raise ValueError("handle_ref debe ser una cadena de 16 caracteres")
        if any(c not in "0123456789abcdef" for c in self.handle_ref):
            raise ValueError("handle_ref debe ser hex minuscula")


@dataclass(frozen=True)
class StartFailed:
    """`start` no creó proceso. `safe_detail` es diagnóstico saneado: nunca
    transporta bytes del descriptor, del entorno ni de stdin."""
    reason_code: str
    safe_detail: str = ""

    def __post_init__(self) -> None:
        if self.reason_code not in START_FAILURE_REASONS:
            raise ValueError(f"reason_code invalido: {self.reason_code!r}")
        if type(self.safe_detail) is not str:
            raise ValueError("safe_detail debe ser str")
        if len(self.safe_detail) > MAX_SAFE_DETAIL:
            raise ValueError("safe_detail excede la cota del schema wire")


StartOutcome = Union[Started, StartFailed]
