#!/usr/bin/env python3
"""Parser de referencia B — CLEAN-ROOM (M0, spec v1.2 §15/M0 enmienda R5),
corregido tras la doble NO-GO externa (2026-08-20).

Protocolo clean-room declarado: este parser se escribió a partir de
- la especificación `docs/especificacion/ektel-runtime-m0-m3-v1.md` (§5, §6,
  §8.3, con las enmiendas del acta de corrección M0 2026-08-20),
- los schemas `contracts/schemas/v1/*.schema.json`,
- los vectores `contracts/vectors/v1/`,
SIN leer el código de `contracts/parsers/reference/`. Es table-driven: carga
los schemas en runtime e interpreta su subconjunto documentado (const, enum,
pattern con semántica Draft 2020-12 — coincidencia NO anclada; los schemas
auto-anclan sus patrones con ^ y fin absoluto (?![\\s\\S]), spec §5.7 —,
type+minimum/maximum, minLength/maxLength, required, additionalProperties,
$ref local, oneOf con discriminador const, allOf/if/then (unión por
state de execution-result, H3), unevaluatedProperties (cerrado por
check_union), format ektel-b64u-canonical).

Independencia (FIX-AND-RETRY, punto 6): este parser y el parser A fueron
corregidos en el mismo ciclo por el mismo agente, con conocimiento mutuo
de los hallazgos. El acuerdo A/B acredita convergencia frente al corpus
versionado, NO independencia estadística de dos autores aislados; la
mirada independiente queda a cargo de la re-verificación externa (acta
de corrección M0 §4.2).

Correcciones aplicadas (hallazgos externos):
- pattern pasa de re.fullmatch (reinterpretación del estándar) a
  re.search con semántica Draft 2020-12; los schemas v1 auto-anclan
  sus patrones y rechazan prefijos, sufijos y "\\n" final por sí
  mismos (spec §5.7, FIX-AND-RETRY);
- canonicalidad base64url en campos con format=ektel-b64u-canonical
  (ADR-010: bits residuales en cero, verificado re-codificando);
- uniones discriminadas por outcome (started sin handle_ref ya no pasa);
- iteración de campos en orden del schema (precedencia §5.6);
- bool nunca es int (schema_version: true → invalid_value, no
  invalid_type: el const/enum con igualdad de tipo estricto lo clasifica);
- capability: exp <= nbf → invalid_value (§6, ventana vacía).

Precedencia de diagnósticos (§5.6): size_exceeded → malformed_json →
duplicate_key → schema_version_unsupported (documento) → unknown_field →
missing_field → invalid_type → invalid_value; en sobres: estructura →
bad_base64 → bad_signature (MAC) → header (alg_unsupported,
schema_version_unsupported, typ) → payload.

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
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "v1"
SIZE_LIMIT = 65536  # techo global por documento (§5.1)

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

B64U_FULL = re.compile(r"[A-Za-z0-9_-]*")
HEX_FULL = re.compile(r"[0-9a-f]+")


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


# -- JSON estricto (§5.1) -----------------------------------------------------

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
    except RecursionError:
        # Anidamiento excesivo (M0-FAR-CLAUDE-01, ronda interna):
        # fail-closed como malformed_json, sin excepción al caller.
        return None, "malformed_json"


# -- Canonicalidad base64url (ADR-010) ----------------------------------------

def b64u_canonical(s: str) -> bool:
    """Sin padding, alfabeto cerrado y bits residuales en cero: se comprueba
    re-codificando (test de pertenencia, NO re-serialización para verificar)."""
    if not B64U_FULL.fullmatch(s):
        return False
    if len(s) % 4 == 1:
        return False
    try:
        decoded = urlsafe_b64decode(s + "=" * ((-len(s)) % 4))
    except ValueError:
        return False
    return urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == s


def b64u_decode(s: str) -> bytes:
    return urlsafe_b64decode(s + "=" * ((-len(s)) % 4))


# -- Intérprete del subconjunto de JSON Schema --------------------------------

_schemas_cache: dict[str, dict] = {}


def load_schema(name: str) -> dict:
    if name not in _schemas_cache:
        _schemas_cache[name] = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return _schemas_cache[name]


def _const_eq(value, option) -> bool:
    return value == option and type(value) is type(option)


def check(value, schema: dict) -> str | None:
    """Valida contra el subconjunto de contracts/schemas/v1. Orden por
    documento: unknown_field → missing_field → valor en orden del schema."""
    if "$ref" in schema:
        return check(value, load_schema(schema["$ref"]))
    # H2 (gate Claude): el TIPO se evalúa ANTES que const/enum — un valor
    # del tipo equivocado es invalid_type (precedencia §5.6), no
    # invalid_value. Con type declarado + enum/const: primero tipo.
    t = schema.get("type")
    if t is None and ("properties" in schema or "required" in schema
                      or "allOf" in schema or "if" in schema):
        # Sub-schema condicional (if/then/allOf de la unión por state, H3)
        # sin "type" explícito: se trata como objeto.
        t = "object"
    if t == "string" and not isinstance(value, str):
        return "invalid_type"
    if t == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        return "invalid_type"
    if t == "boolean" and not isinstance(value, bool):
        return "invalid_type"
    if t == "array" and not isinstance(value, list):
        return "invalid_type"
    if t == "object" and not isinstance(value, dict):
        return "invalid_type"
    if "const" in schema:
        return None if _const_eq(value, schema["const"]) else "invalid_value"
    if "enum" in schema:
        return None if any(_const_eq(value, o) for o in schema["enum"]) else "invalid_value"
    if t == "object":
        if not isinstance(value, dict):
            return "invalid_type"
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties")
        if "oneOf" in schema:
            return check_union(value, schema)
        if addl is False:
            for k in value:
                if k not in props:
                    return "unknown_field"
        for k in schema.get("required", []):
            if k not in value:
                return "missing_field"
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            return "invalid_value"
        for k in props:  # orden del schema (§5.6)
            if k in value:
                d = check(value[k], props[k])
                if d:
                    return d
        if isinstance(addl, dict):
            for k in value:
                if k not in props:
                    d = check(value[k], addl)
                    if d:
                        return d
        # allOf con if/then (unión discriminada por campo, H3): el `if`
        # matchea si la instancia lo valida; entonces se aplica el
        # `then` (required + properties por alternativa).
        for sub in schema.get("allOf", []):
            cond = sub.get("if")
            if cond is None or check(value, cond) is None:
                d = check(value, sub.get("then", {}))
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
        if schema.get("format") == "ektel-b64u-canonical" and not b64u_canonical(value):
            return "bad_base64"
        if "minLength" in schema and len(value) < schema["minLength"]:
            return "invalid_value"
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return "invalid_value"
        if "pattern" in schema and not re.search(schema["pattern"], value):
            # Semántica JSON Schema Draft 2020-12 (ECMA-262, NO anclada).
            # Los schemas v1 auto-anclan sus patrones (^ y fin absoluto
            # (?![\s\S])): rechazan prefijos, sufijos y newline final por
            # sí mismos (spec §5.7, FIX-AND-RETRY).
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


def _forbidden_by_not(value, alt: dict) -> bool:
    """Evalúa el subconjunto `not: {anyOf: [{required:[k]}...]}`."""
    neg = alt.get("not", {})
    for cond in neg.get("anyOf", []):
        if all(k in value for k in cond.get("required", [])):
            return True
    return False


def check_union(value, schema: dict) -> str | None:
    """oneOf con discriminador const: la alternativa se elige por el campo
    cuyo valor es const en todas las ramas; sus campos son obligatorios en
    ella y los de las otras, prohibidos (not/anyOf/required)."""
    base_props = schema.get("properties", {})
    alts = schema["oneOf"]
    disc = None
    for k in base_props:
        if all(k in a.get("properties", {}) and "const" in a["properties"][k] for a in alts):
            disc = k
            break
    if disc is None:
        return "invalid_value"
    allowed = set(base_props)
    for a in alts:
        allowed |= set(a.get("properties", {}))
    for k in value:
        if k not in allowed:
            return "unknown_field"
    for k in schema.get("required", []):
        if k not in value:
            return "missing_field"
    for k in base_props:  # orden del schema (§5.6)
        if k in value:
            d = check(value[k], base_props[k])
            if d:
                return d
    disc_val = value.get(disc)
    chosen = None
    for a in alts:
        if _const_eq(disc_val, a["properties"][disc]["const"]):
            chosen = a
            break
    if chosen is None:
        return "invalid_value"
    if _forbidden_by_not(value, chosen):
        return "unknown_field"
    for k in chosen.get("required", []):
        if k not in value and k not in schema.get("required", []):
            return "missing_field"
    for k in chosen.get("properties", {}):
        if k in value and k not in base_props:
            d = check(value[k], chosen["properties"][k])
            if d:
                return d
    return None


def schema_version_diag(value) -> str | None:
    """Regla uniforme de schema_version (FIX-AND-RETRY 2, B8): entero > 1 →
    schema_version_unsupported (versión mayor desconocida, §5.6); entero
    <= 0 y booleano caen en la validación de valor (invalid_value), no
    aquí."""
    if isinstance(value, dict):
        sv = value.get("schema_version")
        if isinstance(sv, int) and not isinstance(sv, bool) and sv > 1:
            return "schema_version_unsupported"
    return None


# -- Criptografía byte-exacta (§5.2, §6.4, §6.5, ADR-010) ---------------------

def envelope_mac(key: bytes, domain: str, phb64: str, plb64: str) -> bytes:
    msg = b"ektel/" + domain.encode("ascii") + b"/v1\x00" + phb64.encode() + b"." + plb64.encode()
    return hmac.new(key, msg, hashlib.sha256).digest()


# -- Parsers por tipo ----------------------------------------------------------

def parse_signed_envelope(wire_type: str, raw: bytes, key: bytes) -> ParseResult:
    env, diag = strict_json(raw)
    if diag:
        return reject(diag)
    diag = check(env, load_schema("envelope.schema.json"))
    if diag:
        return reject(diag)
    phb64, plb64, sig = env["protected_header_b64"], env["payload_b64"], env["signature"]
    # Verificar MAC ANTES de decodificar (§5.2); la canonicalidad ya quedó
    # comprobada por format=ektel-b64u-canonical en el schema del sobre.
    if not hmac.compare_digest(b64u_decode(sig),
                               envelope_mac(key, ENVELOPE_DOMAINS[wire_type], phb64, plb64)):
        return reject("bad_signature")
    header, diag = strict_json(b64u_decode(phb64))
    if diag:
        return reject(diag)
    if not isinstance(header, dict):
        return reject("invalid_type")
    if isinstance(header.get("alg"), str) and header["alg"] != "HS256":
        return reject("alg_unsupported")
    diag = schema_version_diag(header)
    if diag:
        return reject(diag)
    diag = check(header, load_schema("protected-header.schema.json"))
    if diag:
        return reject(diag)
    if header["typ"] != HEADER_TYP[wire_type]:
        return reject("invalid_value")
    payload, diag = strict_json(b64u_decode(plb64))
    if diag:
        return reject(diag)
    diag = schema_version_diag(payload)
    if diag:
        return reject(diag)
    diag = check(payload, load_schema(PAYLOAD_SCHEMA_FILES[wire_type]))
    if diag:
        return reject(diag)
    if wire_type == "capability-envelope" and payload["exp"] <= payload["nbf"]:
        return reject("invalid_value")  # ventana vacía (§6, corrección M0)
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
    raw = b64decode(doc["bytes"] + "=" * ((-len(doc["bytes"])) % 4))
    r = parse_wire(wire_type, raw, bytes.fromhex(key_hex))
    print(json.dumps({"verdict": r.verdict, "diagnostic": r.diagnostic,
                      "identity_digest": r.identity_digest}))
