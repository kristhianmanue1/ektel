"""Servicio de admisión M1 (propuesta §6.2; regla 2 final de la adenda).

Orden fijo de validación (propuesta §6.2, adoptada por spec §4) con la
precedencia de la regla 2 final:

1. Capa de contrato del documento exterior (§5.8) → `malformed_descriptor`.
2. Coherencia interna del descriptor: representabilidad D-P3 (NUL/`=`/
   `os.fsencode`) y coherencia interna de `stdin_policy` con digest
   efectivo (D-P1) → `malformed_descriptor`. [Regla 2 final paso 1:
   la incoherencia de stdin precede a la autenticación de la capacidad;
   la representabilidad es validación de valores del descriptor
   (propuesta §6.2 paso 2), misma clase de diagnóstico.]
3. Autenticación de la capacidad: canonicalidad/MAC/header/payload/
   vigencia (§5.2/§6.9/§7.3) y `key_id` activo → `capability_rejected`.
   [Regla 2 final paso 2.]
4. Tras autenticar: coherencia descriptor↔`action_binding`, incluido el
   digest efectivo de stdin → `capability_rejected`. [Paso 3.]
5. PoP (ADR-003 §1.5) → `capability_rejected`; luego replay (reserva CAS
   del nonce, §7.4 — único efecto durable, idempotente por CAS) →
   `capability_rejected`. [Paso 4.]
6. Política según `policy_mode ∈ {absent, optional, required}` (§9,
   ADR-008 B7): `Deny` → `policy_denied`; puerto ausente/`Indeterminate`/
   `Allow` expirado o tardío → `policy_unavailable` en `required`, o
   degradación declarada en el resultado en `optional` (fail-open
   declarado; nunca silencioso). El paso 7 (evidencia obligatoria previa
   al inicio) es inerte en M1: el AuditSink es M3 (ADR-008 A3).

Sin efectos parciales antes de terminar la admisión (propuesta §6.2),
salvo la reserva CAS del nonce (ADR-004 A1: ante ambigüedad se prefiere
falso replay rechazado — un rechazo posterior quema el nonce).

Mapping M1 documentado (asentable en el acto de cierre): los diagnósticos
§5.6 de la capa de contrato del descriptor se traducen a
`malformed_descriptor`; los de la capacidad y la PoP, a
`capability_rejected` (la PoP autentica la posesión de la capacidad); un
replay store no disponible (caído/lleno/error) rechaza con
`capability_rejected` + `retryable=True` (vocabulario cerrado §8.3; sin
código nuevo — el fallo no es del descriptor sino de la infraestructura
de replay, y `retryable` lo declara).

API EXPERIMENTAL (spec §16). stdlib-only. Relojes inyectables (§7.1:
pared para vigencia, monotónico para plazos; nunca se cruzan).
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Optional, cast

from ..adapters.operator_key import OperatorKeyError, load_operator_key
from ..domain import contract_layer
from ..domain.admission_token import build_admission_token
from ..domain.capability import verify_capability
from ..domain.crypto import validate_key_material
from ..domain.outcomes import (
    Admitted,
    AdmissionOutcome,
    AdmissionRejected,
    PolicyReceipt,
    REASON_CAPABILITY_REJECTED,
    REASON_MALFORMED_DESCRIPTOR,
    REASON_POLICY_DENIED,
    REASON_POLICY_UNAVAILABLE,
)
from ..domain.pop import verify_invocation_proof
from ..domain.representability import RepresentabilityError, check_execve_strings
from ..domain.stdin_policy import effective_stdin
from ..ports.policy_port import Allow, Deny, Indeterminate, PolicyPort
from ..ports.replay_store import ReplayStore, ReserveOutcome

POLICY_MODES = ("absent", "optional", "required")

#: Garantías v1 (spec §9): clase real hasta que su hito las opere.
_REQUESTED_GUARANTEES = ("runtime_supervision", "output_bounds", "audit_trail")

_BINDING_FIELDS = (
    "action_id", "command_absolute", "args", "cwd", "env_allowlist_values",
    "stdin_policy_digest", "deadline_ms", "output_limits", "requested_guarantees",
)


def _representable_float(value: object) -> Optional[float]:
    """Float finito; los enteros no pueden perder precisión al convertirse."""
    # Tipos exactos: una subclase numérica puede controlar __float__, __int__
    # o comparaciones en esta frontera no confiable.
    if type(value) not in (int, float):
        return None
    numeric = cast(int | float, value)
    try:
        converted = float(numeric)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(converted):
        return None
    if isinstance(numeric, int) and int(converted) != numeric:
        return None
    return converted


def _safe_reserve_until(exp_wall: int, skew_tolerance_s: float) -> Optional[float]:
    """Cota durable finita que nunca vence antes del `exp` autenticado."""
    try:
        exp_float = float(exp_wall)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(exp_float):
        return None
    # Si la conversión redondeó hacia abajo, avanzar un ULP conserva la
    # propiedad de seguridad: la reserva puede durar más, nunca menos que exp.
    if exp_float < exp_wall:
        exp_float = math.nextafter(exp_float, math.inf)
    reserve_until = exp_float + skew_tolerance_s
    if (not math.isfinite(reserve_until)
            or reserve_until < exp_wall):
        return None
    return reserve_until


def _rejected(reason: str, detail: str = "", retryable: bool = False) -> AdmissionRejected:
    return AdmissionRejected(reason_code=reason, safe_detail=detail, retryable=retryable)


class AdmissionService:
    """Servicio de admisión M1. Inicialización fail-closed (clave/sal
    válidas o excepción); `admit(raw)` ejecuta el orden §6.2."""

    def __init__(
        self,
        *,
        replay_store: ReplayStore,
        deployment_salt: bytes,
        operator_key: Optional[bytes] = None,
        operator_key_path: Optional[Path] = None,
        policy_port: Optional[PolicyPort] = None,
        policy_mode: str = "absent",
        policy_timeout_s: float = 5.0,
        skew_tolerance_s: float = 30.0,
        wall_clock: Callable[[], float] = time.time,
        mono_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if policy_mode not in POLICY_MODES:
            raise ValueError(f"policy_mode invalido: {policy_mode!r}")
        policy_timeout = _representable_float(policy_timeout_s)
        if policy_timeout is None or policy_timeout <= 0.0:
            raise ValueError("policy_timeout_s debe ser finito y mayor que cero")
        skew_tolerance = _representable_float(skew_tolerance_s)
        if skew_tolerance is None or skew_tolerance < 0.0:
            raise ValueError("skew_tolerance_s debe ser finito y no negativo")
        if not callable(wall_clock) or not callable(mono_clock):
            raise ValueError("wall_clock y mono_clock deben ser invocables")
        if (operator_key is None) == (operator_key_path is None):
            raise ValueError("indica exactamente una fuente de operator_key")
        if operator_key is None:
            assert operator_key_path is not None
            operator_key = load_operator_key(operator_key_path)
        self._operator_key = operator_key
        try:
            self._active_key_id = validate_key_material(operator_key, deployment_salt)
        except ValueError as exc:
            raise OperatorKeyError(f"config:{exc}") from exc
        self._replay_store = replay_store
        self._policy_port = policy_port
        self._policy_mode = policy_mode
        self._policy_timeout_s = policy_timeout
        self._skew_tolerance_s = skew_tolerance
        self._wall_clock = wall_clock
        self._mono_clock = mono_clock

    @property
    def active_key_id(self) -> str:
        """`key_id` activo (adenda final regla 1)."""
        return self._active_key_id

    def admit(self, raw: bytes) -> AdmissionOutcome:
        """Admite un `ActionRequest` (bytes wire) según el orden §6.2."""
        # 1. Capa de contrato del documento exterior (§5.8).
        result = contract_layer.parse_action_request(raw)
        if result.verdict != "accept":
            return _rejected(REASON_MALFORMED_DESCRIPTOR,
                             f"contract:{result.diagnostic}")
        doc = result.value

        # 2. Coherencia interna del descriptor (D-P3 + D-P1, regla 2 final
        #    paso 1) — precede a la autenticación de la capacidad.
        try:
            check_execve_strings(doc)
        except RepresentabilityError as exc:
            return _rejected(REASON_MALFORMED_DESCRIPTOR, exc.detail)
        stdin = effective_stdin(doc["stdin_policy"])
        if isinstance(stdin, str):
            return _rejected(REASON_MALFORMED_DESCRIPTOR, stdin)
        stdin_bytes, stdin_digest = stdin

        # 3. Autenticación de la capacidad (regla 2 final paso 2).
        now_wall = self._read_clock(self._wall_clock)
        if now_wall is None:
            return _rejected(REASON_CAPABILITY_REJECTED,
                             "wall_clock_unavailable", retryable=True)
        cap = verify_capability(doc["capability_envelope"], self._operator_key,
                                self._active_key_id, now_wall,
                                self._skew_tolerance_s)
        if isinstance(cap, str):
            return _rejected(REASON_CAPABILITY_REJECTED, cap)

        # 4. Coherencia con el action_binding autenticado (paso 3).
        binding = cap.action_binding
        for field in _BINDING_FIELDS:
            expected = binding.get(field)
            if field == "stdin_policy_digest":
                actual: object = stdin_digest
            else:
                actual = doc.get(field)
            if actual != expected:
                return _rejected(REASON_CAPABILITY_REJECTED,
                                 f"binding:{field}")
        if cap.nonce != doc["nonce"]:
            return _rejected(REASON_CAPABILITY_REJECTED, "binding:nonce")

        # 5. PoP (paso 4, primera mitad).
        pop_error = verify_invocation_proof(doc["invocation_proof"],
                                            self._operator_key,
                                            cap.identity_digest, doc["nonce"])
        if pop_error is not None:
            return _rejected(REASON_CAPABILITY_REJECTED, pop_error)

        # 6. Replay: reserva CAS del nonce — único efecto durable (§6.2/§7.4).
        reserve_until = _safe_reserve_until(cap.exp, self._skew_tolerance_s)
        if reserve_until is None:
            return _rejected(REASON_CAPABILITY_REJECTED,
                             "time:reserve_until_unrepresentable")
        try:
            reserve: object = self._replay_store.reserve_nonce(
                cap.issuer_id, doc["nonce"], reserve_until)
        except Exception:
            return _rejected(REASON_CAPABILITY_REJECTED,
                             "replay_store_unavailable", retryable=True)
        if reserve is ReserveOutcome.ALREADY_RESERVED:
            return _rejected(REASON_CAPABILITY_REJECTED, "nonce_replay")
        if reserve is not ReserveOutcome.RESERVED:
            return _rejected(REASON_CAPABILITY_REJECTED,
                             "replay_store_unavailable", retryable=True)

        # 7. Política (paso 6; paso 7 evidencia: inerte en M1, M3).
        receipt, degraded, policy_error = self._evaluate_policy(doc, cap.identity_digest)
        if policy_error is not None:
            reason = (REASON_POLICY_DENIED if policy_error == "deny"
                      else REASON_POLICY_UNAVAILABLE)
            return _rejected(reason, f"policy:{policy_error}")

        return Admitted(
            admitted_action=build_admission_token(
                self._operator_key, cap.identity_digest, doc["action_id"],
                int(cap.exp), cap.issuer_id),
            identity_digest=cap.identity_digest,
            guarantee_plan=_guarantee_plan(doc.get("requested_guarantees", [])),
            policy_receipt=receipt,
            policy_mode=self._policy_mode,
            policy_degraded=degraded,
            skew_tolerance_s=self._skew_tolerance_s,
            admitted_at_wall=now_wall,
        )

    def _evaluate_policy(
        self, doc: Mapping[str, object], identity_digest: str
    ) -> tuple[Optional[PolicyReceipt], bool, Optional[str]]:
        """Devuelve (recibo, degradada, error). Error 'deny' →
        `policy_denied`; 'unavailable' → `policy_unavailable` en required
        o degradación declarada en optional (§9)."""
        if self._policy_mode == "absent":
            return None, False, None
        if self._policy_port is None:
            if self._policy_mode == "required":
                return None, False, "unavailable"
            return None, True, None  # optional sin puerto: fail-open declarado
        # El núcleo evalúa SU copia inmutable (ADR-008 A2): vista de sólo
        # lectura — la mutación por el adaptador se bloquea por tipo, no
        # por convención (contract tests con FakePolicyPort, INC-4).
        request: Mapping[str, object] = MappingProxyType({
            "schema_version": 1,
            "action_id": doc.get("action_id"),
            "identity_digest": identity_digest,
            "command_absolute": doc.get("command_absolute"),
            "policy_mode": self._policy_mode,
        })
        started = self._read_clock(self._mono_clock)
        if started is None:
            return self._policy_unavailable()
        try:
            # El protocolo ayuda al adaptador bien formado, pero su respuesta
            # cruza una frontera externa: se revalida desde `object`.
            decision: object = self._policy_port.evaluate(request)
        except Exception:
            return self._policy_unavailable()
        if type(decision) is Deny:
            # La clase negativa conserva fuerza fail-closed aunque su recibo
            # sea malformado. Degradarla como indisponibilidad en `optional`
            # convertiría un Deny explícito en admisión.
            return None, False, "deny"
        if type(decision) is Indeterminate:
            try:
                reason: object = decision.reason
            except Exception:
                return self._policy_unavailable()
            if type(reason) is not str or not reason:
                return self._policy_unavailable()
            if self._policy_mode == "required":
                return None, False, "unavailable"
            return None, True, None
        if type(decision) is not Allow:
            return self._policy_unavailable()
        try:
            # Snapshot único: nunca validar un valor y emitir otro obtenido
            # por una segunda lectura controlada por el adaptador.
            decision_id: object = decision.decision_id
            valid_until_raw: object = decision.valid_until_wall
        except Exception:
            return self._policy_unavailable()
        finished = self._read_clock(self._mono_clock)
        if finished is None:
            return self._policy_unavailable()
        elapsed = finished - started
        if not math.isfinite(elapsed) or elapsed < 0.0:
            return self._policy_unavailable()
        tardy = elapsed > self._policy_timeout_s
        # Validación del sobre de respuesta (B7): decision_id, vigencia
        # contra reloj de pared con tolerancia, recepción dentro del plazo
        # monotónico. Un Allow expirado o tardío → Indeterminate (§9).
        now_wall = self._read_clock(self._wall_clock)
        valid_until = _representable_float(valid_until_raw)
        validity_boundary = (None if now_wall is None
                             else now_wall - self._skew_tolerance_s)
        if (type(decision_id) is not str or not decision_id
                or valid_until is None
                or now_wall is None
                or validity_boundary is None
                or not math.isfinite(validity_boundary)
                or validity_boundary > valid_until):
            return self._policy_unavailable()
        if tardy:
            return self._policy_unavailable()
        return PolicyReceipt(decision_id=decision_id,
                             valid_until_wall=valid_until), False, None

    def _policy_unavailable(
        self,
    ) -> tuple[Optional[PolicyReceipt], bool, Optional[str]]:
        if self._policy_mode == "required":
            return None, False, "unavailable"
        return None, True, None

    @staticmethod
    def _read_clock(clock: Callable[[], float]) -> Optional[float]:
        try:
            value = clock()
            return _representable_float(value)
        except Exception:
            return None


def _guarantee_plan(requested: object) -> tuple[dict[str, object], ...]:
    """GuaranteePlan honesto de M1: las garantías v1 (`runtime_supervision`,
    `output_bounds`, `audit_trail`) son mecanismos de M2/M3 — en M1 se
    declaran `unsupported` hasta que su hito las opere con evidencia
    (spec §9 reglas 1–5; `guarantees_applied` refleja lo que realmente
    operó, nunca lo solicitado)."""
    plan = []
    if isinstance(requested, list):
        for magnitude in requested:
            if magnitude in _REQUESTED_GUARANTEES:
                plan.append({
                    "magnitude": magnitude,
                    "class": "unsupported",
                    "platform": "pending",
                    "mechanism": f"mecanismo del hito { _MILESTONE.get(magnitude, 'M?') } (no operado en M1)",
                    "assumptions": [],
                    "known_escapes": [],
                    "failure_mode": "guarantee_not_enforced_in_m1",
                    "evidence_ref": "M1: pendiente de promoción por evidencia (spec §9)",
                })
    return tuple(plan)


_MILESTONE = {
    "runtime_supervision": "M2",
    "output_bounds": "M2",
    "audit_trail": "M3",
}
