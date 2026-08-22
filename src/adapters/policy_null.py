"""PolicyPort nulo — perfil `absent` (spec §9, ADR-008 punto 3).

Con `policy_mode=absent` la aplicación NO invoca el puerto (INC-3); este
adaptador existe como frontera explícita para contract tests: cualquier
llamada es un defecto de configuración y se manifiesta como
`Indeterminate` (que, en required, rechazaría — fail-closed, nunca
silencioso).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from typing import Mapping

from ..ports.policy_port import Indeterminate, PolicyDecision


class NullPolicyPort:
    """Puerto nulo: toda evaluación es Indeterminate."""

    def evaluate(self, request: Mapping[str, object]) -> PolicyDecision:
        return Indeterminate("null-policy-port")
