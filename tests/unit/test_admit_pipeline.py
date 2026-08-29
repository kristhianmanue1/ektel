"""Pruebas del token de admisión (§6.6) y del pipeline `admit` completo
con la precedencia de la regla 2 final, política §9 y replay §7.4."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers_m1 import (  # noqa: E402
    EXP, NOW, MemoryReplayStore, ScriptedPolicy, SpawnSpy, TEST_KEY,
    TEST_SALT, base_binding, capability_identity_digest, emit_request,
    make_capability_envelope, make_pop, make_request, make_service,
    valid_request_bytes)
from src.domain.admission_token import build_admission_token  # noqa: E402
from src.domain.crypto import compute_key_id, mac_envelope  # noqa: E402
from src.domain.outcomes import Admitted, AdmissionRejected  # noqa: E402
from src.ports.policy_port import Allow, Deny, Indeterminate  # noqa: E402
from src.ports.replay_store import ReserveOutcome  # noqa: E402
from src.domain import contract_layer  # noqa: E402


def _b64d(s: str) -> bytes:
    from base64 import urlsafe_b64decode
    return urlsafe_b64decode(s + "=" * ((-len(s)) % 4))


class AdmissionTokenTests(unittest.TestCase):
    def test_estructura_y_mac(self):
        token = build_admission_token(TEST_KEY, "d" * 64, "action-0001",
                                      EXP, "issuer")
        import json
        envelope = json.loads(_b64d(token))
        header = json.loads(_b64d(envelope["protected_header_b64"]))
        payload = json.loads(_b64d(envelope["payload_b64"]))
        self.assertEqual(header["typ"], "admission-token")
        self.assertEqual(payload["identity_digest"], "d" * 64)
        self.assertEqual(payload["action_id"], "action-0001")
        self.assertEqual(payload["exp"], EXP)
        mac = mac_envelope(TEST_KEY, b"ektel/admission/v1",
                           envelope["protected_header_b64"],
                           envelope["payload_b64"])
        self.assertEqual(_b64d(envelope["signature"]), mac)
        # Round-trip contra el parser de contrato congelado: el token debe
        # ser un sobre de admisión válido (§6.6: sobre firmado estándar).
        raw = contract_layer.emit_canonical(envelope)
        result = contract_layer._REF.parse_wire("admission-token", raw, TEST_KEY)
        self.assertEqual((result.verdict, result.diagnostic), ("accept", "ok"))


class AdmitPipelineTests(unittest.TestCase):
    def test_camino_feliz(self):
        svc = make_service()
        out = svc.admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        self.assertEqual(out.identity_digest,
                         capability_identity_digest(make_capability_envelope()))
        self.assertTrue(out.admitted_action)
        self.assertEqual(out.policy_mode, "absent")
        self.assertFalse(out.policy_degraded)
        self.assertEqual(out.skew_tolerance_s, 30.0)
        self.assertEqual(out.admitted_at_wall, NOW)
        # GuaranteePlan honesto: garantías v1 declaradas unsupported (M2/M3).
        self.assertEqual([e["magnitude"] for e in out.guarantee_plan],
                         ["runtime_supervision", "output_bounds"])
        self.assertTrue(all(e["class"] == "unsupported" for e in out.guarantee_plan))

    def test_frontera_spawn_solo_admitted_cruza(self):
        # D-P4-α: el spy sólo acepta Admitted; el servicio no expone start.
        spy = SpawnSpy()
        svc = make_service()
        out = svc.admit(valid_request_bytes())
        spy.submit(out)
        self.assertEqual(len(spy.crossings), 1)

    def test_descriptor_mal_formado_json(self):
        svc = make_service()
        out = svc.admit(b'{"schema_version":1,')
        self.assertEqual((out.reason_code, out.safe_detail[:9]),
                         ("malformed_descriptor", "contract:"))

    def test_descriptor_clave_duplicada(self):
        svc = make_service()
        out = svc.admit(b'{"schema_version":1,"schema_version":1}')
        self.assertEqual(out.reason_code, "malformed_descriptor")
        self.assertIn("duplicate_key", out.safe_detail)

    def test_precedencia_stdin_interno_antes_de_capacidad(self):
        # Regla 2 final: paso 1 (malformed) ANTES que paso 2 (capability)
        # — stdin incoherente + MAC rota → malformed_descriptor.
        doc = make_request()
        doc["stdin_policy"] = {"kind": "inline_b64"}  # incoherente interno
        env = dict(doc["capability_envelope"])
        env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
        doc["capability_envelope"] = env
        out = make_service().admit(emit_request(doc))
        self.assertEqual(out.reason_code, "malformed_descriptor")
        self.assertTrue(out.safe_detail.startswith("stdin_policy:"))

    def test_precedencia_representabilidad_antes_de_capacidad(self):
        doc = make_request(command_absolute="/bin/tru\x00e")
        env = dict(doc["capability_envelope"])
        env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
        doc["capability_envelope"] = env
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("malformed_descriptor", "command_absolute:nul"))

    def test_nul_en_descriptor_malformed(self):
        doc = make_request(args=["--nul\x00"])
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("malformed_descriptor", "args[0]:nul"))

    def test_capacidad_mac_rota(self):
        doc = make_request()
        env = dict(doc["capability_envelope"])
        env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
        doc["capability_envelope"] = env
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("capability_rejected", "contract:bad_signature"))

    def test_binding_discordante(self):
        doc = make_request()
        env = make_capability_envelope(
            binding=base_binding(stdin_digest="0" * 64))
        doc["capability_envelope"] = env
        doc["invocation_proof"] = make_pop(capability_identity_digest(env))
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("capability_rejected", "binding:stdin_policy_digest"))

    def test_binding_comando_discordante(self):
        doc = make_request()
        env = make_capability_envelope(
            binding=base_binding(action_id="action-otro"))
        doc["capability_envelope"] = env
        doc["invocation_proof"] = make_pop(capability_identity_digest(env))
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("capability_rejected", "binding:action_id"))

    def test_precedencia_binding_antes_de_pop(self):
        # Regla 2 final: paso 3 (binding) ANTES que paso 4 (PoP).
        doc = make_request()
        env = make_capability_envelope(
            binding=base_binding(cwd="/otro"))
        doc["capability_envelope"] = env
        pop = make_pop(capability_identity_digest(env))
        pop["mac"] = ("0" if pop["mac"][0] != "0" else "1") + pop["mac"][1:]
        doc["invocation_proof"] = pop
        out = make_service().admit(emit_request(doc))
        self.assertEqual(out.safe_detail, "binding:cwd")

    def test_pop_rota(self):
        doc = make_request()
        pop = make_pop(capability_identity_digest(doc["capability_envelope"]))
        pop["mac"] = ("0" if pop["mac"][0] != "0" else "1") + pop["mac"][1:]
        doc["invocation_proof"] = pop
        out = make_service().admit(emit_request(doc))
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("capability_rejected", "contract:bad_signature"))

    def test_replay_nonce(self):
        store = MemoryReplayStore()
        svc = make_service(store=store)
        first = svc.admit(valid_request_bytes())
        self.assertIsInstance(first, Admitted)
        second = svc.admit(valid_request_bytes())
        self.assertEqual((second.reason_code, second.safe_detail),
                         ("capability_rejected", "nonce_replay"))

    def test_store_no_disponible_fail_closed(self):
        store = MemoryReplayStore(fail=True)
        out = make_service(store=store).admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "capability_rejected")
        self.assertEqual(out.safe_detail, "replay_store_unavailable")
        self.assertTrue(out.retryable)

    def test_store_respuesta_desconocida_o_excepcion_fail_closed(self):
        class UnknownStore(MemoryReplayStore):
            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                return None

        class RaisingStore(MemoryReplayStore):
            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                raise RuntimeError("detalle no confiable")

        for store in (UnknownStore(), RaisingStore()):
            with self.subTest(store=type(store).__name__):
                out = make_service(store=store).admit(valid_request_bytes())
                self.assertEqual(
                    (out.reason_code, out.safe_detail, out.retryable),
                    ("capability_rejected", "replay_store_unavailable", True))

    def test_store_respuesta_hostil_no_ejecuta_igualdad(self):
        class HostileOutcome:
            def __eq__(self, other):
                raise RuntimeError("comparacion controlada por adaptador")

        class HostileStore(MemoryReplayStore):
            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                self._reserved.add((issuer_id, nonce))
                return HostileOutcome()

        out = make_service(store=HostileStore()).admit(valid_request_bytes())
        self.assertEqual(
            (out.reason_code, out.safe_detail, out.retryable),
            ("capability_rejected", "replay_store_unavailable", True))

    def test_exp_enorme_rechaza_tipado_sin_reservar_nonce(self):
        class RecordingStore(MemoryReplayStore):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                self.calls += 1
                return super().reserve_nonce(issuer_id, nonce, reserve_until_wall)

        store = RecordingStore()
        env = make_capability_envelope(exp=10 ** 1000)
        out = make_service(store=store).admit(emit_request(make_request(env=env)))
        self.assertEqual(
            (out.reason_code, out.safe_detail, out.retryable),
            ("capability_rejected", "time:reserve_until_unrepresentable", False))
        self.assertEqual(store.calls, 0)

    def test_ttl_redondeado_nunca_vence_antes_de_exp(self):
        class CapturingStore(MemoryReplayStore):
            def __init__(self):
                super().__init__()
                self.reserve_until_wall = None

            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                self.reserve_until_wall = reserve_until_wall
                return super().reserve_nonce(issuer_id, nonce, reserve_until_wall)

        store = CapturingStore()
        exp = (1 << 53) + 1  # no representable exactamente como float
        env = make_capability_envelope(exp=exp)
        out = make_service(store=store).admit(emit_request(make_request(env=env)))
        self.assertIsInstance(out, Admitted)
        self.assertIsNotNone(store.reserve_until_wall)
        self.assertGreaterEqual(store.reserve_until_wall, exp)

    def test_cota_temporal_derivada_no_finita_rechaza_sin_reserva(self):
        from src.application.admit import AdmissionService

        class RecordingStore(MemoryReplayStore):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def reserve_nonce(self, issuer_id, nonce, reserve_until_wall):
                self.calls += 1
                return super().reserve_nonce(issuer_id, nonce, reserve_until_wall)

        store = RecordingStore()
        largest = float.fromhex("0x1.fffffffffffffp+1023")
        svc = AdmissionService(
            replay_store=store, deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, skew_tolerance_s=largest,
            wall_clock=lambda: largest, mono_clock=lambda: 0.0)
        out = svc.admit(valid_request_bytes())
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("capability_rejected", "time_range_invalid"))
        self.assertEqual(store.calls, 0)

    def test_nonce_quemado_tras_rechazo_de_politica(self):
        # §6.2/ADR-004 A1: sin efectos parciales salvo la reserva CAS; un
        # rechazo posterior (política) quema el nonce — fail-closed.
        store = MemoryReplayStore()
        svc = make_service(store=store, policy_port=ScriptedPolicy(Deny("d1")),
                           policy_mode="required")
        out = svc.admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_denied")
        second = make_service(store=store).admit(valid_request_bytes())
        self.assertEqual((second.reason_code, second.safe_detail),
                         ("capability_rejected", "nonce_replay"))

    def test_precedencia_replay_antes_de_politica(self):
        store = MemoryReplayStore()
        svc = make_service(store=store, policy_port=ScriptedPolicy(Deny("d1")),
                           policy_mode="required")
        svc.admit(valid_request_bytes())  # quema el nonce
        out = svc.admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "capability_rejected")  # no policy_denied

    def test_politica_required_deny(self):
        out = make_service(policy_port=ScriptedPolicy(Deny("d1")),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("policy_denied", "policy:deny"))

    def test_politica_required_sin_puerto(self):
        out = make_service(policy_port=None,
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual((out.reason_code, out.safe_detail),
                         ("policy_unavailable", "policy:unavailable"))

    def test_politica_required_indeterminate(self):
        out = make_service(policy_port=ScriptedPolicy(Indeterminate("x")),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_politica_required_allow_expirado(self):
        # B7: valid_until contra reloj de pared con tolerancia; un Allow
        # expirado se convierte en Indeterminate → rechazo si es requerido.
        decision = Allow("d1", valid_until_wall=NOW - 3600)
        out = make_service(policy_port=ScriptedPolicy(decision),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_unavailable")

    def test_politica_required_allow_valido_con_recibo(self):
        decision = Allow("d1", valid_until_wall=NOW + 3600)
        out = make_service(policy_port=ScriptedPolicy(decision),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        assert isinstance(out, Admitted)
        self.assertEqual(out.policy_receipt.decision_id, "d1")

    def test_politica_optional_indeterminate_degradada_declarada(self):
        out = make_service(policy_port=ScriptedPolicy(Indeterminate("x")),
                           policy_mode="optional").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        assert isinstance(out, Admitted)
        self.assertTrue(out.policy_degraded)
        self.assertIsNone(out.policy_receipt)

    def test_politica_optional_sin_puerto_degradada(self):
        out = make_service(policy_port=None,
                           policy_mode="optional").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        assert isinstance(out, Admitted)
        self.assertTrue(out.policy_degraded)

    def test_politica_optional_deny_rechaza(self):
        # Un Deny explícito no es fail-open (§9: sólo Indeterminate o
        # indisponibilidad lo son).
        out = make_service(policy_port=ScriptedPolicy(Deny("d1")),
                           policy_mode="optional").admit(valid_request_bytes())
        self.assertEqual(out.reason_code, "policy_denied")

    def test_politica_absent_no_invoca_puerto(self):
        port = ScriptedPolicy(Allow("d1", NOW + 3600))
        out = make_service(policy_port=port,
                           policy_mode="absent").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        self.assertEqual(port.calls, [])

    def test_politica_evalua_copia_propia_inmutable(self):
        # ADR-008 A2: el núcleo construye su propia solicitud; el adaptador
        # recibe una copia y mutarla no altera la admisión.
        class MutatingPolicy(ScriptedPolicy):
            def evaluate(self, request):
                try:
                    request["action_id"] = "mutado"  # type: ignore[index]
                except TypeError:
                    pass  # Mapping de sólo lectura: también válido
                return Allow("d1", NOW + 3600)
        out = make_service(policy_port=MutatingPolicy(Allow("d1", NOW + 3600)),
                           policy_mode="required").admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)

    def test_arranque_clave_mala_fail_closed(self):
        from src.adapters.operator_key import OperatorKeyError
        from src.application.admit import AdmissionService
        with self.assertRaises(OperatorKeyError):
            make_service(key=TEST_KEY[:-1])  # longitud de clave inválida
        with self.assertRaises(ValueError):
            AdmissionService(  # ambas fuentes a la vez
                replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
                operator_key=TEST_KEY, operator_key_path=Path("/dev/null"),
                wall_clock=lambda: NOW, mono_clock=lambda: 0.0)
        with self.assertRaises(ValueError):
            AdmissionService(  # ninguna fuente
                replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
                wall_clock=lambda: NOW, mono_clock=lambda: 0.0)
        with self.assertRaises(OperatorKeyError):
            AdmissionService(  # sal de longitud inválida
                replay_store=MemoryReplayStore(), deployment_salt=b"corto",
                operator_key=TEST_KEY, wall_clock=lambda: NOW,
                mono_clock=lambda: 0.0)

    def test_configuracion_temporal_invalida_falla_al_arrancar(self):
        from src.application.admit import AdmissionService
        for value in (float("nan"), float("inf"), 10 ** 1000, (1 << 53) + 1,
                      0.0, -1.0, True):
            with self.subTest(policy_timeout_s=value), self.assertRaises(ValueError):
                AdmissionService(
                    replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
                    operator_key=TEST_KEY, policy_timeout_s=value,
                    wall_clock=lambda: NOW, mono_clock=lambda: 0.0)
        for value in (float("nan"), float("inf"), 10 ** 1000,
                      (1 << 53) + 1, -1.0, True):
            with self.subTest(skew_tolerance_s=value), self.assertRaises(ValueError):
                AdmissionService(
                    replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
                    operator_key=TEST_KEY, skew_tolerance_s=value,
                    wall_clock=lambda: NOW, mono_clock=lambda: 0.0)

    def test_reloj_de_pared_no_finito_rechaza_sin_quemar_nonce(self):
        from src.application.admit import AdmissionService
        store = MemoryReplayStore()
        invalid = AdmissionService(
            replay_store=store, deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, wall_clock=lambda: float("nan"),
            mono_clock=lambda: 0.0)
        out = invalid.admit(valid_request_bytes())
        self.assertEqual((out.reason_code, out.safe_detail, out.retryable),
                         ("capability_rejected", "wall_clock_unavailable", True))
        self.assertIsInstance(make_service(store=store).admit(valid_request_bytes()),
                              Admitted)

    def test_reloj_numerico_hostil_rechaza_tipado(self):
        from src.application.admit import AdmissionService

        class HostileInt(int):
            def __float__(self):
                raise RuntimeError("conversion controlada")

        svc = AdmissionService(
            replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, wall_clock=lambda: HostileInt(NOW),
            mono_clock=lambda: 0.0)
        out = svc.admit(valid_request_bytes())
        self.assertEqual((out.reason_code, out.safe_detail, out.retryable),
                         ("capability_rejected", "wall_clock_unavailable", True))


if __name__ == "__main__":
    unittest.main()
