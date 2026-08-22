"""Carga segura de la clave del operador (adenda R1 regla 3 + regla 3
final; ADR-003 §9 base).

Excepción documentada al alcance de INC-3 (encargo): módulo de I/O en
`src/adapters/` para mantener `src/domain` puro.

Perfil exigido — cualquier fallo impide inicializar el servicio
(fail-closed de ARRANQUE; nunca `AdmissionRejected` ni `reason_code`
nuevo, que no existe para defectos de despliegue):

- abrir con `O_NOFOLLOW` y validar con `fstat` del descriptor YA abierto
  (sin TOCTOU `lstat`→`open`, regla 3 final);
- archivo regular, `st_uid == geteuid()`, modo exacto `0o600`;
- leer exactamente 32 bytes crudos y comprobar EOF.

Límite declarado: Python no garantiza zeroization de todas las copias en
memoria (regla 3 final) — el proceso retiene la clave hasta terminar.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

KEY_LEN = 32


class OperatorKeyError(Exception):
    """Fallo de carga de la clave del operador (arranque fail-closed).

    El mensaje es safe (ruta + razón); nunca contiene la clave."""


def load_operator_key(path: Path) -> bytes:
    """Carga la clave con el perfil regla 3 final; lanza
    `OperatorKeyError` en cualquier fallo."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:  # pragma: no cover — plataformas objetivo la tienen
        # La regla 3 final EXIGE O_NOFOLLOW: sin la bandera no hay apertura
        # segura posible; fallar el arranque, no degradar en silencio.
        raise OperatorKeyError("open:o_nofollow-unavailable")
    try:
        fd = os.open(os.fspath(path), os.O_RDONLY | nofollow)
    except OSError as exc:
        raise OperatorKeyError(f"open:{_safe_exc(exc)}") from exc
    try:
        try:
            st = os.fstat(fd)
        except OSError as exc:
            raise OperatorKeyError(f"fstat:{_safe_exc(exc)}") from exc
        if not stat.S_ISREG(st.st_mode):
            raise OperatorKeyError("not-regular")
        if st.st_uid != os.geteuid():
            raise OperatorKeyError("wrong-owner")
        if stat.S_IMODE(st.st_mode) != 0o600:
            raise OperatorKeyError(f"mode:{oct(stat.S_IMODE(st.st_mode))}")
        data = os.read(fd, KEY_LEN + 1)
        if len(data) != KEY_LEN:
            raise OperatorKeyError(f"length:{len(data)}")
        if os.read(fd, 1) != b"":
            raise OperatorKeyError("no-eof")
        return data
    finally:
        os.close(fd)


def _safe_exc(exc: OSError) -> str:
    return f"{type(exc).__name__}:{getattr(exc, 'errno', None)}"
