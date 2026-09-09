"""G-M2-07 — salida acotada, framing y contadores (D-M2-1(a)).

Falsifica: que el prefijo retenido no sea exacto, que las banderas de
truncamiento o los contadores mientan, que un frame supere 64 KiB, o que un
hijo que inunda la salida bloquee al supervisor.

Las partes de `post_kill_forced_pipe_close` pertenecen a INC-M2-4, donde
existe la terminación graduada; aquí no se simulan como verdes.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.posix_supervisor import (  # noqa: E402
    FRAME_MAX_BYTES, PosixSupervisorHost)
from src.domain.start_request import ExecutionPlan  # noqa: E402

TIMEOUT = 60.0


def plan(script: str, *, max_out: int = 4096, max_err: int = 4096,
         stdin_bytes: bytes = b"") -> ExecutionPlan:
    return ExecutionPlan(
        identity_digest="d" * 64, action_id="a", issuer_id="i", exp_wall=0,
        command_absolute=sys.executable, args=("-c", script), cwd="/tmp",
        env=ExecutionPlan.freeze_env({"PATH": "/usr/bin:/bin"}),
        stdin_bytes=stdin_bytes, deadline_ms=60000,
        max_stdout_bytes=max_out, max_stderr_bytes=max_err)


class SupervisorCase(unittest.TestCase):
    def run_plan(self, p: ExecutionPlan) -> object:
        host = PosixSupervisorHost()
        ref = host.spawn(p, deadline_eff_ms=60000)
        action = host.await_terminal(ref, timeout=TIMEOUT)
        self.assertIsNotNone(action, "el supervisor debe entregar terminal")
        return action


class CapturaExactaTests(SupervisorCase):
    def test_salida_por_debajo_del_limite_se_conserva_entera(self) -> None:
        a = self.run_plan(plan("import sys;sys.stdout.write('x'*100)"))
        self.assertEqual(bytes(a.stdout), b"x" * 100)  # type: ignore[attr-defined]
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 100)
        self.assertEqual(t["stdout_discarded_bytes"], 0)
        self.assertFalse(t["stdout_truncation"])

    def test_prefijo_exacto_al_truncar(self) -> None:
        script = "import sys;sys.stdout.write('a'*500 + 'b'*500)"
        a = self.run_plan(plan(script, max_out=500))
        self.assertEqual(bytes(a.stdout), b"a" * 500)  # type: ignore[attr-defined]
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 500)
        self.assertEqual(t["stdout_discarded_bytes"], 500)
        self.assertTrue(t["stdout_truncation"])

    def test_limite_cero_no_retiene_nada_pero_cuenta(self) -> None:
        a = self.run_plan(plan("import sys;sys.stdout.write('z'*300)", max_out=0))
        self.assertEqual(bytes(a.stdout), b"")  # type: ignore[attr-defined]
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 0)
        self.assertEqual(t["stdout_discarded_bytes"], 300)
        self.assertTrue(t["stdout_truncation"])

    def test_streams_independientes(self) -> None:
        script = ("import sys;sys.stdout.write('o'*300);"
                  "sys.stderr.write('e'*900)")
        a = self.run_plan(plan(script, max_out=1000, max_err=100))
        self.assertEqual(bytes(a.stdout), b"o" * 300)  # type: ignore[attr-defined]
        self.assertEqual(bytes(a.stderr), b"e" * 100)  # type: ignore[attr-defined]
        t = a.terminal  # type: ignore[attr-defined]
        self.assertFalse(t["stdout_truncation"])
        self.assertTrue(t["stderr_truncation"])
        self.assertEqual(t["stdout_discarded_bytes"], 0)
        self.assertEqual(t["stderr_discarded_bytes"], 800)

    def test_discarded_bytes_es_la_suma_exacta(self) -> None:
        script = ("import sys;sys.stdout.write('o'*700);"
                  "sys.stderr.write('e'*400)")
        a = self.run_plan(plan(script, max_out=200, max_err=100))
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_discarded_bytes"], 500)
        self.assertEqual(t["stderr_discarded_bytes"], 300)
        self.assertEqual(t["discarded_bytes"], 800)

    def test_multibyte_se_trunca_por_bytes_no_por_caracteres(self) -> None:
        """El contrato acota BYTES; un corte a mitad de carácter es posible y
        no se disimula recomponiendo texto."""
        script = "import sys;sys.stdout.buffer.write('ñ'.encode()*10)"
        a = self.run_plan(plan(script, max_out=5))
        self.assertEqual(len(bytes(a.stdout)), 5)  # type: ignore[attr-defined]
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_discarded_bytes"], 15)


class FramingTests(SupervisorCase):
    def test_ningun_frame_supera_64_kib(self) -> None:
        script = "import sys;sys.stdout.write('x'*(1024*1024))"
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script, max_out=512 * 1024), deadline_eff_ms=60000)
        a = host.await_terminal(ref, timeout=TIMEOUT)
        assert a is not None
        self.assertLessEqual(a.max_frame_seen, FRAME_MAX_BYTES)
        self.assertEqual(len(bytes(a.stdout)), 512 * 1024)

    def test_flood_no_bloquea_al_supervisor(self) -> None:
        """Sigue drenando tras truncar: el hijo nunca queda bloqueado
        escribiendo en un pipe lleno (G-M2-08, parte de drenaje)."""
        script = ("import sys\n"
                  "for _ in range(64): sys.stdout.write('x'*65536)\n")
        a = self.run_plan(plan(script, max_out=1024))
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 1024)
        self.assertEqual(t["stdout_discarded_bytes"], 64 * 65536 - 1024)
        self.assertEqual(t["returncode"], 0)

    def test_flood_en_ambos_streams(self) -> None:
        script = ("import sys\n"
                  "for _ in range(16):\n"
                  "    sys.stdout.write('o'*65536); sys.stderr.write('e'*65536)\n")
        a = self.run_plan(plan(script, max_out=2048, max_err=2048))
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 2048)
        self.assertEqual(t["stderr_retained"], 2048)
        self.assertEqual(t["returncode"], 0)


class StdinTests(SupervisorCase):
    def test_stdin_acotado_llega_al_hijo(self) -> None:
        script = ("import sys;data=sys.stdin.buffer.read();"
                  "sys.stdout.write(str(len(data)))")
        a = self.run_plan(plan(script, stdin_bytes=b"hola mundo"))
        self.assertEqual(bytes(a.stdout), b"10")  # type: ignore[attr-defined]

    def test_hijo_que_no_lee_stdin_no_cuelga(self) -> None:
        """G-M2-08: toda prueba acotada termina."""
        a = self.run_plan(plan("import sys;sys.stdout.write('ok')",
                               stdin_bytes=b"y" * (1024 * 1024)))
        self.assertEqual(bytes(a.stdout), b"ok")  # type: ignore[attr-defined]
        self.assertEqual(a.terminal["returncode"], 0)  # type: ignore[index]


class SalidaDelProcesoTests(SupervisorCase):
    def test_codigo_de_salida_se_reporta_sin_interpretarlo(self) -> None:
        """`executed` significa salida natural, NO exito (invariante 9)."""
        a = self.run_plan(plan("raise SystemExit(7)"))
        self.assertEqual(a.terminal["returncode"], 7)  # type: ignore[index]

    def test_senal_se_refleja_como_returncode_negativo(self) -> None:
        script = "import os,signal;os.kill(os.getpid(), signal.SIGKILL)"
        a = self.run_plan(plan(script))
        self.assertLess(a.terminal["returncode"], 0)  # type: ignore[index,operator]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
