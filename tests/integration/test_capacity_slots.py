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
    FakeProcessHost, distinct_start_request, fake_handoff, make_start_service)


def _request(n: int) -> object:
    return distinct_start_request(n)


def _eventually(cond, timeout: float = 5.0, interval: float = 0.02) -> bool:
    """Espera acotada a que el vigilante del coordinador observe el hecho."""
    import time
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(interval)
    return cond()


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
        host = FakeProcessHost()
        svc = make_start_service(host=host,
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        self.assertEqual(svc.slots_in_use, 1)
        # FIX-M2-R3: el terminal llega por el puerto y el slot se libera con
        # el handoff real (vigilante del coordinador), no por acto del
        # llamador ni por fabricación manual del resultado.
        host.deliver_terminal(out.handle_ref, fake_handoff({"k": 1}))
        resultado = svc.await_result(handle)
        self.assertIsNotNone(resultado)
        self.assertEqual(svc.slots_in_use, 0)

    def test_handle_abandonado_no_deja_registro_ni_slot(self) -> None:
        """FIX-M2-R3: acción terminada sin `await_result` — el slot se libera
        con el handoff terminal y el coordinador no retiene el handle."""
        host = FakeProcessHost()
        svc = make_start_service(host=host,
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        host.deliver_terminal(out.handle_ref, fake_handoff({"outcome": "executed"}))
        self.assertTrue(
            _eventually(lambda: svc.slots_in_use == 0),
            "el handoff terminal libera el slot sin await_result")
        self.assertTrue(
            _eventually(lambda: svc.handle_for(out.handle_ref) is None),
            "tras el handoff no queda registro del handle")
        # La propiedad del resultado depositado es del llamador: su handle
        # sigue pudiendo transferirla aunque el registro ya no exista.
        resultado = svc.await_result(handle)
        self.assertIsNotNone(resultado)
        self.assertEqual(svc.slots_in_use, 0)
        # Y un segundo consumidor recibe ausencia honesta, no otra entrega.
        self.assertIsNone(svc.await_result(handle))

    def test_handle_retenido_conserva_su_memoria(self) -> None:
        """Retener un handle terminal retiene su resultado: memoria del
        llamador, no del runtime. El depósito es privilegio del coordinador
        que acuñó el handle (FIX-M2-R4)."""
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        self.assertTrue(handle.deposit_terminal_result({"payload": "x"}, svc),
                        "el coordinador acuñador puede depositar")
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



class LinealizacionHandoffTests(unittest.TestCase):
    """FIX-M2-R2/R4 — entrega única del terminal y frontera de confianza.

    Falsifica: doble entrega ante `await_result` concurrentes, doble
    liberación de slot con sobre-admisión, recolección por handle forjado,
    cross-instance o de otra acción, y desalojo del handle legítimo por un
    impostor con la misma referencia.
    """

    def _dos_hilos_await(self, svc: object, handle: object,
                         ) -> tuple[object, object]:
        import threading
        resultados: list[object] = []
        barrera = threading.Barrier(2, timeout=30)

        def correr() -> None:
            barrera.wait()
            out: object = svc.await_result(handle)  # type: ignore[attr-defined]
            resultados.append(out)

        hilos = [threading.Thread(target=correr) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)
        self.assertEqual(len(resultados), 2)
        return resultados[0], resultados[1]

    def test_doble_await_concurrente_entrega_una_vez(self) -> None:
        """FIX-M2-R2: dos `await_result` concurrentes sobre el mismo handle —
        exactamente una entrega; el segundo consumidor recibe ausencia
        honesta; el slot se libera una sola vez."""
        host = FakeProcessHost()
        svc = make_start_service(host=host,
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        host.deliver_terminal(out.handle_ref, fake_handoff({"outcome": "executed"}))
        primero, segundo = self._dos_hilos_await(svc, handle)
        entregas = [r for r in (primero, segundo) if r is not None]
        self.assertEqual(len(entregas), 1,
                         "el terminal se entrega exactamente una vez")
        self.assertEqual(svc.slots_in_use, 0,
                         "una sola liberación de slot por una sola acción")

    def test_doble_liberacion_no_admite_una_tercera_accion(self) -> None:
        """FIX-M2-R2: capacidad 2 con otra acción viva — la doble espera del
        terminal de A nunca libera el slot de B; nunca se admite una tercera
        acción por encima de la cota por doble release."""
        host = FakeProcessHost()
        svc = make_start_service(host=host,
                                 config=M2Config.build(max_concurrent_actions=2))
        out_a = svc.start(_request(1))
        out_b = svc.start(_request(2))
        assert isinstance(out_a, Started) and isinstance(out_b, Started)
        handle_a = svc.handle_for(out_a.handle_ref)
        assert handle_a is not None
        self.assertEqual(svc.slots_in_use, 2)
        host.deliver_terminal(out_a.handle_ref, fake_handoff({"outcome": "executed"}))
        # A termina mientras B sigue viva (ninguna entrega para B).
        self._dos_hilos_await(svc, handle_a)
        self.assertTrue(
            _eventually(lambda: svc.slots_in_use == 1),
            "sólo el slot de B queda retenido")
        # La capacidad liberada por A admite exactamente una acción más.
        out_c = svc.start(_request(3))
        self.assertIsInstance(out_c, Started)
        out_d = svc.start(_request(4))
        assert isinstance(out_d, StartFailed)
        self.assertEqual(out_d.safe_detail, "capacity:no_slot",
                         "B sigue viva: no hay cuarto slot")
        self.assertEqual(svc.slots_in_use, 2)

    def test_handle_forjado_no_recolecta_ni_desaloja(self) -> None:
        """FIX-M2-R4: un `ExecutionHandle` forjado con la misma `handle_ref`
        no puede recolectar el terminal ni desalojar al handle legítimo; el
        legítimo conserva íntegro su derecho."""
        from src.domain.execution_handle import ExecutionHandle
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        # El token del impostor no puede autenticarse: material distinto.
        from src.domain.termination import mint_termination_token
        from tests.unit.helpers_m2 import TEST_KEY
        impostor = ExecutionHandle(
            handle_ref=handle.handle_ref,
            coordinator_instance=svc.coordinator_instance,
            identity_digest=handle.identity_digest,
            action_id="action-9999",
            termination_token=mint_termination_token(
                TEST_KEY, svc.coordinator_instance, handle.identity_digest,
                handle.action_id),
        )
        self.assertIsNone(svc.await_result(impostor),
                          "el impostor no recolecta el terminal ajeno")
        host.deliver_terminal(out.handle_ref, fake_handoff({"outcome": "executed"}))
        resultado = svc.await_result(handle)
        self.assertIsNotNone(resultado,
                             "el handle legítimo conserva su derecho íntegro")

    def test_await_result_rechaza_handles_forjados(self) -> None:
        """FIX-M2-R4: matriz negativa de `await_result` — forjado simple,
        cross-instance y de otra acción."""
        from src.domain.execution_handle import ExecutionHandle
        svc = make_start_service()
        out = svc.start(_request(1))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        forjado = ExecutionHandle(
            handle_ref=handle.handle_ref, coordinator_instance="otra",
            identity_digest="d", action_id="a", termination_token="0" * 64)
        self.assertIsNone(svc.await_result(forjado))
        svc_b = make_start_service()  # nueva instancia = reinicio
        self.assertIsNone(svc.await_result(forjado))
        self.assertIsNone(svc_b.await_result(handle),
                          "cross-instance no recolecta")
        # El resultado depositado por el coordinador no puede fabricarse
        # desde fuera del objeto acuñador.
        self.assertFalse(handle.deposit_terminal_result({"x": 1}, None))
        self.assertFalse(handle.deposit_terminal_result({"x": 1}, svc_b))


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
