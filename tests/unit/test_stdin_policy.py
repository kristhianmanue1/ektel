"""Pruebas de las reglas puras de stdin_policy (D-P1 ampliada, adenda R1
regla 1; H6 del acta de corrección M0 §13)."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers_m1 import _b64u  # noqa: E402
from src.domain.stdin_policy import EMPTY_SHA256, effective_stdin  # noqa: E402

EMPTY = hashlib.sha256(b"").hexdigest()


class StdinPolicyTests(unittest.TestCase):
    def test_empty_minimal_ok(self):
        data, digest = effective_stdin({"kind": "empty"})
        self.assertEqual(data, b"")
        self.assertEqual(digest, EMPTY)
        self.assertEqual(digest, EMPTY_SHA256)

    def test_empty_con_sha256_correcto_ok(self):
        # Coherente con el vector dorado areq-valid-01 (empty + sha256(b"")).
        _, digest = effective_stdin({"kind": "empty", "sha256": EMPTY})
        self.assertEqual(digest, EMPTY)

    def test_empty_con_data_b64_malformed(self):
        self.assertEqual(effective_stdin(
            {"kind": "empty", "data_b64": _b64u(b"x")}),
            "stdin_policy:empty-with-data")

    def test_empty_con_sha256_discordante_malformed(self):
        self.assertEqual(effective_stdin(
            {"kind": "empty", "sha256": "0" * 64}),
            "stdin_policy:empty-sha256-mismatch")

    def test_inline_sin_data_malformed(self):
        self.assertEqual(effective_stdin({"kind": "inline_b64"}),
                         "stdin_policy:inline-missing-fields")

    def test_inline_sin_sha256_malformed(self):
        self.assertEqual(effective_stdin(
            {"kind": "inline_b64", "data_b64": _b64u(b"hola")}),
            "stdin_policy:inline-missing-fields")

    def test_inline_coherente_ok(self):
        payload = "contenido de stdin de prueba"
        data, digest = effective_stdin(
            {"kind": "inline_b64", "data_b64": _b64u(payload.encode()),
             "sha256": hashlib.sha256(payload.encode()).hexdigest()})
        self.assertEqual(data, payload.encode())
        self.assertEqual(digest, hashlib.sha256(payload.encode()).hexdigest())

    def test_inline_sha256_discordante_malformed(self):
        self.assertEqual(effective_stdin(
            {"kind": "inline_b64", "data_b64": _b64u(b"hola"),
             "sha256": EMPTY}),
            "stdin_policy:inline-sha256-mismatch")

    def test_inline_no_canonico_malformed(self):
        # Alias no canónico de los MISMOS bytes (b"\xff" → "_w"; "_x"
        # decodifica igual con bits residuales alterados, ADR-010):
        # defensa en profundidad de la capa de admisión.
        data = b"\xff"
        canonical, alias = "_w", "_x"
        assert __import__("base64").urlsafe_b64decode(
            alias + "==") == data == __import__("base64").urlsafe_b64decode(
            canonical + "==")
        self.assertEqual(effective_stdin(
            {"kind": "inline_b64", "data_b64": alias,
             "sha256": hashlib.sha256(data).hexdigest()}),
            "stdin_policy:data-b64-noncanonical")

    def test_kind_invalido_malformed(self):
        self.assertEqual(effective_stdin({"kind": "tty"}),
                         "stdin_policy:kind-invalid")

    def test_no_dict_malformed(self):
        self.assertEqual(effective_stdin(["kind"]), "stdin_policy:no-dict")


if __name__ == "__main__":
    unittest.main()
