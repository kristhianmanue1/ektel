"""Verificación de la capacidad raíz anidada (spec §5.2/§6, ADR-003).

Pasos de la capa de admisión (regla 2 final paso 2 — todo
`capability_rejected`):

1. Capa de contrato sobre el sobre re-emitido: estructura, canonicalidad
   base64url, MAC, header (`alg`/`typ`/`schema_version`) y payload
   (incluido `exp > nbf`, §6.9) — cualquier diagnóstico §5.6 se traduce a
   `capability_rejected` (la MAC precede a la semántica: doble causa MAC
   rota + expirada cae por la MAC, §5.2/§5.6).
2. `key_id` del payload == `key_id` activo del despliegue (adenda final
   regla 1; cambiar clave o sal exige reinicio y reemisión).
3. Vigencia contra reloj de pared con tolerancia de skew declarada (§7.3,
   ADR-004 A3): válido si `nbf - skew <= now <= exp + skew`.

La coherencia descriptor↔`action_binding` NO está aquí: ocurre tras
autenticar (regla 2 final paso 3, en `src/application/admit.py`).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from . import contract_layer


@dataclass(frozen=True)
class CapabilityView:
    """Vista autenticada del payload de la capacidad."""
    identity_digest: str
    issuer_id: str
    key_id: str
    nonce: str
    nbf: int
    exp: int
    artifact_identity_profile: str
    action_binding: dict[str, object]


def _finite_float(value: object) -> float | None:
    """Convierte sólo números reales finitos; bool no es tiempo válido."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def verify_capability(envelope_dict: dict[str, object], operator_key: bytes,
                      active_key_id: str, now_wall: float,
                      skew_tolerance_s: float) -> CapabilityView | str:
    """Devuelve la vista autenticada o un detalle safe de rechazo
    (→ `capability_rejected`)."""
    result = contract_layer.parse_capability_envelope(envelope_dict, operator_key)
    if result.verdict != "accept":
        return f"contract:{result.diagnostic}"
    # El parser de sobre devuelve el payload ya decodificado y validado
    # tras una MAC válida (§5.2 paso 4).
    payload = result.value
    if payload.get("key_id") != active_key_id:
        return "key_id_mismatch"
    nbf = int(payload["nbf"])
    exp = int(payload["exp"])
    now = _finite_float(now_wall)
    skew = _finite_float(skew_tolerance_s)
    if now is None or skew is None or skew < 0.0:
        return "time_input_invalid"
    # Reordenar evita convertir implícitamente claims enteros arbitrarios a
    # float (`10**1000 - 30.0` lanza OverflowError). Las dos cotas derivadas
    # también deben permanecer finitas: una tolerancia que las desborde no
    # adquiere autoridad por comparación con +/-inf.
    not_before_boundary = now + skew
    expiry_boundary = now - skew
    if (not math.isfinite(not_before_boundary)
            or not math.isfinite(expiry_boundary)):
        return "time_range_invalid"
    if not_before_boundary < nbf:
        return "not_yet_valid"
    if expiry_boundary > exp:
        return "expired"
    return CapabilityView(
        identity_digest=result.identity_digest or "",
        issuer_id=payload["issuer_id"],
        key_id=payload["key_id"],
        nonce=payload["nonce"],
        nbf=nbf,
        exp=exp,
        artifact_identity_profile=payload["artifact_identity_profile"],
        action_binding=payload["action_binding"],
    )
