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
        _, effective = host.spawns[0]
        self.assertEqual(effective, 1000, "min(deadline_ms, vigencia restante)")


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

    def test_handle_ref_invalido_no_fabrica_handle(self) -> None:
        svc = make_start_service(host=FakeProcessHost(bad_ref=True))
        out = svc.start(valid_start_request())
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_START_FAILED_INDETERMINATE)



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
    host = PosixSupervisorHost(**kw)  # type: ignore[arg-type]
    return StartService(
        replay_store=MemoryReplayStore(), process_host=host,
        operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
        config=M2Config.build(max_concurrent_actions=4),
        wall_clock=lambda: float(NOW))


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
