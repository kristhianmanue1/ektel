"""Pruebas del adaptador de carga de clave del operador (adenda R1 regla 3
+ regla 3 final: O_NOFOLLOW/fstat/regular/owner/0600/32B/EOF)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.operator_key import (  # noqa: E402
    KEY_LEN, OperatorKeyError, load_operator_key)

KEY = bytes(range(32))


def _write_key(tmpdir: str, data: bytes = KEY, mode: int = 0o600) -> Path:
    path = Path(tmpdir) / "operator.key"
    path.write_bytes(data)
    os.chmod(path, mode)
    return path


class OperatorKeyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_carga_valida(self):
        path = _write_key(self._tmp.name)
        self.assertEqual(load_operator_key(path), KEY)

    def test_tamano_menor(self):
        path = _write_key(self._tmp.name, KEY[:-1])
        with self.assertRaises(OperatorKeyError) as ctx:
            load_operator_key(path)
        self.assertIn("length", str(ctx.exception))

    def test_tamano_mayor_sin_eof(self):
        path = _write_key(self._tmp.name, KEY + b"x")
        with self.assertRaises(OperatorKeyError) as ctx:
            load_operator_key(path)
        self.assertIn("length", str(ctx.exception))

    def test_modo_incorrecto(self):
        path = _write_key(self._tmp.name, mode=0o644)
        with self.assertRaises(OperatorKeyError) as ctx:
            load_operator_key(path)
        self.assertIn("mode", str(ctx.exception))

    def test_symlink_rechazado(self):
        path = _write_key(self._tmp.name)
        link = Path(self._tmp.name) / "link.key"
        link.symlink_to(path)
        with self.assertRaises(OperatorKeyError):
            load_operator_key(link)

    def test_ausente(self):
        with self.assertRaises(OperatorKeyError):
            load_operator_key(Path(self._tmp.name) / "no-existe.key")

    def test_directorio_rechazado(self):
        with self.assertRaises(OperatorKeyError):
            load_operator_key(Path(self._tmp.name))

    def test_key_len_constante(self):
        self.assertEqual(KEY_LEN, 32)


if __name__ == "__main__":
    unittest.main()
