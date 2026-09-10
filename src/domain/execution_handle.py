"""`ExecutionHandle` — objeto local opaco del llamador (ADR-012 D-M2-4).

El **coordinador runtime** es el proceso dueño de handles; ADR-012 le da ese
nombre a lo que ADR-003 llamaba «proceso supervisor», y lo distingue del
**supervisor de acción**, dedicado y uno por acción.

El handle es **local, opaco y no serializable**: en el wire sólo aparece
`handle_ref` para correlación. Porta el token opaco de terminación ligado a la
capacidad admitida para ese `action_id` y a la instancia del coordinador.

**Sin registro global.** El receipt de la primera terminación se guarda en el
propio objeto; al dejar de existir el handle termina también esa retención.
Reiniciar el coordinador invalida todos sus handles.

El estado terminal vive en una capability interna del coordinador asociada por
identidad exacta al handle: el caller nunca recibe autoridad de depósito. Este
objeto sólo muta el receipt y la marca de abandono (FIX-M2-R13).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import threading
from typing import Optional

from .termination import (
    TerminationAccepted,
    new_receipt,
    verify_termination_token,
)


class ExecutionHandle:
    """Handle local del llamador. No serializable, no comparable por valor.

    FIX-M2-R12/R13: el resultado terminal no forma parte de la superficie del
    handle. El coordinador conserva por separado el estado de lifecycle y
    exige identidad exacta de este objeto para `terminate`/`await_result`.
    """

    __slots__ = ("_ref", "_instance", "_identity_digest", "_action_id",
                 "_token", "_lock", "_receipt", "_released", "__weakref__")

    def __init__(self, *, handle_ref: str, coordinator_instance: str,
                 identity_digest: str, action_id: str,
                 termination_token: str) -> None:
        self._ref = handle_ref
        self._instance = coordinator_instance
        self._identity_digest = identity_digest
        self._action_id = action_id
        self._token = termination_token
        # Linealiza el receipt dentro del objeto (D-M2-4).
        self._lock = threading.Lock()
        self._receipt: Optional[str] = None
        self._released = False

    @property
    def handle_ref(self) -> str:
        """Correlación wire (16 hex). No autentica nada por sí sola."""
        return self._ref

    @property
    def identity_digest(self) -> str:
        return self._identity_digest

    @property
    def action_id(self) -> str:
        return self._action_id

    def authenticates_for(self, operator_key: bytes,
                          coordinator_instance: str) -> bool:
        """Verdadero sólo para esta instancia del coordinador y esta acción."""
        return verify_termination_token(
            self._token, operator_key, coordinator_instance,
            self._identity_digest, self._action_id)

    def linearized_receipt(self) -> TerminationAccepted:
        """Primer `terminate` genera y guarda el receipt; repetir con **este
        mismo objeto** devuelve exactamente el mismo receipt (D-M2-4)."""
        with self._lock:
            if self._receipt is None:
                self._receipt = new_receipt()
            return TerminationAccepted(receipt=self._receipt)

    def already_terminated(self) -> bool:
        with self._lock:
            return self._receipt is not None

    def release(self) -> None:
        """Abandono explícito de la capability local por el caller."""
        with self._lock:
            self._released = True

    @property
    def released(self) -> bool:
        with self._lock:
            return self._released

    def __repr__(self) -> str:  # pragma: no cover - diagnóstico saneado
        return f"<ExecutionHandle ref={self._ref} action={self._action_id}>"
