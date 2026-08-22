#!/usr/bin/env python3
"""Generador determinista de vectores dorados M0 (spec v1.2 §5.4).

Emite contracts/vectors/v1/*.vectors.json + index.json. La variable de
entorno EKTEL_VECTORS_OUT redirige la salida a un directorio temporal
(gate de reproducibilidad: diff cero contra contracts/vectors/v1).

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
import os
import struct
from base64 import urlsafe_b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("EKTEL_VECTORS_OUT", ROOT / "contracts" / "vectors" / "v1"))

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


def base_action_request(env: dict, proof: dict) -> dict:
    return {
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


def build_action_request_vectors(env, proof):
    req = base_action_request(env, proof)
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
    # bool no es int: request completo con sólo schema_version=true.
    # (enum/const con tipo distinto cae como invalid_value: el valor no es
    # el 1 entero — la fuga bool==1 de Python queda cerrada).
    r = dict(req)
    r["schema_version"] = True
    vecs.append(vec("areq-invalid-bool-version", "action-request",
                    "schema_version: true — bool no es int (§5.1).",
                    emit_json(r), "reject", "invalid_value"))
    # Enteros negativos ya cubiertos en capability; decimal en ActionRequest:
    r = dict(req)
    r["deadline_ms"] = 5.5
    vecs.append(vec("areq-invalid-decimal", "action-request",
                    "deadline_ms decimal: sin coerción de tipos (§5.1).",
                    emit_json(r), "reject", "invalid_type"))
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
        "reason_code": "capability_rejected",
        "safe_detail": "capability rechazada",
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
    # D-P2 (M1, acta de autorización 2026-08-22): base accept de la alternativa
    # termination_accepted — cierra el hueco de oráculo O-1 del gate final M0
    # (la rama sólo se ejercía en reject por tout-invalid-accepted-extra, que
    # es exactamente este documento + extra_field).
    term_ok = {"schema_version": 1, "outcome": "termination_accepted", "receipt": "opaque"}
    vecs.append(vec("tout-valid-accepted", "termination-outcome", "TerminationAccepted con recibo (base accept de la alternativa; D-P2/O-1).", emit_json(term_ok), "accept", "ok"))
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


def build_correction_vectors(env, dg, proof):
    """Clases nuevas de la corrección M0 (doble NO-GO 2026-08-20 + ADR-010)
    y de la corrección FIX-AND-RETRY de Pinax (2026-08-20): un vector por
    divergencia histórica."""
    vecs = []
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    # Sobre/documento escalar en vez de objeto.
    vecs.append(vec("cap-invalid-scalar", "capability-envelope",
                    "El sobre es una cadena, no un objeto.", emit_json("no-soy-un-sobre"),
                    "reject", "invalid_type"))
    vecs.append(vec("pop-invalid-scalar", "invocation-proof",
                    "La PoP es un entero, no un objeto.", emit_json(42), "reject", "invalid_type"))

    # Enteros negativos y decimales.
    p = dict(CAPABILITY_PAYLOAD)
    p["action_binding"] = dict(p["action_binding"], deadline_ms=-5)
    vecs.append(vec("cap-invalid-negative", "capability-envelope",
                    "deadline_ms negativo (firmado correctamente).",
                    env_bytes(make_envelope("capability", p)), "reject", "invalid_value"))
    # exp <= nbf (ventana vacía; §6 corrección M0).
    p = dict(CAPABILITY_PAYLOAD)
    p["exp"] = p["nbf"]
    vecs.append(vec("cap-invalid-exp-nbf", "capability-envelope",
                    "exp == nbf: ventana de vigencia vacía.",
                    env_bytes(make_envelope("capability", p)), "reject", "invalid_value"))

    # typ cruzado: header typ=admission-token pero MAC con dominio capability.
    header = {"alg": "HS256", "schema_version": 1, "typ": "admission-token"}
    ph = b64u(emit_json(header))
    pl = b64u(emit_json(CAPABILITY_PAYLOAD))
    sig = b64u(mac_envelope("capability", ph, pl))
    vecs.append(vec("cap-invalid-typ-cross", "capability-envelope",
                    "typ del header no coincide con el wire type (MAC válida).",
                    env_bytes({"protected_header_b64": ph, "payload_b64": pl, "signature": sig}),
                    "reject", "invalid_value"))

    # ADR-010: firma con bits residuales no cero (decodifica igual, MAC ok).
    sig_nc = env["signature"][:-1] + alphabet[alphabet.index(env["signature"][-1]) ^ 0b11]
    vecs.append(vec("cap-invalid-noncanon-sig", "capability-envelope",
                    "ADR-010: firma base64url no canónica (flip de bits residuales).",
                    env_bytes(mutate_env(env, signature=sig_nc)), "reject", "bad_base64"))

    # ADR-010: payload re-encodado no canónico con MAC válida para esa cadena.
    raw_payload = emit_json(CAPABILITY_PAYLOAD)
    pad_len = len(raw_payload) % 3
    if pad_len == 0:
        raw_payload = emit_json(dict(CAPABILITY_PAYLOAD, issuer_id=ISSUER + "x"))
    pl_canon = b64u(raw_payload)
    res_bits = (len(pl_canon) * 6 - len(raw_payload) * 8)
    pl_nc = pl_canon[:-1] + alphabet[alphabet.index(pl_canon[-1]) ^ ((1 << res_bits) - 1)]
    assert urlsafe_b64decode_local(pl_canon) == urlsafe_b64decode_local(pl_nc)
    ph2 = b64u(emit_json({"alg": "HS256", "schema_version": 1, "typ": "capability"}))
    sig2 = b64u(mac_envelope("capability", ph2, pl_nc))
    vecs.append(vec("cap-invalid-noncanon-payload", "capability-envelope",
                    "ADR-010: payload base64url no canónico con MAC válida para esa cadena.",
                    env_bytes({"protected_header_b64": ph2, "payload_b64": pl_nc, "signature": sig2}),
                    "reject", "bad_base64"))

    # Campos reordenados, firma válida: acepta con SU digest (los bytes mandan).
    p = dict(CAPABILITY_PAYLOAD)
    reordered_payload = {"nonce": p["nonce"], "schema_version": 1, "issuer_id": p["issuer_id"],
                         "key_id": p["key_id"], "nbf": p["nbf"], "exp": p["exp"],
                         "artifact_identity_profile": p["artifact_identity_profile"],
                         "action_binding": p["action_binding"]}
    env_r = make_envelope("capability", reordered_payload)
    # emit_json ordena claves; para reordenar de verdad hay que serializar a mano.
    raw_manual = json.dumps(reordered_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ph3 = b64u(emit_json({"alg": "HS256", "schema_version": 1, "typ": "capability"}))
    pl3 = b64u(raw_manual)
    sig3 = b64u(mac_envelope("capability", ph3, pl3))
    env3 = {"protected_header_b64": ph3, "payload_b64": pl3, "signature": sig3}
    vecs.append(vec("cap-valid-reordered", "capability-envelope",
                    "Campos del payload en otro orden, MAC válida: acepta; el digest es de ESOS bytes.",
                    env_bytes(env3), "accept", "ok", identity_digest(env3)))

    # Uniones mal formadas (discriminación §8.3).
    vecs.append(vec("sout-invalid-started-nohandle", "start-outcome",
                    "started sin handle_ref: unión discriminada lo exige.",
                    emit_json({"schema_version": 1, "outcome": "started"}), "reject", "missing_field"))
    vecs.append(vec("sout-invalid-failed-withhandle", "start-outcome",
                    "start_failed con handle_ref: campo de la otra alternativa.",
                    emit_json({"schema_version": 1, "outcome": "start_failed",
                               "reason_code": "start_failed", "handle_ref": "0123456789abcdef"}),
                    "reject", "unknown_field"))
    vecs.append(vec("aout-invalid-retired-code", "admission-outcome",
                    "capability_expired retirado: vocabulario colapsado (corrección M0).",
                    emit_json({"schema_version": 1, "outcome": "admission_rejected",
                               "reason_code": "capability_expired", "safe_detail": "x", "retryable": False}),
                    "reject", "invalid_value"))
    vecs.append(vec("aout-invalid-admitted-noplan", "admission-outcome",
                    "admitted sin guarantee_plan.",
                    emit_json({"schema_version": 1, "outcome": "admitted",
                               "admitted_action": "x", "identity_digest": dg}),
                    "reject", "missing_field"))

    # Fuga de "\n" final en campo con patrón (payload firmado).
    p = dict(CAPABILITY_PAYLOAD)
    p["key_id"] = KEY_ID + "\n"
    vecs.append(vec("cap-invalid-newline-keyid", "capability-envelope",
                    "key_id con salto de línea final (pattern auto-anclado, §5.7).",
                    env_bytes(make_envelope("capability", p)), "reject", "invalid_value"))

    # bool no es int: se construye en build_action_request_vectors (req completo).

    # Techo global de 64 KiB (§5.1).
    big = {"schema_version": 1, "metadata_opaque": "x" * 70000}
    vecs.append(vec("areq-invalid-oversize", "action-request",
                    "Documento por encima del techo global de 64 KiB (§5.1).",
                    emit_json(big), "reject", "size_exceeded"))

    # Doble causa: campo desconocido en payload + MAC inválida → gana el MAC:
    # §5.2 manda verificar ANTES de decodificar; la estructura del payload
    # sólo se valida tras una MAC válida (precedencia §5.5).
    p = dict(CAPABILITY_PAYLOAD)
    p["extra"] = 1
    env_x = mutate_env(make_envelope("capability", p), signature=b64u(b"\x00" * 32))
    vecs.append(vec("cap-invalid-doublecause", "capability-envelope",
                    "unknown_field (payload) + MAC inválida: el MAC manda (§5.2/§5.5).",
                    env_bytes(env_x), "reject", "bad_signature"))

    # --- FIX-AND-RETRY (Pinax 2026-08-20) ---------------------------------
    # B1: los schemas rechazan prefijos, sufijos y newline final POR SÍ
    # MISMOS (patterns auto-anclados, semántica Draft 2020-12, §5.7).
    p = dict(CAPABILITY_PAYLOAD)
    p["key_id"] = "x" + KEY_ID
    vecs.append(vec("cap-invalid-keyid-prefix", "capability-envelope",
                    "key_id con prefijo 'x': el pattern auto-anclado lo rechaza (§5.7).",
                    env_bytes(make_envelope("capability", p)), "reject", "invalid_value"))
    p = dict(CAPABILITY_PAYLOAD)
    p["nonce"] = NONCE + "x"
    vecs.append(vec("cap-invalid-nonce-suffix", "capability-envelope",
                    "nonce con sufijo 'x': el pattern auto-anclado lo rechaza (§5.7).",
                    env_bytes(make_envelope("capability", p)), "reject", "invalid_value"))
    req = base_action_request(env, proof)
    r = dict(req)
    r["cwd"] = "/tmp\n"
    vecs.append(vec("areq-invalid-cwd-newline", "action-request",
                    "cwd con salto de línea final: rechazado por el pattern del schema (§5.7).",
                    emit_json(r), "reject", "invalid_value"))
    # Newline final en campo b64url del sobre: bad_base64 ANTES de verificar
    # la MAC (precedencia §5.6); MAC computada sobre la cadena mutada para
    # que el diagnóstico tenga una sola causa.
    ph_nl = env["protected_header_b64"] + "\n"
    env_nl = {"protected_header_b64": ph_nl, "payload_b64": env["payload_b64"],
              "signature": b64u(mac_envelope("capability", ph_nl, env["payload_b64"]))}
    vecs.append(vec("cap-invalid-ph-newline", "capability-envelope",
                    "protected_header_b64 con salto de línea final: bad_base64 (pattern auto-anclado + canonicalidad, §5.6/§5.7).",
                    env_bytes(env_nl), "reject", "bad_base64"))

    # B2: campo extra en cada alternativa de las uniones discriminadas —
    # cerrado por unevaluatedProperties=false en el schema y por
    # unknown_field en ambos parsers (§8.3).
    vecs.append(vec("aout-invalid-admitted-extra", "admission-outcome",
                    "admitted con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "admitted",
                               "admitted_action": "opaque", "identity_digest": dg,
                               "guarantee_plan": GUARANTEE_PLAN, "extra_field": 1}),
                    "reject", "unknown_field"))
    vecs.append(vec("aout-invalid-rejected-extra", "admission-outcome",
                    "admission_rejected con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "admission_rejected",
                               "reason_code": "capability_rejected", "safe_detail": "x",
                               "retryable": False, "extra_field": 1}),
                    "reject", "unknown_field"))
    vecs.append(vec("sout-invalid-started-extra", "start-outcome",
                    "started con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "started",
                               "handle_ref": "0123456789abcdef", "extra_field": 1}),
                    "reject", "unknown_field"))
    vecs.append(vec("sout-invalid-failed-extra", "start-outcome",
                    "start_failed con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "start_failed",
                               "reason_code": "start_failed", "extra_field": 1}),
                    "reject", "unknown_field"))
    vecs.append(vec("tout-invalid-accepted-extra", "termination-outcome",
                    "termination_accepted con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "termination_accepted",
                               "receipt": "opaque", "extra_field": 1}),
                    "reject", "unknown_field"))
    vecs.append(vec("tout-invalid-rejected-extra", "termination-outcome",
                    "termination_rejected con campo extra: cerrado por unevaluatedProperties=false.",
                    emit_json({"schema_version": 1, "outcome": "termination_rejected",
                               "reason_code": "capability_rejected", "extra_field": 1}),
                    "reject", "unknown_field"))

    # --- FIX-AND-RETRY 2 (Pinax 2026-08-20) --------------------------------
    # B7: guarantees_applied de execution-result alineado con guarantee_plan
    # (minLength 1 en magnitude/platform/mechanism/failure_mode; maxItems 64
    # en assumptions/known_escapes) — antes el parser A lo imponía y el
    # schema/parser B no (divergencia reproducida).
    def _eres():
        return {
            "schema_version": 1, "action_id": "action-0001", "identity_digest": dg,
            "state": "executed", "artifact_identity_profile": "route_mutable_unverified",
            "started_at_wall": NBF, "finished_at_wall": NBF + 1,
            "duration_monotonic_ms": 800, "exit_code_or_signal": "exit:0",
            "cause_code": "natural_exit",
            "validity_at_admission": {"nbf": NBF, "exp": EXP},
            "guarantees_applied": [json.loads(json.dumps(GUARANTEE_PLAN[0]))],
            "measurements": {}, "stdout_truncation": False,
            "stderr_truncation": False, "discarded_bytes": 0,
            "last_event_receipt": "",
        }
    for fld, vid, desc in [
        ("magnitude", "eres-invalid-empty-magnitude", "guarantees_applied.magnitude vacío: alineado con guarantee_plan (B7)."),
        ("platform", "eres-invalid-empty-platform", "guarantees_applied.platform vacío: alineado con guarantee_plan (B7)."),
        ("mechanism", "eres-invalid-empty-mechanism", "guarantees_applied.mechanism vacío: alineado con guarantee_plan (B7)."),
        ("failure_mode", "eres-invalid-empty-failure-mode", "guarantees_applied.failure_mode vacío: alineado con guarantee_plan (B7)."),
    ]:
        m = _eres()
        m["guarantees_applied"][0][fld] = ""
        vecs.append(vec(vid, "execution-result", desc, emit_json(m), "reject", "invalid_value"))
    for fld, vid in [("assumptions", "eres-invalid-assumptions-65"),
                     ("known_escapes", "eres-invalid-known-escapes-65")]:
        m = _eres()
        m["guarantees_applied"][0][fld] = [str(i) for i in range(65)]
        vecs.append(vec(vid, "execution-result",
                        f"guarantees_applied.{fld} con 65 elementos: maxItems 64 (B7).",
                        emit_json(m), "reject", "invalid_value"))

    # B8: regla uniforme de schema_version — entero > 1 →
    # schema_version_unsupported; entero <= 0 → invalid_value; bool →
    # invalid_value. invocation-proof con MAC de PoP vigente (la MAC no
    # cubre schema_version: diagnóstico de causa única).
    for sv, vid, diag, desc in [
        (2, "pop-invalid-version-2", "schema_version_unsupported", "Versión mayor desconocida (B8: uniforme, antes A/B divergían)."),
        (0, "pop-invalid-version-0", "invalid_value", "schema_version=0: valor inválido, no versión desconocida (B8)."),
        (-1, "pop-invalid-version-neg", "invalid_value", "schema_version=-1: valor inválido, no versión desconocida (B8)."),
    ]:
        p = pop_for(dg, NONCE)
        p["schema_version"] = sv
        vecs.append(vec(vid, "invocation-proof", desc, emit_json(p), "reject", diag))
    req2 = base_action_request(env, proof)
    for sv, vid, desc in [
        (0, "areq-invalid-version-0", "schema_version=0: invalid_value, no unsupported (B8; antes ambos parsers daban unsupported)."),
        (-1, "areq-invalid-version-neg", "schema_version=-1: invalid_value, no unsupported (B8; antes ambos parsers daban unsupported)."),
    ]:
        r2 = dict(req2)
        r2["schema_version"] = sv
        vecs.append(vec(vid, "action-request", desc, emit_json(r2), "reject", "invalid_value"))
    # Header firmado con schema_version=2 y MAC VÁLIDA para ese header.
    hdr = {"alg": "HS256", "schema_version": 2, "typ": "capability"}
    ph_v = b64u(emit_json(hdr))
    pl_v = b64u(emit_json(CAPABILITY_PAYLOAD))
    sig_v = b64u(mac_envelope("capability", ph_v, pl_v))
    vecs.append(vec("cap-invalid-header-version", "capability-envelope",
                    "Header firmado con schema_version=2 (MAC válida): versión mayor desconocida (B8).",
                    env_bytes({"protected_header_b64": ph_v, "payload_b64": pl_v, "signature": sig_v}),
                    "reject", "schema_version_unsupported"))

    # FASE-1 del gate externo: signature con longitud != 43 (44 chars
    # canónicos = 33 bytes) — rechazada por la validación ESTRUCTURAL del
    # sobre (pattern ^[A-Za-z0-9_-]{43}$ del schema / exact:43 del parser
    # A), ANTES del MAC y como invalid_value. Clasificación deliberada
    # (acta §12): una firma HMAC-SHA256 siempre mide 43 chars canónicos;
    # otra longitud no es firma degenerada sino structura inválida.
    sig44 = b64u(b"\xab" * 33)
    vecs.append(vec("cap-invalid-sig-len-44", "capability-envelope",
                    "signature de 44 chars canónicos (33 bytes): longitud != 43 — rechazo estructural del sobre (invalid_value, antes del MAC; acta §12).",
                    env_bytes(mutate_env(env, signature=sig44)), "reject", "invalid_value"))

    # --- Corrección contractual H1/H2/H3 (2026-08-21) ---------------------
    # H1: alias no canónico de los MISMOS bytes en protected_header_b64 con
    # MAC VÁLIDA recalculada para esa cadena: la canonicalidad es
    # precondición de admisión — bad_base64 GANA a bad_signature (§5.2).
    raw_hdr = emit_json({"alg": "HS256", "schema_version": 1, "typ": "capability"})
    ph_c = b64u(raw_hdr)
    res_bits_h = (len(ph_c) * 6 - len(raw_hdr) * 8)
    assert res_bits_h in (2, 4)  # el header tiene bits residuales alterables
    ph_nc = ph_c[:-1] + alphabet[alphabet.index(ph_c[-1]) ^ ((1 << res_bits_h) - 1)]
    assert urlsafe_b64decode_local(ph_c) == urlsafe_b64decode_local(ph_nc)
    pl_h1 = b64u(emit_json(CAPABILITY_PAYLOAD))
    sig_h1 = b64u(mac_envelope("capability", ph_nc, pl_h1))
    vecs.append(vec("cap-invalid-noncanon-header", "capability-envelope",
                    "H1: protected_header_b64 alias no canónico de los mismos bytes, MAC válida recalculada: reject/bad_base64 (canonicalidad = precondición, §5.2).",
                    env_bytes({"protected_header_b64": ph_nc, "payload_b64": pl_h1, "signature": sig_h1}),
                    "reject", "bad_base64"))

    # H2: frontera M0/M1 congelada — action-request es estructura exterior
    # en M0; firma/PoP anidadas y coherencia semántica son admisión M1.
    # Los tres vectores son ACCEPT/OK POR DISEÑO (spec §5.8).
    import copy as _copy
    req_h2 = base_action_request(env, proof)
    r_badmac = _copy.deepcopy(req_h2)
    r_badmac["capability_envelope"]["signature"] = b64u(b"\xde\xad\xbe\xef" * 8)
    vecs.append(vec("areq-valid-nested-badmac", "action-request",
                    "H2: firma del sobre anidado inválida — accept/ok en M0: la verificación criptográfica anidada es admisión M1 (§5.8).",
                    emit_json(r_badmac), "accept", "ok"))
    r_badpop = _copy.deepcopy(req_h2)
    r_badpop["invocation_proof"]["mac"] = "00" * 32
    vecs.append(vec("areq-valid-nested-badpop", "action-request",
                    "H2: PoP anidada con mac inválida — accept/ok en M0 (§5.8).",
                    emit_json(r_badpop), "accept", "ok"))
    r_mismatch = _copy.deepcopy(req_h2)
    r_mismatch["command_absolute"] = "/usr/bin/false"
    vecs.append(vec("areq-valid-nested-cmd-mismatch", "action-request",
                    "H2: command_absolute del descriptor distinto del action_binding de la capacidad — accept/ok en M0: coherencia semántica es M1 (§5.8).",
                    emit_json(r_mismatch), "accept", "ok"))

    # H3: unión discriminada por state — evidencia suficiente y obtenible.
    def _eres_state(state, cause, **extra):
        m = _eres()
        m["state"] = state
        m["cause_code"] = cause
        m.update(extra)
        return m
    TIMED_REQ = {"started_at_wall": NBF, "finished_at_wall": NBF + 2,
                 "duration_monotonic_ms": 1500, "stdout_truncation": False,
                 "stderr_truncation": False}
    vecs.append(vec("eres-valid-deadline", "execution-result",
                    "H3: deadline_exceeded con causa y observabilidad completas.",
                    emit_json(_eres_state("deadline_exceeded", "deadline_duration", **TIMED_REQ)),
                    "accept", "ok"))
    vecs.append(vec("eres-valid-terminated", "execution-result",
                    "H3: terminated con external_termination y observabilidad.",
                    emit_json(_eres_state("terminated", "external_termination", **TIMED_REQ)),
                    "accept", "ok"))
    m = _eres_state("supervision_failed", "supervision_failure")
    del m["started_at_wall"]; del m["finished_at_wall"]; del m["duration_monotonic_ms"]
    del m["stdout_truncation"]; del m["stderr_truncation"]
    vecs.append(vec("eres-valid-supervision-failed", "execution-result",
                    "H3: supervision_failed SIN tiempos: rama propia que no exige evidencia imposible.",
                    emit_json(m), "accept", "ok"))
    m = _eres_state("executed", "natural_exit", **TIMED_REQ)
    del m["started_at_wall"]
    vecs.append(vec("eres-invalid-exec-no-times", "execution-result",
                    "H3: executed sin started_at_wall: evidencia obligatoria ausente.",
                    emit_json(m), "reject", "missing_field"))
    vecs.append(vec("eres-invalid-exec-bad-cause", "execution-result",
                    "H3: executed con cause_code external_termination: causa incompatible con el estado.",
                    emit_json(_eres_state("executed", "external_termination", **TIMED_REQ)),
                    "reject", "invalid_value"))
    vecs.append(vec("eres-invalid-deadline-bad-cause", "execution-result",
                    "H3: deadline_exceeded con natural_exit: causa incompatible.",
                    emit_json(_eres_state("deadline_exceeded", "natural_exit", **TIMED_REQ)),
                    "reject", "invalid_value"))
    vecs.append(vec("eres-invalid-term-bad-cause", "execution-result",
                    "H3: terminated con supervision_failure: causa incompatible.",
                    emit_json(_eres_state("terminated", "supervision_failure", **TIMED_REQ)),
                    "reject", "invalid_value"))
    m = _eres_state("executed", "natural_exit", **TIMED_REQ)
    del m["cause_code"]
    vecs.append(vec("eres-invalid-missing-cause", "execution-result",
                    "H3: sin cause_code: obligatorio global (unión por state).",
                    emit_json(m), "reject", "missing_field"))
    m = _eres_state("executed", "natural_exit", **TIMED_REQ)
    del m["discarded_bytes"]
    vecs.append(vec("eres-invalid-missing-discarded", "execution-result",
                    "H3: sin discarded_bytes: siempre presente (0 si no hubo truncación, decisión (a)).",
                    emit_json(m), "reject", "missing_field"))

    # --- M0-FAR-CLAUDE-01 (gate Claude, 2026-08-21): H1-H5 ---------------
    # H1: discriminador de unión con tipo no confiable (lista) — ningún
    # parser debe crashear; sin tipo declarado para el discriminador,
    # enum-only → invalid_value (§5.6).
    vecs.append(vec("sout-invalid-disc-list", "start-outcome",
                    "H1: outcome=[] (no hashable): tipo del discriminador validado antes de usarse como clave; invalid_value sin excepción.",
                    emit_json({"schema_version": 1, "outcome": [],
                               "handle_ref": "0123456789abcdef"}),
                    "reject", "invalid_value"))
    # H2: items con type+enum — invalid_type ANTES que invalid_value.
    r_h2 = base_action_request(env, proof)
    r_h2["requested_guarantees"] = [1]
    vecs.append(vec("areq-invalid-guarantees-type", "action-request",
                    "H2: requested_guarantees=[1] — el tipo del item (string) precede a su enum: invalid_type.",
                    emit_json(r_h2), "reject", "invalid_type"))
    # H3: protected-header.typ con tipo equivocado y MAC VÁLIDA —
    # invalid_type (error común A/B corregido).
    ph_h3 = b64u(emit_json({"alg": "HS256", "schema_version": 1, "typ": 1}))
    pl_h3 = b64u(emit_json(CAPABILITY_PAYLOAD))
    vecs.append(vec("cap-invalid-header-typ-int", "capability-envelope",
                    "H3: header typ=1 (int) con MAC válida: type-string precede al enum → invalid_type.",
                    env_bytes({"protected_header_b64": ph_h3, "payload_b64": pl_h3,
                               "signature": b64u(mac_envelope("capability", ph_h3, pl_h3))}),
                    "reject", "invalid_type"))
    # H5: saltos de línea prohibidos por clase explícita, no por "." del
    # motor — CR y U+2028 (LF ya cubierto por areq-invalid-cwd-newline).
    for vid, ch, desc in [
        ("areq-invalid-cmd-cr", "\r", "H5: command_absolute con CR: excluido por clase explícita (independiente del motor)."),
        ("areq-invalid-cmd-u2028", "\u2028", "H5: command_absolute con U+2028: excluido por clase explícita (ECMA-262 y Python coinciden)."),
    ]:
        r_h5 = base_action_request(env, proof)
        r_h5["command_absolute"] = "/bin/e" + ch + "cho"
        vecs.append(vec(vid, "action-request", desc, emit_json(r_h5),
                        "reject", "invalid_value"))
    # H4: caso compuesto — header no canónico + signature de 44: gana el
    # primer campo ofensivo del orden del schema (protected_header_b64)
    # → bad_base64 (MAC válida recalculada para la cadena no canónica).
    ph_h4 = b64u(emit_json({"alg": "HS256", "schema_version": 1, "typ": "capability"}))
    bits_h4 = (len(ph_h4) * 6 - len(emit_json({"alg": "HS256", "schema_version": 1, "typ": "capability"})) * 8)
    ph_h4nc = ph_h4[:-1] + alphabet[alphabet.index(ph_h4[-1]) ^ ((1 << bits_h4) - 1)]
    sig44b = b64u(b"\xab" * 33)
    vecs.append(vec("cap-invalid-noncanon-header-sig44", "capability-envelope",
                    "H4: header no canónico + signature de 44 chars: interleaving por campo — protected_header_b64 precede → bad_base64 (acta §12 corregida).",
                    env_bytes({"protected_header_b64": ph_h4nc, "payload_b64": pl_h3,
                               "signature": sig44b}),
                    "reject", "bad_base64"))
    return vecs


def urlsafe_b64decode_local(s: str) -> bytes:
    from base64 import urlsafe_b64decode as _d
    return _d(s + "=" * ((-len(s)) % 4))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cap_vecs, cap_env, dg = build_capability_vectors()
    adm_vecs = build_admission_token_vectors(dg)
    term_vecs = build_termination_token_vectors(dg)
    pop_vecs, proof = build_pop_vectors(dg)
    areq_vecs = build_action_request_vectors(cap_env, proof)
    out_vecs = build_outcome_vectors(dg)
    corr_vecs = build_correction_vectors(cap_env, dg, proof)

    groups = {
        "capability-envelope": cap_vecs,
        "admission-token": adm_vecs,
        "termination-token": term_vecs,
        "invocation-proof": pop_vecs,
        "action-request": areq_vecs,
        "outcomes": out_vecs,
        "correccion-m0": corr_vecs,
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
