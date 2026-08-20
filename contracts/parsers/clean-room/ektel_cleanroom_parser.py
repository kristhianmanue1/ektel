#!/usr/bin/env python3
"""Parser de referencia B — CLEAN-ROOM (M0, spec v1.2 §15/M0 enmienda R5).

Protocolo clean-room declarado: este parser se escribió a partir de
- la especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md` (§5, §6,
  §8.3),
- los schemas `contracts/schemas/v1/*.schema.json`,
- los vectores `contracts/vectors/v1/`,
SIN leer el código de `contracts/parsers/reference/`. A diferencia del parser
A (validación hand-coded), este interprete es table-driven: carga los schemas
JSON en runtime y aplica el subconjunto de JSON Schema que usan (const, enum,
pattern, type+minimum/maximum, required, additionalProperties, $ref local).

Reglas normativas implementadas (texto de la spec, no del parser A):
- §5.1 JSON estricto: NaN/Infinity fuera, claves duplicadas fuera, campos
  desconocidos fuera, sin coerción (bool ≠ int), límite de tamaño.
- §5.2 sobre fijo; base64url sin padding; verificar MAC ANTES de decodificar;
  MAC = HMAC-SHA256(clave, ASCII("ektel/<dominio>/v1")||0x00||phb64||"."||plb64);
  jamás re-serializar para verificar.
- §5.2/§6.3: alg lista cerrada {"HS256"}; schema_version mayor → rechazo.
- §6.4 PoP: HMAC sobre len32be(nonce)||nonce||digest_bytes con dominio
  ektel/pop/v1.
- §6.5 identity_digest = SHA256(phb64||"."||plb64) hex.

Vocabulario de diagnósticos (cerrado, común M0): ok, malformed_json,
duplicate_key, unknown_field, missing_field, invalid_type, invalid_value,
size_exceeded, bad_base64, bad_signature, alg_unsupported,
schema_version_unsupported.

stdlib-only (ADR-006). API EXPERIMENTAL (spec §16).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import struct
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "v1"
SIZE_LIMIT = 65536

# wire_type -> (schema file, dominio HMAC | None, es_sobre)
ENVELOPE_DOMAINS = {
    "capability-envelope": "capability",
    "admission-token": "admission",
    "termination-token": "termination",
}
PAYLOAD_SCHEMA_FILES = {
    "capability-envelope": "capability-payload.schema.json",
    "admission-token": "admission-token-payload.schema.json",
    "termination-token": "termination-token-payload.schema.json",
}
HEADER_TYP = {
    "capability-envelope": "capability",
    "admission-token": "admission-token",
    "termination-token": "termination-token",
}
DOCUMENT_SCHEMA_FILES = {
    "invocation-proof": "invocation-proof.schema.json",
    "action-request": "action-request.schema.json",
    "admission-outcome": "admission-outcome.schema.json",
    "start-outcome": "start-outcome.schema.json",
    "termination-outcome": "termination-outcome.schema.json",
    "execution-result": "execution-result.schema.json",
}

WIRE_TYPES = sorted(list(ENVELOPE_DOMAINS) + list(DOCUMENT_SCHEMA_FILES))

B64U_RE = re.compile(r"^[A-Za-z0-9_-]*$")
HEX_RE = re.compile(r"^[0-9a-f]+$")


@dataclass
class ParseResult:
    verdict: str
    diagnostic: str
    identity_digest: str | None = None
    value: object = None


def reject(diag: str) -> ParseResult:
    return ParseResult("reject", diag)


def accept(value, digest=None) -> ParseResult:
    return ParseResult("accept", "ok", identity_digest=digest, value=value)


# -- JSON estricto -----------------------------------------------------------

class DupKey(Exception):
    pass


def strict_json(raw: bytes):
    if len(raw) > SIZE_LIMIT:
        return None, "size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "malformed_json"

    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise DupKey(k)
            seen[k] = v
        return seen

    try:
        return json.loads(text, object_pairs_hook=hook,
                          parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c))), None
    except DupKey:
        return None, "duplicate_key"
    except ValueError:
        return None, "malformed_json"


# -- Intérprete del subconjunto de JSON Schema --------------------------------

def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def check(value, schema: dict) -> str | None:
    """Valida value contra el subconjunto usado en contracts/schemas/v1."""
    if "$ref" in schema:
        return check(value, load_schema(schema["$ref"]))
    if "const" in schema:
        if value != schema["const"] or type(value) is not type(schema["const"]):
            return "invalid_value"
        return None
    if "enum" in schema:
        for option in schema["enum"]:
            if value == option and type(value) is type(option):
                return None
        return "invalid_value"
    t = schema.get("type")
    if t == "object":
        if not isinstance(value, dict):
            return "invalid_type"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    return "unknown_field"
        for k in schema.get("required", []):
            if k not in value:
                return "missing_field"
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            return "invalid_value"
        addl = schema.get("additionalProperties")
        for k, v in value.items():
            if k in props:
                d = check(v, props[k])
            elif isinstance(addl, dict):
                d = check(v, addl)
            else:
                continue
            if d:
                return d
        return None
    if t == "array":
        if not isinstance(value, list):
            return "invalid_type"
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            return "invalid_value"
        item_schema = schema.get("items")
        if item_schema:
            for item in value:
                d = check(item, item_schema)
                if d:
                    return d
        return None
    if t == "string":
        if not isinstance(value, str):
            return "invalid_type"
        if "minLength" in schema and len(value) < schema["minLength"]:
            return "invalid_value"
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return "invalid_value"
        if "pattern" in schema and not re.search(schema["pattern"], value):
            return "invalid_value"
        return None
    if t == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return "invalid_type"
        if "minimum" in schema and value < schema["minimum"]:
            return "invalid_value"
        if "maximum" in schema and value > schema["maximum"]:
            return "invalid_value"
        return None
    if t == "boolean":
        return None if isinstance(value, bool) else "invalid_type"
    return None


def schema_version_diag(value) -> str | None:
    """schema_version mayor desconocida → diagnóstico propio (§5.5)."""
    if isinstance(value, dict):
        sv = value.get("schema_version")
        if isinstance(sv, int) and not isinstance(sv, bool) and sv != 1:
            return "schema_version_unsupported"
    return None


# -- Criptografía byte-exacta (§5.2, §6.4, §6.5) ------------------------------

def b64u_decode_strict(s: str) -> bytes:
    if not B64U_RE.match(s):
        raise ValueError("bad_base64")
    if len(s) % 4 == 1:
        raise ValueError("bad_base64")
    return urlsafe_b64decode(s + "=" * ((-len(s)) % 4))


def envelope_mac(key: bytes, domain: str, phb64: str, plb64: str) -> bytes:
    msg = b"ektel/" + domain.encode("ascii") + b"/v1\x00" + phb64.encode() + b"." + plb64.encode()
    return hmac.new(key, msg, hashlib.sha256).digest()


# -- Parsers por tipo ---------------------------------------------------------

def parse_signed_envelope(wire_type: str, raw: bytes, key: bytes) -> ParseResult:
    env, diag = strict_json(raw)
    if diag:
        return reject(diag)
    env_schema = load_schema("envelope.schema.json")
    diag = check(env, env_schema)
    if diag == "invalid_value" and isinstance(env, dict):
        # '=' (padding) u otro carácter fuera del alfabeto base64url en los
        # campos codificados es bad_base64, no invalid_value.
        for k in ("protected_header_b64", "payload_b64", "signature"):
            v = env.get(k)
            if isinstance(v, str) and not B64U_RE.match(v):
                return reject("bad_base64")
    if diag:
        return reject(diag)
    phb64, plb64, sig = env["protected_header_b64"], env["payload_b64"], env["signature"]
    # base64url estricto sin padding: '=' u otro carácter fuera del alfabeto
    # es bad_base64, no invalid_value.
    for field in (phb64, plb64, sig):
        if not B64U_RE.match(field) or len(field) % 4 == 1:
            return reject("bad_base64")
    try:
        sig_bytes = b64u_decode_strict(sig)
    except ValueError:
        return reject("bad_base64")
    # Verificar MAC ANTES de decodificar (§5.2).
    if not hmac.compare_digest(sig_bytes, envelope_mac(key, ENVELOPE_DOMAINS[wire_type], phb64, plb64)):
        return reject("bad_signature")
    try:
        header_raw = b64u_decode_strict(phb64)
        payload_raw = b64u_decode_strict(plb64)
    except ValueError:
        return reject("bad_base64")
    header, diag = strict_json(header_raw)
    if diag:
        return reject(diag)
    diag = check(header, load_schema("protected-header.schema.json"))
    if diag == "invalid_value" and isinstance(header, dict) and header.get("alg") != "HS256":
        return reject("alg_unsupported")
    if diag:
        return reject(diag)
    if header["typ"] != HEADER_TYP[wire_type]:
        return reject("invalid_value")
    payload, diag = strict_json(payload_raw)
    if diag:
        return reject(diag)
    diag = schema_version_diag(payload)
    if diag:
        return reject(diag)
    diag = check(payload, load_schema(PAYLOAD_SCHEMA_FILES[wire_type]))
    if diag:
        return reject(diag)
    digest = hashlib.sha256((phb64 + "." + plb64).encode("ascii")).hexdigest()
    return accept(payload, digest)


def parse_proof(raw: bytes, key: bytes) -> ParseResult:
    value, diag = strict_json(raw)
    if diag:
        return reject(diag)
    diag = schema_version_diag(value)
    if diag:
        return reject(diag)
    diag = check(value, load_schema("invocation-proof.schema.json"))
    if diag:
        return reject(diag)
    nonce = bytes.fromhex(value["nonce"])
    digest_bytes = bytes.fromhex(value["payload_digest"])
    mac = bytes.fromhex(value["mac"])
    msg = b"ektel/pop/v1\x00" + struct.pack(">I", len(nonce)) + nonce + digest_bytes
    if not hmac.compare_digest(mac, hmac.new(key, msg, hashlib.sha256).digest()):
        return reject("bad_signature")
    return accept(value)


def parse_strict_document(wire_type: str, raw: bytes) -> ParseResult:
    value, diag = strict_json(raw)
    if diag:
        return reject(diag)
    diag = schema_version_diag(value)
    if diag:
        return reject(diag)
    diag = check(value, load_schema(DOCUMENT_SCHEMA_FILES[wire_type]))
    if diag:
        return reject(diag)
    return accept(value)


def parse_wire(wire_type: str, raw: bytes, key: bytes) -> ParseResult:
    if wire_type in ENVELOPE_DOMAINS:
        return parse_signed_envelope(wire_type, raw, key)
    if wire_type == "invocation-proof":
        return parse_proof(raw, key)
    if wire_type in DOCUMENT_SCHEMA_FILES:
        return parse_strict_document(wire_type, raw)
    raise ValueError(f"wire type desconocido: {wire_type}")


if __name__ == "__main__":
    import sys
    from base64 import b64decode

    wire_type, vector_file, key_hex = sys.argv[1], sys.argv[2], sys.argv[3]
    doc = json.loads(open(vector_file, encoding="utf-8").read())
    r = parse_wire(wire_type, b64decode(doc["bytes"]), bytes.fromhex(key_hex))
    print(json.dumps({"verdict": r.verdict, "diagnostic": r.diagnostic, "identity_digest": r.identity_digest}))
