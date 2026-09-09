"""Orquestación de `start`, `terminate` y `await_result` — INC-M2-2.

Implementa la **linealización de efectos** de ADR-011 §2.6:

1. plan inmutable por revalidación pura (INC-M2-1);
2. reserva de slot **antes de cualquier efecto irreversible** (D-M2-2);
3. nueva muestra de reloj y recálculo de la cota, **inmediatamente antes** del
   CAS: nunca se reutiliza una duración que ya pudo vencer;
4. CAS durable `unspent → spent`;
5. spawn **inmediatamente después**, sin otra dependencia externa intermedia.

Sólo `ConsumeOutcome.CONSUMED` cruza la frontera de proceso. Ningún valor
truthy ni subtipo no reconocido adquiere autoridad: las comparaciones son por
identidad.

**Reconciliación (ADR-011 §2.6), conservando la incertidumbre:**

| CAS | `start_token_status` | Resultado |
|---|---|---|
| `CONSUMED` | — | spawn |
| `ALREADY_SPENT` | — | `capability_rejected` |
| `UNAVAILABLE`, excepción o tipo desconocido | `spent` | `start_failed_indeterminate` |
| ídem | `unspent` | `start_failed` (otro CAS admisible, **nunca spawn directo**) |
| ídem | `unknown` o consulta no disponible | `start_failed_indeterminate` |

El CAS linealiza el **derecho de inicio**, no garantiza que el spawn sucediera.
Sin handle confirmado, la reconciliación sólo puede afirmar
`start_failed_indeterminate`: no fabrica handle ni reintenta a ciegas.

`audit_mode` es siempre `optional` en M2 (D-M2-5(a)), así que el paso 1 de
§2.6 —el evento pre-inicio con `flush_protocol_completed`— **no existe
todavía**. Esa obligación es de M3 y aquí no se finge satisfecha.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

import secrets
import threading
import time
from typing import Callable, Optional

from ..domain.deadline import deadline_eff_ms
from ..domain.execution_handle import ExecutionHandle
from ..domain.revalidation import revalidate_start_request
from ..domain.start_outcomes import (
    REASON_CAPABILITY_REJECTED,
    REASON_START_FAILED,
    REASON_START_FAILED_INDETERMINATE,
    StartFailed,
    StartOutcome,
    Started,
)
from ..domain.start_request import ExecutionPlan, StartRequest
from ..domain.termination import (
    TerminationOutcome,
    TerminationRejected,
    mint_termination_token,
)
from ..ports.process_host import ProcessHost, SpawnRejected
from ..ports.replay_store import ConsumeOutcome, ReplayStore
from .config import M2Config


def _failed(reason: str, detail: str = "") -> StartFailed:
    return StartFailed(reason_code=reason, safe_detail=detail)


class _SlotPool:
    """Cota de capacidad de D-M2-2(a).

    **No es un presupuesto de memoria baja.** Con límites wire máximos el
    default `1` permite 128 MiB + 128 KiB estables; el máximo `64` permite
    8 GiB + 8 MiB, más overhead. El perfil de despliegue debe publicar ambos
    límites y la caracterización de RSS.
    """

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._used = 0
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        with self._lock:
            if self._used >= self._capacity:
                return False
            self._used += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def in_use(self) -> int:
        with self._lock:
            return self._used


class StartService:
    """Coordinador runtime: dueño de los handles (ADR-012 D-M2-4).

    Reiniciar el coordinador invalida todos sus handles: la instancia entra en
    el material autenticado del token de terminación.
    """

    def __init__(
        self,
        *,
        replay_store: ReplayStore,
        process_host: ProcessHost,
        operator_key: bytes,
        active_key_id: str,
        config: Optional[M2Config] = None,
        skew_tolerance_s: float = 30.0,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(config, M2Config) and config is not None:
            raise ValueError("config debe ser M2Config o None")
        self._config = config if config is not None else M2Config.build()
        self._replay_store = replay_store
        self._process_host = process_host
        self._operator_key = operator_key
        self._active_key_id = active_key_id
        self._skew_tolerance_s = skew_tolerance_s
        self._wall_clock = wall_clock
        self._slots = _SlotPool(self._config.max_concurrent_actions)
        # Identidad de esta instancia: reiniciar invalida los handles emitidos.
        self._instance = secrets.token_hex(8)
        self._handles: dict[str, ExecutionHandle] = {}
        self._handles_lock = threading.Lock()

    @property
    def coordinator_instance(self) -> str:
        return self._instance

    @property
    def slots_in_use(self) -> int:
        return self._slots.in_use

    def start(self, request: object) -> StartOutcome:
        """Ejecuta la linealización de ADR-011 §2.6."""
        if not isinstance(request, StartRequest):
            return _failed(REASON_CAPABILITY_REJECTED, "request:type")

        # 1. Revalidación pura. Sin efectos: el token sigue sin gastar.
        now_wall = self._read_clock()
        if now_wall is None:
            return _failed(REASON_START_FAILED, "clock:unavailable")
        plan = revalidate_start_request(
            request.admitted_action, request.action_request_wire,
            operator_key=self._operator_key, active_key_id=self._active_key_id,
            now_wall=now_wall, skew_tolerance_s=self._skew_tolerance_s)
        if isinstance(plan, StartFailed):
            return plan

        # 2. Slot antes de cualquier efecto irreversible. Sin capacidad no se
        #    consume token: el llamador puede reintentar el mismo token.
        if not self._slots.try_acquire():
            return _failed(REASON_START_FAILED, "capacity:no_slot")
        try:
            return self._start_with_slot(plan)
        except BaseException:
            # Cualquier salida no contemplada libera el slot antes de propagar.
            self._slots.release()
            raise

    def _start_with_slot(self, plan: ExecutionPlan) -> StartOutcome:
        # 3. Nueva muestra de reloj y recálculo, justo antes del CAS.
        now_wall = self._read_clock()
        if now_wall is None:
            self._slots.release()
            return _failed(REASON_START_FAILED, "clock:unavailable")
        if not now_wall < plan.exp_wall:
            self._slots.release()
            return _failed(REASON_CAPABILITY_REJECTED, "token:expired")
        effective_ms = deadline_eff_ms(plan.deadline_ms, plan.exp_wall, now_wall)
        if effective_ms is None:
            # Vida útil nula: rechazar ANTES del CAS y sin spawn. No se gasta
            # un token para crear un proceso sin tiempo de ejecución.
            self._slots.release()
            return _failed(REASON_CAPABILITY_REJECTED, "deadline:effective_zero")

        # 4. CAS durable.
        outcome = self._consume(plan.identity_digest)
        if isinstance(outcome, StartFailed):
            self._slots.release()
            return outcome

        # 5. Spawn inmediato, sin dependencia externa intermedia.
        return self._spawn(plan, effective_ms)

    def _consume(self, identity_digest: str) -> Optional[StartFailed]:
        """CAS y reconciliación. `None` significa `CONSUMED`."""
        try:
            result: object = self._replay_store.consume_start_token(identity_digest)
        except Exception:
            return self._reconcile(identity_digest, "cas:exception")
        if result is ConsumeOutcome.CONSUMED:
            return None
        if result is ConsumeOutcome.ALREADY_SPENT:
            return _failed(REASON_CAPABILITY_REJECTED, "cas:already_spent")
        # UNAVAILABLE, tipo desconocido o valor truthy: sin autoridad.
        return self._reconcile(identity_digest, "cas:unavailable")

    def _reconcile(self, identity_digest: str, origin: str) -> StartFailed:
        """Snapshot posterior, **no atómico** con el CAS. `unspent` sólo
        autoriza intentar otro CAS; nunca autoriza spawn."""
        try:
            status: object = self._replay_store.start_token_status(identity_digest)
        except Exception:
            return _failed(REASON_START_FAILED_INDETERMINATE,
                           f"{origin}:status_unavailable")
        if status == "unspent":
            return _failed(REASON_START_FAILED, f"{origin}:unspent")
        if status == "spent":
            return _failed(REASON_START_FAILED_INDETERMINATE, f"{origin}:spent")
        # "unknown" y cualquier otro valor: prevalece lo indeterminado.
        return _failed(REASON_START_FAILED_INDETERMINATE, f"{origin}:unknown")

    def _spawn(self, plan: ExecutionPlan, effective_ms: int) -> StartOutcome:
        try:
            handle_ref = self._process_host.spawn(plan, deadline_eff_ms=effective_ms)
        except SpawnRejected as exc:
            # Fallo explícito y síncrono ANTES de crear proceso: determinado.
            self._slots.release()
            return _failed(REASON_START_FAILED, f"spawn:{exc.safe_detail}"[:512])
        except Exception:
            # No se puede afirmar que no exista un proceso: indeterminado.
            # El slot NO se libera: podría haber un proceso vivo asociado.
            return _failed(REASON_START_FAILED_INDETERMINATE, "spawn:indeterminate")
        if type(handle_ref) is not str or len(handle_ref) != 16:
            self._slots.release()
            return _failed(REASON_START_FAILED_INDETERMINATE, "spawn:handle_ref_invalid")
        handle = ExecutionHandle(
            handle_ref=handle_ref,
            coordinator_instance=self._instance,
            identity_digest=plan.identity_digest,
            action_id=plan.action_id,
            termination_token=mint_termination_token(
                self._operator_key, self._instance, plan.identity_digest,
                plan.action_id),
        )
        with self._handles_lock:
            self._handles[handle_ref] = handle
        return Started(handle_ref=handle_ref)

    def handle_for(self, handle_ref: str) -> Optional[ExecutionHandle]:
        """Devuelve el handle emitido por **esta** instancia, si vive."""
        with self._handles_lock:
            return self._handles.get(handle_ref)

    def terminate(self, handle: object,
                  reason: object = None) -> TerminationOutcome:
        """`terminate` recibe el `ExecutionHandle` (spec §8.0; la interfaz
        `terminate(ActionId, …)` quedó descartada por no transportar material
        para autenticar al llamador).

        Un handle forjado, cruzado o de otra instancia produce
        `TerminationRejected(capability_rejected)`; no se inventa ningún otro
        reason code.
        """
        from ..domain.termination import TerminationReason
        if reason is not None and reason is not TerminationReason.OPERATOR_REQUESTED:
            return TerminationRejected()
        if not isinstance(handle, ExecutionHandle):
            return TerminationRejected()
        if not handle.authenticates_for(self._operator_key, self._instance):
            return TerminationRejected()
        # Repetición con el mismo objeto: mismo receipt, sin segundo efecto.
        if handle.already_terminated():
            return handle.linearized_receipt()
        # Post-resultado: se linealiza en el handle, NO se contacta al
        # supervisor y NO se reclasifica el resultado (D-M2-4).
        if handle.has_terminal_result:
            return handle.linearized_receipt()
        accepted = handle.linearized_receipt()
        try:
            self._process_host.request_termination(handle.handle_ref)
        except Exception:
            # La terminación es best-effort; el derecho ya quedó ejercido y el
            # receipt no promete que el proceso muriera.
            pass
        return accepted

    def await_result(self, handle: object) -> object:
        """Transfiere la propiedad del resultado terminal y libera el slot.

        En INC-M2-2 el portador `AwaitedExecution` con stdout/stderr todavía no
        existe: la salida acotada llega en INC-M2-3 y su entrega en INC-M2-4.
        """
        if not isinstance(handle, ExecutionHandle):
            return None
        result = handle.take_terminal_result()
        if result is not None:
            self._release_handle(handle)
        return result

    def _release_handle(self, handle: ExecutionHandle) -> None:
        with self._handles_lock:
            self._handles.pop(handle.handle_ref, None)
        handle.release()
        self._slots.release()

    def _read_clock(self) -> Optional[float]:
        try:
            value = self._wall_clock()
        except Exception:
            return None
        return value if type(value) is float and value == value else None
