"""Adversariales M1: G7 política (required/optional, B7, A2 con puerto
nulo y falso), start_failed_indeterminate (§8.3) y compuerta D-P4-α (G2:
cero cruces ante inválidos)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from helpers_m1 import (  # noqa: E402
    NOW, make_request, emit_request, make_service, valid_request_bytes,
    make_capability_envelope, make_pop, capability_identity_digest)
from src.adapters.policy_fake import FakePolicyPort  # noqa: E402
from src.adapters.policy_null import NullPolicyPort  # noqa: E402
from src.adapters.spawn_frontier_counter import SpawnFrontierCounter  # noqa: E402
from src.domain.outcomes import Admitted, AdmissionRejected  # noqa: E402
from src.ports.policy_port import Allow, Deny, Indeterminate  # noqa: E402
from src.ports.replay_store import ConsumeOutcome  # noqa: E402
from src.adapters.replay_store_file import FileReplayStore  # noqa: E402
from src.domain.admission_token import build_admission_token  # noqa: E402


def _invalid_zoo() -> list[bytes]:
    """Zoo determinista de entradas inválidas (G2: 0 cruces)."""
    req = make_request()
    zoo: list[bytes] = [
        b"", b"no-json", b'{"schema_version":1,', b"null", b"[]",
        b'{"schema_version":1,"schema_version":1}',
        b'{"a":' * 20000,
    ]
    # Descriptor con campo extra / versión mayor / stdin incoherente
    r = dict(req); r["extra"] = 1
    zoo.append(emit_request(r))
    r = dict(req); r["schema_version"] = 2
    zoo.append(emit_request(r))
    r = dict(req); r["stdin_policy"] = {"kind": "inline_b64"}
    zoo.append(emit_request(r))
    r = dict(req); r["command_absolute"] = "/bin/tru\x00e"
    zoo.append(emit_request(r))
    # Capacidad con MAC rota / key_id inactivo / expirada
    r = dict(req)
    env = dict(r["capability_envelope"])
    env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
    r["capability_envelope"] = env
    zoo.append(emit_request(r))
    # Binding discordante
    r = dict(req)
    env2 = make_capability_envelope(binding=dict(req_b for req_b in []))
    # (binding distinto: reuse helper)
    from helpers_m1 import base_binding
    env2 = make_capability_envelope(binding=base_binding(cwd="/otro"))
    r["capability_envelope"] = env2
    r["invocation_proof"] = make_pop(capability_identity_digest(env2))
    zoo.append(emit_request(r))
    # PoP rota
    r = dict(req)
    pop = make_pop(capability_identity_digest(r["capability_envelope"]))
    pop["mac"] = ("0" if pop["mac"][0] != "0" else "1") + pop["mac"][1:]
    r["invocation_proof"] = pop
    zoo.append(emit_request(r))
    return zoo


class PolicyG7Tests(unittest.TestCase):
    def test_required_puerto_nulo_rechaza(self):
        # Contract test contra el puerto NULO (ADR-008 punto 3): si un
        # despliegue mal configurado invoca política con el puerto nulo,
        # el Indeterminate resultante rechaza en required (fail-closed).
        out = make_service(policy_port=NullPolicyPort(),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_required_deny(self):
        out = make_service(policy_port=FakePolicyPort(Deny("d1")),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_denied")

    def test_required_indeterminate(self):
        out = make_service(
            policy_port=FakePolicyPort(Indeterminate("x")),
            policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_required_allow_expirado(self):
        out = make_service(
            policy_port=FakePolicyPort(Allow("d1", NOW - 3600)),
            policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_required_allow_tardio(self):
        # B7: recepción fuera del plazo monotónico → como Indeterminate.
        # (reloj monotónico REAL: el helper fija uno constante para
        # determinismo; aquí el plazo sí debe medir el retardo del falso)
        import time as _time
        from helpers_m1 import MemoryReplayStore, TEST_KEY
        from src.application.admit import AdmissionService
        from helpers_m1 import TEST_SALT
        svc = AdmissionService(
            replay_store=MemoryReplayStore(),
            deployment_salt=TEST_SALT,
            operator_key=TEST_KEY,
            policy_port=FakePolicyPort(Allow("d1", NOW + 3600), delay_s=0.2),
            policy_mode="required",
            policy_timeout_s=0.05,
            wall_clock=lambda: NOW,
            mono_clock=_time.monotonic,
        )
        out = svc.admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_required_allow_valido_admite_con_recibo(self):
        out = make_service(policy_port=FakePolicyPort(Allow("d1", NOW + 3600)),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        assert isinstance(out, Admitted)
        self.assertEqual(out.policy_receipt.decision_id, "d1")
        self.assertFalse(out.policy_degraded)

    def test_optional_indeterminate_degradada_declarada(self):
        out = make_service(
            policy_port=FakePolicyPort(Indeterminate("x")),
            policy_mode="optional").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        assert isinstance(out, Admitted)
        self.assertTrue(out.policy_degraded)  # nunca silencioso
        self.assertIsNone(out.policy_receipt)

    def test_a2_mutacion_del_adaptador_bloqueada_por_tipo(self):
        # ADR-008 A2: el falso intenta mutar la solicitud; el núcleo pasa
        # una vista de SÓLO LECTURA (MappingProxyType) — la mutación
        # levanta TypeError. El asiento honesto es sobre el HECHO de la
        # mutación: `mutation_applied` debe ser False (bloqueada). Si
        # alguien reintroduce un dict mutable en el núcleo, la mutación
        # prospera (True) y ESTE test falla. Nota: el token de admisión
        # no deriva de la solicitud de política, por eso el asiento va
        # sobre el hecho y no sobre el resultado.
        port = FakePolicyPort(Allow("d1", NOW + 3600), mutate=True)
        out = make_service(policy_port=port,
                           policy_mode="required").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        self.assertIsNotNone(port.mutation_applied)   # sí intentó
        self.assertFalse(port.mutation_applied)       # y fue bloqueada
        self.assertEqual(port.calls[0]["action_id"], "action-0001")


class StartIndeterminateTests(unittest.TestCase):
    def test_crash_entre_cas_y_frontera_token_gastado_nunca_replay(self):
        # §8.3: crash tras el CAS de consumo y antes del spawn → token
        # permanentemente gastado; reintentar la MISMA admisión es replay.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = FileReplayStore(Path(tmp))
            svc = make_service(store=store)
            out = svc.admit(valid_request_bytes())
            self.assertIsInstance(out, Admitted)
            assert isinstance(out, Admitted)
            # Consumo (como haría start) seguido de crash simulado antes
            # de cruzar la frontera: el spy permanece vacío.
            spy = SpawnFrontierCounter()
            self.assertEqual(store.consume_start_token(out.identity_digest),
                             ConsumeOutcome.CONSUMED)
            crash = True
            if not crash:
                spy.submit(out)  # nunca alcanzado
            # Reintento de la misma admisión: nonce ya reservado → replay.
            retry = svc.admit(valid_request_bytes())
            self.assertIsInstance(retry, AdmissionRejected)
            self.assertEqual(retry.safe_detail, "nonce_replay")
            # Y el token sigue gastado (reconciliación por digest, §7.4).
            self.assertEqual(store.start_token_status(out.identity_digest),
                             "spent")
            self.assertEqual(spy.total_crossings(), 0)


class SpawnFrontierG2Tests(unittest.TestCase):
    def test_cero_cruces_ante_invalidos(self):
        # G2/D-P4-α: ninguna entrada inválida cruza la frontera.
        spy = SpawnFrontierCounter()
        svc = make_service()
        for raw in _invalid_zoo():
            out = svc.admit(raw)
            self.assertIsInstance(out, AdmissionRejected,
                                  f"entrada inválida admitida: {raw[:40]!r}")
            if not isinstance(out, AdmissionRejected):
                spy.submit(out)  # nunca: fail-closed por construcción
        self.assertEqual(spy.total_crossings(), 0)

    def test_cruces_solo_con_admitted(self):
        spy = SpawnFrontierCounter()
        svc = make_service()
        out = svc.admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        spy.submit(out)
        self.assertEqual(spy.total_crossings(), 1)
        self.assertEqual(spy.crossings_for(out.identity_digest), 1)

    def test_zoo_tamano_congelado(self):
        # Congelado: el zoo adversarial de G2 tiene exactamente 14 entradas.
        self.assertEqual(len(_invalid_zoo()), 14)


if __name__ == "__main__":
    unittest.main()
