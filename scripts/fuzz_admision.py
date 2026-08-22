#!/usr/bin/env python3
"""Fuzz de admisión M1 con oráculo (G8; spec §15 M1 «fuzzing sin aceptación
ambigua»; adenda R1 regla 5 / D-P4-α).

Disciplina heredada del fuzz M0 (B9.1/B9.2): bases verificadas ANTES de
mutar, oráculo por mutación comprobado contra la implementación POR
SEPARADO (el acuerdo entre dos implementaciones no sustituye al oráculo),
detección de ERROR COMÚN, y crash = fallo del gate (nunca excepción
propagada).

Bases: documentos `ActionRequest` válidos construidos desde el corpus dorado
(capacidad + PoP coherentes del generador), verificados `Admitted` contra el
servicio ANTES de mutar (cualquier fallo → base_errors y el gate falla).

Oráculo por clase de mutación (determinista):

- `doc_*` (documento exterior): extra → `malformed_descriptor`/
  unknown... NO: la capa de contrato rechaza con diagnóstico §5.6 que la
  admisión traduce a `malformed_descriptor`; campos de stdin/representabilidad
  → `malformed_descriptor` con safe_detail prefijado.
- `cap_*` (sobre de capacidad): MAC rota / alias no canónico / versión /
  key_id → `capability_rejected` (safe_detail `contract:*` o detalle de
  vigencia/ligadura).
- `pop_*`: MAC rota / digest / nonce → `capability_rejected`.
- `binding_*`: discordancia descriptor↔action_binding → `capability_rejected`
  (`binding:*`).
- `replay_*`: nonce ya reservado → `capability_rejected`/`nonce_replay`.
- `policy_*` (modo required): Deny → `policy_denied`.

Sensibilidad demostrada (tests): divergencia artificial (oráculo saboteado),
ERROR COMÚN (implementación saboteada con el diagnóstico incorrecto — el
oráculo lo detiene), y CRASH (implementación que lanza RuntimeError — el
gate lo reporta, no lo propaga).

Determinismo por ÍNDICE (más fuerte que semilla: la mutación i es
siempre la misma clase con el mismo salto) con conteos por clase y fingerprint
sha256 del corpus de bases. API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from helpers_m1 import (  # noqa: E402
    EXP, NOW, TEST_KEY, TEST_SALT, base_binding, capability_identity_digest,
    emit_request, make_capability_envelope, make_pop, make_request,
    make_service, _b64u, _emit)
from src.adapters.replay_store_file import FileReplayStore  # noqa: E402
from src.adapters.spawn_frontier_counter import SpawnFrontierCounter  # noqa: E402
from src.domain.outcomes import Admitted, AdmissionRejected  # noqa: E402
from src.ports.policy_port import Deny  # noqa: E402
from src.ports.replay_store import ReserveOutcome  # noqa: E402
from src.adapters.policy_fake import FakePolicyPort  # noqa: E402

SEED = 20260822

#: Oráculo por clase: (veredicto esperado, reason_code esperado).
ORACLE: dict[str, tuple[str, str]] = {
    "doc_extra": ("reject", "malformed_descriptor"),
    "doc_sv_2": ("reject", "malformed_descriptor"),
    "doc_stdin_empty_data": ("reject", "malformed_descriptor"),
    "doc_stdin_inline_nodata": ("reject", "malformed_descriptor"),
    "doc_stdin_inline_badsha": ("reject", "malformed_descriptor"),
    "doc_nul_command": ("reject", "malformed_descriptor"),
    "doc_nul_arg": ("reject", "malformed_descriptor"),
    "doc_env_name_equals": ("reject", "malformed_descriptor"),
    "doc_surrogate_cwd": ("reject", "malformed_descriptor"),
    "cap_mac": ("reject", "capability_rejected"),
    # NOTA de clasificación (asentada en INC-3/estado post-M1): la
    # canonicalidad de los campos del sobre ANIDADO la aserta el schema
    # exterior M0 (§5.8 «incluida la forma base64url canónica de los
    # campos anidados») → la admisión la traduce a malformed_descriptor;
    # la regla 2 final archiva «canonicalidad» bajo capability_rejected
    # para el sobre COMO objeto superior.
    "cap_alias": ("reject", "malformed_descriptor"),
    "cap_sv2": ("reject", "capability_rejected"),
    "cap_keyid": ("reject", "capability_rejected"),
    "cap_expired": ("reject", "capability_rejected"),
    "pop_mac": ("reject", "capability_rejected"),
    "pop_digest": ("reject", "capability_rejected"),
    "pop_nonce": ("reject", "capability_rejected"),
    "binding_stdin": ("reject", "capability_rejected"),
    "binding_command": ("reject", "capability_rejected"),
    "replay_nonce": ("reject", "capability_rejected"),
    "policy_deny": ("reject", "policy_denied"),
}

_ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def _alias_of(canonical: str) -> str:
    """Alias no canónico de los MISMOS bytes (bits residuales, ADR-010)."""
    from base64 import urlsafe_b64decode
    raw = urlsafe_b64decode(canonical + "=" * ((-len(canonical)) % 4))
    residual = (len(canonical) * 6 - len(raw) * 8) % 8
    assert residual in (2, 4)
    return canonical[:-1] + _ALPHABET[_ALPHABET.index(canonical[-1]) ^ ((1 << residual) - 1)]


def _hexflip(value: str, salt: int) -> str:
    i = salt % len(value)
    c = value[i]
    repl = "0" if c != "0" else "1"
    return value[:i] + repl + value[i + 1:]


def build_bases() -> list[tuple[str, bytes, dict]]:
    """Bases válidas coherentes (nonce/salteados por índice para replay)."""
    bases = []
    for i, kind in enumerate(("empty", "inline")):
        nonce = f"{i + 1:02x}" * 16 if kind == "empty" else f"{i + 5:02x}" * 16
        if kind == "empty":
            stdin = {"kind": "empty"}
        else:
            data = f"carga-{i}".encode()
            stdin = {"kind": "inline_b64", "data_b64": _b64u(data),
                     "sha256": hashlib.sha256(data).hexdigest()}
        binding = base_binding(stdin_digest=hashlib.sha256(
            b"" if kind == "empty" else f"carga-{i}".encode()).hexdigest())
        env = make_capability_envelope(binding=binding, nonce=nonce)
        doc = make_request(env=env, stdin=stdin, nonce=nonce)
        bases.append((f"base-{kind}", emit_request(doc), doc))
    return bases


def mutate(doc: dict, index: int) -> tuple[str, dict] | None:
    """Mutación determinista por índice; devuelve (clase, doc mutado)."""
    classes = sorted(ORACLE)
    cls = classes[index % len(classes)]
    d = json.loads(json.dumps(doc))  # copia profunda
    if cls == "doc_extra":
        d["campo_extra"] = 1
    elif cls == "doc_sv_2":
        d["schema_version"] = 2
    elif cls == "doc_stdin_empty_data":
        d["stdin_policy"] = {"kind": "empty", "data_b64": _b64u(b"x")}
    elif cls == "doc_stdin_inline_nodata":
        d["stdin_policy"] = {"kind": "inline_b64"}
    elif cls == "doc_stdin_inline_badsha":
        d["stdin_policy"] = {"kind": "inline_b64", "data_b64": _b64u(b"x"),
                             "sha256": "0" * 64}
    elif cls == "doc_nul_command":
        d["command_absolute"] = "/bin/tru\x00e"
    elif cls == "doc_nul_arg":
        d["args"] = ["--x\x00"]
    elif cls == "doc_env_name_equals":
        d["env_allowlist_values"] = {"A=B": "1"}
    elif cls == "doc_surrogate_cwd":
        d["cwd"] = "/tm\ud800p"
    elif cls == "cap_mac":
        sig = d["capability_envelope"]["signature"]
        d["capability_envelope"]["signature"] = _hexflip(sig, index)
    elif cls == "cap_alias":
        ph = d["capability_envelope"]["protected_header_b64"]
        d["capability_envelope"]["protected_header_b64"] = _alias_of(ph)
    elif cls == "cap_sv2":
        # header firmado con schema_version=2 y MAC válida para ese header
        header = {"alg": "HS256", "schema_version": 2, "typ": "capability"}
        from src.domain.crypto import mac_envelope
        ph = _b64u(_emit(header))
        payload = json.loads(json.dumps(
            doc["capability_envelope"]))  # payload intacto
        pl = payload["payload_b64"]
        sig = _b64u(mac_envelope(TEST_KEY, b"ektel/capability/v1", ph, pl))
        d["capability_envelope"] = {"protected_header_b64": ph,
                                    "payload_b64": pl, "signature": sig}
    elif cls == "cap_keyid":
        from src.domain.crypto import compute_key_id
        env = make_capability_envelope(key_id=compute_key_id(TEST_SALT, b"k" * 32))
        d["capability_envelope"] = env
    elif cls == "cap_expired":
        env = make_capability_envelope(nbf=NOW - 7200, exp=NOW - 3600)
        d["capability_envelope"] = env
    elif cls == "pop_mac":
        d["invocation_proof"]["mac"] = _hexflip(
            d["invocation_proof"]["mac"], index)
    elif cls == "pop_digest":
        d["invocation_proof"]["payload_digest"] = "e" * 64
    elif cls == "pop_nonce":
        d["invocation_proof"]["nonce"] = "f" * 32
    elif cls == "binding_stdin":
        env = make_capability_envelope(binding=base_binding(stdin_digest="a" * 64))
        d["capability_envelope"] = env
    elif cls == "binding_command":
        env = make_capability_envelope(binding=base_binding(command_absolute="/bin/otro"))
        d["capability_envelope"] = env
    elif cls in ("replay_nonce", "policy_deny"):
        pass  # no mutan el doc: operan sobre el contexto
    else:  # pragma: no cover
        return None
    return cls, d


def bases_fingerprint(bases: list[tuple[str, bytes, dict]]) -> str:
    hasher = hashlib.sha256()
    for name, raw, _doc in bases:
        hasher.update(name.encode())
        hasher.update(raw)
    return hasher.hexdigest()


def _emit_raw(doc: dict) -> bytes:
    """Serialización que ADMITE surrogates escapados (el wire real puede
    transportarlos; la admisión debe rechazarlos por fsencode, regla 4
    final). json.dumps con ensure_ascii=True los emite como \\ud800."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def run_admission_fuzz(svc_admit=None) -> dict:
    """Ejecuta el fuzz completo. `svc_admit` inyectable para las pruebas de
    sensibilidad (sabotajes); None → servicio real por mutación."""
    bases = build_bases()
    fingerprint = bases_fingerprint(bases)

    # Verificación de bases: cada base debe ser Admitted ANTES de mutar.
    base_errors: list[dict] = []
    base_services = _service_pool()
    try:
        for name, raw, _doc in bases:
            out = base_services[0].admit(raw)
            if not isinstance(out, Admitted):
                base_errors.append({"base": name, "razon": "no-admitted"})
        # replay/policy usan la base[0] quemada por su propio contexto
        results = {"bases": len(bases), "base_errors": base_errors,
                   "total_mutations": 0, "oracle_failures": [], "crashes": [],
                   "per_class": {}, "fingerprint": fingerprint}
        if base_errors:
            return results

        classes = sorted(ORACLE)
        mutations = 0
        for index in range(len(classes) * 3):  # 3 pasadas con sales distintos
            cls = classes[index % len(classes)]
            name, raw, doc = bases[index % len(bases)]
            mutation = mutate(doc, index)
            assert mutation is not None
            _cls, mutated_doc = mutation
            payload = _emit_raw(mutated_doc)

            # Contexto por mutación (store fresco + modo por defecto).
            svc = svc_admit if svc_admit is not None else _fresh_service(cls)
            try:
                if cls == "replay_nonce":
                    # Quemar el nonce de ESTA base y reintentar la misma
                    # entrada: la segunda admisión debe ser replay.
                    svc.admit(raw)
                    out = svc.admit(raw)
                else:
                    out = svc.admit(payload)
            except Exception as exc:  # crash: fallo del gate, no propagado
                results["crashes"].append(
                    {"clase": cls, "excepcion": type(exc).__name__})
                continue
            mutations += 1
            expected_verdict, expected_reason = ORACLE[cls]
            # Oráculo: veredicto + reason_code exactos.
            if expected_verdict == "reject":
                ok = (isinstance(out, AdmissionRejected)
                      and out.reason_code == expected_reason)
            else:  # pragma: no cover — todas las clases son reject
                ok = isinstance(out, Admitted)
            if not ok:
                got = (out.reason_code if isinstance(out, AdmissionRejected)
                       else type(out).__name__)
                results["oracle_failures"].append(
                    {"clase": cls, "esperado": expected_reason, "obtenido": got})
            results["per_class"][cls] = results["per_class"].get(cls, 0) + 1
        results["total_mutations"] = mutations
        return results
    finally:
        for s in base_services[1:]:
            s.close()
        for s in _POOL:
            s.close()
        _POOL.clear()
        import shutil
        for d in _POOL_DIRS:
            shutil.rmtree(d, ignore_errors=True)
        _POOL_DIRS.clear()


_POOL: list[FileReplayStore] = []
_POOL_DIRS: list[str] = []


def _fresh_service(cls: str):
    """Servicio con contexto nuevo por mutación (replay/policy necesitan
    estados concretos)."""
    if cls == "policy_deny":
        return make_service(store=_new_store(),
                            policy_port=FakePolicyPort(Deny("d1")),
                            policy_mode="required")
    return make_service(store=_new_store())


def _new_store() -> FileReplayStore:
    tmp = tempfile.mkdtemp(prefix="ektel-fuzz-")
    _POOL_DIRS.append(tmp)
    store = FileReplayStore(Path(tmp))
    _POOL.append(store)
    return store


def _service_pool() -> list:
    store = _new_store()
    return [make_service(store=store), store]


def main() -> int:
    results = run_admission_fuzz()
    ok = (not results["base_errors"] and not results["oracle_failures"]
          and not results["crashes"])
    print(f"[admission] bases: {results['bases']} · mutaciones: "
          f"{results['total_mutations']} · fallos de oráculo: "
          f"{len(results['oracle_failures'])} · crashes: "
          f"{len(results['crashes'])} · errores de base: "
          f"{len(results['base_errors'])}")
    for cls in sorted(results["per_class"]):
        print(f"  {cls}: {results['per_class'][cls]}")
    print(f"  fingerprint bases: {results['fingerprint']}")
    if not ok:
        for f in results["oracle_failures"][:5]:
            print(f"  ORACLE FAIL: {f}")
        for c in results["crashes"][:5]:
            print(f"  CRASH: {c}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
