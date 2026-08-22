"""Puerto PolicyPort (spec v1.2 §9, ADR-008).

`evaluate(PolicyEvaluationRequest) -> PolicyDecision` con
`Allow`/`Deny`/`Indeterminate` (§9.1). El núcleo evalúa **su propia copia**
de la solicitud (ADR-008 A2: el adaptador puede intentar mutarla; el
núcleo ignora la mutación). La validación del sobre de respuesta es del
núcleo (B7): `decision_id`, vigencia `valid_until` contra reloj de pared
con la tolerancia declarada y recepción dentro del timeout medido con
reloj monotónico (los plazos nunca usan reloj de pared; la vigencia sí,
por ser afirmación civil compartida con el emisor) — ver
`src/application/admit.py`.

Un `Allow` expirado o tardío se convierte en `Indeterminate` — y en
rechazo cuando el puerto sea requerido (§9). Ektel afirma la presencia de
un `Allow`, no la corrección de la política externa (no-claim N16).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Union


@dataclass(frozen=True)
class Allow:
    decision_id: str
    valid_until_wall: float


@dataclass(frozen=True)
class Deny:
    decision_id: str


@dataclass(frozen=True)
class Indeterminate:
    reason: str


PolicyDecision = Union[Allow, Deny, Indeterminate]


class PolicyPort(Protocol):
    """Contrato del puerto de política (§9.1)."""

    def evaluate(self, request: Mapping[str, object]) -> PolicyDecision:
        """Evalúa una solicitud inmutable y devuelve una decisión tipada.
        El timeout del adaptador se manifiesta como `Indeterminate` o como
        una respuesta tardía que el núcleo descarta por el plazo
        monotónico (B7)."""
        ...
