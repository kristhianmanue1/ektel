"""Pruebas de verificación de capacidad (regla 2 final paso 2: §5.2/§6.9/
§7.3 + key_id activo) y de PoP (ADR-003 §1.5, regla 2 final paso 4)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers_m1 import (  # noqa: E402
    EXP, NBF, NOW, TEST_KEY, TEST_KEY_ID, TEST_SALT, base_binding,
    capability_identity_digest, make_capability_envelope, make_pop)
from src.domain.capability import verify_capability  # noqa: E402
from src.domain.crypto import compute_key_id  # noqa: E402
from src.domain.pop import verify_invocation_proof  # noqa: E402


def _verify(env, now=NOW, key=TEST_KEY, key_id=TEST_KEY_ID, skew=30.0):
    return verify_capability(env, key, key_id, now, skew)


class CapabilityTests(unittest.TestCase):
    def test_valida(self):
        view = _verify(make_capability_envelope())
        self.assertIsNotNone(view)
        self.assertEqual(view.identity_digest,
                         capability_identity_digest(make_capability_envelope()))
        self.assertEqual(view.artifact_identity_profile, "route_mutable_unverified")

    def test_mac_rota(self):
        env = make_capability_envelope()
        env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
        self.assertEqual(_verify(env), "contract:bad_signature")

    def test_alias_no_canonico_con_mac_recalculada(self):
        # ADR-010: alias no canónico de los MISMOS bytes (bits residuales
        # alterados vía índice del alfabeto, técnica del generator) →
        # bad_base64 aunque la MAC fuera válida para esa cadena; la
        # canonicalidad precede al MAC (§5.2).
        from base64 import urlsafe_b64decode
        alphabet = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz0123456789-_")
        env = make_capability_envelope()
        ph = env["protected_header_b64"]
        raw = urlsafe_b64decode(ph + "=" * ((-len(ph)) % 4))
        residual = (len(ph) * 6 - len(raw) * 8) % 8
        assert residual in (2, 4)
        alias_char = alphabet[alphabet.index(ph[-1]) ^ ((1 << residual) - 1)]
        env2 = dict(env, protected_header_b64=ph[:-1] + alias_char)
        self.assertEqual(_verify(env2), "contract:bad_base64")

    def test_expirada(self):
        env = make_capability_envelope(exp=NBF + 1)
        self.assertEqual(_verify(env, now=NBF + 3600), "expired")

    def test_aun_no_valida(self):
        env = make_capability_envelope(nbf=NOW + 7200, exp=NOW + 14400)
        self.assertEqual(_verify(env, now=NOW), "not_yet_valid")

    def test_skew_tolerado(self):
        env = make_capability_envelope(exp=NBF + 1)
        view = _verify(env, now=NBF + 1 + 30.0, skew=30.0)
        self.assertFalse(isinstance(view, str))

    def test_exp_menor_igual_nbf_rechazo_contrato(self):
        env = make_capability_envelope(exp=NBF)
        self.assertEqual(_verify(env), "contract:invalid_value")

    def test_key_id_no_activo(self):
        otro = compute_key_id(TEST_SALT, bytes(32))
        env = make_capability_envelope(key_id=otro)
        self.assertEqual(_verify(env), "key_id_mismatch")

    def test_doble_causa_mac_rota_y_expirada_cripto_primero(self):
        # §5.2/§5.6: la MAC precede a la semántica — el diagnóstico de
        # contrato (bad_signature) gana a la vigencia.
        env = make_capability_envelope(exp=NBF + 1)
        env["signature"] = ("A" if env["signature"][0] != "A" else "B") + env["signature"][1:]
        self.assertEqual(_verify(env, now=NBF + 7200), "contract:bad_signature")


class PopTests(unittest.TestCase):
    def setUp(self):
        self.env = make_capability_envelope()
        self.digest = capability_identity_digest(self.env)

    def test_valida(self):
        self.assertIsNone(verify_invocation_proof(
            make_pop(self.digest), TEST_KEY, self.digest, "a1" * 16))

    def test_mac_rota(self):
        pop = make_pop(self.digest)
        pop["mac"] = ("0" if pop["mac"][0] != "0" else "1") + pop["mac"][1:]
        self.assertEqual(verify_invocation_proof(
            pop, TEST_KEY, self.digest, "a1" * 16), "contract:bad_signature")

    def test_digest_de_otra_capacidad(self):
        otro = capability_identity_digest(make_capability_envelope(
            binding=base_binding(stdin_digest="f" * 64)))
        self.assertEqual(verify_invocation_proof(
            make_pop(otro), TEST_KEY, self.digest, "a1" * 16),
            "pop:payload-digest-mismatch")

    def test_nonce_no_ligado_al_descriptor(self):
        self.assertEqual(verify_invocation_proof(
            make_pop(self.digest), TEST_KEY, self.digest, "b2" * 16),
            "pop:nonce-mismatch")


if __name__ == "__main__":
    unittest.main()
