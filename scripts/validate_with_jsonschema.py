#!/usr/bin/env python3
"""Validación EXTERNA estratificada de los schemas v1 (Draft 2020-12).

Herramienta de conformidad offline pedida por los FIX-AND-RETRY de Pinax
(B9.3, tercera ronda): demuestra que los schemas son válidos y
auto-suficientes ante un consumidor externo, examinando TODAS las capas
aplicables de cada vector dorado:

  capa envelope  → envelope.schema.json (estructura, patterns, format)
  capa header    → protected-header.schema.json (decodificando phb64)
  capa payload   → {capability,admission-token,termination-token}-payload
  capa documento → el schema raíz del wire type (no-sobres)

Configuración exigida (contracts/README.md):
1. registro de TODOS los schemas locales por $id (https://ektel.local/…),
2. SIN resolución de red (dominio privado declarativo),
3. registro y aserción del formato ektel-b64u-canonical.

Expectativas por vector:
- accept  → TODAS sus capas aplicables DEBEN validar.
- reject  → si el defecto es visible al schema, DEBE rechazar en la capa
  esperada (envelope / header / payload / documento).
- skipped → sólo lo verdaderamente fuera del alcance de JSON Schema, con
  razón individual precisa:
    * malformed_json / duplicate_key: JSON estricto del parser (json.loads
      estándar acepta NaN y colapsa claves duplicadas);
    * size_exceeded: techo de bytes del parser, no del schema;
    * bad_signature: verificación criptográfica, no del schema;
    * exp <= nbf: regla semántica §6.9 no expresable en el subconjunto;
    * typ != wire_type: consistencia typ↔wire_type, gate del parser §5.5.

NO es dependencia del proyecto: requiere `jsonschema >= 4.18` en el
intérprete que lo ejecute (p. ej. venv efímero); la suite del proyecto
sigue stdlib-only (ADR-006). Exit 0 si y sólo si no hay discrepancias.
"""
from __future__ import annotations

import json
import re
import sys
from base64 import b64decode, urlsafe_b64decode, urlsafe_b64encode
from pathlib import Path

try:
    import jsonschema
    from referencing import Registry
    from referencing.jsonschema import DRAFT202012
except ModuleNotFoundError:  # pragma: no cover
    print("Este script requiere 'jsonschema>=4.18' (venv efímero); "
          "no es dependencia del proyecto.", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "contracts" / "schemas" / "v1"
VECTORS = ROOT / "contracts" / "vectors" / "v1"

ENVELOPE_WIRE = {"capability-envelope", "admission-token", "termination-token"}
ROOT_SCHEMA = {
    "capability-envelope": "envelope.schema.json",
    "admission-token": "envelope.schema.json",
    "termination-token": "envelope.schema.json",
    "invocation-proof": "invocation-proof.schema.json",
    "action-request": "action-request.schema.json",
    "admission-outcome": "admission-outcome.schema.json",
    "start-outcome": "start-outcome.schema.json",
    "termination-outcome": "termination-outcome.schema.json",
    "execution-result": "execution-result.schema.json",
}
PAYLOAD_SCHEMA = {
    "capability-envelope": "capability-payload.schema.json",
    "admission-token": "admission-token-payload.schema.json",
    "termination-token": "termination-token-payload.schema.json",
}
WIRE_TYP = {"capability-envelope": "capability",
            "admission-token": "admission-token",
            "termination-token": "termination-token"}


def b64u_canonical(value) -> bool:
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"[A-Za-z0-9_-]*", value):
        return False
    if len(value) % 4 == 1:
        return False
    decoded = urlsafe_b64decode(value + "=" * ((-len(value)) % 4))
    return urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value


def build_validators():
    resources = []
    meta_ok = 0
    for f in sorted(SCHEMAS.glob("*.schema.json")):
        contents = json.loads(f.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(contents)
        meta_ok += 1
        resources.append((contents["$id"], DRAFT202012.create_resource(contents)))
    registry = Registry().with_resources(resources)
    fc = jsonschema.FormatChecker()
    fc.checks("ektel-b64u-canonical", raises=ValueError)(b64u_canonical)

    def make(fname):
        schema = json.loads((SCHEMAS / fname).read_text(encoding="utf-8"))
        return jsonschema.Draft202012Validator(
            schema, registry=registry, format_checker=fc)

    validators = {wt: make(fname) for wt, fname in ROOT_SCHEMA.items()}
    header_v = make("protected-header.schema.json")
    payload_v = {wt: make(fname) for wt, fname in PAYLOAD_SCHEMA.items()}
    return meta_ok, validators, header_v, payload_v


def layer_result(validator, instance) -> tuple[bool, str]:
    errors = list(validator.iter_errors(instance))
    return (not errors), (errors[0].message[:100] if errors else "")


def main() -> int:
    meta_ok, validators, header_v, payload_v = build_validators()
    discrepancies = []
    skips = []          # (vid, categoría, razón individual)
    rejects_by_layer = {"envelope": 0, "header": 0, "payload": 0, "documento": 0}
    accepts_validated = 0
    accept_total = 0

    for group_file in sorted(VECTORS.glob("*.vectors.json")):
        doc = json.loads(group_file.read_text(encoding="utf-8"))
        for v in doc["vectors"]:
            vid, wire_type, expect = v["id"], v["wire_type"], v["expect"]
            raw = b64decode(v["bytes"] + "=" * ((-len(v["bytes"])) % 4))
            diag = expect.get("diagnostic")

            # -- skips verdaderamente fuera de JSON Schema ----------------
            if expect["verdict"] == "reject":
                if diag == "malformed_json":
                    # json.loads estándar PARSEA NaN/Infinity: si la instancia
                    # llega a parsearse, el defecto ES visible al schema (el
                    # tipo float no pasa `integer`) y se valida abajo como
                    # rechazo en capa documento. Sólo se salta lo ilegible.
                    try:
                        json.loads(raw)
                        parseable = True
                    except ValueError:
                        parseable = False
                    if not parseable:
                        skips.append((vid, "parser:json-estricto",
                                      "bytes ilegibles para json.loads "
                                      "estándar; gate del parser §5.1"))
                        continue
                if diag == "duplicate_key":
                    skips.append((vid, "parser:json-estricto",
                                  "json.loads colapsa claves duplicadas; el "
                                  "rechazo del schema sería por causas ajenas "
                                  "a la duplicación (gate §5.1)"))
                    continue
                if diag == "size_exceeded":
                    skips.append((vid, "parser:bytes",
                                  "techo global de 64 KiB medido sobre bytes; "
                                  "gate del parser §5.1"))
                    continue
                if diag == "bad_signature":
                    skips.append((vid, "cripto:mac",
                                  "verificación HMAC; no es responsabilidad "
                                  "del schema (§5.2)"))
                    continue

            try:
                instance = json.loads(raw)
            except ValueError:
                discrepancies.append((vid, "json ilegible inesperado"))
                continue

            if wire_type in ENVELOPE_WIRE:
                env_ok, env_msg = layer_result(validators[wire_type], instance)
                if expect["verdict"] == "accept":
                    accept_total += 1
                    if not env_ok:
                        discrepancies.append((vid, f"accept pero envelope "
                                                  f"rechaza: {env_msg}"))
                        continue
                    # decodificar capas internas (herramienta offline de
                    # conformidad: decodifica base64url canónico).
                    try:
                        header = json.loads(urlsafe_b64decode(
                            instance["protected_header_b64"] + "=" *
                            ((-len(instance["protected_header_b64"])) % 4)))
                        payload = json.loads(urlsafe_b64decode(
                            instance["payload_b64"] + "=" *
                            ((-len(instance["payload_b64"])) % 4)))
                    except ValueError as exc:
                        discrepancies.append((vid, f"capas internas "
                                                  f"ilegibles: {exc}"))
                        continue
                    h_ok, h_msg = layer_result(header_v, header)
                    p_ok, p_msg = layer_result(payload_v[wire_type], payload)
                    if not h_ok:
                        discrepancies.append((vid, f"accept pero header "
                                                  f"rechaza: {h_msg}"))
                    elif not p_ok:
                        discrepancies.append((vid, f"accept pero payload "
                                                  f"rechaza: {p_msg}"))
                    else:
                        accepts_validated += 1
                    continue
                # reject de sobre: localizar la capa esperada.
                if diag == "invalid_value":
                    # Excepciones semánticas precisas (B9.3.7):
                    try:
                        hdr = json.loads(urlsafe_b64decode(
                            instance["protected_header_b64"] + "=" *
                            ((-len(instance["protected_header_b64"])) % 4)))
                    except (ValueError, KeyError, TypeError):
                        hdr = {}
                    if isinstance(hdr, dict) and \
                            hdr.get("typ") != WIRE_TYP[wire_type]:
                        skips.append((vid, "parser:typ↔wire_type",
                                      "typ del header válido para SU schema "
                                      "pero discordante con el wire type; "
                                      "gate del parser §5.5"))
                        continue
                    if isinstance(hdr, dict) and wire_type == "capability-envelope":
                        try:
                            pl = json.loads(urlsafe_b64decode(
                                instance["payload_b64"] + "=" *
                                ((-len(instance["payload_b64"])) % 4)))
                        except (ValueError, KeyError, TypeError):
                            pl = {}
                        if isinstance(pl, dict) and pl.get("exp") is not None \
                                and pl.get("nbf") is not None \
                                and pl["exp"] <= pl["nbf"]:
                            skips.append((vid, "semántica:§6.9",
                                          "exp>nbf es regla del parser, no "
                                          "expresable en el subconjunto del "
                                          "schema"))
                            continue
                if not env_ok:
                    if diag in {"bad_base64", "invalid_type", "invalid_value"}:
                        # bad_base64/invalid_type: estructura y format del
                        # sobre; invalid_value: patrón estructural del sobre
                        # (p. ej. signature != 43 chars, acta §12) —
                        # rechazos legítimos de la capa envelope.
                        rejects_by_layer["envelope"] += 1
                        continue
                    discrepancies.append((vid, f"reject/{diag}: envelope "
                                              f"rechaza ({env_msg}) pero la "
                                              f"capa esperada era interna"))
                    continue
                # envelope válido: decodificar header/payload y validar capas.
                try:
                    header = json.loads(urlsafe_b64decode(
                        instance["protected_header_b64"] + "=" *
                        ((-len(instance["protected_header_b64"])) % 4)))
                    payload = json.loads(urlsafe_b64decode(
                        instance["payload_b64"] + "=" *
                        ((-len(instance["payload_b64"])) % 4)))
                except (ValueError, KeyError, TypeError) as exc:
                    discrepancies.append((vid, f"reject/{diag} con capas "
                                              f"internas ilegibles: {exc}"))
                    continue
                if diag == "alg_unsupported":
                    h_ok, h_msg = layer_result(header_v, header)
                    if h_ok:
                        discrepancies.append((vid, "alg_unsupported pero el "
                                                  f"header VALIDA ({h_msg})"))
                    else:
                        rejects_by_layer["header"] += 1
                    continue
                if diag == "invalid_type":
                    # Defecto visible en el header decodificado (p. ej.
                    # typ=1 con MAC válida, M0-FAR-CLAUDE-01 H3).
                    h_ok, h_msg = layer_result(header_v, header)
                    if h_ok:
                        p_ok2, p_msg2 = layer_result(payload_v[wire_type], payload)
                        if not p_ok2:
                            rejects_by_layer["payload"] += 1
                            continue
                        discrepancies.append((vid, "invalid_type pero "
                                                  "header y payload VALIDAN"))
                    else:
                        rejects_by_layer["header"] += 1
                    continue
                if diag == "schema_version_unsupported":
                    hv = header.get("schema_version")
                    want = "header" if (isinstance(hv, int) and hv != 1) \
                        else "payload"
                    h_ok, h_msg = layer_result(header_v, header)
                    p_ok, p_msg = layer_result(payload_v[wire_type], payload)
                    if want == "header" and not h_ok:
                        rejects_by_layer["header"] += 1
                    elif want == "payload" and h_ok and not p_ok:
                        rejects_by_layer["payload"] += 1
                    else:
                        discrepancies.append((vid,
                                              f"sv/{want} no coincide: "
                                              f"header_ok={h_ok} "
                                              f"payload_ok={p_ok}"))
                    continue
                if diag in {"unknown_field", "missing_field", "invalid_value"}:
                    h_ok, h_msg = layer_result(header_v, header)
                    p_ok, p_msg = layer_result(payload_v[wire_type], payload)
                    if h_ok and not p_ok:
                        rejects_by_layer["payload"] += 1
                    else:
                        discrepancies.append((vid,
                                              f"reject/{diag} esperado en "
                                              f"payload pero header_ok="
                                              f"{h_ok} payload_ok={p_ok}"))
                    continue
                discrepancies.append((vid, f"diagnóstico {diag} sin "
                                          f"regla de capa"))
                continue

            # -- documentos (no-sobres) -----------------------------------
            ok, msg = layer_result(validators[wire_type], instance)
            if expect["verdict"] == "accept":
                accept_total += 1
                if ok:
                    accepts_validated += 1
                else:
                    discrepancies.append((vid, f"accept pero el schema "
                                              f"rechaza: {msg}"))
            else:
                if ok:
                    discrepancies.append((vid, f"reject/{diag} pero el "
                                              f"schema ACEPTA"))
                else:
                    rejects_by_layer["documento"] += 1

    print(f"schemas meta-validados (Draft 2020-12): {meta_ok}")
    print(f"vectores accept completamente validados (todas las capas): "
          f"{accepts_validated}/{accept_total}")
    print("rechazos observados por capa: " + ", ".join(
        f"{k}={v}" for k, v in rejects_by_layer.items()))
    print(f"skips parser/cripto/semántica: {len(skips)}")
    for vid, cat, why in skips:
        print(f"  skip {vid} [{cat}]: {why}")
    print(f"discrepancias: {len(discrepancies)}")
    for vid, why in discrepancies:
        print(f"  DISCREPANCIA {vid}: {why}")
    return 1 if discrepancies else 0


if __name__ == "__main__":
    raise SystemExit(main())
