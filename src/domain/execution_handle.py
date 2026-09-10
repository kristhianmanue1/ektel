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

**Propiedad del resultado.** Tras el handoff terminal el resultado pasa a ser
propiedad del handle que conserva el llamador; retener un handle ya terminal
puede retener su resultado, pero esa memoria es del llamador y ektel no afirma
gobernarla. Abandonar el último referente libera resultado y metadatos sin
mantener un slot ni un registro global.

Este objeto es deliberadamente **mutable en dos aspectos** —receipt y
resultado terminal—, porque D-M2-4 exige linealizar ambos «atómicamente en el
handle». Todo lo demás es inmutable tras la construcción.

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

    FIX-M2-R2/R4: el depósito del resultado terminal está reservado a la ruta
    del coordinador que acuñó el handle — el hilo vigilante creado en el
    `spawn` — mediante identidad de objeto (`deposit_terminal_result`). Un
    objeto forjado o ajeno no puede fabricar resultados ni interponerlos en
    el handle legítimo.
    """

    __slots__ = ("_ref", "_instance", "_identity_digest", "_action_id",
                 "_token", "_lock", "_receipt", "_result", "_released",
                 "_coordinator", "_terminal_ready")

    def __init__(self, *, handle_ref: str, coordinator_instance: str,
                 identity_digest: str, action_id: str,
                 termination_token: str,
                 coordinator: object = None) -> None:
        self._ref = handle_ref
        self._instance = coordinator_instance
        self._identity_digest = identity_digest
        self._action_id = action_id
        self._token = termination_token
        # Linealiza receipt y resultado dentro del objeto (D-M2-4).
        self._lock = threading.Lock()
        self._receipt: Optional[str] = None
        self._result: object = None
        self._released = False
        # Identidad del coordinador que acuñó el handle: la única ruta con
        # autoridad para depositar el terminal. `None` (construcción ajena)
        # nunca deposita.
        self._coordinator = coordinator
        self._terminal_ready = threading.Event()

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

    @property
    def has_terminal_result(self) -> bool:
        with self._lock:
            return self._result is not None

    def authenticates_for(self, operator_key: bytes,
                          coordinator_instance: str) -> bool:
        """Verdadero sólo para esta instancia del coordinador y esta acción."""
        return verify_termination_token(
            self._token, operator_key, coordinator_instance,
            self._identity_digest, self._action_id)

    def deposit_terminal_result(self, result: object,
                                coordinator: object) -> bool:
        """FIX-M2-R2: transferencia única de ownership del terminal.

        Sólo el coordinador que acuñó este handle puede depositar. Devuelve
        `False` (sin efecto) ante cualquier otro origen: un objeto forjado o
        ajeno no puede fabricar resultados.
        """
        if self._coordinator is None or coordinator is not self._coordinator:
            return False
        with self._lock:
            self._result = result
        self._terminal_ready.set()
        return True

    def mark_terminal_closed(self) -> None:
        """Ausencia definitiva del traspaso: despierta a los esperadores sin
        fabricar resultado. La invoca el vigilante del coordinador."""
        self._terminal_ready.set()

    def wait_terminal(self, timeout: Optional[float]) -> bool:
        """Espera acotada (o indefinida con `None`) al cierre del terminal."""
        return self._terminal_ready.wait(timeout)

    def take_terminal_result(self) -> object:
        """`await_result` transfiere la propiedad; el handle conserva sólo
        metadatos acotados de ciclo de vida."""
        with self._lock:
            result, self._result = self._result, None
            return result

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
        """Abandono explícito: libera resultado y metadatos. No hay registro
        global del que darse de baja."""
        with self._lock:
            self._result = None
            self._released = True

    @property
    def released(self) -> bool:
        with self._lock:
            return self._released

    def __repr__(self) -> str:  # pragma: no cover - diagnóstico saneado
        return f"<ExecutionHandle ref={self._ref} action={self._action_id}>"
