"""ektel ports — protocolos del núcleo M1 (spec v1.2 §4/§9, ADR-008).

API EXPERIMENTAL (spec §16). El dominio no importa adaptadores (§4);
`SpawnFrontier` es instrumental (D-P4-α, sólo pruebas).
"""
from .policy_port import Allow, Deny, Indeterminate, PolicyDecision, PolicyPort
from .replay_store import ConsumeOutcome, ReplayStore, ReserveOutcome
from .spawn_frontier import SpawnFrontier

__all__ = [
    "Allow", "Deny", "Indeterminate", "PolicyDecision", "PolicyPort",
    "ConsumeOutcome", "ReplayStore", "ReserveOutcome", "SpawnFrontier",
]
