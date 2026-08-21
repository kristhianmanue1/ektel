#!/usr/bin/env python3
r"""Parser de referencia A para los wire types ektel v1 (M0, corregido).

Implementa el perfil byte-exacto de la spec v1.2 (§5, §6, §8.3) con las
correcciones de la doble NO-GO externa (2026-08-20) y ADR-010:

- JSON estricto (§5.1): sin NaN/Infinity, sin claves duplicadas, sin campos
  desconocidos, sin coerción de tipos (bool NO es int), techo global de
  64 KiB por documento (§5.1 enmendado).
- pattern (§5.7): semántica JSON Schema Draft 2020-12 — coincidencia NO
  anclada (ECMA-262). Los patrones internos de este parser van
  auto-anclados (^ y fin absoluto (?![\s\S])) y rechazan prefijos,
  sufijos y newline final por sí mismos.
- Sobres firmados (§5.2): estructura fija; base64url SIN padding y CANÓNICO
  (bits residuales en cero, verificado re-codificando — ADR-010); MAC
  verificado ANTES de decodificar; nunca re-serializa para verificar.
  MAC = HMAC-SHA256(key, ASCII("ektel/<dominio>/v1") || 0x00 || phb64 || "."
  || plb64). identity_digest = SHA256(phb64 || "." || plb64) hex.
- PoP (§6.4): HMAC-SHA256(key, "ektel/pop/v1" || 0x00 || len32be(nonce) ||
  nonce || digest_bytes).
- Uniones discriminadas (§8.3): los outcomes validan por alternativa; los
  campos de una alternativa son obligatorios en ella y prohibidos fuera.
- Precedencia de diagnósticos fija (§5.6): size_exceeded → malformed_json →
  duplicate_key → schema_version_unsupported (documento) → unknown_field →
  missing_field → invalid_type → invalid_value; en sobres: estructura →
  bad_base64 (alfabeto/padding/canonicalidad) → bad_signature (MAC) →
  header (alg_unsupported, schema_version_unsupported, typ) → payload.

Diagnósticos (vocabulario cerrado de parser, M0):
ok, size_exceeded, malformed_json, duplicate_key, unknown_field,
missing_field, invalid_type, invalid_value, bad_base64, bad_signature,
alg_unsupported, schema_version_unsupported.

stdlib-only (ADR-006). API EXPERIMENTAL (spec §16).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import struct
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from typing import Any

SIZE_LIMIT = 65536  # techo global por documento (§5.1)

DOMAINS = {
    "capability": b"ektel/capability/v1\x00",
    "admission-token": b"ektel/admission/v1\x00",
    "termination-token": b"ektel/termination/v1\x00",
}
POP_DOMAIN = b"ektel/pop/v1\x00"

ENVELOPE_TYPES = {
    "capability-envelope": "capability",
    "admission-token": "admission-token",
    "termination-token": "termination-token",
}

B64U_RE = re.compile(r"[A-Za-z0-9_-]*")
HEX_RE = {}


def _hex_re(n: int) -> re.Pattern:
    if n not in HEX_RE:
        HEX_RE[n] = re.compile(r"^[0-9a-f]{%d}(?![\s\S])" % n)
    return HEX_RE[n]


@dataclass
class ParseResult:
    verdict: str
    diagnostic: str
    identity_digest: str | None = None
    value: Any = None


def _reject(d: str) -> ParseResult:
    return ParseResult("reject", d)


def _accept(v: Any, d: str | None = None) -> ParseResult:
    return ParseResult("accept", "ok", identity_digest=d, value=v)


# ---------------------------------------------------------------------------
# JSON estricto (§5.1)
# ---------------------------------------------------------------------------

class _DupKey(Exception):
    pass


def _strict_loads(raw: bytes):
    if len(raw) > SIZE_LIMIT:
        return None, "size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "malformed_json"

    def hook(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise _DupKey(k)
            obj[k] = v
        return obj

    try:
        return json.loads(text, object_pairs_hook=hook,
                          parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c))), None
    except _DupKey:
        return None, "duplicate_key"
    except ValueError:
        return None, "malformed_json"
    except RecursionError:
        # Anidamiento más profundo que la capacidad del decodificador
        # (dentro del techo de 64 KiB): fail-closed como malformed_json
        # (hallazgo de la ronda adversarial interna M0-FAR-CLAUDE-01;
        # asiento normativo §5.1 de la spec). Nunca excepción al caller.
        return None, "malformed_json"


# ---------------------------------------------------------------------------
# Motor de validación por campos (hand-coded, fiel a contracts/schemas/v1)
# Precedencia por documento: unknown_field → missing_field → checks de valor
# en orden declarado por el schema (§5.6).
# ---------------------------------------------------------------------------

def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_fields(value: Any, fields: list[tuple[str, dict]], required: set[str]) -> str | None:
    if not isinstance(value, dict):
        return "invalid_type"
    known = {name for name, _ in fields}
    for key in value:
        if key not in known:
            return "unknown_field"
    for key in required:
        if key not in value:
            return "missing_field"
    for name, spec in fields:
        if name in value:
            diag = _check_value(value[name], spec)
            if diag:
                return diag
    return None


def _check_value(v: Any, spec: dict) -> str | None:
    t = spec["t"]
    if t == "str":
        if not isinstance(v, str):
            return "invalid_type"
        if "min" in spec and len(v) < spec["min"]:
            return "invalid_value"
        if "max" in spec and len(v) > spec["max"]:
            return "invalid_value"
        if "pattern" in spec and not spec["pattern"].search(v):
            # Semántica JSON Schema Draft 2020-12: pattern NO anclada
            # (ECMA-262). Los patrones internos van auto-anclados con
            # ^ y fin absoluto (?![\s\S]) — rechazan prefijos, sufijos y
            # newline final por sí mismos (spec §5.7, FIX-AND-RETRY).
            return "invalid_value"
        return None
    if t == "int":
        if not _is_int(v):
            return "invalid_type"
        if "min" in spec and v < spec["min"]:
            return "invalid_value"
        if "max" in spec and v > spec["max"]:
            return "invalid_value"
        return None
    if t == "bool":
        return None if isinstance(v, bool) else "invalid_type"
    if t == "b64c":
        if not isinstance(v, str):
            return "invalid_type"
        if not _b64u_canonical(v):
            return "bad_base64"
        if "min" in spec and len(v) < spec["min"]:
            return "invalid_value"
        if "exact" in spec and len(v) != spec["exact"]:
            return "invalid_value"
        return None
    if t == "enum":
        # H3 (gate Claude): si el schema declara tipo para el campo (p. ej.
        # protected-header.typ: type string + enum), el tipo se comprueba
        # ANTES de la pertenencia (invalid_type precede a invalid_value,
        # §5.6). Sin tipo declarado (outcome, kind, state…), enum sólo da
        # invalid_value.
        vt = spec.get("vt")
        if vt == "str" and not isinstance(v, str):
            return "invalid_type"
        for option in spec["vals"]:
            if v == option and type(v) is type(option):
                return None
        return "invalid_value"
    if t == "list_str":
        if not isinstance(v, list) or any(not isinstance(i, str) for i in v):
            return "invalid_type"
        if len(v) > spec.get("max_items", 1024):
            return "invalid_value"
        if "vals" in spec:
            for i in v:
                if i not in spec["vals"]:
                    return "invalid_value"
        return None
    if t == "map_str":
        if not isinstance(v, dict) or any(not isinstance(k, str) or not isinstance(i, str) for k, i in v.items()):
            return "invalid_type"
        if len(v) > spec.get("max_props", 1024):
            return "invalid_value"
        return None
    if t == "map_int":
        if not isinstance(v, dict) or any(not isinstance(k, str) or not _is_int(i) for k, i in v.items()):
            return "invalid_type"
        return None
    if t == "obj":
        return _check_fields(v, spec["fields"], spec["req"])
    if t == "list_obj":
        if not isinstance(v, list):
            return "invalid_type"
        for item in v:
            diag = _check_fields(item, spec["fields"], spec["req"])
            if diag:
                return diag
        return None
    raise AssertionError(f"tipo de spec desconocido: {t}")


def _sv_field() -> tuple[str, dict]:
    return ("schema_version", {"t": "enum", "vals": [1]})


# ---------------------------------------------------------------------------
# Tablas de campos (orden = precedencia de §5.6)
# ---------------------------------------------------------------------------

def _output_limits() -> dict:
    return {"t": "obj", "fields": [
        ("max_stdout_bytes", {"t": "int", "min": 0, "max": 67108864}),
        ("max_stderr_bytes", {"t": "int", "min": 0, "max": 67108864}),
    ], "req": {"max_stdout_bytes", "max_stderr_bytes"}}


GUARANTEE_CLASSES = ["enforced", "reactive", "observed", "unsupported"]
REQUESTED_GUARANTEES = ["runtime_supervision", "output_bounds", "audit_trail"]


def _guarantee_entry() -> dict:
    return {"t": "list_obj", "fields": [
        ("magnitude", {"t": "str", "min": 1}),
        ("class", {"t": "enum", "vals": GUARANTEE_CLASSES}),
        ("platform", {"t": "str", "min": 1}),
        ("mechanism", {"t": "str", "min": 1}),
        ("assumptions", {"t": "list_str", "max_items": 64}),
        ("known_escapes", {"t": "list_str", "max_items": 64}),
        ("failure_mode", {"t": "str", "min": 1}),
        ("evidence_ref", {"t": "str"}),
    ], "req": {"magnitude", "class", "platform", "mechanism", "assumptions",
               "known_escapes", "failure_mode", "evidence_ref"}}


CAPABILITY_PAYLOAD = ([
    _sv_field(),
    ("issuer_id", {"t": "str", "min": 1, "max": 128}),
    ("key_id", {"t": "str", "pattern": _hex_re(16)}),
    ("nonce", {"t": "str", "pattern": _hex_re(32)}),
    ("nbf", {"t": "int", "min": 0}),
    ("exp", {"t": "int", "min": 0}),
    ("artifact_identity_profile", {"t": "enum", "vals": ["route_mutable_unverified"]}),
    ("action_binding", {"t": "obj", "fields": [
        ("action_id", {"t": "str", "min": 1, "max": 128}),
        ("command_absolute", {"t": "str", "pattern": re.compile(r"^/[^\r\n\u2028\u2029]*(?![\s\S])")}),
        ("args", {"t": "list_str", "max_items": 256}),
        ("cwd", {"t": "str", "pattern": re.compile(r"^/[^\r\n\u2028\u2029]*(?![\s\S])")}),
        ("env_allowlist_values", {"t": "map_str", "max_props": 64}),
        ("stdin_policy_digest", {"t": "str", "pattern": _hex_re(64)}),
        ("deadline_ms", {"t": "int", "min": 1, "max": 3600000}),
        ("output_limits", _output_limits()),
        ("requested_guarantees", {"t": "list_str", "max_items": 16, "vals": REQUESTED_GUARANTEES}),
    ], "req": {"action_id", "command_absolute", "args", "cwd", "env_allowlist_values",
               "stdin_policy_digest", "deadline_ms", "output_limits", "requested_guarantees"}}),
], {"schema_version", "issuer_id", "key_id", "nonce", "nbf", "exp",
    "artifact_identity_profile", "action_binding"})

ADMISSION_TOKEN_PAYLOAD = ([
    _sv_field(),
    ("identity_digest", {"t": "str", "pattern": _hex_re(64)}),
    ("action_id", {"t": "str", "min": 1, "max": 128}),
    ("exp", {"t": "int", "min": 0}),
    ("issuer_id", {"t": "str", "min": 1, "max": 128}),
], {"schema_version", "identity_digest", "action_id", "exp", "issuer_id"})

TERMINATION_TOKEN_PAYLOAD = ([
    _sv_field(),
    ("action_id", {"t": "str", "min": 1, "max": 128}),
    ("identity_digest", {"t": "str", "pattern": _hex_re(64)}),
], {"schema_version", "action_id", "identity_digest"})

PAYLOAD_SPECS = {
    "capability": CAPABILITY_PAYLOAD,
    "admission-token": ADMISSION_TOKEN_PAYLOAD,
    "termination-token": TERMINATION_TOKEN_PAYLOAD,
}

INVOCATION_PROOF = ([
    _sv_field(),
    ("nonce", {"t": "str", "pattern": _hex_re(32)}),
    ("payload_digest", {"t": "str", "pattern": _hex_re(64)}),
    ("mac", {"t": "str", "pattern": _hex_re(64)}),
], {"schema_version", "nonce", "payload_digest", "mac"})

ENVELOPE_FIELDS = ([
    ("protected_header_b64", {"t": "b64c", "min": 1}),
    ("payload_b64", {"t": "b64c", "min": 1}),
    # Longitud exacta 43 = HMAC-SHA256 (32 bytes) en base64url sin padding;
    # es parte del pattern del schema (envelope.schema.json) y se valida
    # ANTES del MAC (hallazgo del fuzz diferencial versionado 2026-08-20).
    ("signature", {"t": "b64c", "min": 1, "exact": 43}),
], {"protected_header_b64", "payload_b64", "signature"})

HEADER_FIELDS = ([
    ("alg", {"t": "enum", "vals": ["HS256"]}),  # const en el schema: sin tipo declarado
    _sv_field(),
    ("typ", {"t": "enum", "vals": ["capability", "admission-token", "termination-token"], "vt": "str"}),
], {"alg", "schema_version", "typ"})

STDIN_POLICY = {"t": "obj", "fields": [
    ("kind", {"t": "enum", "vals": ["empty", "inline_b64"]}),
    ("data_b64", {"t": "b64c"}),
    ("sha256", {"t": "str", "pattern": _hex_re(64)}),
], "req": {"kind"}}

ACTION_REQUEST = ([
    _sv_field(),
    ("action_id", {"t": "str", "min": 1, "max": 128}),
    ("command_absolute", {"t": "str", "pattern": re.compile(r"^/[^\r\n\u2028\u2029]*(?![\s\S])")}),
    ("args", {"t": "list_str", "max_items": 256}),
    ("cwd", {"t": "str", "pattern": re.compile(r"^/[^\r\n\u2028\u2029]*(?![\s\S])")}),
    ("env_allowlist_values", {"t": "map_str", "max_props": 64}),
    ("stdin_policy", STDIN_POLICY),
    ("deadline_ms", {"t": "int", "min": 1, "max": 3600000}),
    ("capability_envelope", {"t": "obj", "fields": ENVELOPE_FIELDS[0], "req": ENVELOPE_FIELDS[1]}),
    ("invocation_proof", {"t": "obj", "fields": INVOCATION_PROOF[0], "req": INVOCATION_PROOF[1]}),
    ("nonce", {"t": "str", "pattern": _hex_re(32)}),
    ("repair_policy", {"t": "enum", "vals": ["none"]}),
    ("output_limits", _output_limits()),
    ("requested_guarantees", {"t": "list_str", "max_items": 16, "vals": REQUESTED_GUARANTEES}),
    ("metadata_opaque", {"t": "str", "max": 4096}),
], {"schema_version", "action_id", "command_absolute", "args", "cwd",
    "env_allowlist_values", "stdin_policy", "deadline_ms", "capability_envelope",
    "invocation_proof", "nonce", "repair_policy", "output_limits",
    "requested_guarantees", "metadata_opaque"})

ADMISSION_REASON_CODES = [
    "malformed_descriptor", "capability_rejected", "policy_denied",
    "policy_unavailable", "audit_unavailable", "guarantee_unsupported",
]

# Uniones discriminadas (§8.3): campo discriminador -> alternativa ->
# (campos de la alternativa, obligatorios de la alternativa, prohibidos del resto)
def _union(disc: str, common: list[tuple[str, dict]], common_req: set[str],
           alts: dict[Any, tuple[list[tuple[str, dict]], set[str]]]):
    return (disc, common, common_req, alts)


ADMISSION_OUTCOME_UNION = _union(
    "outcome",
    [_sv_field()],
    {"schema_version", "outcome"},
    {
        "admitted": ([
            ("admitted_action", {"t": "str", "min": 1}),
            ("identity_digest", {"t": "str", "pattern": _hex_re(64)}),
            ("policy_receipt", {"t": "str"}),
            ("guarantee_plan", _guarantee_entry()),
        ], {"admitted_action", "identity_digest", "guarantee_plan"}),
        "admission_rejected": ([
            ("reason_code", {"t": "enum", "vals": ADMISSION_REASON_CODES}),
            ("safe_detail", {"t": "str", "max": 512}),
            ("retryable", {"t": "bool"}),
            ("evidence_receipt", {"t": "str"}),
        ], {"reason_code", "safe_detail", "retryable"}),
    },
)

START_OUTCOME_UNION = _union(
    "outcome",
    [_sv_field()],
    {"schema_version", "outcome"},
    {
        "started": ([("handle_ref", {"t": "str", "pattern": _hex_re(16)})], {"handle_ref"}),
        "start_failed": ([
            ("reason_code", {"t": "enum", "vals": ["start_failed", "start_failed_indeterminate",
                                                   "capability_rejected"]}),
            ("safe_detail", {"t": "str", "max": 512}),
        ], {"reason_code"}),
    },
)

TERMINATION_OUTCOME_UNION = _union(
    "outcome",
    [_sv_field()],
    {"schema_version", "outcome"},
    {
        "termination_accepted": ([("receipt", {"t": "str", "min": 1})], {"receipt"}),
        "termination_rejected": ([
            ("reason_code", {"t": "enum", "vals": ["capability_rejected"]}),
            ("safe_detail", {"t": "str", "max": 512}),
        ], {"reason_code"}),
    },
)

UNION_SPECS = {
    "admission-outcome": ADMISSION_OUTCOME_UNION,
    "start-outcome": START_OUTCOME_UNION,
    "termination-outcome": TERMINATION_OUTCOME_UNION,
}

EXECUTION_RESULT = ([
    _sv_field(),
    ("action_id", {"t": "str", "min": 1, "max": 128}),
    ("identity_digest", {"t": "str", "pattern": _hex_re(64)}),
    ("state", {"t": "enum", "vals": ["executed", "deadline_exceeded", "terminated", "supervision_failed"]}),
    ("artifact_identity_profile", {"t": "enum", "vals": ["route_mutable_unverified"]}),
    ("started_at_wall", {"t": "int", "min": 0}),
    ("finished_at_wall", {"t": "int", "min": 0}),
    ("duration_monotonic_ms", {"t": "int", "min": 0}),
    ("exit_code_or_signal", {"t": "str"}),
    ("cause_code", {"t": "enum", "vals": ["natural_exit", "deadline_duration",
                                          "deadline_validity_exhausted",
                                          "external_termination", "supervision_failure"]}),
    ("validity_at_admission", {"t": "obj", "fields": [
        ("nbf", {"t": "int", "min": 0}), ("exp", {"t": "int", "min": 0}),
    ], "req": {"nbf", "exp"}}),
    ("guarantees_applied", _guarantee_entry()),
    ("measurements", {"t": "map_int"}),
    ("stdout_truncation", {"t": "bool"}),
    ("stderr_truncation", {"t": "bool"}),
    ("discarded_bytes", {"t": "int", "min": 0}),
    ("last_event_receipt", {"t": "str"}),
], {"schema_version", "action_id", "identity_digest", "state",
    "artifact_identity_profile", "guarantees_applied",
    "cause_code", "discarded_bytes"})

# Unión discriminada por state (corrección H3): cada estado exige causa
# compatible y evidencia suficiente y obtenible; supervision_failed no
# exige tiempos (la evidencia puede no existir). discarded_bytes es
# siempre obligatorio (0 cuando no hubo truncación) — decisión (a).
_STATE_CAUSES = {
    "executed": {"natural_exit"},
    "deadline_exceeded": {"deadline_duration", "deadline_validity_exhausted"},
    "terminated": {"external_termination"},
    "supervision_failed": {"supervision_failure"},
}
_STATE_EXTRA_REQUIRED = {
    "executed": {"started_at_wall", "finished_at_wall", "duration_monotonic_ms",
                 "stdout_truncation", "stderr_truncation"},
    "deadline_exceeded": {"started_at_wall", "finished_at_wall", "duration_monotonic_ms",
                          "stdout_truncation", "stderr_truncation"},
    "terminated": {"started_at_wall", "finished_at_wall", "duration_monotonic_ms",
                   "stdout_truncation", "stderr_truncation"},
    "supervision_failed": set(),
}


def _check_execution_result_state(value: dict) -> str | None:
    state = value.get("state")
    if state not in _STATE_CAUSES:
        return "invalid_value"  # cubierto por el enum de la tabla; defensivo
    for key in _STATE_EXTRA_REQUIRED[state]:
        if key not in value:
            return "missing_field"
    if value.get("cause_code") not in _STATE_CAUSES[state]:
        return "invalid_value"
    return None

DOCUMENT_SPECS = {
    "action-request": ACTION_REQUEST,
    "execution-result": EXECUTION_RESULT,
}


# ---------------------------------------------------------------------------
# Primitivas criptográficas (perfil byte-exacto v1, C2 + ADR-010)
# ---------------------------------------------------------------------------

def _b64u_canonical(s: str) -> bool:
    """base64url estricto, sin padding y CANÓNICO (ADR-010): los bits
    residuales deben ser cero; se comprueba re-codificando (test de
    pertenencia al conjunto canónico, no re-serialización para verificar)."""
    if not B64U_RE.fullmatch(s):
        return False
    if len(s) % 4 == 1:
        return False
    try:
        decoded = urlsafe_b64decode(s + "=" * ((-len(s)) % 4))
    except ValueError:
        return False
    return urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == s


def _b64u_decode(s: str) -> bytes:
    return urlsafe_b64decode(s + "=" * ((-len(s)) % 4))


def _mac_envelope(key: bytes, typ: str, phb64: str, plb64: str) -> bytes:
    return hmac.new(key, DOMAINS[typ] + phb64.encode("ascii") + b"." + plb64.encode("ascii"),
                    hashlib.sha256).digest()


def identity_digest(phb64: str, plb64: str) -> str:
    return hashlib.sha256((phb64 + "." + plb64).encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------
# Parsers por wire type
# ---------------------------------------------------------------------------

def parse_envelope(typ: str, raw: bytes, key: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    diag = _check_fields(value, *ENVELOPE_FIELDS)
    if diag:
        return _reject(diag)
    phb64, plb64, sig = (value["protected_header_b64"], value["payload_b64"], value["signature"])
    for field in (phb64, plb64, sig):
        if not _b64u_canonical(field):
            return _reject("bad_base64")
    # Orden obligatorio: MAC ANTES de decodificar (§5.2).
    if not hmac.compare_digest(_b64u_decode(sig), _mac_envelope(key, typ, phb64, plb64)):
        return _reject("bad_signature")
    header, diag = _strict_loads(_b64u_decode(phb64))
    if diag:
        return _reject(diag)
    if not isinstance(header, dict):
        return _reject("invalid_type")
    if isinstance(header.get("alg"), str) and header["alg"] != "HS256":
        return _reject("alg_unsupported")
    hv = header.get("schema_version")
    if _is_int(hv) and hv > 1:
        return _reject("schema_version_unsupported")
    diag = _check_fields(header, *HEADER_FIELDS)
    if diag:
        return _reject(diag)
    if header["typ"] != typ:
        return _reject("invalid_value")
    payload, diag = _strict_loads(_b64u_decode(plb64))
    if diag:
        return _reject(diag)
    if isinstance(payload, dict):
        sv = payload.get("schema_version")
        if _is_int(sv) and sv > 1:
            return _reject("schema_version_unsupported")
    diag = _check_fields(payload, *PAYLOAD_SPECS[typ])
    if diag:
        return _reject(diag)
    if typ == "capability" and payload["exp"] <= payload["nbf"]:
        return _reject("invalid_value")  # exp <= nbf: ventana vacía (§6, acta corrección M0)
    return _accept(payload, identity_digest(phb64, plb64))


def parse_invocation_proof(raw: bytes, key: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    # Regla uniforme de schema_version (FIX-AND-RETRY 2, B8): entero > 1 →
    # versión mayor desconocida; <= 0 y bool caen en la validación de valor.
    if isinstance(value, dict):
        sv = value.get("schema_version")
        if _is_int(sv) and sv > 1:
            return _reject("schema_version_unsupported")
    diag = _check_fields(value, *INVOCATION_PROOF)
    if diag:
        return _reject(diag)
    nonce = bytes.fromhex(value["nonce"])
    digest_bytes = bytes.fromhex(value["payload_digest"])
    mac = bytes.fromhex(value["mac"])
    msg = POP_DOMAIN + struct.pack(">I", len(nonce)) + nonce + digest_bytes
    if not hmac.compare_digest(mac, hmac.new(key, msg, hashlib.sha256).digest()):
        return _reject("bad_signature")
    return _accept(value)


def _parse_union(value: Any, union) -> str | None:
    disc, common, common_req, alts = union
    if not isinstance(value, dict):
        return "invalid_type"
    alt_fields = {k: {n for n, _ in f} for k, (f, _) in alts.items()}
    allowed = {n for n, _ in common} | {disc} | set().union(*alt_fields.values())
    for key in value:
        if key not in allowed:
            return "unknown_field"
    for key in common_req:
        if key not in value:
            return "missing_field"
    for name, spec in common:
        if name in value:
            diag = _check_value(value[name], spec)
            if diag:
                return diag
    disc_val = value.get(disc)
    # H1 (gate Claude): el discriminador es dato no confiable — su tipo se
    # valida ANTES de usarlo como clave (unhashable no provoca excepción).
    # Sin tipo declarado para el discriminador en el schema raíz (sólo
    # enum/const), un valor de tipo equivocado cae como invalid_value.
    if isinstance(disc_val, (list, dict, set, bytearray)):
        return "invalid_value"
    if disc_val not in alts:
        return "invalid_value"
    alt_spec, alt_req = alts[disc_val]
    forbidden = set().union(*(alt_fields[k] for k in alts if k != disc_val)) - {n for n, _ in alt_spec}
    for key in value:
        if key in forbidden:
            return "unknown_field"
    for key in alt_req:
        if key not in value:
            return "missing_field"
    for name, spec in alt_spec:
        if name in value:
            diag = _check_value(value[name], spec)
            if diag:
                return diag
    return None


def parse_document(wire_type: str, raw: bytes) -> ParseResult:
    value, diag = _strict_loads(raw)
    if diag:
        return _reject(diag)
    if isinstance(value, dict):
        sv = value.get("schema_version")
        if _is_int(sv) and sv > 1:
            return _reject("schema_version_unsupported")
    if wire_type in UNION_SPECS:
        diag = _parse_union(value, UNION_SPECS[wire_type])
    else:
        diag = _check_fields(value, *DOCUMENT_SPECS[wire_type])
        if diag is None and wire_type == "execution-result" and isinstance(value, dict):
            diag = _check_execution_result_state(value)  # unión por state (H3)
    if diag:
        return _reject(diag)
    return _accept(value)


def parse_wire(wire_type: str, raw: bytes, key: bytes) -> ParseResult:
    if wire_type in ENVELOPE_TYPES:
        return parse_envelope(ENVELOPE_TYPES[wire_type], raw, key)
    if wire_type == "invocation-proof":
        return parse_invocation_proof(raw, key)
    if wire_type in UNION_SPECS or wire_type in DOCUMENT_SPECS:
        return parse_document(wire_type, raw)
    raise ValueError(f"wire type desconocido: {wire_type}")


WIRE_TYPES = sorted(list(ENVELOPE_TYPES) + ["invocation-proof"] +
                    list(UNION_SPECS) + list(DOCUMENT_SPECS))


if __name__ == "__main__":
    import sys
    from base64 import b64decode

    wire_type, vector_file, key_hex = sys.argv[1], sys.argv[2], sys.argv[3]
    doc = json.loads(open(vector_file, encoding="utf-8").read())
    raw = b64decode(doc["bytes"] + "=" * ((-len(doc["bytes"])) % 4))
    r = parse_wire(wire_type, raw, bytes.fromhex(key_hex))
    print(json.dumps({"verdict": r.verdict, "diagnostic": r.diagnostic,
                      "identity_digest": r.identity_digest}))
