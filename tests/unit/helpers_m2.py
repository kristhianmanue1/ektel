"""Fixtures deterministas para las pruebas M2 (INC-M2-1).

Reutiliza los constructores M1 **por importación**, sin modificar
`helpers_m1.py`: la evidencia M1 se preserva intacta (acta de autorización
M2, A-M2-1). Sin I/O y sin procesos: INC-M2-1 no crea spawn real.
"""
from __future__ import annotations

import threading
from typing import Any

from .helpers_m1 import (  # noqa: F401
    EXP,
    NOW,
    TEST_KEY,
    TEST_KEY_ID,
    TEST_SALT,
    emit_request,
    make_request,
    make_service,
    valid_request_bytes,
)
from src.domain.start_request import StartRequest


class RecordingSpy:
    """Espía de pureza (G-M2-02): registra cualquier cruce prohibido.

    La revalidación no recibe puertos, así que este espía comprueba la
    propiedad más fuerte disponible: que los símbolos que podrían producir
    un efecto no se invocan durante la revalidación.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def record(self, name: str) -> None:
        self.calls.append(name)


def admitted_token(raw: bytes, **service_kwargs: Any) -> str:
    """Ejecuta la admisión M1 y devuelve el `admitted_action` emitido."""
    service = make_service(**service_kwargs)
    outcome = service.admit(raw)
    token = getattr(outcome, "admitted_action", None)
    if not isinstance(token, str):
        raise AssertionError(f"la admision no produjo token: {outcome!r}")
    return token


def valid_start_pair(**overrides: Any) -> tuple[str, bytes]:
    """Par `(admitted_action, action_request_wire)` coherente y revalidable."""
    raw = valid_request_bytes(**overrides)
    return admitted_token(raw), raw


def valid_start_request(**overrides: Any) -> StartRequest:
    token, raw = valid_start_pair(**overrides)
    return StartRequest(admitted_action=token, action_request_wire=raw)


class FakeProcessHost:
    """Doble determinista del `ProcessHost` (INC-M2-2: cero spawn real).

    FIX-M2-R2/R3: el doble emula el ciclo de vida del terminal. Sin entrega,
    `collect_terminal` no retorna: el slot permanece retenido, igual que un
    host real ante una acción sin terminal. `deliver_terminal` entrega un
    traspaso por el puerto legítimo; `deliver_absence` marca ausencia
    definitiva (canal caído sin terminal).
    """

    def __init__(self, *, reject: bool = False, raise_unknown: bool = False,
                 bad_ref: bool = False, bad_ref_hex: bool = False,
                 config_fingerprint: str | None = None) -> None:
        self.reject = reject
        self.raise_unknown = raise_unknown
        self.bad_ref = bad_ref
        self.bad_ref_hex = bad_ref_hex
        self._config_fingerprint = config_fingerprint
        self.spawns: list[Any] = []
        self.terminations: list[str] = []
        self._n = 0
        self._lock = threading.Lock()
        self._terminals: dict[str, Any] = {}
        self._absences: set[str] = set()
        self._events: dict[str, threading.Event] = {}

    @property
    def config_fingerprint(self) -> str:
        if self._config_fingerprint is None:
            raise RuntimeError("host de prueba sin perfil M2 acreditado")
        return self._config_fingerprint

    def bind_config(self, fingerprint: str) -> None:
        if self._config_fingerprint is None:
            self._config_fingerprint = fingerprint

    def _event_for(self, handle_ref: str) -> Any:
        with self._lock:
            event = self._events.get(handle_ref)
            if event is None:
                event = threading.Event()
                self._events[handle_ref] = event
            return event

    def spawn(self, plan: Any, *, deadline_eff_ms: int,
              config_fingerprint: str | None = None,
              validity_bound: bool = False) -> str:
        from src.ports.process_host import SpawnRejected
        requested = (self.config_fingerprint if config_fingerprint is None
                     else config_fingerprint)
        if requested != self.config_fingerprint:
            raise SpawnRejected("config_fingerprint_mismatch")
        if self.reject:
            raise SpawnRejected("host_rejected")
        if self.raise_unknown:
            raise RuntimeError("fallo opaco del host")
        self.spawns.append((plan, deadline_eff_ms, validity_bound))
        if self.bad_ref:
            return "no-es-un-ref"
        if self.bad_ref_hex:
            return "g" * 16
        self._n += 1
        return f"{self._n:016x}"

    def request_termination(self, handle_ref: str) -> None:
        self.terminations.append(handle_ref)

    def deliver_terminal(self, handle_ref: str, handoff: Any) -> None:
        """Entrega un traspaso por el puerto: la ruta legítima del terminal,
        dirigida a una única acción."""
        with self._lock:
            self._terminals[handle_ref] = handoff
        self._event_for(handle_ref).set()

    def deliver_absence(self, handle_ref: str) -> None:
        """Ausencia definitiva de una acción: no llegará terminal alguno."""
        with self._lock:
            self._absences.add(handle_ref)
        self._event_for(handle_ref).set()

    def collect_terminal(self, handle_ref: str, *,
                         timeout: Any) -> Any:
        """Espera la entrega del terminal de ESA acción. `None` sólo tras
        `deliver_absence` (ausencia definitiva) o, con timeout finito, al
        agotarse la espera."""
        self._event_for(handle_ref).wait(timeout)
        with self._lock:
            if handle_ref in self._terminals:
                return self._terminals[handle_ref]
        return None


def fake_handoff(raw: Any = None, stdout: bytes = b"",
                 stderr: bytes = b"") -> Any:
    """Traspaso terminal determinista para el doble del host."""
    from src.domain.execution_result import TerminalHandoff
    return TerminalHandoff(raw=dict(raw or {}), stdout=stdout, stderr=stderr)


class HostileStore:
    """Store que devuelve valores sin autoridad o falla, para reconciliación."""

    def __init__(self, consume: Any = None, status: object = "unknown",
                 raise_consume: bool = False,
                 raise_status: bool = False) -> None:
        self._consume = consume
        self._status = status
        self._raise_consume = raise_consume
        self._raise_status = raise_status
        self.status_calls = 0

    def reserve_nonce(self, issuer_id: str, nonce: str, until: float) -> Any:
        from src.ports.replay_store import ReserveOutcome
        return ReserveOutcome.RESERVED

    def consume_start_token(self, identity_digest: str) -> Any:
        if self._raise_consume:
            raise RuntimeError("store caido")
        return self._consume

    def start_token_status(self, identity_digest: str) -> Any:
        self.status_calls += 1
        if self._raise_status:
            raise RuntimeError("status caido")
        return self._status


def make_m2_admission(config: Any) -> Any:
    from src.application.admit import AdmissionService
    from .helpers_m1 import MemoryReplayStore
    return AdmissionService(
        replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
        operator_key=TEST_KEY, m2_config=config,
        wall_clock=lambda: float(NOW))


def make_start_service(store: Any = None, host: Any = None,
                       config: Any = None, now: float | None = None) -> Any:
    """Construye un `StartService` con relojes y dobles deterministas."""
    from src.application.start_service import StartService
    from src.application.config import M2Config
    from .helpers_m1 import MemoryReplayStore
    profile = config if config is not None else M2Config.build()
    process_host = host if host is not None else FakeProcessHost()
    if isinstance(process_host, FakeProcessHost):
        process_host.bind_config(profile.fingerprint)
    return StartService(
        replay_store=store if store is not None else MemoryReplayStore(),
        process_host=process_host,
        operator_key=TEST_KEY,
        active_key_id=TEST_KEY_ID,
        config=profile,
        admission_service=make_m2_admission(profile),
        declared_config_fingerprint=profile.fingerprint,
        skew_tolerance_s=30.0,
        wall_clock=(lambda: float(NOW) if now is None else now),
    )


def start_with_issuance(svc: Any, request: StartRequest) -> Any:
    """Fixture explícita: emitir por Admission M2 antes de ejercitar Start.

    No registra fingerprints ni altera tokens: la emisión genuina debe producir
    el mismo token. Los tests negativos de provenance llaman start directamente.
    Un replay de admisión conserva el token presentado para probar su rechazo.
    """
    from src.domain.outcomes import Admitted
    out = svc._admission.admit(request.action_request_wire)
    if isinstance(out, Admitted):
        assert out.admitted_action == request.admitted_action
    return svc.start(request)


def distinct_start_request(n: int) -> StartRequest:
    """`StartRequest` coherente y **distinto** por índice.

    Varía `action_id` y `nonce` **en el binding de la capacidad además de en
    el documento**: cambiar sólo el documento produce `binding:action_id` y la
    admisión lo rechaza (no es un fallo del runtime sino del fixture).
    """
    from .helpers_m1 import (
        base_binding, make_capability_envelope, make_request)
    action_id = f"action-{n:04d}"
    nonce = f"{n:032x}"
    envelope = make_capability_envelope(
        binding=base_binding(action_id=action_id), nonce=nonce)
    doc = make_request(env=envelope, nonce=nonce, action_id=action_id)
    raw = emit_request(doc)
    return StartRequest(admitted_action=admitted_token(raw),
                        action_request_wire=raw)
