"""Representabilidad de las cadenas del futuro `execve` — D-P3 ampliada
(adenda R1 regla 2) + regla 4 de la adenda final.

Reglas de la capa de admisión (→ `malformed_descriptor`):

- NUL (`\\x00`) prohibido en `command_absolute`, `cwd`, cada elemento de
  `args`, y nombres/valores de `env_allowlist_values`;
- nombre de entorno no vacío y sin `=`;
- cada una de esas cadenas debe superar `os.fsencode` (encoding del
  filesystem): `UnicodeEncodeError` → `malformed_descriptor` (regla 4
  final; p. ej. surrogates escapados que JSON transporta pero el
  filesystem no puede representar).

Límite consciente (orden del dueño, documentado, no omisión): TAB y U+0085
permanecen admitidos cuando son representables — no hay evidencia para
prohibirlos en v1.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import os


class RepresentabilityError(ValueError):
    """Cadena no representable para el futuro execve (detalle safe)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _check_string(value: object, where: str) -> None:
    if not isinstance(value, str):
        raise RepresentabilityError(f"{where}:not-string")
    if "\x00" in value:
        raise RepresentabilityError(f"{where}:nul")
    try:
        os.fsencode(value)
    except UnicodeEncodeError:
        raise RepresentabilityError(f"{where}:not-fsencodable") from None


def check_execve_strings(doc: dict[str, object]) -> None:
    """Valida todas las cadenas destinadas al futuro `execve` (M2).
    Levanta `RepresentabilityError` con detalle safe (campo:defecto)."""
    _check_string(doc.get("command_absolute"), "command_absolute")
    _check_string(doc.get("cwd"), "cwd")
    args = doc.get("args")
    if isinstance(args, list):
        for i, arg in enumerate(args):
            _check_string(arg, f"args[{i}]")
    env = doc.get("env_allowlist_values")
    if isinstance(env, dict):
        for name, val in env.items():
            if not isinstance(name, str) or name == "":
                raise RepresentabilityError("env:name-empty")
            if "=" in name:
                raise RepresentabilityError("env:name-equals")
            _check_string(name, "env.name")
            _check_string(val, "env.value")
