"""Fixtures deterministas para las pruebas unitarias M1.

Construye `ActionRequest` coherentes (capacidad + PoP + binding) con clave
de prueba de 32 bytes, sal de despliegue de 32 bytes y relojes fijos
inyectables. Sin I/O. La clave/sal de prueba NUNCA salen de los tests.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.operator_key import OperatorKeyError  # noqa: E402
from src.application.admit import AdmissionService  # noqa: E402
from src.domain.crypto import compute_key_id, mac_envelope, mac_pop  # noqa: E402
from src.ports.policy_port import Allow, Deny, Indeterminate, PolicyPort  # noqa: E402
from src.ports.replay_store import ReplayStore, ReserveOutcome  # noqa: E402
from src.ports.spawn_frontier import SpawnFrontier  # noqa: E402
from src.domain.outcomes import Admitted  # noqa: E402
from typing import Mapping  # noqa: E402

TEST_KEY = bytes(range(32))
TEST_SALT = bytes.fromhex("11" * 32)  # 32 bytes exactos (regla 1 final)
TEST_KEY_ID = compute_key_id(TEST_SALT, TEST_KEY)

NBF = 1_735_689_600
EXP = 1_798_761_600
NOW = (NBF + EXP) // 2
NONCE_HEX = "a1" * 16
ISSUER = "operator-dev"

DEADLINE_MS = 5000
OUTPUT_LIMITS = {"max_stdout_bytes": 65536, "max_stderr_bytes": 65536}
REQUESTED_GUARANTEES = ["runtime_supervision", "output_bounds"]


def _b64u(data: bytes) -> str:
    from base64 import urlsafe_b64encode
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _emit(obj) -> bytes:
    import json
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _decode_b64u(value: str) -> bytes:
    from base64 import urlsafe_b64decode
    return urlsafe_b64decode(value + "=" * ((-len(value)) % 4))


def make_capability_envelope(key: bytes = TEST_KEY, key_id: str = TEST_KEY_ID,
                             nbf: int = NBF, exp: int = EXP,
                             binding: dict | None = None,
                             nonce: str = NONCE_HEX) -> dict:
    """Sobre de capacidad coherente con `BASE_DESCRIPTOR`."""
    header = {"alg": "HS256", "schema_version": 1, "typ": "capability"}
    payload = {
        "schema_version": 1,
        "issuer_id": ISSUER,
        "key_id": key_id,
        "nonce": nonce,
        "nbf": nbf,
        "exp": exp,
        "artifact_identity_profile": "route_mutable_unverified",
        "action_binding": binding or base_binding(),
    }
    ph, pl = _b64u(_emit(header)), _b64u(_emit(payload))
    sig = _b64u(mac_envelope(key, b"ektel/capability/v1", ph, pl))
    return {"protected_header_b64": ph, "payload_b64": pl, "signature": sig}


def base_binding(stdin_digest: str = hashlib.sha256(b"").hexdigest(),
                 **overrides) -> dict:
    binding = {
        "action_id": "action-0001",
        "command_absolute": "/usr/bin/true",
        "args": [],
        "cwd": "/tmp",
        "env_allowlist_values": {"PATH": "/usr/bin:/bin"},
        "stdin_policy_digest": stdin_digest,
        "deadline_ms": DEADLINE_MS,
        "output_limits": dict(OUTPUT_LIMITS),
        "requested_guarantees": list(REQUESTED_GUARANTEES),
    }
    binding.update(overrides)
    return binding


def make_pop(cap_identity_digest: str, nonce_hex: str = NONCE_HEX,
             key: bytes = TEST_KEY) -> dict:
    nonce = bytes.fromhex(nonce_hex)
    digest_bytes = bytes.fromhex(cap_identity_digest)
    mac = mac_pop(key, nonce, digest_bytes).hex()
    return {
        "schema_version": 1,
        "nonce": nonce_hex,
        "payload_digest": cap_identity_digest,
        "mac": mac,
    }


def capability_identity_digest(envelope: dict) -> str:
    return hashlib.sha256(
        (envelope["protected_header_b64"] + "." + envelope["payload_b64"]).encode("ascii")
    ).hexdigest()


def make_request(env: dict | None = None, stdin: dict | None = None,
                 nonce: str = NONCE_HEX, **overrides) -> dict:
    """ActionRequest coherente con `make_capability_envelope()`."""
    doc = {
        "schema_version": 1,
        "action_id": "action-0001",
        "command_absolute": "/usr/bin/true",
        "args": [],
        "cwd": "/tmp",
        "env_allowlist_values": {"PATH": "/usr/bin:/bin"},
        "stdin_policy": stdin or {"kind": "empty"},
        "deadline_ms": DEADLINE_MS,
        "capability_envelope": env or make_capability_envelope(),
        "nonce": nonce,
        "repair_policy": "none",
        "output_limits": dict(OUTPUT_LIMITS),
        "requested_guarantees": list(REQUESTED_GUARANTEES),
        "metadata_opaque": "",
        "invocation_proof": {},
    }
    doc["invocation_proof"] = make_pop(
        capability_identity_digest(doc["capability_envelope"]), nonce)
    doc.update(overrides)
    return doc


def emit_request(doc: dict) -> bytes:
    return _emit(doc)


class MemoryReplayStore:
    """Double de pruebas del ReplayStore (en memoria, §7.4: sólo pruebas)."""

    def __init__(self, fail: bool = False) -> None:
        self._reserved: set[tuple[str, str]] = set()
        self._spent: set[str] = set()
        self.fail = fail

    def reserve_nonce(self, issuer_id: str, nonce: str,
                      reserve_until_wall: float) -> ReserveOutcome:
        if self.fail:
            return ReserveOutcome.UNAVAILABLE
        key = (issuer_id, nonce)
        if key in self._reserved:
            return ReserveOutcome.ALREADY_RESERVED
        self._reserved.add(key)
        return ReserveOutcome.RESERVED

    def consume_start_token(self, identity_digest: str):
        from src.ports.replay_store import ConsumeOutcome
        if self.fail:
            return ConsumeOutcome.UNAVAILABLE
        if identity_digest in self._spent:
            return ConsumeOutcome.ALREADY_SPENT
        self._spent.add(identity_digest)
        return ConsumeOutcome.CONSUMED

    def start_token_status(self, identity_digest: str) -> str:
        return "spent" if identity_digest in self._spent else "unspent"


class ScriptedPolicy:
    """Double del PolicyPort con decisión inyectable."""

    def __init__(self, decision) -> None:
        self.decision = decision
        self.calls: list[dict] = []

    def evaluate(self, request: Mapping[str, object]):
        self.calls.append(dict(request))
        return self.decision


class SpawnSpy:
    """Spy de la frontera instrumental (D-P4-α): contabiliza cruces."""

    def __init__(self) -> None:
        self.crossings: list[Admitted] = []

    def submit(self, admitted: Admitted) -> None:
        self.crossings.append(admitted)


def make_service(store=None, policy_port=None, policy_mode: str = "absent",
                 skew: float = 30.0, key: bytes = TEST_KEY) -> AdmissionService:
    return AdmissionService(
        replay_store=store if store is not None else MemoryReplayStore(),
        deployment_salt=TEST_SALT,
        operator_key=key,
        policy_port=policy_port,
        policy_mode=policy_mode,
        skew_tolerance_s=skew,
        wall_clock=lambda: NOW,
        mono_clock=lambda: 0.0,
    )


def valid_request_bytes(**overrides) -> bytes:
    return emit_request(make_request(**overrides))


class M1TestCase(unittest.TestCase):
    """Base con utilidades de aserción de outcomes."""
