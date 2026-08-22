"""Pruebas de representabilidad D-P3 ampliada (adenda R1 regla 2) +
regla 4 final (os.fsencode)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers_m1 import make_request  # noqa: E402
from src.domain.representability import (  # noqa: E402
    RepresentabilityError, check_execve_strings)


class RepresentabilityTests(unittest.TestCase):
    def _doc(self, **overrides):
        return make_request(**overrides)

    def test_valido_ok(self):
        check_execve_strings(self._doc())  # no raises

    def test_nul_en_command(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(command_absolute="/bin/tru\x00e"))
        self.assertEqual(ctx.exception.detail, "command_absolute:nul")

    def test_nul_en_cwd(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(cwd="/tm\x00p"))
        self.assertEqual(ctx.exception.detail, "cwd:nul")

    def test_nul_en_arg(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(args=["--o\x00ut"]))
        self.assertEqual(ctx.exception.detail, "args[0]:nul")

    def test_nul_en_env_valor(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(env_allowlist_values={"PATH": "/a\x00b"}))
        self.assertEqual(ctx.exception.detail, "env.value:nul")

    def test_env_nombre_vacio(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(env_allowlist_values={"": "/bin"}))
        self.assertEqual(ctx.exception.detail, "env:name-empty")

    def test_env_nombre_con_igual(self):
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(env_allowlist_values={"A=B": "1"}))
        self.assertEqual(ctx.exception.detail, "env:name-equals")

    def test_surrogate_no_representable(self):
        # JSON puede transportar surrogates escapados; el filesystem no
        # puede representarlos (regla 4 final).
        with self.assertRaises(RepresentabilityError) as ctx:
            check_execve_strings(self._doc(command_absolute="/bin/\ud800true"))
        self.assertEqual(ctx.exception.detail, "command_absolute:not-fsencodable")

    def test_tab_y_u0085_permitidos(self):
        # Límite consciente documentado (orden del dueño): TAB y U+0085
        # permanecen admitidos mientras no haya evidencia para prohibirlos.
        check_execve_strings(self._doc(
            args=["--ta\tb", "--ne\u0085xt"],
            env_allowlist_values={"A": " ", "B": "val\u0085or"}))


if __name__ == "__main__":
    unittest.main()
