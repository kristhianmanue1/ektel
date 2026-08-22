"""Verificación de la proof-of-possession anidada (ADR-003 §1.5, spec §5.8).

Dos partes:

1. Capa de contrato + cripto del documento PoP re-emitido (dominio
   `ektel/pop/v1`, MAC sobre `len32be(nonce) || nonce || payload_digest`)
   — diagnóstico §5.6 → `capability_rejected`.
2. Coherencia con la capacidad y el descriptor (regla 2 final paso 4):
   `payload_digest` == `identity_digest` de la capacidad autenticada y
   `nonce` == nonce del descriptor — el nonce queda ligado al descriptor
   concreto y no es reusable con otro payload bajo la misma capacidad.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from . import contract_layer


def verify_invocation_proof(proof_dict: dict[str, object], operator_key: bytes,
                            capability_identity_digest: str,
                            descriptor_nonce: str) -> str | None:
    """Devuelve un detalle safe de rechazo (→ `capability_rejected`) o
    `None` si la PoP es válida y coherente."""
    result = contract_layer.parse_invocation_proof(proof_dict, operator_key)
    if result.verdict != "accept":
        return f"contract:{result.diagnostic}"
    proof = result.value
    if proof.get("payload_digest") != capability_identity_digest:
        return "pop:payload-digest-mismatch"
    if proof.get("nonce") != descriptor_nonce:
        return "pop:nonce-mismatch"
    return None
