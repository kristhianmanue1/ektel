"""G-M2-05 — concurrencia y reinicio sobre el store real.

Falsifica: que dos procesos compitiendo con el **mismo token** produzcan más
de un CAS ganador, que un reinicio pierda el estado `spent`, o que ocurra un
doble spawn.

Usa el `FileReplayStore` real (dos CAS con fsync), no un doble en memoria.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.replay_store_file import FileReplayStore  # noqa: E402
from src.application.config import M2Config  # noqa: E402
from src.domain.start_outcomes import (  # noqa: E402
    REASON_CAPABILITY_REJECTED, StartFailed, Started)
from tests.unit.helpers_m2 import (  # noqa: E402
    FakeProcessHost, distinct_start_request, make_start_service)


class CarreraPorElMismoTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = FileReplayStore(Path(self._tmp.name))

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def test_un_solo_ganador_y_un_solo_spawn(self) -> None:
        hilos_n = 12
        host = FakeProcessHost()
        svc = make_start_service(
            store=self.store, host=host,
            config=M2Config.build(max_concurrent_actions=hilos_n))
        request = distinct_start_request(1)
        # Emisión real previa a la carrera; ningún hilo registra provenance.
        svc._admission.admit(request.action_request_wire)
        resultados: list[object] = []
        lock = threading.Lock()
        barrera = threading.Barrier(hilos_n, timeout=30)

        def correr() -> None:
            try:
                barrera.wait()
                out: object = svc.start(request)
            except BaseException as exc:
                out = exc
            with lock:
                resultados.append(out)

        hilos = [threading.Thread(target=correr) for _ in range(hilos_n)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)

        self.assertFalse([r for r in resultados if isinstance(r, BaseException)])
        ganadores = [r for r in resultados if isinstance(r, Started)]
        self.assertEqual(len(ganadores), 1, "el CAS debe tener un solo ganador")
        self.assertEqual(len(host.spawns), 1, "nunca doble spawn")
        perdedores = [r for r in resultados if isinstance(r, StartFailed)]
        self.assertEqual(len(perdedores), hilos_n - 1)
        for p in perdedores:
            self.assertEqual(p.reason_code, REASON_CAPABILITY_REJECTED)
            self.assertIn(p.safe_detail, ("cas:already_spent", "config:issuance_missing"))

    def test_reinicio_del_store_conserva_spent(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(store=self.store, host=host)
        request = distinct_start_request(2)
        svc._admission.admit(request.action_request_wire)
        self.assertIsInstance(svc.start(request), Started)
        # Reiniciar el store: releer desde disco.
        self.store.close()
        reabierto = FileReplayStore(Path(self._tmp.name))
        try:
            svc2 = make_start_service(store=reabierto, host=host)
            segundo = svc2.start(request)
            assert isinstance(segundo, StartFailed)
            self.assertEqual(segundo.safe_detail, "config:issuance_missing")
            self.assertEqual(reabierto.start_token_status(
                host.spawns[0][0].identity_digest), "spent",
                "R16 no sustituye la prueba de replay durable")
            self.assertEqual(len(host.spawns), 1)
        finally:
            reabierto.close()

    def test_reinicio_del_coordinador_no_reabre_el_token(self) -> None:
        """Reiniciar el coordinador invalida handles, no derechos de inicio."""
        host = FakeProcessHost()
        request = distinct_start_request(3)
        svc_a = make_start_service(store=self.store, host=host)
        svc_a._admission.admit(request.action_request_wire)
        self.assertIsInstance(svc_a.start(request), Started)
        svc_b = make_start_service(store=self.store, host=host)
        segundo = svc_b.start(request)
        assert isinstance(segundo, StartFailed)
        self.assertEqual(segundo.safe_detail, "config:issuance_missing")
        self.assertEqual(self.store.start_token_status(
            host.spawns[0][0].identity_digest), "spent")
        self.assertEqual(len(host.spawns), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
