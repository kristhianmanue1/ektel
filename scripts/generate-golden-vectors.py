#!/usr/bin/env python3
"""Generador determinista de vectores dorados M0 (spec v1.2 §5.4).

Emite contracts/vectors/v1/*.vectors.json + index.json.

Determinismo: clave de prueba fija (SOLO PRUEBAS, ver index.json), timestamps
fijos, serialización JSON compacta con claves ordenadas (sólo para EMISIÓN;
la verificación nunca re-serializa, §5.2).

Perfil byte-exacto v1 (C2): HS256 fijo; base64url sin padding;
MAC = HMAC(key, ASCII("ektel/<dominio>/v1") || 0x00 || phb64 || "." || plb64).
PoP: MAC = HMAC(key, "ektel/pop/v1" || 0x00 || len32be(nonce) || nonce || digest_bytes).
identity_digest = SHA256(ASCII(phb64) || "." || ASCII(plb64)) en hex.

stdlib-only (ADR-006). API experimental (spec §16).
"""
import hashlib
import hmac
import json
import struct
from base64 import urlsafe_b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "contracts" / "vectors" / "v1"

# Clave de prueba fija. NUNCA usar fuera de los vectores: no es una clave
# operativa; existe para que los vectores sean reproducibles byte a byte.
TEST_KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
KEY_ID = hashlib.sha256(b"ektel-golden-deployment-salt" + TEST_KEY).hexdigest()[:16]

NBF = 1735689600  # 2025-01-01T00:00:00Z
EXP = 1798761600  # 2027-01-01T00:00:00Z
NONCE = "a1" * 16
ISSUER = "operator-dev"


def b64u(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def emit_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def mac_envelope(domain: str, phb64: str, plb64: str) -> bytes:
    msg = b"ektel/" + domain.encode("ascii") + b"/v1\x00" + phb64.encode("ascii") + b"." + plb64.encode("ascii")
    return hmac.new(TEST_KEY, msg, hashlib.sha256).digest()


def make_envelope(typ: str, payload: dict) -> dict:
    header = {"alg": "HS256", "schema_version": 1, "typ": typ}
    phb64 = b64u(emit_json(header))
    plb64 = b64u(emit_json(payload))
    sig = b64u(mac_envelope(typ.replace("-", "_") if typ == "capability" else _domain(typ), phb64, plb64))
    return {"protected_header_b64": phb64, "payload_b64": plb64, "signature": sig}


def _domain(typ: str) -> str:
    return {"capability": "capability", "admission-token": "admission", "termination-token": "termination"}[typ]


def identity_digest(env: dict) -> str:
    return hashlib.sha256((env["protected_header_b64"] + "." + env["payload_b64"]).encode("ascii")).hexdigest()


CAPABILITY_PAYLOAD = {
    "schema_version": 1,
    "issuer_id": ISSUER,
    "key_id": KEY_ID,
    "nonce": NONCE,
    "nbf": NBF,
    "exp": EXP,
    "artifact_identity_profile": "route_mutable_unverified",
    "action_binding": {
        "action_id": "action-0001",
        "command_absolute": "/usr/bin/true",
        "args": [],
        "cwd": "/tmp",
        "env_allowlist_values": {"PATH": "/usr/bin:/bin"},
        "stdin_policy_digest": hashlib.sha256(b"").hexdigest(),
        "deadline_ms": 5000,
        "output_limits": {"max_stdout_bytes": 65536, "max_stderr_bytes": 65536},
        "requested_guarantees": ["runtime_supervision", "output_bounds"],
    },
}

GUARANTEE_PLAN = [
    {
        "magnitude": "supervision",
        "class": "enforced",
        "platform": "linux-aarch64",
        "mechanism": "killpg + monotonic deadline",
        "assumptions": ["grupo de procesos observado"],
        "known_escapes": ["daemonizacion doble fork"],
        "failure_mode": "supervision_failed",
        "evidence_ref": "docs/evidencia/caracterizacion-linux-2026-08-20.md",
    }
]


def pop_for(cap_digest: str, nonce: str) -> dict:
    nonce_bytes = bytes.fromhex(nonce)
    digest_bytes = bytes.fromhex(cap_digest)
    msg = b"ektel/pop/v1\x00" + struct.pack(">I", len(nonce_bytes)) + nonce_bytes + digest_bytes
    return {
        "schema_version": 1,
        "nonce": nonce,
        "payload_digest": cap_digest,
        "mac": hmac.new(TEST_KEY, msg, hashlib.sha256).hexdigest(),
    }


def vec(vid, wire_type, desc, raw: bytes, verdict, diagnostic, digest=None):
    v = {
        "id": vid,
        "wire_type": wire_type,
        "description": desc,
        "encoding": "base64",
        "bytes": b64u(raw),
        "expect": {"verdict": verdict, "diagnostic": diagnostic},
    }
    if digest:
        v["expect"]["identity_digest"] = digest
    return v


def env_bytes(env: dict) -> bytes:
    return emit_json(env)


def mutate_env(env: dict, **kw) -> dict:
    e = dict(env)
    e.update(kw)
    return e


def build_capability_vectors():
    env = make_envelope("capability", CAPABILITY_PAYLOAD)
    dg = identity_digest(env)
    vecs = [vec("cap-valid-01", "capability-envelope", "Sobre de capacidad válido.", env_bytes(env), "accept", "ok", dg)]
    # MAC inválida
    bad = mutate_env(env, signature=b64u(b"\x00" * 32))
    vecs.append(vec("cap-invalid-mac", "capability-envelope", "Firma sustituida: MAC no verifica.", env_bytes(bad), "reject", "bad_signature"))
    # padding en base64
    padded = mutate_env(env, payload_b64=env["payload_b64"] + "=")
    vecs.append(vec("cap-invalid-b64pad", "capability-envelope", "payload_b64 con padding: base64url estricto lo rechaza.", env_bytes(padded), "reject", "bad_base64"))
    # campo desconocido en payload
    p = dict(CAPABILITY_PAYLOAD)
    p["unknown_field"] = True
    env2 = make_envelope("capability", p)
    vecs.append(vec("cap-invalid-unknown-field", "capability-envelope", "Campo desconocido en el payload (firmado correctamente).", env_bytes(env2), "reject", "unknown_field"))
    # alg distinto
    header = {"alg": "none", "schema_version": 1, "typ": "capability"}
    ph = b64u(emit_json(header))
    pl = b64u(emit_json(CAPABILITY_PAYLOAD))
    sig = b64u(mac_envelope("capability", ph, pl))
    vecs.append(vec("cap-invalid-alg", "capability-envelope", "alg=none: lista cerrada, no hay downgrade (§6.3).", env_bytes({"protected_header_b64": ph, "payload_b64": pl, "signature": sig}), "reject", "alg_unsupported"))
    # schema_version mayor
    p = dict(CAPABILITY_PAYLOAD)
    p["schema_version"] = 2
    env3 = make_envelope("capability", p)
    vecs.append(vec("cap-invalid-version", "capability-envelope", "schema_version=2: el núcleo rechaza versiones mayores desconocidas.", env_bytes(env3), "reject", "schema_version_unsupported"))
    # perfil de identidad no soportado
    p = dict(CAPABILITY_PAYLOAD)
    p["artifact_identity_profile"] = "route_pinned_verified"
    env4 = make_envelope("capability", p)
    vecs.append(vec("cap-invalid-profile", "capability-envelope", "artifact_identity_profile distinto del único valor v1 (§6.1).", env_bytes(env4), "reject", "invalid_value"))
    return vecs, env, dg


def build_admission_token_vectors(dg):
    payload = {"schema_version": 1, "identity_digest": dg, "action_id": "action-0001", "exp": EXP, "issuer_id": ISSUER}
    env = make_envelope("admission-token", payload)
    vecs = [vec("adm-valid-01", "admission-token", "Token de admisión válido.", env_bytes(env), "accept", "ok", identity_digest(env))]
    bad = mutate_env(env, signature=b64u(b"\xff" * 32))
    vecs.append(vec("adm-invalid-mac", "admission-token", "MAC de admisión inválida.", env_bytes(bad), "reject", "bad_signature"))
    p = dict(payload)
    p["identity_digest"] = "zz" * 32
    env2 = make_envelope("admission-token", p)
    vecs.append(vec("adm-invalid-digest", "admission-token", "identity_digest no hex de 64.", env_bytes(env2), "reject", "invalid_value"))
    return vecs


def build_termination_token_vectors(dg):
    payload = {"schema_version": 1, "action_id": "action-0001", "identity_digest": dg}
    env = make_envelope("termination-token", payload)
    vecs = [vec("term-valid-01", "termination-token", "Token de terminación válido.", env_bytes(env), "accept", "ok", identity_digest(env))]
    bad = mutate_env(env, signature=b64u(b"\x01" * 32))
    vecs.append(vec("term-invalid-mac", "termination-token", "MAC de terminación inválida.", env_bytes(bad), "reject", "bad_signature"))
    p = dict(payload)
    del p["identity_digest"]
    env2 = make_envelope("termination-token", p)
    vecs.append(vec("term-invalid-missing", "termination-token", "Falta identity_digest.", env_bytes(env2), "reject", "missing_field"))
    return vecs


def build_pop_vectors(dg):
    proof = pop_for(dg, NONCE)
    vecs = [vec("pop-valid-01", "invocation-proof", "PoP válida para la capacidad dorada.", emit_json(proof), "accept", "ok")]
    bad = dict(proof)
    bad["mac"] = "00" * 32
    vecs.append(vec("pop-invalid-mac", "invocation-proof", "MAC de PoP inválida.", emit_json(bad), "reject", "bad_signature"))
    bad2 = dict(proof)
    bad2["nonce"] = "a1" * 15
    vecs.append(vec("pop-invalid-nonce", "invocation-proof", "Nonce de longitud distinta a 16 bytes.", emit_json(bad2), "reject", "invalid_value"))
    return vecs, proof


def build_action_request_vectors(env, proof):
    req = {
        "schema_version": 1,
        "action_id": "action-0001",
        "command_absolute": "/usr/bin/true",
        "args": [],
        "cwd": "/tmp",
        "env_allowlist_values": {"PATH": "/usr/bin:/bin"},
        "stdin_policy": {"kind": "empty", "sha256": hashlib.sha256(b"").hexdigest()},
        "deadline_ms": 5000,
        "capability_envelope": env,
        "invocation_proof": proof,
        "nonce": NONCE,
        "repair_policy": "none",
        "output_limits": {"max_stdout_bytes": 65536, "max_stderr_bytes": 65536},
        "requested_guarantees": ["runtime_supervision", "output_bounds"],
        "metadata_opaque": "",
    }
    vecs = [vec("areq-valid-01", "action-request", "ActionRequest completo y válido.", emit_json(req), "accept", "ok")]
    r = dict(req)
    r["extra"] = 1
    vecs.append(vec("areq-invalid-unknown", "action-request", "Campo desconocido (§5.1).", emit_json(r), "reject", "unknown_field"))
    r = dict(req)
    r["schema_version"] = 2
    vecs.append(vec("areq-invalid-version", "action-request", "schema_version=2 rechazado.", emit_json(r), "reject", "schema_version_unsupported"))
    r = dict(req)
    r["repair_policy"] = "restart"
    vecs.append(vec("areq-invalid-repair", "action-request", "repair_policy fuera del vocabulario cerrado v1.", emit_json(r), "reject", "invalid_value"))
    raw = emit_json(req).replace(b'"deadline_ms":5000', b'"deadline_ms":NaN')
    vecs.append(vec("areq-invalid-nan", "action-request", "NaN rechazado por JSON estricto (§5.1).", raw, "reject", "malformed_json"))
    # clave duplicada
    raw2 = b'{"schema_version":1,"schema_version":1}'
    vecs.append(vec("areq-invalid-dupkey", "action-request", "Clave duplicada rechazada (§5.1).", raw2, "reject", "duplicate_key"))
    return vecs


def build_outcome_vectors(dg):
    admitted = {
        "schema_version": 1,
        "outcome": "admitted",
        "admitted_action": "opaque",
        "identity_digest": dg,
        "guarantee_plan": GUARANTEE_PLAN,
    }
    rejected = {
        "schema_version": 1,
        "outcome": "admission_rejected",
        "reason_code": "capability_expired",
        "safe_detail": "capability expirada",
        "retryable": False,
    }
    vecs = [
        vec("aout-valid-admitted", "admission-outcome", "Admitted con guarantee_plan.", emit_json(admitted), "accept", "ok"),
        vec("aout-valid-rejected", "admission-outcome", "AdmissionRejected con código cerrado.", emit_json(rejected), "accept", "ok"),
    ]
    r = dict(rejected)
    r["reason_code"] = "budget_exceeded"
    vecs.append(vec("aout-invalid-budget", "admission-outcome", "budget_exceeded no existe en v1 (§8.3).", emit_json(r), "reject", "invalid_value"))
    started = {"schema_version": 1, "outcome": "started", "handle_ref": "0123456789abcdef"}
    failed = {"schema_version": 1, "outcome": "start_failed", "reason_code": "start_failed_indeterminate"}
    vecs += [
        vec("sout-valid-started", "start-outcome", "Started con referencia opaca de handle.", emit_json(started), "accept", "ok"),
        vec("sout-valid-failed", "start-outcome", "StartFailed con start_failed_indeterminate (C4).", emit_json(failed), "accept", "ok"),
    ]
    f = dict(failed)
    f["reason_code"] = "executed"
    vecs.append(vec("sout-invalid-state", "start-outcome", "Estado de ejecución en StartFailed: los tipos son por operación (C1).", emit_json(f), "reject", "invalid_value"))
    term = {"schema_version": 1, "outcome": "termination_rejected", "reason_code": "capability_rejected"}
    vecs.append(vec("tout-valid-rejected", "termination-outcome", "TerminationRejected por handle inválido.", emit_json(term), "accept", "ok"))
    result = {
        "schema_version": 1,
        "action_id": "action-0001",
        "identity_digest": dg,
        "state": "executed",
        "artifact_identity_profile": "route_mutable_unverified",
        "started_at_wall": NBF,
        "finished_at_wall": NBF + 1,
        "duration_monotonic_ms": 800,
        "exit_code_or_signal": "exit:0",
        "cause_code": "natural_exit",
        "validity_at_admission": {"nbf": NBF, "exp": EXP},
        "guarantees_applied": GUARANTEE_PLAN,
        "measurements": {},
        "stdout_truncation": False,
        "stderr_truncation": False,
        "discarded_bytes": 0,
        "last_event_receipt": "",
    }
    vecs.append(vec("eres-valid-executed", "execution-result", "ExecutionResult executed con causa natural_exit.", emit_json(result), "accept", "ok"))
    r = dict(result)
    r["state"] = "admission_rejected"
    vecs.append(vec("eres-invalid-prestart", "execution-result", "Estado pre-inicio en ExecutionResult: sólo post-inicio (C1).", emit_json(r), "reject", "invalid_value"))
    return vecs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cap_vecs, cap_env, dg = build_capability_vectors()
    adm_vecs = build_admission_token_vectors(dg)
    term_vecs = build_termination_token_vectors(dg)
    pop_vecs, proof = build_pop_vectors(dg)
    areq_vecs = build_action_request_vectors(cap_env, proof)
    out_vecs = build_outcome_vectors(dg)

    groups = {
        "capability-envelope": cap_vecs,
        "admission-token": adm_vecs,
        "termination-token": term_vecs,
        "invocation-proof": pop_vecs,
        "action-request": areq_vecs,
        "outcomes": out_vecs,
    }
    for name, vecs in groups.items():
        doc = {
            "schema": "ektel/golden-vectors/v1",
            "wire_type_group": name,
            "generated": "2026-08-20",
            "vectors": vecs,
        }
        (OUT / f"{name}.vectors.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    index = {
        "schema": "ektel/golden-vectors-index/v1",
        "generated": "2026-08-20",
        "spec": "docs/especificacion/ektel-runtime-m0-m3-v1.md (v1.2)",
        "groups": sorted(groups),
        "test_key_hex": TEST_KEY.hex(),
        "test_key_notice": "CLAVE SOLO DE PRUEBA: fija para reproducibilidad de vectores; prohibida fuera de tests.",
        "key_id": KEY_ID,
        "domains": ["ektel/capability/v1", "ektel/pop/v1", "ektel/admission/v1", "ektel/termination/v1"],
        "capability_identity_digest": dg,
    }
    (OUT / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(len(v) for v in groups.values())
    print(f"vectores emitidos: {total} en {len(groups)} grupos -> {OUT}")


if __name__ == "__main__":
    main()
