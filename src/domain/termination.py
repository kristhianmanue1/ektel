"""Terminación local M2 — D-M2-4 (ADR-012), spec §8.0.

**Local y opaca.** El acta de autorización M2 (A-M2-4/A-M2-5) prohíbe crear
wire schema nuevo, `termination-token-payload` firmado, envelope, protocolo
remoto, capability distribuida o mecanismo cross-host. Nada de este módulo
viaja: el token de terminación y el receipt son objetos locales.

`TerminationReason` v1 admite **únicamente** `OPERATOR_REQUESTED`; no
transporta detalle arbitrario. El `receipt` de `TerminationAccepted` es un
identificador opaco local de la solicitud: **no** es un recibo de AuditSink,
no lleva claim de durabilidad ni MAC y nunca se registra completo.

El **token de terminación** que porta el `ExecutionHandle` sí está ligado
criptográficamente a la capacidad tal como fue admitida para ese `action_id`
y a la instancia del coordinador. Esa MAC es puramente local: existe para que
un handle forjado o cruzado no pueda autenticarse **sin necesidad de un
registro global** (D-M2-4: «no existe registro global de receipts»).

Reiniciar el coordinador invalida todos sus handles: la instancia entra en el
material autenticado.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Union

from .crypto import DOMAIN_TERMINATION
from .start_outcomes import REASON_CAPABILITY_REJECTED


class TerminationReason(Enum):
    """Único valor v1 (D-M2-4). Ampliar esto es cambio de contrato."""
    OPERATOR_REQUESTED = "operator_requested"


@dataclass(frozen=True)
class TerminationAccepted:
    """`receipt` opaco, local, no durable y sin MAC. Repetir la operación con
    el mismo objeto handle devuelve el mismo receipt."""
    receipt: str


@dataclass(frozen=True)
class TerminationRejected:
    """Único reason code posible: `capability_rejected` (D-M2-4). No se
    inventa ningún otro."""
    reason_code: str = REASON_CAPABILITY_REJECTED

    def __post_init__(self) -> None:
        if self.reason_code != REASON_CAPABILITY_REJECTED:
            raise ValueError("TerminationRejected solo admite capability_rejected")


TerminationOutcome = Union[TerminationAccepted, TerminationRejected]


def new_receipt() -> str:
    """Identificador opaco de solicitud. No es prueba de durabilidad ni de
    que la terminación surtiera efecto."""
    return secrets.token_hex(16)


def mint_termination_token(operator_key: bytes, coordinator_instance: str,
                           identity_digest: str, action_id: str) -> str:
    """Token opaco local ligado a (instancia, capacidad admitida, acción).

    No es un documento wire y no se serializa hacia ningún consumidor: sólo
    vive dentro del `ExecutionHandle` del llamador.
    """
    msg = b"\x00".join((
        DOMAIN_TERMINATION,
        coordinator_instance.encode("ascii"),
        identity_digest.encode("ascii"),
        action_id.encode("ascii"),
    ))
    return hmac.new(operator_key, msg, "sha256").hexdigest()


def verify_termination_token(token: object, operator_key: bytes,
                             coordinator_instance: str, identity_digest: str,
                             action_id: str) -> bool:
    """Comparación en tiempo constante. Un handle forjado, cruzado o de otra
    instancia del coordinador no puede producir un token válido."""
    if type(token) is not str:
        return False
    expected = mint_termination_token(operator_key, coordinator_instance,
                                      identity_digest, action_id)
    return hmac.compare_digest(expected, token)
