#!/usr/bin/env python3
"""Fuzz diferencial determinista A/B con ORÁCULO sobre el corpus dorado (M0).

Persiste la corrida de fuzz del acta de corrección M0 (2026-08-20) como
reproducción exacta (FIX-AND-RETRY de Pinax, punto 4). El segundo
FIX-AND-RETRY (B9) añadió mutaciones semánticas; el TERCERO (B9.1/B9.2)
las reconstruye con bases y oráculo honestos:

- Fuzz de BYTES: por cada vector del corpus, MUTS_PER_VECTOR casos
  deterministas (semilla 20260820), clases cerradas: bitflip, truncate,
  prefix_nl, suffix_nl, prefix_space, suffix_space, insert_char,
  flip_two_bits. Criterio: acuerdo A/B (una mutación de bytes no tiene
  resultado único predecible).
- Fuzz SEMÁNTICO: parte EXCLUSIVAMENTE de vectores dorados accept
  (B9.1); antes de mutar, se verifica que A y B aceptan la base como
  ok (si no, el gate falla con base_errors). Cada mutación declara un
  ORÁCULO —veredicto, diagnóstico, capa y clase— (B9.2) y se comprueba
  POR SEPARADO contra A y contra B, además del acuerdo diferencial A/B.
  En sobres y invocation-proof la MAC se RE-COMPUTA tras mutar, para que
  la mutación tenga una sola causa.

Matriz del oráculo (congelada, tests/contract/test_fuzz_diferencial.py):
  sv > 1 (documento, payload o header)  → schema_version_unsupported
  sv 0, negativo o bool                 → invalid_value
  campo extra (documento/payload/header)→ unknown_field
  campo requerido ausente               → missing_field
  patrón, minLength o maxItems violado  → invalid_value

Campos requeridos/patrón deterministas por wire_type y alternativa
(B9.2.5): ver DOC_REQUIRED, OUTCOME_REQUIRED, DOC_PATTERN, OUTCOME_PATTERN,
ENVELOPE_PAYLOAD_*; nunca sorted(doc)[0].

Uso:
    python3 scripts/fuzz_diferencial.py            # bytes + semántico
    python3 scripts/fuzz_diferencial.py --json     # salida JSON

Exit 0 si y sólo si 0 divergencias, 0 fallos de oráculo y 0 errores de
base. stdlib-only (ADR-006). El gate permanente congela conteos exactos y
el fingerprint sha256 del corpus, y verifica sensibilidad tanto a
divergencia artificial como a ERROR COMÚN A/B (ambos parsers saboteados
con el mismo diagnóstico incorrecto: debe detenerlo el oráculo).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
import sys
from base64 import b64decode, urlsafe_b64encode
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "reference"))
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "clean-room"))

import ektel_ref_parser as parser_a  # noqa: E402
import ektel_cleanroom_parser as parser_b  # noqa: E402

VECTORS = ROOT / "contracts" / "vectors" / "v1"
SEED = 20260820
MUTS_PER_VECTOR = 17
CLASSES = ("bitflip", "truncate", "prefix_nl", "suffix_nl",
           "prefix_space", "suffix_space", "insert_char", "flip_two_bits")

ENV_DOMAINS = {"capability-envelope": "capability",
               "admission-token": "admission",
               "termination-token": "termination"}
ENV_TYP = {"capability-envelope": "capability",
           "admission-token": "admission-token",
           "termination-token": "termination-token"}
# Campo con patrón del payload, por wire type de sobre (determinista).
ENV_PAYLOAD_PATTERN = {"capability-envelope": "key_id",
                       "admission-token": "identity_digest",
                       "termination-token": "identity_digest"}
# Campo requerido del payload que se elimina (determinista; todos los
# campos de los tres payloads son requeridos).
ENV_PAYLOAD_REQUIRED = {"capability-envelope": "nonce",
                        "admission-token": "issuer_id",
                        "termination-token": "identity_digest"}
# Campos requeridos/patrón de documentos (deterministas, B9.2.5).
DOC_REQUIRED = {"action-request": "nonce",
                "execution-result": "state",
                "invocation-proof": "mac"}
DOC_PATTERN = {"action-request": "command_absolute",
               "execution-result": "identity_digest",
               "invocation-proof": "nonce"}
OUTCOME_REQUIRED = {
    "admission-outcome": {"admitted": "admitted_action",
                          "admission_rejected": "reason_code"},
    "start-outcome": {"started": "handle_ref",
                      "start_failed": "reason_code"},
    "termination-outcome": {"termination_accepted": "receipt",
                            "termination_rejected": "reason_code"},
}
OUTCOME_PATTERN = {
    "admission-outcome": {"admitted": "identity_digest"},
    "start-outcome": {"started": "handle_ref"},
}


def _b64u(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _emit(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _unb64(s: str) -> bytes:
    return b64decode(s + "=" * ((-len(s)) % 4))


def _env_mac(key: bytes, domain: str, ph: str, pl: str) -> bytes:
    msg = b"ektel/" + domain.encode("ascii") + b"/v1\x00" + \
        ph.encode("ascii") + b"." + pl.encode("ascii")
    return hmac.new(key, msg, hashlib.sha256).digest()


def _pop_mac(key: bytes, nonce_hex: str, digest_hex: str) -> str:
    nb, db = bytes.fromhex(nonce_hex), bytes.fromhex(digest_hex)
    msg = b"ektel/pop/v1\x00" + len(nb).to_bytes(4, "big") + nb + db
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _re_signed(wire_type: str, header: dict, payload: dict, key: bytes) -> bytes:
    ph = _b64u(_emit(header))
    pl = _b64u(_emit(payload))
    sig = _b64u(_env_mac(key, ENV_DOMAINS[wire_type], ph, pl))
    return _emit({"protected_header_b64": ph, "payload_b64": pl, "signature": sig})


def _without(d: dict, k: str) -> dict:
    return {kk: vv for kk, vv in d.items() if kk != k}


def _mut(name: str, raw: bytes, diag: str, layer: str) -> dict:
    """Toda mutación semántica declara oráculo: reject + diagnóstico +
    capa (B9.2)."""
    return {"class": name, "raw": raw, "verdict": "reject",
            "diagnostic": diag, "layer": layer}


def load_corpus() -> tuple[bytes, list[tuple[str, bytes, str, dict]]]:
    """Corpus completo con expect (B9.1): (id, bytes, wire_type, expect)."""
    index = json.loads((VECTORS / "index.json").read_text(encoding="utf-8"))
    key = bytes.fromhex(index["test_key_hex"])
    corpus = []
    for group_file in sorted(VECTORS.glob("*.vectors.json")):
        doc = json.loads(group_file.read_text(encoding="utf-8"))
        for v in doc["vectors"]:
            raw = b64decode(v["bytes"] + "=" * ((-len(v["bytes"])) % 4))
            corpus.append((v["id"], raw, v["wire_type"], v["expect"]))
    return key, corpus


def corpus_fingerprint(corpus) -> str:
    h = hashlib.sha256()
    for vid, raw, wire_type, _expect in corpus:
        h.update(f"{vid}|{wire_type}|".encode("utf-8"))
        h.update(raw)
        h.update(b"\x00")
    return h.hexdigest()


def semantic_mutations(wire_type: str, raw: bytes, key: bytes) -> list[dict]:
    """Mutaciones semánticas deterministas CON oráculo, sobre una base
    accept. Campos requeridos/patrón deterministas por wire_type y
    alternativa; en sobres y PoP la MAC se re-computa (causa única)."""
    doc = json.loads(raw)
    muts: list[dict] = []
    if wire_type in ENV_DOMAINS:
        header = json.loads(_unb64(doc["protected_header_b64"]))
        payload = json.loads(_unb64(doc["payload_b64"]))
        pf = ENV_PAYLOAD_PATTERN[wire_type]
        rf = ENV_PAYLOAD_REQUIRED[wire_type]
        for name, sv, diag in [("payload_sv_2", 2, "schema_version_unsupported"),
                               ("payload_sv_0", 0, "invalid_value"),
                               ("payload_sv_neg", -1, "invalid_value"),
                               ("payload_sv_true", True, "invalid_value")]:
            muts.append(_mut(name, _re_signed(wire_type, header,
                                              dict(payload, schema_version=sv), key),
                             diag, "sobre:payload"))
        muts.append(_mut("payload_extra", _re_signed(
            wire_type, header, dict(payload, zz_semantic_extra=1), key),
            "unknown_field", "sobre:payload"))
        muts.append(_mut("payload_missing", _re_signed(
            wire_type, header, _without(payload, rf), key),
            "missing_field", "sobre:payload"))
        muts.append(_mut("payload_pattern_nl", _re_signed(
            wire_type, header, dict(payload, **{pf: payload[pf] + "\n"}), key),
            "invalid_value", "sobre:payload"))
        muts.append(_mut("header_sv_2", _re_signed(
            wire_type, dict(header, schema_version=2), payload, key),
            "schema_version_unsupported", "sobre:header"))
        muts.append(_mut("header_extra", _re_signed(
            wire_type, dict(header, zz_semantic_extra=1), payload, key),
            "unknown_field", "sobre:header"))
        # M0-FAR-CLAUDE-01 (H3): confusión de tipos en type+enum del
        # header — typ entero, MAC re-computada: invalid_type (el tipo
        # precede al enum; detecta el error común A/B).
        if isinstance(header.get("typ"), str):
            muts.append(_mut("header_typ_int", _re_signed(
                wire_type, dict(header, typ=1), payload, key),
                "invalid_type", "sobre:header"))
        return muts
    # invocation-proof: la MAC de PoP cubre nonce/payload_digest; las
    # mutaciones de esos campos re-computan la MAC (causa única).
    if wire_type == "invocation-proof":
        for name, sv, diag in [("doc_sv_2", 2, "schema_version_unsupported"),
                               ("doc_sv_0", 0, "invalid_value"),
                               ("doc_sv_neg", -1, "invalid_value"),
                               ("doc_sv_true", True, "invalid_value")]:
            muts.append(_mut(name, _emit(dict(doc, schema_version=sv)),
                             diag, "documento"))
        muts.append(_mut("doc_extra", _emit(dict(doc, zz_semantic_extra=1)),
                         "unknown_field", "documento"))
        muts.append(_mut("doc_missing", _emit(_without(doc, DOC_REQUIRED[wire_type])),
                         "missing_field", "documento"))
        for fld in ("nonce", "payload_digest"):
            # Sufijo hex válido: cambia la LONGITUD (lo que el patrón censura)
            # y mantiene la MAC computable.
            m = dict(doc, **{fld: doc[fld] + "ab"})
            m["mac"] = _pop_mac(key, m["nonce"], m["payload_digest"])
            muts.append(_mut(f"pop_{fld}_len_plus_mac_recomputed", _emit(m),
                             "invalid_value", "documento"))
        return muts
    # Outcomes: alternativa por el discriminador outcome.
    if wire_type in OUTCOME_REQUIRED:
        alt = doc.get("outcome")
        if alt not in OUTCOME_REQUIRED[wire_type]:
            return []
        for name, sv, diag in [("doc_sv_2", 2, "schema_version_unsupported"),
                               ("doc_sv_0", 0, "invalid_value"),
                               ("doc_sv_neg", -1, "invalid_value"),
                               ("doc_sv_true", True, "invalid_value")]:
            muts.append(_mut(name, _emit(dict(doc, schema_version=sv)),
                             diag, "documento"))
        muts.append(_mut("doc_extra", _emit(dict(doc, zz_semantic_extra=1)),
                         "unknown_field", "documento"))
        muts.append(_mut("doc_missing", _emit(
            _without(doc, OUTCOME_REQUIRED[wire_type][alt])),
            "missing_field", "documento"))
        pat = OUTCOME_PATTERN.get(wire_type, {}).get(alt)
        if pat and pat in doc:
            muts.append(_mut("doc_pattern_nl", _emit(
                dict(doc, **{pat: doc[pat] + "\n"})), "invalid_value", "documento"))
        # M0-FAR-CLAUDE-01 (H1): confusión de tipos del DISCRIMINADOR —
        # tipo no hashable/erróneo; sin tipo declarado (enum-only) →
        # invalid_value, sin excepción en ningún parser.
        muts.append(_mut("doc_disc_type_confusion", _emit(
            dict(doc, outcome=[])), "invalid_value", "documento"))
        return muts
    # Documentos generales: action-request, execution-result.
    for name, sv, diag in [("doc_sv_2", 2, "schema_version_unsupported"),
                           ("doc_sv_0", 0, "invalid_value"),
                           ("doc_sv_neg", -1, "invalid_value"),
                           ("doc_sv_true", True, "invalid_value")]:
        muts.append(_mut(name, _emit(dict(doc, schema_version=sv)), diag, "documento"))
    muts.append(_mut("doc_extra", _emit(dict(doc, zz_semantic_extra=1)),
                     "unknown_field", "documento"))
    muts.append(_mut("doc_missing", _emit(_without(doc, DOC_REQUIRED[wire_type])),
                     "missing_field", "documento"))
    # M0-FAR-CLAUDE-01 (H2): confusión de tipos en items con type+enum —
    # invalid_type precede a invalid_value.
    if wire_type == "action-request":
        muts.append(_mut("doc_enum_item_type", _emit(
            dict(doc, requested_guarantees=[1])), "invalid_type", "documento"))
    if wire_type == "execution-result":
        # Const/enum sin tipo declarado: tipo equivocado → invalid_value.
        muts.append(_mut("doc_const_type", _emit(dict(doc, state=1)),
                         "invalid_value", "documento"))
    pf = DOC_PATTERN[wire_type]
    muts.append(_mut("doc_pattern_nl", _emit(dict(doc, **{pf: doc[pf] + "\n"})),
                     "invalid_value", "documento"))
    if wire_type == "action-request":
        muts.append(_mut("doc_maxitems", _emit(dict(
            doc, requested_guarantees=["audit_trail"] * 17)), "invalid_value", "documento"))
        muts.append(_mut("doc_args_257", _emit(dict(doc, args=["x"] * 257)),
                         "invalid_value", "documento"))
    if wire_type == "execution-result":
        ga = [dict(doc["guarantees_applied"][0])]
        ga[0]["magnitude"] = ""
        muts.append(_mut("doc_minlength", _emit(dict(doc, guarantees_applied=ga)),
                         "invalid_value", "documento"))
        ga = [dict(doc["guarantees_applied"][0])]
        ga[0]["assumptions"] = [str(i) for i in range(65)]
        muts.append(_mut("doc_array_max_65", _emit(dict(doc, guarantees_applied=ga)),
                         "invalid_value", "documento"))
    return muts


def _result_tuple(r):
    return (r.verdict, r.diagnostic, r.identity_digest)


def _safe_parse(parse, wire_type, raw, key):
    """M0-FAR-CLAUDE-01: ninguna entrada no confiable puede provocar
    excepción — un crash se registra como fallo del parser (crash), no
    se propaga ni se ignora."""
    try:
        return parse(wire_type, raw, key), None
    except Exception as exc:  # noqa: BLE001 - exactly the failure we hunt
        return None, f"{type(exc).__name__}: {exc}"


def run_fuzz() -> dict:
    """Fuzz de BYTES: acuerdo diferencial A/B sobre el corpus completo."""
    key, corpus = load_corpus()
    rng = random.Random(SEED)
    total = 0
    divergences = []
    per_class: dict[str, int] = {}
    for vid, raw, wire_type, _expect in corpus:
        for m in range(MUTS_PER_VECTOR):
            cls = CLASSES[m % len(CLASSES)]
            mutated = mutate(rng, raw, cls)
            total += 1
            per_class[cls] = per_class.get(cls, 0) + 1
            ra, crash_a = _safe_parse(parser_a.parse_wire, wire_type, mutated, key)
            rb, crash_b = _safe_parse(parser_b.parse_wire, wire_type, mutated, key)
            if crash_a or crash_b:
                divergences.append({
                    "vector": vid, "family": "bytes", "mutation_index": m,
                    "class": cls + "+crash",
                    "a": ["CRASH", crash_a or "-"],
                    "b": ["CRASH", crash_b or "-"],
                    "bytes_b64": _b64u(mutated),
                })
                continue
            if _result_tuple(ra) != _result_tuple(rb):
                divergences.append({
                    "vector": vid, "family": "bytes", "mutation_index": m,
                    "class": cls,
                    "a": [ra.verdict, ra.diagnostic, ra.identity_digest],
                    "b": [rb.verdict, rb.diagnostic, rb.identity_digest],
                    "bytes_b64": _b64u(mutated),
                })
    return {
        "family": "bytes",
        "seed": SEED,
        "muts_per_vector": MUTS_PER_VECTOR,
        "corpus_vectors": len(corpus),
        "corpus_fingerprint": corpus_fingerprint(corpus),
        "total_mutations": total,
        "per_class": dict(sorted(per_class.items())),
        "divergences": divergences,
        "divergence_count": len(divergences),
    }


def run_semantic_fuzz(parse_a=None, parse_b=None) -> dict:
    """Fuzz SEMÁNTICO con oráculo (B9.1/B9.2).

    Bases: SOLO vectores accept, verificadas contra A y B antes de mutar
    (base_errors hace fallar el gate). Cada mutación se comprueba contra
    el oráculo POR SEPARADO para A y para B, y además A==B. parse_a/parse_b
    permiten inyectar parsers saboteados (pruebas de sensibilidad)."""
    pa = parse_a or parser_a.parse_wire
    pb = parse_b or parser_b.parse_wire
    key, corpus = load_corpus()
    bases = 0
    base_errors = []
    total = 0
    divergences = []
    oracle_failures = []
    per_class: dict[str, int] = {}
    for vid, raw, wire_type, expect in corpus:
        if expect.get("verdict") != "accept":
            continue
        ra0, crash_a = _safe_parse(pa, wire_type, raw, key)
        rb0, crash_b = _safe_parse(pb, wire_type, raw, key)
        if crash_a or crash_b:
            base_errors.append({"vector": vid,
                                "a": ["CRASH", crash_a or "ok"],
                                "b": ["CRASH", crash_b or "ok"]})
            continue
        if (ra0.verdict, ra0.diagnostic) != ("accept", "ok") or \
           (rb0.verdict, rb0.diagnostic) != ("accept", "ok"):
            base_errors.append({"vector": vid,
                                "a": [ra0.verdict, ra0.diagnostic],
                                "b": [rb0.verdict, rb0.diagnostic]})
            continue
        muts = semantic_mutations(wire_type, raw, key)
        if not muts:
            base_errors.append({"vector": vid, "razon": "sin mutaciones"})
            continue
        bases += 1
        for m in muts:
            total += 1
            per_class[m["class"]] = per_class.get(m["class"], 0) + 1
            ra, crash_a = _safe_parse(pa, wire_type, m["raw"], key)
            rb, crash_b = _safe_parse(pb, wire_type, m["raw"], key)
            for label, crash in (("A", crash_a), ("B", crash_b)):
                if crash:
                    oracle_failures.append({
                        "vector": vid, "class": m["class"], "parser": label,
                        "layer": m["layer"], "crash": crash,
                        "expected": [m["verdict"], m["diagnostic"]],
                        "got": ["CRASH"],
                    })
            if crash_a or crash_b:
                continue
            if _result_tuple(ra) != _result_tuple(rb):
                divergences.append({
                    "vector": vid, "family": "semantic", "class": m["class"],
                    "a": [ra.verdict, ra.diagnostic, ra.identity_digest],
                    "b": [rb.verdict, rb.diagnostic, rb.identity_digest],
                })
            for label, r in (("A", ra), ("B", rb)):
                if (r.verdict, r.diagnostic) != (m["verdict"], m["diagnostic"]):
                    oracle_failures.append({
                        "vector": vid, "class": m["class"], "parser": label,
                        "layer": m["layer"],
                        "expected": [m["verdict"], m["diagnostic"]],
                        "got": [r.verdict, r.diagnostic],
                    })
    return {
        "family": "semantic",
        "bases": bases,
        "base_errors": base_errors,
        "total_mutations": total,
        "per_class": dict(sorted(per_class.items())),
        "divergences": divergences,
        "divergence_count": len(divergences),
        "oracle_failures": oracle_failures,
        "oracle_failure_count": len(oracle_failures),
    }


def mutate(rng: random.Random, raw: bytes, cls: str) -> bytes:
    if not raw:
        return raw + b"x"
    pos = rng.randrange(len(raw))
    if cls == "bitflip":
        bit = rng.randrange(8)
        return raw[:pos] + bytes([raw[pos] ^ (1 << bit)]) + raw[pos + 1:]
    if cls == "flip_two_bits":
        bit = rng.randrange(8)
        other = (bit + 1 + rng.randrange(7)) % 8
        b = raw[pos] ^ (1 << bit) ^ (1 << other)
        return raw[:pos] + bytes([b]) + raw[pos + 1:]
    if cls == "truncate":
        k = rng.randrange(1, max(2, len(raw)))
        return raw[:-k]
    if cls == "prefix_nl":
        return b"\n" + raw
    if cls == "suffix_nl":
        return raw + b"\n"
    if cls == "prefix_space":
        return b" " + raw
    if cls == "suffix_space":
        return raw + b" "
    if cls == "insert_char":
        ch = rng.choice(b" \n\t\"={}0123456789abcdefABCDEF"
                        b"+/ABCDEFGHIJKLMNOPQRSTUVWXYZ-_.")
        return raw[:pos] + bytes([ch]) + raw[pos:]
    raise AssertionError(cls)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()
    results = [run_fuzz(), run_semantic_fuzz()]
    if args.json:
        print(json.dumps(results, indent=1, sort_keys=True))
    else:
        for r in results:
            if r["family"] == "bytes":
                print(f"[bytes] corpus: {r['corpus_vectors']} · "
                      f"mutaciones: {r['total_mutations']} · "
                      f"divergencias: {r['divergence_count']}")
                print(f"  fingerprint corpus: {r['corpus_fingerprint']}")
            else:
                print(f"[semantic] bases accept: {r['bases']} · "
                      f"mutaciones: {r['total_mutations']} · "
                      f"divergencias A/B: {r['divergence_count']} · "
                      f"fallos de oráculo: {r['oracle_failure_count']} · "
                      f"errores de base: {len(r['base_errors'])}")
            for cls, n in r["per_class"].items():
                print(f"  {cls}: {n}")
            for d in r["divergences"][:20]:
                print(f"  DIVERGENCIA {d['vector']} ({d.get('class')}): "
                      f"A={d['a']} B={d['b']}")
            for f in r.get("oracle_failures", [])[:20]:
                print(f"  ORÁCULO {f['vector']} ({f['class']}, parser {f['parser']}, "
                      f"capa {f['layer']}): esperado {f['expected']}, obtuvo {f['got']}")
            for e in r.get("base_errors", [])[:20]:
                print(f"  BASE NO-ACCEPT {e}")
    bad = any(r["divergence_count"] for r in results) or \
        results[1]["oracle_failure_count"] or results[1]["base_errors"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
