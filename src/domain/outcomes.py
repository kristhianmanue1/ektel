"""Resultados de admisión M1 (spec v1.2 §8.2/§8.3).

Vocabulario cerrado de `reason_code` de `AdmissionRejected` (§8.3, asientos
de la corrección M0): `malformed_descriptor`, `capability_rejected`,
`policy_denied`, `policy_unavailable`, `audit_unavailable`,
`guarantee_unsupported`. Los diagnósticos de parser de contrato (§5.6) NO se
mezclan: la capa de admisión los traduce a estos códigos (regla 2 final de
la adenda: descriptor → `malformed_descriptor`; capacidad →
`capability_rejected`).

`safe_detail` nunca filtra secretos, claves ni material de firma (§8.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union


REASON_MALFORMED_DESCRIPTOR = "malformed_descriptor"
REASON_CAPABILITY_REJECTED = "capability_rejected"
REASON_POLICY_DENIED = "policy_denied"
REASON_POLICY_UNAVAILABLE = "policy_unavailable"
REASON_AUDIT_UNAVAILABLE = "audit_unavailable"
REASON_GUARANTEE_UNSUPPORTED = "guarantee_unsupported"

#: Vocabulario cerrado §8.3 (asiento: `capability_invalid/expired/reused`
#: NO existen; la distinción se colapsa en `capability_rejected`).
ADMISSION_REJECT_REASONS = frozenset({
    REASON_MALFORMED_DESCRIPTOR,
    REASON_CAPABILITY_REJECTED,
    REASON_POLICY_DENIED,
    REASON_POLICY_UNAVAILABLE,
    REASON_AUDIT_UNAVAILABLE,
    REASON_GUARANTEE_UNSUPPORTED,
})


@dataclass(frozen=True)
class PolicyReceipt:
    """Recibo de la decisión `Allow` del PolicyPort (§8.2, ADR-008 D7b)."""
    decision_id: str
    valid_until_wall: float


@dataclass(frozen=True)
class Admitted:
    """Admisión aceptada (§8.2).

    `admitted_action` es el token de admisión opaco (§6.6: sobre firmado
    estándar, dominio `ektel/admission/v1`). Las declaraciones adicionales
    (`policy_mode`, `policy_degraded`, `skew_tolerance_s`,
    `admitted_at_wall`) son el vehículo M1 de G14/§2.2 del paquete pre-M1:
    en M1 estos datos viven en el resultado, no en un evento (M3).
    """
    admitted_action: str
    identity_digest: str
    guarantee_plan: tuple[dict[str, object], ...]
    policy_receipt: PolicyReceipt | None = None
    policy_mode: str = "absent"
    policy_degraded: bool = False
    skew_tolerance_s: float = 30.0
    admitted_at_wall: float = 0.0


@dataclass(frozen=True)
class AdmissionRejected:
    """Rechazo de admisión con código cerrado §8.3."""
    reason_code: str
    safe_detail: str = ""
    retryable: bool = False


AdmissionOutcome = Union[Admitted, AdmissionRejected]
