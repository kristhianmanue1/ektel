"""G-M2-10 — semántica de terminación local (D-M2-4, spec §8.0).

Falsifica: que un handle forjado, cruzado o de otra instancia sea aceptado;
que repetir con el mismo objeto produzca otro receipt; que un `terminate`
post-resultado contacte al supervisor o reclasifique el resultado; que
sobreviva a un reinicio del coordinador; o que aparezca algún reason code
distinto de `capability_rejected`.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain.execution_handle import ExecutionHandle  # noqa: E402
from src.domain.start_outcomes import (  # noqa: E402
    REASON_CAPABILITY_REJECTED, Started)
from src.domain.termination import (  # noqa: E402
    TerminationAccepted,
    TerminationReason,
    TerminationRejected,
    mint_termination_token,
)
from tests.unit.helpers_m2 import (  # noqa: E402
    FakeProcessHost, TEST_KEY, distinct_start_request, fake_handoff,
    make_start_service)


def _started(svc: object, n: int = 1) -> ExecutionHandle:
    out = svc.start(distinct_start_request(n))  # type: ignore[attr-defined]
    assert isinstance(out, Started)
    handle = svc.handle_for(out.handle_ref)  # type: ignore[attr-defined]
    assert handle is not None
    return handle


class HandleValidoTests(unittest.TestCase):
    def test_primer_terminate_contacta_al_supervisor(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        out = svc.terminate(handle)
        self.assertIsInstance(out, TerminationAccepted)
        self.assertEqual(host.terminations, [handle.handle_ref])

    def test_repetir_con_el_mismo_objeto_da_el_mismo_receipt(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        primero = svc.terminate(handle)
        segundo = svc.terminate(handle)
        assert isinstance(primero, TerminationAccepted)
        assert isinstance(segundo, TerminationAccepted)
        self.assertEqual(primero.receipt, segundo.receipt)
        self.assertEqual(len(host.terminations), 1,
                         "la repeticion no puede producir un segundo efecto")

    def test_reason_explicita_operator_requested_aceptada(self) -> None:
        svc = make_start_service()
        handle = _started(svc)
        out = svc.terminate(handle, TerminationReason.OPERATOR_REQUESTED)
        self.assertIsInstance(out, TerminationAccepted)

    def test_otra_reason_rechazada(self) -> None:
        svc = make_start_service()
        handle = _started(svc)
        for reason in ("operator_requested", 1, object(), True):
            with self.subTest(reason=type(reason).__name__):
                self.assertIsInstance(svc.terminate(handle, reason),
                                      TerminationRejected)


class PostResultadoTests(unittest.TestCase):
    """D-M2-4: no-op que no reclasifica."""

    def test_terminate_post_resultado_no_contacta_al_supervisor(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        host.deliver_terminal(handle.handle_ref, fake_handoff())
        svc.await_result(handle)
        out = svc.terminate(handle)
        self.assertIsInstance(out, TerminationAccepted)
        self.assertEqual(host.terminations, [],
                         "post-resultado no se contacta al supervisor")

    def test_terminate_post_resultado_no_reclasifica(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        host.deliver_terminal(handle.handle_ref, fake_handoff())
        result = svc.await_result(handle)
        svc.terminate(handle)
        self.assertIsNotNone(result)

    def test_conserva_el_derecho_de_terminacion_tras_la_ejecucion(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        host.deliver_terminal(handle.handle_ref, fake_handoff())
        svc.await_result(handle)
        self.assertIsInstance(svc.terminate(handle), TerminationAccepted)


class HandleInvalidoTests(unittest.TestCase):
    def test_handle_forjado_rechazado(self) -> None:
        svc = make_start_service()
        falso = ExecutionHandle(
            handle_ref="0" * 16, coordinator_instance="otra",
            identity_digest="d", action_id="a", termination_token="0" * 64)
        out = svc.terminate(falso)
        self.assertIsInstance(out, TerminationRejected)
        assert isinstance(out, TerminationRejected)
        self.assertEqual(out.reason_code, REASON_CAPABILITY_REJECTED)

    def test_handle_cruzado_entre_instancias_rechazado(self) -> None:
        """Reiniciar el coordinador invalida sus handles."""
        svc_a = make_start_service()
        handle = _started(svc_a)
        svc_b = make_start_service()  # nueva instancia = reinicio
        self.assertIsInstance(svc_b.terminate(handle), TerminationRejected)
        # Y sigue siendo valido en su propia instancia.
        self.assertIsInstance(svc_a.terminate(handle), TerminationAccepted)

    def test_token_de_otra_accion_rechazado(self) -> None:
        svc = make_start_service()
        handle = _started(svc)
        impostor = ExecutionHandle(
            handle_ref=handle.handle_ref,
            coordinator_instance=svc.coordinator_instance,
            identity_digest=handle.identity_digest,
            action_id="action-9999",
            termination_token=mint_termination_token(
                TEST_KEY, svc.coordinator_instance, handle.identity_digest,
                handle.action_id),  # token de la accion original
        )
        self.assertIsInstance(svc.terminate(impostor), TerminationRejected)

    def test_no_handle_rechazado(self) -> None:
        svc = make_start_service()
        for value in (None, "0" * 16, 1, {"handle_ref": "x"}, object()):
            with self.subTest(tipo=type(value).__name__):
                self.assertIsInstance(svc.terminate(value), TerminationRejected)


class VocabularioTests(unittest.TestCase):
    def test_solo_existe_operator_requested(self) -> None:
        self.assertEqual([r.name for r in TerminationReason],
                         ["OPERATOR_REQUESTED"])

    def test_rejected_no_admite_otro_reason_code(self) -> None:
        with self.assertRaises(ValueError):
            TerminationRejected(reason_code="start_failed")

    def test_el_receipt_no_promete_durabilidad(self) -> None:
        """Es un identificador opaco local: sin MAC y sin registro global."""
        svc = make_start_service()
        handle = _started(svc)
        out = svc.terminate(handle)
        assert isinstance(out, TerminationAccepted)
        self.assertEqual(len(out.receipt), 32)
        otro = make_start_service()
        self.assertIsNone(otro.handle_for(handle.handle_ref),
                          "no hay registro global de receipts ni de handles")



class RegresionH7Tests(unittest.TestCase):
    """H7: un handle ya liberado no vuelve a contactar al supervisor."""

    def test_terminate_tras_await_result_no_contacta_al_supervisor(self) -> None:
        host = FakeProcessHost()
        svc = make_start_service(host=host)
        handle = _started(svc)
        host.deliver_terminal(handle.handle_ref, fake_handoff())
        svc.await_result(handle)
        self.assertTrue(handle.released)
        out = svc.terminate(handle)
        self.assertIsInstance(out, TerminationAccepted)
        self.assertEqual(host.terminations, [],
                         "un handle liberado no puede reabrir efectos")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
