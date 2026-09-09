"""Fixtures deterministas para las pruebas M2 (INC-M2-1).

Reutiliza los constructores M1 **por importación**, sin modificar
`helpers_m1.py`: la evidencia M1 se preserva intacta (acta de autorización
M2, A-M2-1). Sin I/O y sin procesos: INC-M2-1 no crea spawn real.
"""
from __future__ import annotations

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
