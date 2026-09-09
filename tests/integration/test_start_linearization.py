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
from src.ports.replay_store import ConsumeOutcome  # noqa: E402
from tests.unit.helpers_m1 import MemoryReplayStore  # noqa: E402
from tests.unit.helpers_m2 import (  # noqa: E402
    FakeProcessHost,
    HostileStore,
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
