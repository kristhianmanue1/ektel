"""Token de admisión — `admitted_action` (spec v1.2 §6.6, B2/C4).

Sobre firmado estándar (§5.2, dominio `ektel/admission/v1`) con payload v1
`{schema_version, identity_digest, action_id, exp, issuer_id}`. Valor opaco
devuelto por `admit` en `Admitted.admitted_action`; `start` (M2) deberá
re-verificar integridad, vigencia y consumo único (dos registros CAS,
§7.4). En M1 sólo se emite: la compuerta de spawn es instrumental (D-P4-α)
y no existe API `start` productiva.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import hashlib
from base64 import urlsafe_b64encode

from . import contract_layer
from .crypto import DOMAIN_ADMISSION, mac_envelope


def build_admission_token(operator_key: bytes, identity_digest: str,
                          action_id: str, exp_wall: int,
                          issuer_id: str) -> str:
    """Emite `admitted_action` = b64url del sobre de admisión (§6.6)."""
    header = {"alg": "HS256", "schema_version": 1, "typ": "admission-token"}
    payload = {
        "schema_version": 1,
        "identity_digest": identity_digest,
        "action_id": action_id,
        "exp": exp_wall,
        "issuer_id": issuer_id,
    }
    ph_b64 = _b64u(contract_layer.emit_canonical(header))
    pl_b64 = _b64u(contract_layer.emit_canonical(payload))
    sig = _b64u(mac_envelope(operator_key, DOMAIN_ADMISSION, ph_b64, pl_b64))
    token = {"protected_header_b64": ph_b64, "payload_b64": pl_b64, "signature": sig}
    return _b64u(contract_layer.emit_canonical(token))


def admission_token_digest(admitted_action: str) -> str:
    """Digest de trazabilidad del token (sólo para tests/diagnóstico)."""
    return hashlib.sha256(admitted_action.encode("ascii")).hexdigest()


def _b64u(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
