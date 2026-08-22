"""Puerto ReplayStore (spec v1.2 §7.4–7.5, ADR-004).

Dos registros CAS durable DISTINTOS:

- `nonce_reservation` durante `admit`: clave `(issuer_id, nonce)`,
  estados `free → reserved`; el nonce se reserva antes de emitir la
  admisión y permanece reservado hasta `exp + tolerancia`.
- `start_token_consumption` inmediatamente antes de crear el proceso
  (M2): clave `identity_digest`, estados `unspent → spent`.

En M1 el puerto se define y se ejercita con doubles (INC-3) y el
adaptador durable de archivo llega en INC-4. Sin store disponible, la
admisión rechaza fail-closed (ADR-004 §5); un store en memoria sólo
existe en pruebas.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from enum import Enum
from typing import Protocol


class ReserveOutcome(Enum):
    """Resultado CAS de `nonce_reservation`."""
    RESERVED = "reserved"
    ALREADY_RESERVED = "already_reserved"   # replay del nonce (§7.4)
    UNAVAILABLE = "unavailable"             # store caído/lleno/error fsync


class ConsumeOutcome(Enum):
    """Resultado CAS de `start_token_consumption` (uso productivo: M2)."""
    CONSUMED = "consumed"
    ALREADY_SPENT = "already_spent"         # perdedor concurrente (§7.4)
    UNAVAILABLE = "unavailable"


class ReplayStore(Protocol):
    """Protocolo del replay store durable (§7.4)."""

    def reserve_nonce(self, issuer_id: str, nonce: str,
                      reserve_until_wall: float) -> ReserveOutcome:
        """CAS `free → reserved` sobre `(issuer_id, nonce)`. Idempotente
        sólo en el sentido de no re-reservar: un nonce ya reservado
        devuelve `ALREADY_RESERVED` (fail-closed ante ambigüedad,
        ADR-004 A1)."""
        ...

    def consume_start_token(self, identity_digest: str) -> ConsumeOutcome:
        """CAS `unspent → spent` por `identity_digest` (uso: M2)."""
        ...

    def start_token_status(self, identity_digest: str) -> str:
        """`"unspent" | "spent" | "unknown"` — reconciliación por digest,
        nunca replay (§7.4)."""
        ...
