#!/usr/bin/env python3
"""Parser de referencia A para los wire types ektel v1 (M0).

Implementa el perfil byte-exacto de la spec v1.2 (§5, §6, §8.3):

- JSON estricto (§5.1): sin NaN/Infinity, sin claves duplicadas, sin campos
  desconocidos, sin coerción de tipos (bool no es int), sin versiones mayores.
- Sobres firmados (§5.2): estructura fija {protected_header_b64, payload_b64,
  signature}; base64url SIN padding; MAC verificado ANTES de decodificar;
  nunca re-serializa para verificar; MAC = HMAC-SHA256(key,
  ASCII("ektel/<dominio>/v1") || 0x00 || phb64 || "." || plb64).
- PoP (§6.4): HMAC-SHA256(key, "ektel/pop/v1" || 0x00 || len32be(nonce) ||
  nonce || digest_bytes).
- identity_digest = SHA256(ASCII(phb64) || "." || ASCII(plb64)) en hex.

Diagnósticos (vocabulario cerrado de parser, M0):
ok, malformed_json, duplicate_key, unknown_field, missing_field,
invalid_type, invalid_value, bad_base64, bad_signature, alg_unsupported,
schema_version_unsupported.

stdlib-only (ADR-006). API EXPERIMENTAL (spec §16): sin compromiso de
estabilidad hasta cerrar M0 con la prueba de implementación independiente.

Uso:
    from ektel_ref_parser import parse_wire
    result = parse_wire(wire_type, raw_bytes, key=test_key)
    result.verdict          # "accept" | "reject"
    result.diagnostic       # vocabulario cerrado
    result.identity_digest  # sólo en sobres aceptados
"""
from __future__ import annotations

import hashlib
import hmac
import json
import struct
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from typing import Any

B64U_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")

DOMAINS = {
    "capability": b"ektel/capability/v1\x00",
    "admission-token": b"ektel/admission/v1\x00",
    "termination-token": b"ektel/termination/v1\x00",
}

POP_DOMAIN = b"ektel/pop/v1\x00"

MAX_WIRE_BYTES = 65536


@dataclass
class ParseResult:
    verdict: str
    diagnostic: str
    identity_digest: str | None = None
    value: Any = None


def _reject(diagnostic: str) -> ParseResult:
    return ParseResult("reject", diagnostic)


def _accept(value: Any, identity_digest: str | None = None) -> ParseResult:
    return ParseResult("accept", "ok", identity_digest=identity_digest, value=value)


# ---------------------------------------------------------------------------
# JSON estricto (§5.1)
# ---------------------------------------------------------------------------

def _no_constant(_s: str) -> Any:
    raise ValueError("constant not allowed")


def _strict_loads(raw: bytes) -> tuple[Any, str | None]:
    """Devuelve (objeto, diagnostico_de_rechazo|None)."""
    if len(raw) > MAX_WIRE_BYTES:
        return None, "size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "malformed_json"

    def no_dupes(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise _DuplicateKey(k)
            obj[k] = v
        return obj

    try:
        value = json.loads(text, object_pairs_hook=no_dupes, parse_constant=_no_constant)
    except _DuplicateKey:
        return None, "duplicate_key"
    except (ValueError, json.JSONDecodeError):
        return None, "malformed_json"
    return value, None


class _DuplicateKey(Exception):
    pass


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_hex(s: Any, n: int) -> bool:
    return isinstance(s, str) and len(s) == n and all(c in "0123456789abcdef" for c in s)


# ---------------------------------------------------------------------------
# Validación estructural por campos (hand-coded, spec §5.1)
# ---------------------------------------------------------------------------

def _check_object(value: Any, spec: dict[str, tuple[str, Any]], required: set[str]) -> str | None:
    """spec: campo -> ("kind", extra). Devuelve diagnóstico o None.

    kinds: str, int, bool, enum, hex(n), b64u, object(sub), array_str,
    array_obj(sub), map_str, map_int, any
    """
    if not isinstance(value, dict):
        return "invalid_type"
    for key in value:
        if key not in spec:
            return "unknown_field"
    for key in required:
        if key not in value:
            return "missing_field"
    for key, (kind, extra) in spec.items():
        if key not in value:
            continue
        diag = _check_kind(value[key], kind, extra)
        if diag:
            return diag
    return None


def _check_kind(v: Any, kind: str, extra: Any) -> str | None:
    if kind == "str":
        if not isinstance(v, str):
            return "invalid_type"
        if extra and len(v) > extra:
            return "invalid_value"
    elif kind == "int":
        if not _is_int(v):
            return "invalid_type"
        if extra and not (extra[0] <= v <= extra[1]):
            return "invalid_value"
    elif kind == "bool":
        if not isinstance(v, bool):
            return "invalid_type"
    elif kind == "enum":
        if v not in extra:
            return "invalid_value"
    elif kind == "hex":
        if not _is_hex(v, extra):
            return "invalid_value"
    elif kind == "b64u":
        if not isinstance(v, str) or any(c not in B64U_ALPHABET for c in v):
            return "bad_base64"
    elif kind == "array_str":
        if not isinstance(v, list) or len(v) > extra:
            return "invalid_type"
        if any(not isinstance(i, str) for i in v):
            return "invalid_type"
    elif kind == "map_str":
        if not isinstance(v, dict) or len(v) > extra:
            return "invalid_type"
        if any(not isinstance(k, str) or not isinstance(i, str) for k, i in v.items()):
            return "invalid_type"
    elif kind == "object":
        return _check_object(v, extra[0], extra[1])
    elif kind == "array_obj":
        if not isinstance(v, list):
            return "invalid_type"
        for item in v:
            diag = _check_object(item, extra[0], extra[1])
            if diag:
                return diag
    elif kind == "any":
        return None
    return None


# ---------------------------------------------------------------------------
# Esquemas de campos (fiel a contracts/schemas/v1)
# ---------------------------------------------------------------------------

OUTPUT_LIMITS = ({"max_stdout_bytes": ("int", (0, 67108864)), "max_stderr_bytes": ("int", (0, 67108864))},
                 {"max_stdout_bytes", "max_stderr_bytes"})

GUARANTEE_ENTRY = ({
    "magnitude": ("str", 0), "class": ("enum", ["enforced", "reactive", "observed", "unsupported"]),
    "platform": ("str", 0), "mechanism": ("str", 0),
    "assumptions": ("array_str", 64), "known_escapes": ("array_str", 64),
    "failure_mode": ("str", 0), "evidence_ref": ("str", 0),
}, {"magnitude", "class", "platform", "mechanism", "assumptions", "known_escapes", "failure_mode", "evidence_ref"})

GUARANTEES_ENUM = ["runtime_supervision", "output_bounds", "audit_trail"]

ACTION_BINDING = ({
    "action_id": ("str", 128), "command_absolute": ("str", 0), "args": ("array_str", 256),
    "cwd": ("str", 0), "env_allowlist_values": ("map_str", 64),
    "stdin_policy_digest": ("hex", 64), "deadline_ms": ("int", (1, 3600000)),
    "output_limits": ("object", OUTPUT_LIMITS),
    "requested_guarantees": ("array_str", 16),
}, {"action_id", "command_absolute", "args", "cwd", "env_allowlist_values",
    "stdin_policy_digest", "deadline_ms", "output_limits", "requested_guarantees"})

CAPABILITY_PAYLOAD = ({
    "schema_version": ("enum", [1]), "issuer_id": ("str", 128), "key_id": ("hex", 16),
    "nonce": ("hex", 32), "nbf": ("int", None), "exp": ("int", None),
    "artifact_identity_profile": ("enum", ["route_mutable_unverified"]),
    "action_binding": ("object", ACTION_BINDING),
}, {"schema_version", "issuer_id", "key_id", "nonce", "nbf", "exp",
    "artifact_identity_profile", "action_binding"})

ADMISSION_TOKEN_PAYLOAD = ({
    "schema_version": ("enum", [1]), "identity_digest": ("hex", 64),
    "action_id": ("str", 128), "exp": ("int", None), "issuer_id": ("str", 128),
}, {"schema_version", "identity_digest", "action_id", "exp", "issuer_id"})

TERMINATION_TOKEN_PAYLOAD = ({
    "schema_version": ("enum", [1]), "action_id": ("str", 128), "identity_digest": ("hex", 64),
}, {"schema_version", "action_id", "identity_digest"})

PAYLOAD_SPECS = {
    "capability": CAPABILITY_PAYLOAD,
    "admission-token": ADMISSION_TOKEN_PAYLOAD,
    "termination-token": TERMINATION_TOKEN_PAYLOAD,
}

INVOCATION_PROOF = ({
    "schema_version": ("enum", [1]), "nonce": ("hex", 32),
    "payload_digest": ("hex", 64), "mac": ("hex", 64),
}, {"schema_version", "nonce", "payload_digest", "mac"})

STDIN_POLICY = ({
    "kind": ("enum", ["empty", "inline_b64"]),
    "data_b64": ("b64u", 0), "sha256": ("hex", 64),
}, {"kind"})

ACTION_REQUEST = ({
    "schema_version": ("enum", [1]), "action_id": ("str", 128),
    "command_absolute": ("str", 0), "args": ("array_str", 256), "cwd": ("str", 0),
    "env_allowlist_values": ("map_str", 64), "stdin_policy": ("object", STDIN_POLICY),
    "deadline_ms": ("int", (1, 3600000)),
    "capability_envelope": ("any", None), "invocation_proof": ("any", None),
    "nonce": ("hex", 32), "repair_policy": ("enum", ["none"]),
    "output_limits": ("object", OUTPUT_LIMITS),
    "requested_guarantees": ("array_str", 16), "metadata_opaque": ("str", 4096),
}, {"schema_version", "action_id", "command_absolute", "args", "cwd",
    "env_allowlist_values", "stdin_policy", "deadline_ms", "capability_envelope",
    "invocation_proof", "nonce", "repair_policy", "output_limits",
    "requested_guarantees", "metadata_opaque"})

ADMISSION_OUTCOME = ({
    "schema_version": ("enum", [1]), "outcome": ("enum", ["admitted", "admission_rejected"]),
    "admitted_action": ("str", 0), "identity_digest": ("hex", 64),
    "policy_receipt": ("str", 0), "guarantee_plan": ("array_obj", GUARANTEE_ENTRY),
    "reason_code": ("enum", ["malformed_descriptor", "capability_invalid", "capability_expired",
                             "capability_reused", "capability_rejected", "policy_denied",
                             "policy_unavailable", "audit_unavailable", "guarantee_unsupported"]),
    "safe_detail": ("str", 512), "retryable": ("bool", None), "evidence_receipt": ("str", 0),
}, {"schema_version", "outcome"})

START_OUTCOME = ({
    "schema_version": ("enum", [1]), "outcome": ("enum", ["started", "start_failed"]),
    "handle_ref": ("hex", 16),
    "reason_code": ("enum", ["start_failed", "start_failed_indeterminate", "capability_rejected"]),
    "safe_detail": ("str", 512),
}, {"schema_version", "outcome"})

TERMINATION_OUTCOME = ({
    "schema_version": ("enum", [1]), "outcome": ("enum", ["termination_accepted", "termination_rejected"]),
    "receipt": ("str", 0), "reason_code": ("enum", ["capability_rejected"]), "safe_detail": ("str", 512),
}, {"schema_version", "outcome"})

EXECUTION_RESULT = ({
    "schema_version": ("enum", [1]), "action_id": ("str", 128), "identity_digest": ("hex", 64),
    "state": ("enum", ["executed", "deadline_exceeded", "terminated", "supervision_failed"]),
    "artifact_identity_profile": ("enum", ["route_mutable_unverified"]),
    "started_at_wall": ("int", None), "finished_at_wall": ("int", None),
    "duration_monotonic_ms": ("int", None), "exit_code_or_signal": ("str", 0),
    "cause_code": ("enum", ["natural_exit", "deadline_duration", "deadline_validity_exhausted",
                            "external_termination", "supervision_failure"]),
    "validity_at_admission": ("object", ({"nbf": ("int", None), "exp": ("int", None)}, {"nbf", "exp"})),
    "guarantees_applied": ("array_obj", GUARANTEE_ENTRY),
    "measurements": ("any", None),
    "stdout_truncation": ("bool", None), "stderr_truncation": ("bool", None),
    "discarded_bytes": ("int", None), "last_event_receipt": ("str", 0),
}, {"schema_version", "action_id", "identity_digest", "state",
    "artifact_identity_profile", "guarantees_applied"})

DOCUMENT_SPECS = {
    "action-request": ACTION_REQUEST,
    "admission-outcome": ADMISSION_OUTCOME,
    "start-outcome": START_OUTCOME,
    "termination-outcome": TERMINATION_OUTCOME,
    "execution-result": EXECUTION_RESULT,
    "invocation-proof": INVOCATION_PROOF,
}


# ---------------------------------------------------------------------------
# Primitivas criptográficas (perfil byte-exacto v1, C2)
# ---------------------------------------------------------------------------

def _b64u_decode(s: str) -> bytes:
    if any(c not in B64U_ALPHABET for c in s):
        raise ValueError("bad_base64")
    pad = (-len(s)) % 4
    return urlsafe_b64decode(s + "=" * pad)


def _mac_envelope(key: bytes, typ: str, phb64: str, plb64: str) -> bytes:
    msg = DOMAINS[typ] + phb64.encode("ascii") + b"." + plb64.encode("ascii")
    return hmac.new(key, msg, hashlib.sha256).digest()


def identity_digest(phb64: str, plb64: str) -> str:
    return hashlib.sha256((phb64 + "." + plb64).encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------
# Parsers por wire type
# ---------------------------------------------------------------------------

ENVELOPE_SPEC = ({
    "protected_header_b64": ("b64u", 0), "payload_b64": ("b64u", 0), "signature": ("b64u", 0),
}, {"protected_header_b64", "payload_b64", "signature"})


def parse_envelope(typ: str, raw: bytes, key: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    diag = _check_object(value, *ENVELOPE_SPEC)
    if diag:
        return _reject(diag)
    phb64, plb64, sig = value["protected_header_b64"], value["payload_b64"], value["signature"]
    # Padding explícito: la cadena no debe decodificar a longitud con '='.
    for field in (phb64, plb64, sig):
        if len(field) % 4 == 1:
            return _reject("bad_base64")
    # Orden obligatorio: verificar MAC ANTES de decodificar (§5.2).
    try:
        sig_bytes = _b64u_decode(sig)
    except ValueError:
        return _reject("bad_base64")
    if len(sig_bytes) != 32:
        return _reject("bad_signature")
    expected = _mac_envelope(key, typ, phb64, plb64)
    if not hmac.compare_digest(sig_bytes, expected):
        return _reject("bad_signature")
    # Ahora sí, decodificar.
    try:
        header_raw = _b64u_decode(phb64)
        payload_raw = _b64u_decode(plb64)
    except ValueError:
        return _reject("bad_base64")
    header, diag = _strict_loads(header_raw)
    if diag:
        return _reject(diag)
    if not isinstance(header, dict):
        return _reject("invalid_type")
    if set(header) != {"alg", "schema_version", "typ"}:
        return _reject("unknown_field" if set(header) > {"alg", "schema_version", "typ"} else "missing_field")
    if header["alg"] != "HS256":
        return _reject("alg_unsupported")
    if header["schema_version"] != 1 or not _is_int(header["schema_version"]):
        return _reject("schema_version_unsupported")
    if header["typ"] != typ:
        return _reject("invalid_value")
    payload, diag = _strict_loads(payload_raw)
    if diag:
        return _reject(diag)
    spec, required = PAYLOAD_SPECS[typ]
    diag = _check_object(payload, spec, required)
    if diag == "invalid_value" and isinstance(payload, dict) and payload.get("schema_version") not in (None, 1):
        return _reject("schema_version_unsupported")
    if diag:
        return _reject(diag)
    return _accept(payload, identity_digest=identity_digest(phb64, plb64))


def parse_invocation_proof(raw: bytes, key: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    diag = _check_object(value, *INVOCATION_PROOF)
    if diag:
        return _reject(diag)
    nonce = bytes.fromhex(value["nonce"])
    digest_bytes = bytes.fromhex(value["payload_digest"])
    mac = bytes.fromhex(value["mac"])
    msg = POP_DOMAIN + struct.pack(">I", len(nonce)) + nonce + digest_bytes
    expected = hmac.new(key, msg, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        return _reject("bad_signature")
    return _accept(value)


def parse_document(wire_type: str, raw: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    spec, required = DOCUMENT_SPECS[wire_type]
    diag = _check_object(value, spec, required)
    if diag == "invalid_value" and isinstance(value, dict):
        sv = value.get("schema_version")
        if sv is not None and sv != 1:
            return _reject("schema_version_unsupported")
    if diag:
        return _reject(diag)
    return _accept(value)


def parse_wire(wire_type: str, raw: bytes, key: bytes) -> ParseResult:
    if wire_type in ENVELOPE_TYPES:
        return parse_envelope(ENVELOPE_TYPES[wire_type], raw, key)
    if wire_type == "invocation-proof":
        return parse_invocation_proof(raw, key)
    if wire_type in DOCUMENT_SPECS:
        return parse_document(wire_type, raw)
    raise ValueError(f"wire type desconocido: {wire_type}")


ENVELOPE_TYPES = {
    "capability-envelope": "capability",
    "admission-token": "admission-token",
    "termination-token": "termination-token",
}

WIRE_TYPES = sorted(list(ENVELOPE_TYPES) + ["invocation-proof"] + list(DOCUMENT_SPECS))


if __name__ == "__main__":
    import sys
    from base64 import b64decode

    wire_type, vector_file = sys.argv[1], sys.argv[2]
    doc = json.loads(open(vector_file, encoding="utf-8").read())
    test_key = bytes.fromhex(doc.get("test_key_hex", ""))
    raw = b64decode(doc["bytes"])
    r = parse_wire(wire_type, raw, test_key)
    print(json.dumps({"verdict": r.verdict, "diagnostic": r.diagnostic, "identity_digest": r.identity_digest}))
