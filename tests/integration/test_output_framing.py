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



class RegresionRondaAdversarialTests(unittest.TestCase):
    """Regresiones de la ronda adversarial 2026-09-09 (H1..H4, H11).

    Cada prueba de esta clase falla contra el código anterior a la corrección.
    """

    def test_h1_coordinador_que_no_confirma_no_bloquea_el_drenaje(self) -> None:
        """D-M2-1(a): si el coordinador deja de consumir, el supervisor SIGUE
        drenando y descarta. Antes se bloqueaba en `credit.acquire()`."""
        import src.adapters.posix_supervisor as mod

        class SordoHost(mod.PosixSupervisorHost):
            def _collect(self, action: object) -> None:  # type: ignore[override]
                source = action.process.stdout  # type: ignore[attr-defined]
                try:
                    while True:
                        frame = mod._read_frame(source)
                        if frame is None:
                            break
                        kind, _, payload = frame
                        if kind == b"T":
                            action.terminal = __import__("json").loads(  # type: ignore[attr-defined]
                                payload.decode("utf-8"))
                            break
                finally:
                    action.done.set()  # type: ignore[attr-defined]

        script = ("import sys\n"
                  "for _ in range(32): sys.stdout.write('x'*65536)\n")
        host = SordoHost()
        ref = host.spawn(plan(script, max_out=1024 * 1024), deadline_eff_ms=60000)
        action = host.await_terminal(ref, timeout=45)
        self.assertIsNotNone(action, "el supervisor no debe quedar bloqueado")
        assert action is not None
        t = action.terminal
        assert t is not None
        self.assertTrue(t["credit_starved"],
                        "debe declarar que degrado a descarte")
        self.assertEqual(t["returncode"], 0, "el hijo debe poder terminar")
        self.assertGreater(t["stdout_discarded_bytes"], 0)

    def test_h2_nieto_que_retiene_pipes_no_cuelga(self) -> None:
        """G-M2-08: toda espera acotada. Antes no llegaba terminal jamas."""
        script = ("import subprocess,sys\n"
                  "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\n"
                  "sys.stdout.write('padre-sale')\n")
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script), deadline_eff_ms=60000)
        action = host.await_terminal(ref, timeout=30)
        self.assertIsNotNone(action, "debe entregar terminal pese al nieto")
        assert action is not None
        t = action.terminal
        assert t is not None
        self.assertTrue(t["forced_pipe_close"],
                        "debe declarar el cierre forzado de pipes")
        self.assertEqual(t["returncode"], 0)

    def test_h4_entrega_incremental_antes_de_que_el_hijo_salga(self) -> None:
        """`read1`, no `read`: antes no llegaba nada hasta EOF."""
        import time
        script = ("import sys,time\n"
                  "sys.stdout.write('temprano');sys.stdout.flush()\n"
                  "time.sleep(4)\n")
        host = PosixSupervisorHost()
        t0 = time.monotonic()
        ref = host.spawn(plan(script), deadline_eff_ms=60000)
        accion = host._actions[ref]
        while time.monotonic() - t0 < 3.0:
            if bytes(accion.stdout):
                break
            time.sleep(0.05)
        transcurrido = time.monotonic() - t0
        self.assertEqual(bytes(accion.stdout), b"temprano")
        self.assertLess(transcurrido, 3.0,
                        "la salida debe llegar antes de que el hijo termine")
        host.await_terminal(ref, timeout=30)

    def test_h11_nunca_mas_de_un_frame_no_confirmado_por_stream(self) -> None:
        """D-M2-1(a)/G-M2-07: la propiedad se MIDE, no se afirma."""
        script = ("import sys\n"
                  "for _ in range(16):\n"
                  "    sys.stdout.write('o'*65536); sys.stderr.write('e'*65536)\n")
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script, max_out=512 * 1024, max_err=512 * 1024),
                         deadline_eff_ms=60000)
        action = host.await_terminal(ref, timeout=45)
        assert action is not None and action.terminal is not None
        t = action.terminal
        self.assertLessEqual(t["max_unacked_stdout"], 1)
        self.assertLessEqual(t["max_unacked_stderr"], 1)
        self.assertGreaterEqual(t["max_unacked_stdout"], 1,
                                "la medicion debe haber observado trafico real")

    def test_h6_el_registro_no_crece_sin_limite(self) -> None:
        host = PosixSupervisorHost()
        for _ in range(3):
            ref = host.spawn(plan("import sys;sys.stdout.write('ok')"),
                             deadline_eff_ms=60000)
            self.assertIsNotNone(host.await_terminal(ref, timeout=30))
        self.assertEqual(host.pending_actions, 0,
                         "entregar el terminal debe soltar el registro")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
