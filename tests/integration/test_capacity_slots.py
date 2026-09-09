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



class RegresionSlotsTests(unittest.TestCase):
    """H5 y H6 de la ronda adversarial."""

    def test_h5_el_slot_retenido_por_indeterminacion_es_observable(self) -> None:
        svc = make_start_service(host=FakeProcessHost(raise_unknown=True),
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "spawn:indeterminate")
        self.assertEqual(svc.slots_in_use, 1)
        # Antes la capacidad perdida era invisible y sin ruta de recuperacion.
        retenidos = svc.retained_by_indeterminacy
        self.assertEqual(len(retenidos), 1)

    def test_h5_liberar_es_acto_explicito_y_recupera_capacidad(self) -> None:
        svc = make_start_service(host=FakeProcessHost(raise_unknown=True),
                                 config=M2Config.build(max_concurrent_actions=1))
        svc.start(_request(1))
        identidad = svc.retained_by_indeterminacy[0]
        self.assertFalse(svc.release_indeterminate("no-existe"))
        self.assertTrue(svc.release_indeterminate(identidad))
        self.assertEqual(svc.slots_in_use, 0)
        self.assertEqual(svc.retained_by_indeterminacy, ())
        # Liberar dos veces no regala capacidad.
        self.assertFalse(svc.release_indeterminate(identidad))
        self.assertEqual(svc.slots_in_use, 0)


class CotasDeCapacidadTests(unittest.TestCase):
    """G-M2-12: el modelo de payload por capacidad, medido a escala ejecutable.

    La corrida a limites maximos —64 acciones de 64 MiB por stream, 16 GiB de
    pico SOLO de payload— **no se ejecuta**. Dos razones, ambas declaradas:

    1. el paquete M2 §2.2 excluye expresamente los tests de presion extrema;
    2. este host tiene 16 GiB de RAM fisica, de modo que la corrida no seria
       una medicion sino un OOM.

    Lo que si se hace: confirmar la formula aritmeticamente y comprobar
    empiricamente, a escala reducida, que el payload retenido real se ajusta al
    modelo lineal. La extrapolacion a escala maxima es **aritmetica, no
    medida**, y asi consta en la evidencia.
    """

    def test_el_payload_retenido_se_ajusta_al_modelo_lineal(self) -> None:
        import sys as _sys
        from src.adapters.posix_supervisor import (
            FRAME_MAX_BYTES, PosixSupervisorHost)
        from src.domain.deadline import payload_bounds
        from src.domain.start_request import ExecutionPlan

        acciones = 6
        limite = 256 * 1024        # por stream y accion
        script = ("import sys\n"
                  "for _ in range(12): sys.stdout.write('o'*65536)\n"
                  "for _ in range(12): sys.stderr.write('e'*65536)\n")
        host = PosixSupervisorHost()
        refs = []
        for _ in range(acciones):
            p = ExecutionPlan(
                identity_digest="d" * 64, action_id="a", issuer_id="i",
                exp_wall=0, command_absolute=_sys.executable,
                args=("-c", script), cwd="/tmp",
                env=ExecutionPlan.freeze_env({"PATH": "/usr/bin:/bin"}),
                stdin_bytes=b"", deadline_ms=60000,
                max_stdout_bytes=limite, max_stderr_bytes=limite)
            refs.append(host.spawn(p, deadline_eff_ms=60000))

        total = 0
        for ref in refs:
            a = host.await_terminal(ref, timeout=90)
            self.assertIsNotNone(a)
            assert a is not None
            total += len(bytes(a.stdout)) + len(bytes(a.stderr))
            # Cada accion retiene exactamente su limite por stream.
            self.assertEqual(len(bytes(a.stdout)), limite)
            self.assertEqual(len(bytes(a.stderr)), limite)

        cota = payload_bounds(limite, limite, FRAME_MAX_BYTES,
                              concurrent_actions=acciones).stable_bytes
        self.assertLessEqual(total, cota,
                             "el payload retenido excede la cota estable")
        # El modelo es lineal en el numero de acciones: se comprueba, no se
        # asume, que la cota agregada es multiplo exacto de la individual.
        individual = payload_bounds(limite, limite, FRAME_MAX_BYTES).stable_bytes
        self.assertEqual(cota, individual * acciones)

    def test_la_escala_maxima_esta_declarada_como_no_ejecutada(self) -> None:
        """Deja constancia en codigo de la cifra que NO se midio."""
        from src.domain.deadline import payload_bounds
        mib = 1024 * 1024
        gib = 1024 * mib
        b = payload_bounds(64 * mib, 64 * mib, 65536, concurrent_actions=64)
        self.assertEqual(b.stable_bytes, 8 * gib + 8 * mib)
        self.assertEqual(b.materialization_peak_bytes, 16 * gib + 8 * mib)
        # La cifra excede la RAM fisica del host de referencia: ejecutarla
        # seria un OOM, no una medicion.
        self.assertGreater(b.materialization_peak_bytes, 16 * gib)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
