"""Concurrencia CAS (§7.4/§6.6): dos `admit` concurrentes con el mismo
nonce → exactamente una `Admitted`; el perdedor `capability_rejected`.
Incluye el caso DOS INSTANCIAS del store sobre el mismo directorio
(exclusión por flock). Barreras deterministas con `threading` (stdlib)."""
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from helpers_m1 import make_service, valid_request_bytes  # noqa: E402
from src.adapters.replay_store_file import FileReplayStore  # noqa: E402
from src.domain.outcomes import Admitted, AdmissionRejected  # noqa: E402
from src.ports.replay_store import ConsumeOutcome  # noqa: E402


def _parallel_admit(dir_path: Path, n: int, payload: bytes):
    """n servicios, cada uno con SU PROPIA instancia del store sobre el
    MISMO directorio; liberación simultánea por barrera."""
    stores = [FileReplayStore(dir_path) for _ in range(n)]
    services = [make_service(store=s) for s in stores]
    barrier = threading.Barrier(n)

    def submit(i: int):
        barrier.wait()
        return services[i].admit(payload)

    try:
        with ThreadPoolExecutor(max_workers=n) as pool:
            return list(pool.map(submit, range(n)))
    finally:
        for store in stores:
            store.close()


class CasConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_cuatro_admits_mismo_nonce_una_gana(self):
        results = _parallel_admit(self.dir, 4, valid_request_bytes())
        admitted = [r for r in results if isinstance(r, Admitted)]
        losers = [r for r in results if isinstance(r, AdmissionRejected)]
        self.assertEqual(len(admitted), 1)
        self.assertEqual(len(losers), 3)
        for loser in losers:
            self.assertEqual(loser.reason_code, "capability_rejected")
            self.assertEqual(loser.safe_detail, "nonce_replay")

    def test_dos_instancias_del_store_mismo_directorio_sin_doble_reserva(self):
        # Instancias DISTINTAS (fd propio) sobre el mismo estado durable:
        # la exclusión es el flock del lock-file, no memoria compartida.
        results = _parallel_admit(self.dir, 2, valid_request_bytes())
        admitted = [r for r in results if isinstance(r, Admitted)]
        self.assertEqual(len(admitted), 1)
        # Y el estado durable registra exactamente una reserva.
        import json
        state = json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(len(state["nonces"]), 1)

    def test_consumo_token_simultaneo_uno_solo(self):
        store = FileReplayStore(self.dir)
        self.addCleanup(store.close)
        barrier = threading.Barrier(2)

        def consume(_i: int):
            barrier.wait()
            return store.consume_start_token("d" * 64)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(consume, range(2)))
        self.assertEqual(results.count(ConsumeOutcome.CONSUMED), 1)
        self.assertEqual(results.count(ConsumeOutcome.ALREADY_SPENT), 1)


if __name__ == "__main__":
    unittest.main()
