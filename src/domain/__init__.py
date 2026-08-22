"""ektel domain — verificaciones puras de admisión M1 (spec v1.2 §5–§8).

Sin I/O ni procesos (§4). La capa de contrato M0 se reutiliza por import
(`contract_layer`); la capa de admisión añade lo que §5.8 diferió a M1.

API EXPERIMENTAL (spec §16).
"""
from .capability import CapabilityView, verify_capability
from .crypto import (
    DOMAIN_ADMISSION, DOMAIN_CAPABILITY, DOMAIN_POP, DOMAIN_TERMINATION,
    compute_key_id, identity_digest, mac_envelope, mac_pop,
    validate_key_material,
)
from .outcomes import (
    ADMISSION_REJECT_REASONS, Admitted, AdmissionOutcome, AdmissionRejected,
    PolicyReceipt,
)
from .pop import verify_invocation_proof
from .representability import RepresentabilityError, check_execve_strings
from .stdin_policy import EMPTY_SHA256, effective_stdin

__all__ = [
    "ADMISSION_REJECT_REASONS", "CapabilityView", "DOMAIN_ADMISSION",
    "DOMAIN_CAPABILITY", "DOMAIN_POP", "DOMAIN_TERMINATION", "EMPTY_SHA256",
    "Admitted", "AdmissionOutcome", "AdmissionRejected", "PolicyReceipt",
    "RepresentabilityError", "check_execve_strings", "compute_key_id",
    "effective_stdin", "identity_digest", "mac_envelope", "mac_pop",
    "validate_key_material", "verify_capability", "verify_invocation_proof",
]
