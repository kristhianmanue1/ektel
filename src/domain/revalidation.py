"""Revalidación pura de `start` — ADR-011 §2.3, pasos 1 a 7.

Ruta **separada** de la admisión. ADR-011 prohíbe expresamente reutilizar
`AdmissionService.admit()`: confundiría la reserva previa esperada con un
replay y repetiría efectos y dependencias no deterministas.

Invariante 2 del paquete M2, acreditado por G-M2-02: esta ruta **no** llama
`reserve_nonce`, **no** evalúa `PolicyPort` y **no** emite otro token. Es
pura por construcción — no toca reloj, disco, red ni puertos: `now_wall` se
inyecta y no hay ningún parámetro de puerto en la firma.

Orden fijo (ADR-011 §2.3):

1. tipos exactos de ambos campos y techo de 64 KiB **antes** del parseo;
2. forma, canonicalidad base64url, MAC y payload cerrado del token de
   admisión con la clave activa;
3. re-parseo de `action_request_wire` con el parser v1 congelado;
4. repetición de representabilidad (`command_absolute`, cwd, args, entorno,
   stdin);
5. capacidad y PoP, incluido reloj de pared, nonce, digest efectivo de stdin
   y coherencia completa descriptor ↔ `action_binding`;
6. igualdad exacta token ↔ material revalidado para `identity_digest`,
   `action_id`, `exp` e `issuer_id`;
7. construcción del `ExecutionPlan` inmutable desde esa única instantánea.

Todo fallo de forma, cripto, vigencia o coherencia produce
`StartFailed(capability_rejected)` con `safe_detail` saneado. No se crea
proceso y, mientras no se intente el CAS, el token permanece sin gastar.

**Vigencia estricta (invariante 6):** en `start` se exige `now_wall < exp`
sin tolerancia de skew. El skew de admisión no concede tiempo de ejecución.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import hmac
import json
import math
from base64 import urlsafe_b64decode
from typing import Any, Mapping, Union

from . import contract_layer
from .capability import verify_capability
from .crypto import DOMAIN_ADMISSION, mac_envelope
from .representability import RepresentabilityError, check_execve_strings
from .start_outcomes import (
    REASON_CAPABILITY_REJECTED,
    StartFailed,
)
from .start_request import MAX_ACTION_REQUEST_BYTES, ExecutionPlan
# Fuente única de la canonicalidad base64url (ADR-010: bits residuales en
# cero). Se importa en vez de duplicarse: una segunda copia de un control
# criptográfico puede divergir de la original sin que ningún test lo note.
from .stdin_policy import _b64u_canonical, effective_stdin

#: Campos que la capacidad autenticada liga al descriptor (idénticos a los
#: de la admisión M1: la revalidación no relaja ni amplía la coherencia).
_BINDING_FIELDS = (
    "action_id", "command_absolute", "args", "cwd", "env_allowlist_values",
    "stdin_policy_digest", "deadline_ms", "output_limits", "requested_guarantees",
)

_TOKEN_ENVELOPE_KEYS = frozenset({"protected_header_b64", "payload_b64", "signature"})
_TOKEN_HEADER = {"alg": "HS256", "schema_version": 1, "typ": "admission-token"}
_TOKEN_PAYLOAD_KEYS = frozenset({
    "schema_version", "identity_digest", "action_id", "exp", "issuer_id",
})


def _fail(detail: str) -> StartFailed:
    return StartFailed(reason_code=REASON_CAPABILITY_REJECTED, safe_detail=detail)


def _exact_int(value: object) -> Union[int, None]:
    """Entero exacto; `bool` no es un entero válido en esta frontera."""
    if type(value) is not int:
        return None
    return value


def _decode_b64u_strict(value: object) -> Union[bytes, None]:
    """Decodifica sólo base64url canónico ASCII (ADR-010)."""
    if type(value) is not str or value == "":
        return None
    if not value.isascii():
        return None
    try:
        if not _b64u_canonical(value):
            return None
        return urlsafe_b64decode(value + "=" * ((-len(value)) % 4))
    except Exception:
        return None


def verify_admission_token(
    admitted_action: object, operator_key: bytes, now_wall: float
) -> Union[dict[str, Any], str]:
    """Paso 2: forma, canonicalidad, MAC y payload cerrado del token.

    Devuelve el payload autenticado o un detalle saneado de rechazo. La
    vigencia se comprueba **estricta**: `now_wall < exp`, sin skew.
    """
    envelope_raw = _decode_b64u_strict(admitted_action)
    if envelope_raw is None:
        return "token:b64-noncanonical"
    try:
        envelope = json.loads(envelope_raw.decode("utf-8"))
    except Exception:
        return "token:json-invalid"
    if not isinstance(envelope, dict) or set(envelope) != _TOKEN_ENVELOPE_KEYS:
        return "token:envelope-shape"
    ph_b64 = envelope["protected_header_b64"]
    pl_b64 = envelope["payload_b64"]
    sig_b64 = envelope["signature"]
    header_raw = _decode_b64u_strict(ph_b64)
    payload_raw = _decode_b64u_strict(pl_b64)
    signature = _decode_b64u_strict(sig_b64)
    if header_raw is None or payload_raw is None or signature is None:
        return "token:segment-b64-noncanonical"
    # MAC antes de interpretar semántica alguna del payload (§5.2 paso 3).
    expected = mac_envelope(operator_key, DOMAIN_ADMISSION, ph_b64, pl_b64)
    if not hmac.compare_digest(expected, signature):
        return "token:mac-invalid"
    try:
        header = json.loads(header_raw.decode("utf-8"))
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return "token:segment-json-invalid"
    if header != _TOKEN_HEADER:
        return "token:header-mismatch"
    if not isinstance(payload, dict) or set(payload) != _TOKEN_PAYLOAD_KEYS:
        return "token:payload-shape"
    if payload["schema_version"] != 1 or type(payload["schema_version"]) is bool:
        return "token:schema-version"
    for field in ("identity_digest", "action_id", "issuer_id"):
        if type(payload[field]) is not str:
            return f"token:{field}-type"
    exp = _exact_int(payload["exp"])
    if exp is None:
        return "token:exp-type"
    if not isinstance(now_wall, float) or not math.isfinite(now_wall):
        return "token:clock-invalid"
    # Invariante 6: estricto y sin skew. La admisión pudo conceder tolerancia;
    # la ejecución no la hereda.
    if not now_wall < exp:
        return "token:expired"
    return payload


def revalidate_start_request(
    admitted_action: object,
    action_request_wire: object,
    *,
    operator_key: bytes,
    active_key_id: str,
    now_wall: float,
    skew_tolerance_s: float,
) -> Union[ExecutionPlan, StartFailed]:
    """Ejecuta los siete pasos y devuelve el plan inmutable o `StartFailed`.

    Función pura: sin reloj propio, sin puertos, sin efectos. No reserva
    nonce, no evalúa política y no emite token (invariante 2).
    """
    # 1. Tipos exactos y techo, antes de cualquier parseo.
    if type(admitted_action) is not str:
        return _fail("request:admitted_action-type")
    if type(action_request_wire) is not bytes:
        return _fail("request:action_request_wire-type")
    if len(action_request_wire) > MAX_ACTION_REQUEST_BYTES:
        return _fail("request:action_request_wire-too-large")

    # 2. Token de admisión: forma, canonicalidad, MAC, payload cerrado y
    #    vigencia estricta.
    token = verify_admission_token(admitted_action, operator_key, now_wall)
    if isinstance(token, str):
        return _fail(token)

    # 3. Re-parseo del descriptor con el parser v1 congelado.
    parsed = contract_layer.parse_action_request(action_request_wire)
    if parsed.verdict != "accept":
        return _fail(f"contract:{parsed.diagnostic}")
    doc = parsed.value

    # 4. Representabilidad del futuro execve y coherencia interna de stdin.
    try:
        check_execve_strings(doc)
    except RepresentabilityError as exc:
        return _fail(exc.detail)
    stdin = effective_stdin(doc["stdin_policy"])
    if isinstance(stdin, str):
        return _fail(stdin)
    stdin_bytes, stdin_digest = stdin

    # 5. Capacidad y PoP, con reloj de pared y coherencia completa con el
    #    `action_binding` autenticado.
    cap = verify_capability(doc["capability_envelope"], operator_key,
                            active_key_id, now_wall, skew_tolerance_s)
    if isinstance(cap, str):
        return _fail(cap)
    binding = cap.action_binding
    for field in _BINDING_FIELDS:
        expected_value = binding.get(field)
        actual: object = stdin_digest if field == "stdin_policy_digest" else doc.get(field)
        if actual != expected_value:
            return _fail(f"binding:{field}")
    if cap.nonce != doc["nonce"]:
        return _fail("binding:nonce")
    # PoP: importada aquí para mantener el orden de ADR-011 explícito.
    from .pop import verify_invocation_proof
    pop_error = verify_invocation_proof(doc["invocation_proof"], operator_key,
                                        cap.identity_digest, doc["nonce"])
    if pop_error is not None:
        return _fail(pop_error)

    # 6. Igualdad exacta token ↔ material revalidado.
    if token["identity_digest"] != cap.identity_digest:
        return _fail("token:identity_digest-mismatch")
    if token["action_id"] != doc["action_id"]:
        return _fail("token:action_id-mismatch")
    if token["exp"] != cap.exp:
        return _fail("token:exp-mismatch")
    if token["issuer_id"] != cap.issuer_id:
        return _fail("token:issuer_id-mismatch")

    # 7. Plan inmutable desde esta única instantánea validada.
    plan = _build_plan(doc, cap.identity_digest, cap.issuer_id, cap.exp, stdin_bytes)
    return plan if isinstance(plan, ExecutionPlan) else _fail(plan)


def _build_plan(
    doc: Mapping[str, object], identity_digest: str, issuer_id: str,
    exp_wall: int, stdin_bytes: bytes,
) -> Union[ExecutionPlan, str]:
    """Paso 7. Los tipos ya fueron aceptados por el parser congelado; aquí
    sólo se estrechan a los exactos que el plan promete."""
    args = doc.get("args")
    env = doc.get("env_allowlist_values")
    limits = doc.get("output_limits")
    if not isinstance(args, list) or not all(type(a) is str for a in args):
        return "plan:args-type"
    if not isinstance(env, dict) or not all(
            type(k) is str and type(v) is str for k, v in env.items()):
        return "plan:env-type"
    if not isinstance(limits, dict):
        return "plan:output_limits-type"
    deadline_ms = _exact_int(doc.get("deadline_ms"))
    max_out = _exact_int(limits.get("max_stdout_bytes"))
    max_err = _exact_int(limits.get("max_stderr_bytes"))
    if deadline_ms is None or max_out is None or max_err is None:
        return "plan:numeric-type"
    command = doc.get("command_absolute")
    cwd = doc.get("cwd")
    action_id = doc.get("action_id")
    if type(command) is not str or type(cwd) is not str or type(action_id) is not str:
        return "plan:string-type"
    return ExecutionPlan(
        identity_digest=identity_digest,
        action_id=action_id,
        issuer_id=issuer_id,
        exp_wall=exp_wall,
        command_absolute=command,
        args=tuple(args),
        cwd=cwd,
        env=ExecutionPlan.freeze_env(env),
        stdin_bytes=stdin_bytes,
        deadline_ms=deadline_ms,
        max_stdout_bytes=max_out,
        max_stderr_bytes=max_err,
    )
