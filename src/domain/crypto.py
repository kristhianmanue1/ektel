"""Perfil criptográfico byte-exacto v1 (spec v1.2 §5.2, ADR-002/003, ADR-010).

- MAC de sobre: `HMAC-SHA256(key, ASCII("ektel/<dominio>/v1") || 0x00 ||
  phb64 || "." || plb64)` — sobre las cadenas ASCII tal como viajan, sin
  decodificar ni re-serializar (§5.2). Dominios cerrados: capability, pop,
  admission, termination (§6.4).
- `identity_digest` (§6.5): SHA-256 de `phb64 + "." + plb64` ASCII; dos
  serializaciones distintas son identidades distintas (ADR-010 §6).
- PoP (ADR-003 §1.5): dominio `ektel/pop/v1` sobre
  `len32be(nonce) || nonce || payload_digest`.
- `key_id` (adenda final regla 1):
  `sha256(deployment_salt || operator_key).hexdigest()[:16]`, hex minúscula.
  `deployment_salt` es configuración de exactamente 32 bytes (estable por
  despliegue, no secreto); cambiar clave o sal exige reinicio y reemisión.
  Los vectores dorados conservan su sal literal histórica de prueba.

La verificación de sobres la hace la capa de contrato (parser de referencia
M0); estas primitivas sirven a la generación (token de admisión) y a las
comprobaciones de la capa de admisión.

API EXPERIMENTAL (spec §16). stdlib-only (ADR-006).
"""
from __future__ import annotations

import hashlib
import hmac
import struct

DOMAIN_CAPABILITY = b"ektel/capability/v1"
DOMAIN_POP = b"ektel/pop/v1"
DOMAIN_ADMISSION = b"ektel/admission/v1"
DOMAIN_TERMINATION = b"ektel/termination/v1"

DEPLOYMENT_SALT_LEN = 32
OPERATOR_KEY_LEN = 32


def mac_envelope(key: bytes, domain: bytes, ph_b64: str, pl_b64: str) -> bytes:
    """MAC de sobre sobre las cadenas ASCII tal como viajan (§5.2)."""
    msg = domain + b"\x00" + ph_b64.encode("ascii") + b"." + pl_b64.encode("ascii")
    return hmac.new(key, msg, hashlib.sha256).digest()


def identity_digest(ph_b64: str, pl_b64: str) -> str:
    """SHA-256 hex de la cadena autenticada (§6.5)."""
    return hashlib.sha256((ph_b64 + "." + pl_b64).encode("ascii")).hexdigest()


def mac_pop(key: bytes, nonce: bytes, payload_digest: bytes) -> bytes:
    """MAC de proof-of-possession (ADR-003 §1.5):
    `ektel/pop/v1 || 0x00 || len32be(nonce) || nonce || payload_digest`."""
    msg = DOMAIN_POP + b"\x00" + struct.pack(">I", len(nonce)) + nonce + payload_digest
    return hmac.new(key, msg, hashlib.sha256).digest()


def compute_key_id(deployment_salt: bytes, operator_key: bytes) -> str:
    """`key_id` = `sha256(salt || key).hexdigest()[:16]` (adenda final
    regla 1). No valida longitudes aquí (ver `validate_key_material`)."""
    return hashlib.sha256(deployment_salt + operator_key).hexdigest()[:16]


def validate_key_material(operator_key: bytes, deployment_salt: bytes) -> str:
    """Valida el material de configuración (32 bytes exactos cada uno) y
    devuelve el `key_id` activo. Fail-closed en el arranque, no por
    petición (adenda R1 regla 3)."""
    if len(operator_key) != OPERATOR_KEY_LEN:
        raise ValueError(
            f"operator_key: se esperaban {OPERATOR_KEY_LEN} bytes, hay {len(operator_key)}")
    if len(deployment_salt) != DEPLOYMENT_SALT_LEN:
        raise ValueError(
            f"deployment_salt: se esperaban {DEPLOYMENT_SALT_LEN} bytes, hay {len(deployment_salt)}")
    return compute_key_id(deployment_salt, operator_key)
