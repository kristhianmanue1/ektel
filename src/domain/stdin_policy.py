"""Reglas puras de `stdin_policy` — D-P1 ampliada (adenda R1 regla 1).

Semántica M1 de la coherencia interna y del digest efectivo de stdin, sin
tocar el wire contract M0 (H6 del acta de corrección M0 §13, resuelto en la
capa de admisión):

- `empty`: sólo `{kind:"empty"}` como forma esencial; `data_b64` prohibido
  (bytes efectivos `b""`); `sha256`, si viaja, debe ser el SHA-256 de los
  bytes vacíos. Esta lectura admite el vector dorado `areq-valid-01`
  (`{"kind":"empty","sha256":sha256(b"")}`) y cierra la holgura H6
  (`empty` con `data_b64`, o con `sha256` discordante, es
  `malformed_descriptor` en admisión).
- `inline_b64`: exige `data_b64` canónico Y `sha256`; se decodifica; el
  campo `sha256` debe coincidir con el digest de los bytes decodificados.
- Digest efectivo: `sha256(bytes efectivos)`; debe coincidir con
  `action_binding.stdin_policy_digest` de la capacidad autenticada
  (esa comparación ocurre tras autenticar — regla 2 final paso 3, ver
  `src/application/admit.py`).

La canonicalidad de `data_b64` ya la aserta la capa de contrato (§5.2); esta
función la re-comprueba como defensa en profundidad de la capa de admisión.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import hashlib
from base64 import urlsafe_b64encode, urlsafe_b64decode

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _b64u_canonical(value: str) -> bool:
    reencoded = urlsafe_b64encode(
        urlsafe_b64decode(value + "=" * ((-len(value)) % 4))
    ).rstrip(b"=").decode("ascii")
    return reencoded == value


def effective_stdin(policy: object) -> tuple[bytes, str] | str:
    """Devuelve `(bytes_efectivos, digest_efectivo)` o un detalle de
    incoherencia interna (→ `malformed_descriptor`, regla 2 final paso 1)."""
    if not isinstance(policy, dict):
        return "stdin_policy:no-dict"
    assert isinstance(policy, dict)
    kind = policy.get("kind")
    if kind == "empty":
        if "data_b64" in policy:
            return "stdin_policy:empty-with-data"
        sha = policy.get("sha256")
        if sha is not None and sha != EMPTY_SHA256:
            return "stdin_policy:empty-sha256-mismatch"
        return b"", EMPTY_SHA256
    if kind == "inline_b64":
        data_b64 = policy.get("data_b64")
        sha = policy.get("sha256")
        if not isinstance(data_b64, str) or not isinstance(sha, str):
            return "stdin_policy:inline-missing-fields"
        if not _b64u_canonical(data_b64):
            return "stdin_policy:data-b64-noncanonical"
        data = urlsafe_b64decode(data_b64 + "=" * ((-len(data_b64)) % 4))
        digest = hashlib.sha256(data).hexdigest()
        if sha != digest:
            return "stdin_policy:inline-sha256-mismatch"
        return data, digest
    return "stdin_policy:kind-invalid"
