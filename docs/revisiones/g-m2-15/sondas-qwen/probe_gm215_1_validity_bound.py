"""Sonda adversarial G-M2-15 (revisor externo) — O6/O14.

Falsación: un deadline acotado por VIGENCIA (remaining < deadline_ms) que
vence debe clasificarse cause=deadline_validity_exhausted (ADR-005/D-M2-3).
Hipótesis del revisor: la clave `validity_bound` nunca llega al dict terminal
del supervisor, así que _build_awaited lee raw.get("validity_bound")=None y la
causa real observada será deadline_duration.

No modifica el repositorio: store y planes viven en /tmp.
"""
import sys, tempfile, threading, time
from pathlib import Path

ROOT = Path("/Users/krisnova/www/aria/ektel")
sys.path.insert(0, str(ROOT))

from tests.unit.helpers_m1 import (
    NOW, TEST_KEY, TEST_KEY_ID, base_binding, emit_request,
    make_capability_envelope, make_request, make_service, MemoryReplayStore)
from src.adapters.replay_store_file import FileReplayStore
from src.adapters.posix_supervisor import PosixSupervisorHost
from src.application.start_service import StartService
from src.application.config import M2Config
from src.domain.start_request import StartRequest

EXP_CUSTOM = NOW + 3          # vigencia: 3 s tras el reloj de admisión
DEADLINE_MS = 5000            # duración pedida: 5 s > remaining → validity-bound

binding = base_binding(command_absolute="/bin/sleep", args=["5"],
                       deadline_ms=DEADLINE_MS)
envelope = make_capability_envelope(binding=binding, exp=EXP_CUSTOM)
doc = make_request(env=envelope, command_absolute="/bin/sleep",
                   args=["5"], deadline_ms=DEADLINE_MS)
raw = emit_request(doc)

service = make_service(store=MemoryReplayStore())
outcome = service.admit(raw)
token = getattr(outcome, "admitted_action", None)
assert isinstance(token, str), f"admision fallo: {outcome!r}"

tmpdir = Path(tempfile.mkdtemp(prefix="gm215-probe1-"))
store = FileReplayStore(tmpdir)
host = PosixSupervisorHost(termination_grace_ms=500)
svc = StartService(replay_store=store, process_host=host,
                   operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
                   config=M2Config.build(termination_grace_ms=500),
                   wall_clock=lambda: float(NOW + 1))  # remaining ≈ 2000 ms

started = svc.start(StartRequest(admitted_action=token,
                                 action_request_wire=raw))
print("start:", type(started).__name__, getattr(started, "reason_code", ""))
assert type(started).__name__ == "Started", started

handle = svc.handle_for(started.handle_ref)
t0 = time.monotonic()
res = svc.await_result(handle, timeout=30)
elapsed = time.monotonic() - t0
assert res is not None, "ausencia de resultado (inesperado)"
r = res.result
print(f"elapsed_s={elapsed:.2f}")
print("outcome =", r.outcome)
print("cause   =", r.cause)
print("exit    =", r.exit_status)
print("measurements deadline_effective_ms =",
      r.measurements["deadline_effective_ms"])
print("guarantees:", r.guarantees_applied)

expected_cause = "deadline_validity_exhausted"
if r.cause == expected_cause:
    print("VEREDICTO-SONDA-1: NO falsificada — causa correcta")
else:
    print(f"VEREDICTO-SONDA-1: FALSIFICADA — se esperaba {expected_cause!r}, "
          f"se observó {r.cause!r}")
store.close()
