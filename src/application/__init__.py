"""ektel application — orquestación de admisión M1 (propuesta §6.2).

API EXPERIMENTAL (spec §16).
"""
from .admit import AdmissionService, POLICY_MODES

__all__ = ["AdmissionService", "POLICY_MODES"]
