"""Sonda adversarial G-M2-15 — O1 (linealización CAS) y O6 (plazo cero).

A) 8 hilos, MISMO token, FileReplayStore real: exactamente un Started, los
   demás capability_rejected (cas:already_spent); el store durable queda spent.
B) exp == now en el reloj de start: rechazo ANTES del CAS; el token NO se
   consume (status unspent) y no se crea proceso.

No modifica el repositorio.
"""
import sys, tempfile, threading, time
from pathlib import Path

ROOT = Path("/Users/krisnova/www/aria/ektel")
sys.path.insert(0, str(ROOT))

from tests.unit.helpers_m1 import (
    NOW, TEST_KEY, TEST_KEY_ID, MemoryReplayStore, base_binding,
    emit_request, make_capability_envelope, make_request, make_service)
from tests.unit.helpers_m2 import valid_start_request, FakeProcessHost
from src.adapters.replay_store_file import FileReplayStore
from src.application.start_service import StartService
from src.application.config import M2Config
from src.domain.start_request import StartRequest

tmpdir = Path(tempfile.mkdtemp(prefix="gm215-probe3-"))

# --- A) mismo token, 8 hilos, store real -----------------------------------
req = valid_start_request()
store = FileReplayStore(tmpdir / "a")
host = FakeProcessHost()
svc = StartService(replay_store=store, process_host=host,
                   operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
                   config=M2Config.build(max_concurrent_actions=8),
                   wall_clock=lambda: float(NOW))
outs = []
b = threading.Barrier(8)
def w():
    b.wait()
    outs.append(svc.start(req))
ts = [threading.Thread(target=w) for _ in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]
kinds = {}
for o in outs:
    k = (type(o).__name__, getattr(o, "reason_code", ""),
         getattr(o, "safe_detail", ""))
    kinds[k] = kinds.get(k, 0) + 1
for k, v in sorted(kinds.items()):
    print("A)", k, "x", v)
started = sum(1 for o in outs if type(o).__name__ == "Started")
print("A) Started =", started, "| spawns reales en host =", len(host.spawns))
# durabilidad: reabrir el store y comprobar spent
store.close()
store2 = FileReplayStore(tmpdir / "a")
import json
state = json.loads((tmpdir / "a" / "state.json").read_text())
print("A) spent durable tras reinicio =", len(state["spent"]) == 1)
out2 = svc.start(req)
print("A) reintento post-reinicio:", type(out2).__name__,
      getattr(out2, "safe_detail", ""))
store2.close()

# --- B) plazo cero: remaining redondeado a 0 ms → effective_zero ------------
from src.domain.revalidation import revalidate_start_request

EXP0 = NOW + 1  # admisión válida
binding = base_binding(command_absolute="/bin/sleep", args=["1"],
                       action_id="action-zero")
env = make_capability_envelope(binding=binding, exp=EXP0)
doc = make_request(env=env, command_absolute="/bin/sleep", args=["1"],
                   action_id="action-zero")
raw0 = emit_request(doc)
adm = make_service(store=MemoryReplayStore())
res_adm = adm.admit(raw0)
tok0 = getattr(res_adm, "admitted_action", None)
print("B) admision con exp=NOW+1:", type(res_adm).__name__)
assert isinstance(tok0, str), res_adm

# Reloj de start: EXP0 - 0.0004 → remaining = exp*1000 - ceil(now*1000) = 0
NOW_START = float(EXP0) - 0.0004
plan0 = revalidate_start_request(tok0, raw0, operator_key=TEST_KEY,
                                 active_key_id=TEST_KEY_ID,
                                 now_wall=NOW_START, skew_tolerance_s=30.0)
print("B) revalidacion pura:", type(plan0).__name__)
assert hasattr(plan0, "identity_digest"), plan0

storeB = FileReplayStore(tmpdir / "b")
hostB = FakeProcessHost()
svcB = StartService(replay_store=storeB, process_host=hostB,
                    operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
                    wall_clock=lambda: NOW_START)
outB = svcB.start(StartRequest(admitted_action=tok0,
                               action_request_wire=raw0))
print("B) start:", type(outB).__name__, getattr(outB, "reason_code", ""),
      getattr(outB, "safe_detail", ""))
print("B) spawns en host =", len(hostB.spawns))
print("B) status del token en store durable =",
      storeB.start_token_status(plan0.identity_digest),
      "(esperado: unspent — el CAS NO debió ocurrir)")
storeB.close()
print("FIN SONDA 3")
