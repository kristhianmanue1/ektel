"""ektel adapters — borde reemplazable (spec v1.2 §4/§18).

M1: `operator_key` (carga segura), `replay_store_file` (durable dos CAS),
`policy_null`/`policy_fake` (contract tests ADR-008) y
`spawn_frontier_counter` (instrumental D-P4-α, sólo pruebas).

API EXPERIMENTAL (spec §16).
"""
from .operator_key import KEY_LEN, OperatorKeyError, load_operator_key
from .policy_fake import FakePolicyPort
from .policy_null import NullPolicyPort
from .replay_store_file import FileReplayStore, ReplayStoreError
from .spawn_frontier_counter import (
    SpawnCrossing, SpawnFrontierCounter)

__all__ = [
    "KEY_LEN", "OperatorKeyError", "load_operator_key",
    "FakePolicyPort", "NullPolicyPort",
    "FileReplayStore", "ReplayStoreError",
    "SpawnCrossing", "SpawnFrontierCounter",
]
