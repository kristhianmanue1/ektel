"""G-M2-03, G-M2-04 y G-M2-06 — linealización, reconciliación y crash.

Falsifica: que algo distinto de `CONSUMED` cruce la frontera de proceso, que
la reconciliación de ADR-011 §2.6 se aparte de su matriz, y que un token
gastado se reabra o se fabrique un handle.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain.start_outcomes import (  # noqa: E402
    REASON_CAPABILITY_REJECTED,
    REASON_START_FAILED,
    REASON_START_FAILED_INDETERMINATE,
    StartFailed,
    Started,
)
from src.adapters.posix_supervisor import PosixSupervisorHost  # noqa: E402
from src.adapters.replay_store_file import FileReplayStore  # noqa: E402
from src.application.config import M2Config  # noqa: E402
from src.application.start_service import StartService  # noqa: E402
from src.domain.execution_result import (  # noqa: E402
    AwaitedExecution,
    CAUSE_DEADLINE_DURATION,
    CAUSE_NATURAL_EXIT,
    MEASUREMENT_KEYS,
    OUTCOME_DEADLINE_EXCEEDED,
    OUTCOME_EXECUTED,
)
from src.domain.start_request import StartRequest  # noqa: E402
from src.domain.termination import TerminationAccepted  # noqa: E402
from src.ports.replay_store import ConsumeOutcome  # noqa: E402
from tests.unit.helpers_m1 import (  # noqa: E402
    MemoryReplayStore, NOW, TEST_KEY, TEST_KEY_ID, base_binding,
    emit_request, make_capability_envelope, make_request)
from tests.unit.helpers_m2 import (  # noqa: E402
    FakeProcessHost,
    HostileStore,
    admitted_token,
    make_start_service,
    valid_start_request,
)


class OrdenTests(unittest.TestCase):
    """G-M2-03: reloj final → CAS → spawn; sólo CONSUMED cruza."""

    def test_solo_consumed_cruza_a_spawn(self) -> None:
        store = MemoryReplayStore()
        host = FakeProcessHost()
        svc = make_start_service(store=store, host=host)
        out = svc.start(valid_start_request())
        self.assertIsInstance(out, Started)
        self.assertEqual(len(host.spawns), 1)

    def test_already_spent_no_hace_spawn(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(
            store=HostileStore(consume=ConsumeOutcome.ALREADY_SPENT), host=host)
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_CAPABILITY_REJECTED)
        self.assertEqual(host.spawns, [], "ALREADY_SPENT no puede llegar a spawn")

    def test_deadline_efectivo_cero_rechaza_antes_del_cas(self) -> None:
        """Vida util nula: sin CAS y sin spawn. No se gasta el token."""
        store = MemoryReplayStore()
        host = FakeProcessHost()
        from tests.unit.helpers_m1 import EXP
        svc = make_start_service(store=store, host=host, now=float(EXP) - 0.0005)
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "deadline:effective_zero")
        self.assertEqual(host.spawns, [])
        self.assertEqual(store.start_token_status(
            "ff6fb6006a0c2692e0f4bdd8e4bc912e82833b0aec3e00be175f4c0c7595db10"),
            "unspent", "el token no puede gastarse sin vida util")

    def test_el_plazo_efectivo_se_trunca_por_vigencia(self) -> None:
        host = FakeProcessHost()
        from tests.unit.helpers_m1 import EXP
        svc = make_start_service(host=host, now=float(EXP) - 1.0)
        svc.start(valid_start_request())
        _plan, effective, validity_bound = host.spawns[0]
        self.assertEqual(effective, 1000, "min(deadline_ms, vigencia restante)")
        self.assertTrue(validity_bound,
                        "la vigencia acotó el plazo: el dato debe viajar")


class ReconciliacionTests(unittest.TestCase):
    """G-M2-04: la matriz exacta de ADR-011 §2.6."""

    def _run(self, **store_kw: object) -> tuple[object, HostileStore, FakeProcessHost]:
        store = HostileStore(**store_kw)  # type: ignore[arg-type]
        host = FakeProcessHost()
        svc = make_start_service(store=store, host=host)
        return svc.start(valid_start_request()), store, host

    def test_unavailable_mas_unspent_es_start_failed(self) -> None:
        out, store, host = self._run(
            consume=ConsumeOutcome.UNAVAILABLE, status="unspent")
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED)
        self.assertEqual(store.status_calls, 1)
        self.assertEqual(host.spawns, [], "unspent nunca autoriza spawn directo")

    def test_unavailable_mas_spent_es_indeterminado(self) -> None:
        out, _, host = self._run(
            consume=ConsumeOutcome.UNAVAILABLE, status="spent")
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)
        self.assertEqual(host.spawns, [])

    def test_unavailable_mas_unknown_es_indeterminado(self) -> None:
        out, _, _ = self._run(
            consume=ConsumeOutcome.UNAVAILABLE, status="unknown")
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)

    def test_excepcion_en_cas_reconcilia(self) -> None:
        out, store, _ = self._run(raise_consume=True, status="unspent")
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED)
        self.assertEqual(store.status_calls, 1)

    def test_status_no_disponible_prevalece_indeterminado(self) -> None:
        out, _, _ = self._run(raise_consume=True, raise_status=True)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)

    def test_valores_truthy_no_adquieren_autoridad(self) -> None:
        """Ni objetos truthy ni subtipos no reconocidos cruzan como CONSUMED."""
        for bogus in (True, 1, "CONSUMED", object(), [ConsumeOutcome.CONSUMED]):
            with self.subTest(valor=type(bogus).__name__):
                out, _, host = self._run(consume=bogus, status="unknown")
                assert isinstance(out, StartFailed)
                self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)
                self.assertEqual(host.spawns, [])

    def test_status_desconocido_no_se_interpreta_como_unspent(self) -> None:
        for status in ("SPENT", "", None, True, 0):
            with self.subTest(status=status):
                out, _, _ = self._run(
                    consume=ConsumeOutcome.UNAVAILABLE, status=status)
                assert isinstance(out, StartFailed)
                self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)


class CrashYSpawnTests(unittest.TestCase):
    """G-M2-06: alrededor del spawn no se inventa handle ni se reabre token."""

    def test_fallo_sincrono_del_host_es_determinado(self) -> None:
        store = MemoryReplayStore()
        svc = make_start_service(store=store, host=FakeProcessHost(reject=True))
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED)
        self.assertIn("host_rejected", out.safe_detail)

    def test_excepcion_opaca_del_host_es_indeterminada(self) -> None:
        """No se puede afirmar que no exista un proceso."""
        svc = make_start_service(host=FakeProcessHost(raise_unknown=True))
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)

    def test_excepcion_opaca_no_libera_el_slot(self) -> None:
        """Podria haber un proceso vivo: liberar el slot mentiria sobre la cota."""
        svc = make_start_service(host=FakeProcessHost(raise_unknown=True))
        svc.start(valid_start_request())
        self.assertEqual(svc.slots_in_use, 1)

    def test_token_gastado_no_se_reabre_tras_fallo_de_spawn(self) -> None:
        store = MemoryReplayStore()
        svc = make_start_service(store=store, host=FakeProcessHost(reject=True))
        req = valid_start_request()
        svc.start(req)
        segundo = svc.start(req)
        assert isinstance(segundo, StartFailed)
        self.assertEqual(segundo.reason_code, REASON_CAPABILITY_REJECTED)
        self.assertEqual(segundo.safe_detail, "cas:already_spent")

    def test_handle_ref_invalido_no_fabrica_handle_y_retienel_slot(self) -> None:
        """FIX-M2-R5: un ref inválido post-spawn es indeterminado CON
        retención de capacidad — no se libera el slot como si se supiera que
        no existe proceso (OAI-M2-02 v1 / F5)."""
        svc = make_start_service(host=FakeProcessHost(bad_ref=True),
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)
        self.assertEqual(svc.slots_in_use, 1,
                         "podría existir proceso: el slot se retiene")
        self.assertEqual(len(svc.retained_by_indeterminacy), 1,
                         "la identidad queda registrada y recuperable")

    def test_handle_ref_no_hex_es_indeterminado_sin_excepcion(self) -> None:
        """FIX-M2-R5 (OAI-M2-02 v2): un ref de 16 caracteres no hex pasa el
        chequeo de longitud pero no puede fabricar `Started`; la rama es
        indeterminada con retención y nunca propaga excepción liberando
        capacidad con spawn ocurrido."""
        svc = make_start_service(host=FakeProcessHost(bad_ref_hex=True),
                                 config=M2Config.build(max_concurrent_actions=1))
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)
        self.assertEqual(out.safe_detail, "spawn:handle_ref_invalid")
        self.assertEqual(svc.slots_in_use, 1)
        self.assertEqual(len(svc.retained_by_indeterminacy), 1)



class RegresionRelojYEstadoTests(unittest.TestCase):
    """H8 y H10 de la ronda adversarial."""

    def test_h8_reloj_infinito_no_pasa_como_valido(self) -> None:
        for now in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(now=now):
                svc = make_start_service(now=now)
                out = svc.start(valid_start_request())
                assert isinstance(out, StartFailed)
                self.assertEqual(out.reason_code, REASON_START_FAILED)
                self.assertEqual(out.safe_detail, "clock:unavailable")

    def test_h10_status_de_otro_tipo_no_adquiere_autoridad(self) -> None:
        """Antes se comparaba con `==`; un objeto con `__eq__` a medida podia
        hacerse pasar por 'unspent' y degradar un indeterminado."""
        class Mentiroso:
            def __eq__(self, other: object) -> bool:
                return True

        host = FakeProcessHost()
        svc = make_start_service(
            store=HostileStore(consume=ConsumeOutcome.UNAVAILABLE,
                               status=Mentiroso()),
            host=host)
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)
        self.assertEqual(out.safe_detail, "cas:unavailable:status_type")
        self.assertEqual(host.spawns, [])




def _pair(script: str, n: int = 1, *, deadline_ms: int = 30000,
          max_out: int = 65536) -> StartRequest:
    """Peticion coherente que ejecuta `script` con el interprete actual."""
    action_id = f"action-{n:04d}"
    nonce = f"{n:032x}"
    limits = {"max_stdout_bytes": max_out, "max_stderr_bytes": 4096}
    binding = base_binding(action_id=action_id, command_absolute=sys.executable,
                           args=["-c", script], deadline_ms=deadline_ms,
                           output_limits=limits)
    env = make_capability_envelope(binding=binding, nonce=nonce)
    doc = make_request(env=env, nonce=nonce, action_id=action_id,
                       command_absolute=sys.executable, args=["-c", script],
                       deadline_ms=deadline_ms, output_limits=limits)
    raw = emit_request(doc)
    return StartRequest(admitted_action=admitted_token(raw),
                        action_request_wire=raw)


def _real_service(**kw: object) -> StartService:
    """Coordinador real contra supervisor real: sin dobles."""
    now = kw.pop("now", None)
    cfg = M2Config.build(max_concurrent_actions=4, **kw)
    host = PosixSupervisorHost.from_config(cfg)
    reloj = (lambda: float(NOW)) if now is None else (lambda: float(now))  # type: ignore[arg-type]
    return StartService(
        replay_store=MemoryReplayStore(), process_host=host,
        operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
        config=cfg, declared_config_fingerprint=cfg.fingerprint,
        wall_clock=reloj)


class CicloCompletoTests(unittest.TestCase):
    """INC-M2-4: `start` -> supervision -> `await_result` con procesos reales.

    Falsifica que `await_result` fabrique resultados, pierda la salida acotada
    o clasifique por exit status en vez de por causa.
    """

    def test_salida_natural_entrega_awaited_execution(self) -> None:
        svc = _real_service()
        out = svc.start(_pair("import sys;sys.stdout.write('hola');"
                              "sys.stderr.write('err')"))
        self.assertIsInstance(out, Started)
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        self.assertIsInstance(awaited, AwaitedExecution)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.stdout, b"hola")
        self.assertEqual(awaited.stderr, b"err")
        self.assertEqual(awaited.result.outcome, OUTCOME_EXECUTED)
        self.assertEqual(awaited.result.cause, CAUSE_NATURAL_EXIT)
        self.assertEqual(awaited.result.exit_status, 0)

    def test_executed_con_exit_status_no_cero(self) -> None:
        """`executed` es salida natural, NO exito (invariante 9)."""
        svc = _real_service()
        out = svc.start(_pair("raise SystemExit(3)", n=2))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.result.outcome, OUTCOME_EXECUTED)
        self.assertEqual(awaited.result.exit_status, 3)

    def test_deadline_excedido_se_clasifica_por_causa(self) -> None:
        svc = _real_service(termination_grace_ms=500)
        out = svc.start(_pair("import time;time.sleep(60)", n=3,
                              deadline_ms=1500))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.result.outcome, OUTCOME_DEADLINE_EXCEEDED)
        self.assertEqual(awaited.result.cause, CAUSE_DEADLINE_DURATION)

    def test_vigencia_acotada_produce_causa_de_vigencia_end_to_end(self) -> None:
        """FIX-M2-R1: con `remaining_validity <= deadline_ms` el resultado
        real — StartService → ProcessHost → supervisor → TerminalHandoff →
        ExecutionResult — reporta `deadline_validity_exhausted`. No basta
        `classify()` puro: el dato debe cruzar todo el cableado."""
        from src.domain.execution_result import (
            CAUSE_DEADLINE_VALIDITY_EXHAUSTED)
        from tests.unit.helpers_m1 import EXP
        svc = _real_service(termination_grace_ms=200,
                            now=float(EXP) - 0.5)
        out = svc.start(_pair("import time;time.sleep(60)", n=8,
                              deadline_ms=30000))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.result.outcome, OUTCOME_DEADLINE_EXCEEDED)
        self.assertEqual(awaited.result.cause, CAUSE_DEADLINE_VALIDITY_EXHAUSTED,
                         "la vigencia restante (≈500 ms) acotó el plazo")
        self.assertEqual(
            awaited.result.measurements["deadline_effective_ms"], 500)

    def test_terminate_antes_del_deadline_gana_el_primer_hecho(self) -> None:
        """FIX-M2-R8: terminación externa observada antes de la escalación →
        `terminated`, aunque el proceso ignore TERM y el deadline acabe
        matándolo. El estado final con dos booleanos no puede decidir esto."""
        import time as _time
        from src.domain.execution_result import (
            CAUSE_EXTERNAL_TERMINATION, OUTCOME_TERMINATED)
        svc = _real_service(termination_grace_ms=500)
        out = svc.start(_pair(
            "import signal,time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(60)\n", n=9, deadline_ms=3000))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        _time.sleep(0.3)   # << soft_termination (3000 - 500 = 2500 ms)
        self.assertIsInstance(svc.terminate(handle),
                              TerminationAccepted)
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.result.outcome, OUTCOME_TERMINATED,
                         "el primer hecho observado fue la terminación")
        self.assertEqual(awaited.result.cause, CAUSE_EXTERNAL_TERMINATION)
        self.assertEqual(awaited.result.exit_status, -9,
                         "el proceso ignoró TERM: murió por el KILL")

    def test_mediciones_congeladas_y_garantias_aplicadas(self) -> None:
        svc = _real_service(termination_grace_ms=700)
        out = svc.start(_pair("import sys;sys.stdout.write('x')", n=4,
                              deadline_ms=2500))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(tuple(awaited.result.measurements), MEASUREMENT_KEYS)
        self.assertEqual(awaited.result.measurements["useful_runtime_ms"], 1800)
        # `guarantees_applied` declara lo que opero, no lo pedido.
        self.assertIn("termination_grace_ms_applied=700",
                      awaited.result.guarantees_applied)
        self.assertIn("useful_runtime_ms=1800", awaited.result.guarantees_applied)

    def test_la_configuracion_declarada_es_la_aplicada(self) -> None:
        """FIX-M2-R6 (OAI-M2-03): una única autoridad de configuración — el
        host compuesto desde el mismo `M2Config` que declara el
        `GuaranteePlan` aplica exactamente los valores declarados."""
        from src.domain.start_outcomes import Started as _Started
        from tests.unit.helpers_m1 import EXP, NOW as _NOW
        host = PosixSupervisorHost.from_config(
            M2Config.build(termination_grace_ms=500))
        svc = StartService(
            replay_store=MemoryReplayStore(), process_host=host,
            operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
            config=M2Config.build(termination_grace_ms=500),
            declared_config_fingerprint=M2Config.build(
                termination_grace_ms=500).fingerprint,
            wall_clock=lambda: float(NOW))
        out = svc.start(_pair("import sys;sys.stdout.write('x')", n=10,
                              deadline_ms=2500))
        self.assertIsInstance(out, _Started)
        assert isinstance(out, _Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        awaited = svc.await_result(handle, timeout=40)
        assert isinstance(awaited, AwaitedExecution)
        self.assertEqual(awaited.result.measurements["termination_grace_ms"],
                         500, "aplicado == declarado")
        self.assertEqual(awaited.result.measurements["useful_runtime_ms"],
                         2000, "deadline - gracia declarada")
        self.assertIn("termination_grace_ms_applied=500",
                      awaited.result.guarantees_applied)

    def test_el_slot_se_libera_al_completar_el_traspaso(self) -> None:
        svc = _real_service()
        out = svc.start(_pair("import sys;sys.stdout.write('x')", n=5))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        self.assertEqual(svc.slots_in_use, 1)
        svc.await_result(handle, timeout=40)
        self.assertEqual(svc.slots_in_use, 0)
        self.assertIsNone(svc.handle_for(out.handle_ref))

    def test_ausencia_honesta_si_no_llega_el_traspaso(self) -> None:
        """`None`, no un resultado fabricado."""
        svc = _real_service()
        out = svc.start(_pair("import time;time.sleep(30)", n=6,
                              deadline_ms=60000))
        assert isinstance(out, Started)
        handle = svc.handle_for(out.handle_ref)
        assert handle is not None
        self.assertIsNone(svc.await_result(handle, timeout=0.5))
        svc.terminate(handle)


class CrashAlrededorDelCasTests(unittest.TestCase):
    """G-M2-06 con inyeccion de crash REAL: el proceso muere por SIGKILL
    antes o despues de persistir el CAS, sobre el `FileReplayStore` durable.

    Un `os._exit` no basta como modelo: SIGKILL no deja correr atexit, buffers
    ni finalizadores, que es justo lo que puede ocultar un fallo de durabilidad.
    """

    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _matar_en(self, momento: str, identity: str) -> int:
        """Consume (o no) el token y muere por SIGKILL en el momento pedido."""
        import os
        import subprocess as sp
        guion = (
            "import os, signal, sys\n"
            "sys.path.insert(0, %r)\n"
            "from src.adapters.replay_store_file import FileReplayStore\n"
            "from pathlib import Path\n"
            "s = FileReplayStore(Path(%r))\n"
            "momento = %r\n"
            "if momento == 'antes':\n"
            "    os.kill(os.getpid(), signal.SIGKILL)\n"
            "out = s.consume_start_token(%r)\n"
            "s.close()\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n"
        ) % (str(ROOT), str(self.dir), momento, identity)
        proc = sp.run([sys.executable, "-c", guion], capture_output=True)
        return proc.returncode

    def test_crash_antes_del_cas_deja_el_token_sin_gastar(self) -> None:
        identidad = "a" * 64
        rc = self._matar_en("antes", identidad)
        self.assertEqual(rc, -9, "el hijo debe morir por SIGKILL")
        store = FileReplayStore(self.dir)
        try:
            self.assertEqual(store.start_token_status(identidad), "unspent")
            # Y sigue siendo consumible: el crash no lo quemo.
            self.assertIs(store.consume_start_token(identidad),
                          ConsumeOutcome.CONSUMED)
        finally:
            store.close()

    def test_crash_despues_del_cas_no_reabre_el_token(self) -> None:
        identidad = "b" * 64
        rc = self._matar_en("despues", identidad)
        self.assertEqual(rc, -9)
        store = FileReplayStore(self.dir)
        try:
            # El CAS quedo durable pese al SIGKILL inmediato.
            self.assertEqual(store.start_token_status(identidad), "spent")
            self.assertIs(store.consume_start_token(identidad),
                          ConsumeOutcome.ALREADY_SPENT)
        finally:
            store.close()

    def test_tras_crash_post_cas_el_coordinador_no_fabrica_handle(self) -> None:
        """El CAS linealiza el derecho de inicio, no prueba que hubo spawn."""
        identidad = "c" * 64
        self._matar_en("despues", identidad)
        store = FileReplayStore(self.dir)
        try:
            host = FakeProcessHost()
            svc = make_start_service(store=store, host=host)
            # Peticion cuya identidad es la ya gastada por el proceso muerto:
            # se emula reconciliando directamente sobre el store real.
            self.assertEqual(store.start_token_status(identidad), "spent")
            self.assertEqual(host.spawns, [],
                             "sin handle confirmado no se fabrica ninguno")
            self.assertIsNone(svc.handle_for("0" * 16))
        finally:
            store.close()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
