"""R15/R16: ataques a interfaces admitidas y lifecycle local (no sandbox)."""
from __future__ import annotations

import threading
import unittest

from src.application.admit import AdmissionService
from src.application.config import M2Config
from src.application.start_service import StartService, _terminal_pair, _build_awaited
from src.domain.execution_handle import ExecutionHandle
from src.domain.outcomes import Admitted, AdmissionRejected
from src.domain.start_outcomes import Started, StartFailed
from src.domain.start_request import StartRequest
from src.domain.termination import TerminationRejected
from tests.unit.helpers_m1 import MemoryReplayStore, TEST_KEY, TEST_KEY_ID, TEST_SALT, NOW, EXP
from tests.unit.helpers_m2 import distinct_start_request, FakeProcessHost, fake_handoff, HostileStore


class CountingStore(MemoryReplayStore):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def consume_start_token(self, identity_digest):
        self.calls += 1
        return super().consume_start_token(identity_digest)


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.now = float(NOW)
        self.config = M2Config.build(max_concurrent_actions=2)
        self.admission = self.issuer(self.config)
        self.store = CountingStore()
        self.host = FakeProcessHost(config_fingerprint=self.config.fingerprint)
        self.svc = self.service(self.admission)

    def issuer(self, config):
        return AdmissionService(replay_store=MemoryReplayStore(),
            operator_key=TEST_KEY, deployment_salt=TEST_SALT,
            m2_config=config, wall_clock=lambda: self.now)

    def service(self, admission, config=None, declared=None):
        return StartService(replay_store=self.store, process_host=self.host,
            operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
            config=config or self.config, admission_service=admission,
            declared_config_fingerprint=declared, wall_clock=lambda: self.now)

    def issue(self, n=1, issuer=None):
        req = distinct_start_request(n)
        out = (issuer or self.admission).admit(req.action_request_wire)
        self.assertIsInstance(out, Admitted)
        self.assertEqual(out.admitted_action, req.admitted_action)
        return req

    def assert_no_effect(self, outcome):
        self.assertIsInstance(outcome, StartFailed)
        self.assertEqual(self.store.calls, 0)
        self.assertEqual(self.store._spent, set())
        self.assertEqual(self.host.spawns, [])

    def test_A_B_B_caller_claims_B(self):
        a = self.issuer(M2Config.build(termination_grace_ms=2000))
        b = M2Config.build(termination_grace_ms=1500)
        self.host = FakeProcessHost(config_fingerprint=b.fingerprint)
        svc = self.service(a, b, b.fingerprint)
        self.assert_no_effect(svc.start(self.issue(issuer=a)))

    def test_string_without_issuer_is_not_authority(self):
        svc = self.service(None, declared=self.config.fingerprint)
        self.assert_no_effect(svc.start(distinct_start_request(1)))

    def test_other_genuine_issuer_same_config_is_not_provenance(self):
        other = self.issuer(self.config)
        self.assert_no_effect(self.svc.start(self.issue(issuer=other)))

    def test_caller_fingerprint_is_ignored_even_when_wrong(self):
        svc = self.service(self.admission, declared="0" * 64)
        out = svc.start(self.issue())
        self.assertIsInstance(out, Started)
        self.host.deliver_absence(out.handle_ref)

    def test_restart_loses_unspent_provenance(self):
        req = self.issue()
        restarted = self.service(self.issuer(self.config))
        self.assert_no_effect(restarted.start(req))

    def test_reusing_admission_does_not_transfer_old_emissions(self):
        req = self.issue()
        restarted = self.service(self.admission)
        self.assert_no_effect(restarted.start(req))
        self.assert_no_effect(self.svc.start(req))

    def test_capacity_expiry_and_no_public_register(self):
        self.issue(1)
        self.issue(2)
        req = distinct_start_request(3)
        out = self.admission.admit(req.action_request_wire)
        self.assertIsInstance(out, AdmissionRejected)
        self.assertEqual(out.safe_detail, "m2:issuance_capacity")
        self.assertEqual(len(self.admission._issuances), 2)
        self.assertFalse(hasattr(self.admission, "register"))
        self.now = float(EXP) + 31  # también fuera del skew de Admission M1
        # Expired requests remain invalid, but old evidence no longer occupies N.
        self.assertIsInstance(self.admission.admit(req.action_request_wire), AdmissionRejected)
        self.assertEqual(len(self.admission._issuances), 0)
        self.assert_no_effect(self.svc.start(req))

    def test_failed_admission_does_not_occupy_capacity(self):
        for _ in range(4):
            self.assertIsInstance(self.admission.admit(b"{}"), AdmissionRejected)
        self.assertEqual(len(self.admission._issuances), 0)
        self.issue()

    def test_concurrent_admissions_cannot_exceed_N(self):
        requests = [distinct_start_request(n) for n in range(10, 18)]
        barrier = threading.Barrier(len(requests))
        outcomes = []
        def admit(req):
            barrier.wait()
            outcomes.append(self.admission.admit(req.action_request_wire))
        threads = [threading.Thread(target=admit, args=(req,)) for req in requests]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sum(isinstance(out, Admitted) for out in outcomes), 2)
        self.assertEqual(len(self.admission._issuances), 2)

    def test_unspent_and_unknown_keep_evidence_but_spent_retires_it(self):
        for status in ("unspent", "unknown", "spent"):
            with self.subTest(status=status):
                issuer = self.issuer(self.config)
                svc = StartService(replay_store=HostileStore(status=status),
                    process_host=self.host, operator_key=TEST_KEY,
                    active_key_id=TEST_KEY_ID, config=self.config,
                    admission_service=issuer, wall_clock=lambda: self.now)
                req = self.issue(issuer=issuer)
                self.assertIsInstance(svc.start(req), StartFailed)
                self.assertEqual(req.admitted_action in issuer._issuances,
                                 status != "spent")
                self.assertEqual(self.host.spawns, [])

    def test_no_overwrite_on_repeated_emission(self):
        req = self.issue()
        original = dict(self.admission._issuances)
        self.assertIsInstance(self.admission.admit(req.action_request_wire), AdmissionRejected)
        self.assertEqual(self.admission._issuances, original)

    def test_pre_cas_failure_keeps_evidence(self):
        req = self.issue()
        self.host._config_fingerprint = "0" * 64  # fault injection of drift
        self.assert_no_effect(self.svc.start(req))
        self.assertIn(req.admitted_action, self.admission._issuances)
        self.host._config_fingerprint = self.config.fingerprint
        out = self.svc.start(req)
        self.assertIsInstance(out, Started)
        self.assertEqual(len(self.admission._issuances), 0)
        self.host.deliver_absence(out.handle_ref)

    def test_spent_retirement_independent_of_terminal(self):
        req = self.issue()
        out = self.svc.start(req)
        self.assertIsInstance(out, Started)
        self.assertEqual(len(self.admission._issuances), 0)
        self.assertIsInstance(self.svc.start(req), StartFailed)
        self.assertEqual(self.store.calls, 1)
        self.assertEqual(len(self.host.spawns), 1)
        self.host.deliver_absence(out.handle_ref)

    def test_hostile_handles_and_timeouts_are_controlled(self):
        class HostileHandle(ExecutionHandle):
            def __hash__(self):
                raise AssertionError("must not invoke hostile hash")
        for handle in (object.__new__(ExecutionHandle),
                       object.__new__(HostileHandle), object(), {}, None):
            self.assertIsNone(self.svc.await_result(handle))
            self.assertIsInstance(self.svc.terminate(handle), TerminationRejected)
        out = self.svc.start(self.issue())
        handle = self.svc.handle_for(out.handle_ref)
        for timeout in (float("nan"), float("inf"), -1, True, 10**1000, object()):
            self.assertIsNone(self.svc.await_result(handle, timeout=timeout))
        self.host.deliver_terminal(out.handle_ref, fake_handoff(stdout=b"real"))
        self.assertEqual(self.svc.await_result(handle).stdout, b"real")

    def test_incomplete_start_request_is_controlled(self):
        self.assert_no_effect(self.svc.start(object.__new__(StartRequest)))

    def test_reader_has_no_writer_and_timeout_does_not_close(self):
        out = self.svc.start(self.issue())
        handle = self.svc.handle_for(out.handle_ref)
        for obj in (self.svc, handle, self.svc._record_for(handle)):
            for name in ("deposit_once", "close_without_result", "finish", "store_terminal_result"):
                self.assertFalse(hasattr(obj, name))
        self.assertIsNone(self.svc.await_result(handle, timeout=0))
        self.assertFalse(self.svc._record_for(handle).terminal_closed)
        self.host.deliver_terminal(out.handle_ref, fake_handoff(stdout=b"real"))
        self.assertEqual(self.svc.await_result(handle).stdout, b"real")
        self.assertIsNone(self.svc.await_result(handle))

    def test_internal_writer_race_has_one_transition_and_delivery(self):
        # Instrumentación interna, no claim de aislamiento del intérprete.
        reader, writer = _terminal_pair("0" * 16)
        result = _build_awaited(fake_handoff(stdout=b"real"))
        barrier = threading.Barrier(8)
        accepted = []
        def finish(n):
            barrier.wait()
            accepted.append(writer(result if n % 2 else None))
        threads = [threading.Thread(target=finish, args=(n,)) for n in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sum(accepted), 1)
        self.assertTrue(reader.terminal_closed)
        first = reader.take_once()
        self.assertIn(first, (None, result))
        self.assertIsNone(reader.take_once())


if __name__ == "__main__":
    unittest.main()
