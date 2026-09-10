"""Sonda adversarial G-M2-15 (revisor externo) — O3/O5.

Falsación: `await_terminal` hace get→wait→pop NO atómicos y descarta el valor
del pop; dos hilos que esperan el mismo handle ya completado pueden obtener
AMBOS el handoff terminal: doble entrega del resultado y doble
`_slots.release()` → corrupción de capacidad (más procesos vivos que
max_concurrent_actions).

No modifica el repositorio.
"""
import sys, tempfile, threading, time
from pathlib import Path

ROOT = Path("/Users/krisnova/www/aria/ektel")
sys.path.insert(0, str(ROOT))

from tests.unit.helpers_m1 import TEST_KEY, TEST_KEY_ID
from tests.unit.helpers_m2 import distinct_start_request, make_start_service
from src.adapters.replay_store_file import FileReplayStore
from src.adapters.posix_supervisor import PosixSupervisorHost
from src.application.config import M2Config

tmpdir = Path(tempfile.mkdtemp(prefix="gm215-probe2-"))
store = FileReplayStore(tmpdir)
host = PosixSupervisorHost()
CAP = 2
svc = make_start_service(store=store, host=host,
                         config=M2Config.build(max_concurrent_actions=CAP))

doble_entrega = 0
corrupcion_slot = 0
ITER = 40

for i in range(ITER):
    req = distinct_start_request(i)          # /usr/bin/true, rápido
    out = svc.start(req)
    if type(out).__name__ != "Started":
        print("start fallo:", out); continue
    h = svc.handle_for(out.handle_ref)
    # Esperar a que la acción termine para que ambos hilos encuentren done
    time.sleep(0.15)
    resultados = []
    b = threading.Barrier(2)
    def worker():
        b.wait()
        resultados.append(svc.await_result(h, timeout=10))
    t1 = threading.Thread(target=worker); t2 = threading.Thread(target=worker)
    t1.start(); t2.start(); t1.join(); t2.join()
    no_none = [x for x in resultados if x is not None]
    if len(no_none) == 2:
        doble_entrega += 1
        print(f"iter {i}: DOBLE ENTREGA — ambos hilos recibieron resultado")
    if svc.slots_in_use != 0:
        corrupcion_slot += 1
        print(f"iter {i}: slots_in_use={svc.slots_in_use} tras await (esperado 0)")

print(f"RESUMEN: doble_entrega={doble_entrega}/{ITER} "
      f"corrupcion_slot={corrupcion_slot}/{ITER}")

# --- Demostración de consecuencia: sobre-admisión por encima de la capacidad
req_a = distinct_start_request(1000)  # acción larga
import json
from tests.unit.helpers_m1 import (base_binding, emit_request,
    make_capability_envelope, make_request, make_service, MemoryReplayStore,
    NOW)
binding = base_binding(command_absolute="/bin/sleep", args=["4"],
                       action_id="action-larga")
env = make_capability_envelope(binding=binding)
doc = make_request(env=env, command_absolute="/bin/sleep", args=["4"],
                   action_id="action-larga")
raw_larga = emit_request(doc)
adm = make_service(store=MemoryReplayStore())
tok = adm.admit(raw_larga).admitted_action
from src.domain.start_request import StartRequest
larga = svc.start(StartRequest(admitted_action=tok,
                               action_request_wire=raw_larga))
print("start larga:", type(larga).__name__)
hl = svc.handle_for(larga.handle_ref)
time.sleep(0.15)
# Doble await sobre una acción rápida mientras la larga vive
req_r = distinct_start_request(2000)
rapida = svc.start(req_r)
hr = svc.handle_for(rapida.handle_ref)
time.sleep(0.15)
res = []
b = threading.Barrier(2)
def w():
    b.wait(); res.append(svc.await_result(hr, timeout=10))
ts = [threading.Thread(target=w) for _ in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
print("doble entrega en demo:", sum(1 for x in res if x is not None) == 2)
print("slots_in_use con acción LARGA viva (esperado 1):", svc.slots_in_use)
if svc.slots_in_use < 1:
    # capacidad corrupta: se puede admitir de más
    extra_ok = 0
    for n in (3001, 3002):
        o = svc.start(distinct_start_request(n))
        if type(o).__name__ == "Started":
            extra_ok += 1
            svc.await_result(svc.handle_for(o.handle_ref), timeout=10)
    print("starts extra admitidos con la acción larga viva:", extra_ok,
          "(capacidad=2; larga+2 extras = 3 vivos simultáneos si no se esperan)")
store.close()
print("FIN SONDA 2")
