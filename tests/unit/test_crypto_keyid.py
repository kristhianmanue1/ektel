"""Pruebas del perfil criptográfico v1 (§5.2/§6.5) y de key_id (adenda
final regla 1), cruzado con el corpus dorado."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers_m1 import TEST_KEY, TEST_SALT  # noqa: E402
from src.domain.crypto import (  # noqa: E402
    compute_key_id, identity_digest, mac_envelope, mac_pop,
    validate_key_material)

INDEX = json.loads(
    (ROOT / "contracts" / "vectors" / "v1" / "index.json").read_text(encoding="utf-8"))


class CryptoProfileTests(unittest.TestCase):
    def test_key_id_formula_contra_corpus_dorado(self):
        # La sal literal histórica de los vectores (que conservan su sal de
        # prueba por mandato de la adenda final) + TEST_KEY del index →
        # key_id publicado en index.json.
        golden_salt = b"ektel-golden-deployment-salt"
        self.assertEqual(compute_key_id(golden_salt, TEST_KEY), INDEX["key_id"])

    def test_key_id_sal_produccion_32_bytes(self):
        self.assertEqual(len(compute_key_id(TEST_SALT, TEST_KEY)), 16)
        self.assertEqual(compute_key_id(TEST_SALT, TEST_KEY),
                         compute_key_id(TEST_SALT, TEST_KEY).lower())

    def test_validate_material_ok(self):
        key_id = validate_key_material(TEST_KEY, TEST_SALT)
        self.assertEqual(key_id, compute_key_id(TEST_SALT, TEST_KEY))

    def test_validate_key_longitud_fail_closed(self):
        with self.assertRaises(ValueError):
            validate_key_material(TEST_KEY[:-1], TEST_SALT)

    def test_validate_salt_longitud_fail_closed(self):
        with self.assertRaises(ValueError):
            validate_key_material(TEST_KEY, TEST_SALT[:-1])

    def test_mac_dominio_separado(self):
        a = mac_envelope(TEST_KEY, b"ektel/capability/v1", "cGg", "cGw")
        b = mac_envelope(TEST_KEY, b"ektel/admission/v1", "cGg", "cGw")
        self.assertNotEqual(a, b)

    def test_identity_digest_forma(self):
        self.assertEqual(identity_digest("cGg", "cGw"),
                         __import__("hashlib").sha256(b"cGg.cGw").hexdigest())

    def test_pop_ligada_por_longitud(self):
        # len32be evita concatenación ambigua (ADR-003 §1.5): nonces de
        # longitudes distintas con el mismo prefijo no colisionan.
        import struct
        m1 = mac_pop(TEST_KEY, b"ab", b"\x00" * 32)
        m2 = mac_pop(TEST_KEY, b"a", b"b" + b"\x00" * 31)
        self.assertNotEqual(m1, m2)
        self.assertEqual(struct.pack(">I", 2), b"\x00\x00\x00\x02")


if __name__ == "__main__":
    unittest.main()
