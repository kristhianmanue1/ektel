"""ektel ports — protocolos del núcleo M1 y M2 (spec v1.2 §4/§9, ADR-008).

API EXPERIMENTAL (spec §16). El dominio no importa adaptadores (§4);
`SpawnFrontier` es instrumental (D-P4-α, sólo pruebas).

`ProcessHost` (M2) es la frontera **paralela** por la que M2 crea procesos.
No sustituye ni retira `SpawnFrontier`: el acta de autorización M2 (A-M2-1)
preserva la frontera instrumental M1 y su evidencia. Retirar un símbolo M1 de
este re-export sería `SCOPE VIOLATION`.
"""
from .policy_port import Allow, Deny, Indeterminate, PolicyDecision, PolicyPort
from .process_host import ProcessHost, SpawnRejected
from .replay_store import ConsumeOutcome, ReplayStore, ReserveOutcome
from .spawn_frontier import SpawnFrontier

__all__ = [
    "Allow", "Deny", "Indeterminate", "PolicyDecision", "PolicyPort",
    "ConsumeOutcome", "ReplayStore", "ReserveOutcome", "SpawnFrontier",
    "ProcessHost", "SpawnRejected",
]
