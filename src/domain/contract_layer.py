"""Capa de contrato M0 reutilizada por la admisión M1 (spec v1.2 §5.8).

M0 congeló los parsers de referencia (gateados contra el corpus de 91
vectores, INC-2/D-P2); M1 NO duplica esa validación: importa el parser de
referencia A (`contracts/parsers/reference/ektel_ref_parser.py`) y lo usa
como capa de contrato. La capa de ADMISIÓN (este paquete) añade la semántica
que §5.8 diferió a M1: firma del sobre anidado, PoP anidada, coherencia
descriptor↔`action_binding` y vigencia.

Re-serialización fiel de objetos anidados: para verificar la capacidad y la
PoP anidadas en un `ActionRequest` se re-emiten sus objetos con JSON
canónico compacto (`sort_keys`) y se someten al parser de sobre. Esto es
fiel porque (a) el documento exterior ya pasó el parseo estricto M0 (claves
duplicadas y tipos imposibles fueron rechazados antes) y (b) la MAC cubre
los valores ASCII `protected_header_b64 + "." + payload_b64` (§5.2), NO los
bytes del documento del sobre: la re-serialización no altera el input de la
MAC. El parser aplica sobre esa representación los cuatro pasos congelados
de §5.2 (estructura → base64url canónico → MAC → semántica).

API EXPERIMENTAL (spec §16). stdlib-only (ADR-006).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PARSER_A = _REPO_ROOT / "contracts" / "parsers" / "reference" / "ektel_ref_parser.py"


def _load_reference_parser() -> Any:
    name = "ektel_ref_parser_admission"
    spec = importlib.util.spec_from_file_location(name, _PARSER_A)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"no se pudo cargar el parser de referencia: {_PARSER_A}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # requerido por @dataclass del parser
    spec.loader.exec_module(module)
    return module


_REF = _load_reference_parser()


def emit_canonical(obj: Any) -> bytes:
    """JSON compacto con claves ordenadas (sólo re-emisión de objetos ya
    estrictamente validados; la verificación nunca re-serializa para
    verificar sobre el wire original, §5.2)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def parse_action_request(raw: bytes) -> Any:
    """Capa de contrato del documento exterior (§5.8: sólo estructura
    exterior en M0; `accept` ≠ autorización). La clave no se usa para wire
    types de documento."""
    return _REF.parse_wire("action-request", raw, b"")


def parse_capability_envelope(envelope_dict: dict[str, object], key: bytes) -> Any:
    """Capa de contrato + cripto del sobre de capacidad anidado: aplica los
    cuatro pasos de §5.2 (estructura, canonicalidad, MAC, header/payload
    semánticos, incluido `exp > nbf` de §6.9) sobre el sobre re-emitido."""
    return _REF.parse_wire("capability-envelope", emit_canonical(envelope_dict), key)


def parse_invocation_proof(proof_dict: dict[str, object], key: bytes) -> Any:
    """Capa de contrato + cripto de la PoP anidada (dominio `ektel/pop/v1`,
    ADR-003 §1.5)."""
    return _REF.parse_wire("invocation-proof", emit_canonical(proof_dict), key)


def decode_b64u_json(value_b64: str) -> Any:
    """Decodifica un campo base64url ya validado y parsea su JSON. Seguro
    porque sólo se invoca sobre payloads que el parser de sobre ya validó
    estrictamente tras una MAC válida (§5.2 paso 4)."""
    from base64 import urlsafe_b64decode

    raw = urlsafe_b64decode(value_b64 + "=" * ((-len(value_b64)) % 4))
    return json.loads(raw.decode("utf-8"))
