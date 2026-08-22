"""Adaptador de política de PRUEBA (ADR-008 punto 3: contract tests contra
el puerto nulo y uno falso; el núcleo se prueba completo sin CAGF).

Comportamientos configurables: `Allow`/`Deny`/`Indeterminate`/timeout.
**Intenta mutar la solicitud** (ADR-008 A2) para verificar que el núcleo
evalúa su propia copia inmutable: la mutación que logre debe ser ignorada
por la aplicación (los contract tests lo asientan).

API EXPERIMENTAL (spec §16). stdlib-only. SÓLO pruebas.
"""
from __future__ import annotations

import time
from typing import Mapping

from ..ports.policy_port import Allow, Deny, Indeterminate, PolicyDecision


class FakePolicyPort:
    """Puerto falso con decisión inyectable, retardo (tardío para B7) y
    mutación intencional de la solicitud (A2)."""

    def __init__(self, decision: PolicyDecision | None = None,
                 delay_s: float = 0.0, mutate: bool = True) -> None:
        self.decision = decision or Deny("fake-default")
        self.delay_s = delay_s
        self.mutate = mutate
        #: `None` = no intentó mutar; `False` = intentó y fue BLOQUEADA
        #: (sólo lectura por tipo); `True` = la mutación PROSPERÓ (defecto
        #: del núcleo: los contract tests deben fallar en ese caso).
        self.mutation_applied: bool | None = None
        self.calls: list[dict[str, object]] = []

    def evaluate(self, request: Mapping[str, object]) -> PolicyDecision:
        self.calls.append(dict(request))
        if self.mutate:
            self.mutation_applied = False
            try:
                request["action_id"] = "mutado-por-adaptador"  # type: ignore[index]
                self.mutation_applied = True
            except TypeError:
                pass  # Vista de sólo lectura (MappingProxyType): bloqueada
        if self.delay_s:
            time.sleep(self.delay_s)
        return self.decision
