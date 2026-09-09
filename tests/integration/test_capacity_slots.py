"""G-M2-12 — capacidad `max_concurrent_actions` (D-M2-2(a)).

Falsifica: exceder la cota, gastar tokens por falta de slot, dejar registro
global tras abandonar un handle, o no liberar el slot en el handoff terminal.
"""
from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.application.config import M2Config  # noqa: E402
from src.domain.start_outcomes import (  # noqa: E402
    REASON_START_FAILED, StartFailed, Started)
from tests.unit.helpers_m1 import MemoryReplayStore  # noqa: E402
from tests.unit.helpers_m2 import (  # noqa: E402
    FakeProcessHost, distinct_start_request, make_start_service)


def _request(n: int) -> object:
    return distinct_start_request(n)


class CapacidadTests(unittest.TestCase):
    def test_la_cota_no_se_excede(self) -> None:
        svc = make_start_service(config=M2Config.build(max_concurrent_actions=2))
        self.assertIsInstance(svc.start(_request(1)), Started)
        self.assertIsInstance(svc.start(_request(2)), Started)
        tercero = svc.start(_request(3))
        assert isinstance(tercero, StartFailed)
        self.assertEqual(tercero.reason_code, REASON_START_FAILED)
        self.assertEqual(tercero.safe_detail, "capacity:no_slot")
        self.assertEqual(svc.slots_in_use, 2)

    def test_falta_de_slot_no_gasta_token(self) -> None:
        store = MemoryReplayStore()
        svc = make_start_service(store=store,
                                 config=M2Config.build(max_concurrent_actions=1))
        svc.start(_request(1))
        req2 = _request(2)
        rechazado = svc.start(req2)
        assert isinstance(rechazado, StartFailed)
        self.assertEqual(rechazado.safe_detail, "capacity:no_slot")
        # El mismo token sigue sin gastar: el llamador puede reintentar.
        segundo = svc.start(req2)
        assert isinstance(segundo, StartFailed)
        self.assertEqual(segundo.safe_detail, "capacity:no_slot",
                         "seguir sin capacidad, no 'ya gastado'")

    def test_el_vocabulario_no_distingue_backpressure(self) -> None:
        """`start_failed` no lleva `retryable`: M2 no afirma esa distincion
        como machine-readable (D-M2-2(a))."""
        svc = make_start_service(config=M2Config.build(max_concurrent_actions=1))
        svc.start(_request(1))
        out = svc.start(_request(2))
        assert isinstance(out, StartFailed)
        self.assertFalse(hasattr(out, "retryable"))

    def test_fallo_pre_spawn_libera_el_slot(self) -> None:
        svc = make_start_service(host=FakeProcessHost(reject=True),
                                 config=M2Config.build(max_concurrent_actions=1))
        svc.start(_request(1))
        self.assertEqual(svc.slots_in_use, 0)
        # Con el slot libre, la siguiente accion llega hasta el spawn: falla
        # por el host, NO por capacidad. Esa distincion es la prueba de que el
        # slot se libero.
        segundo = svc.start(_request(2))
        assert isinstance(segundo, StartFailed)
        self.assertEqual(segundo.safe_detail, "spawn:host_rejected")

    def test_handoff_terminal_libera_el_slot(self) -> None:
        svc = make_start_service(config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        handle.store_terminal_result({"outcome": "executed"})
        self.assertEqual(svc.slots_in_use, 1)
        resultado = svc.await_result(handle)
        self.assertEqual(resultado, {"outcome": "executed"})
        self.assertEqual(svc.slots_in_use, 0)

    def test_handle_abandonado_no_deja_registro_global(self) -> None:
        svc = make_start_service(config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        handle.store_terminal_result({"outcome": "executed"})
        svc.await_result(handle)
        self.assertIsNone(svc.handle_for(out.handle_ref),
                          "tras el handoff no queda registro del handle")

    def test_handle_retenido_conserva_su_memoria(self) -> None:
        """Retener un handle terminal retiene su resultado: memoria del
        llamador, no del runtime."""
        svc = make_start_service()
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        handle.store_terminal_result({"payload": "x"})
        self.assertTrue(handle.has_terminal_result)


class CarreraDeSlotsTests(unittest.TestCase):
    """La cota debe cumplirse tambien bajo concurrencia real de hilos."""

    def test_carrera_no_excede_la_cota(self) -> None:
        capacidad = 4
        intentos = 16
        svc = make_start_service(
            config=M2Config.build(max_concurrent_actions=capacidad))
        # Construir TODO antes de lanzar hilos: si un hilo fallara antes de la
        # barrera, los demas quedarian bloqueados para siempre y el fallo se
        # presentaria como cuelgue en vez de como error.
        peticiones = [_request(i) for i in range(1, intentos + 1)]
        resultados: list[object] = []
        lock = threading.Lock()
        barrera = threading.Barrier(intentos, timeout=30)

        def correr(req: object) -> None:
            try:
                barrera.wait()
                out = svc.start(req)
            except BaseException as exc:  # nunca colgar la suite
                out = exc
            with lock:
                resultados.append(out)

        hilos = [threading.Thread(target=correr, args=(r,)) for r in peticiones]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)

        self.assertFalse([r for r in resultados if isinstance(r, BaseException)],
                         "ningun hilo debe terminar en excepcion")
        iniciados = [r for r in resultados if isinstance(r, Started)]
        self.assertEqual(len(resultados), intentos)
        self.assertLessEqual(len(iniciados), capacidad,
                             "la cota de capacidad se excedio bajo carrera")
        self.assertLessEqual(svc.slots_in_use, capacidad)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
