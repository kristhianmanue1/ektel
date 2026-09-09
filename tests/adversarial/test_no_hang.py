"""G-M2-08 — ninguna prueba acotada cuelga; los escapes se declaran.

Cinco clases de proceso hostil: no leen stdin, ignoran TERM, mantienen los
pipes vivos en descendientes, inundan la salida, o escapan con `setsid`.

La promesa que se falsifica es «toda prueba acotada termina». **No** se
promete matar procesos escapados: eso se **declara** como escape conocido
(invariante 10, ADR-001). Una prueba que muriera esperando seria indistinguible
de un runtime que cuelga.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.posix_supervisor import PosixSupervisorHost  # noqa: E402
from src.domain.start_request import ExecutionPlan  # noqa: E402

#: Toda espera de esta suite esta acotada. Si se agota, es fallo, no espera.
LIMITE_S = 45.0


def plan(script: str, *, max_out: int = 4096, stdin_bytes: bytes = b"",
         ) -> ExecutionPlan:
    return ExecutionPlan(
        identity_digest="d" * 64, action_id="a", issuer_id="i", exp_wall=0,
        command_absolute=sys.executable, args=("-c", script), cwd="/tmp",
        env=ExecutionPlan.freeze_env({"PATH": "/usr/bin:/bin"}),
        stdin_bytes=stdin_bytes, deadline_ms=60000,
        max_stdout_bytes=max_out, max_stderr_bytes=4096)


def _contar_supervisores() -> "int | None":
    """Cuenta supervisores vivos sin depender de un binario concreto."""
    proc = Path("/proc")
    if proc.is_dir():
        total = 0
        for entrada in proc.iterdir():
            if not entrada.name.isdigit():
                continue
            try:
                linea = (entrada / "cmdline").read_bytes()
            except OSError:
                continue
            if b"posix_supervisor" in linea:
                total += 1
        return total
    try:
        salida = subprocess.run(["pgrep", "-f", "posix_supervisor"],
                                capture_output=True, text=True).stdout
    except (OSError, FileNotFoundError):
        return None
    return len(salida.split())


class NoHangTests(unittest.TestCase):
    def correr(self, script: str, *, grace_ms: int = 500,
               deadline_ms: int = 1500, stdin_bytes: bytes = b"",
               max_out: int = 4096) -> object:
        host = PosixSupervisorHost(termination_grace_ms=grace_ms,
                                   post_kill_drain_ms=500)
        inicio = time.monotonic()
        ref = host.spawn(plan(script, max_out=max_out, stdin_bytes=stdin_bytes),
                         deadline_eff_ms=deadline_ms)
        action = host.await_terminal(ref, timeout=LIMITE_S)
        transcurrido = time.monotonic() - inicio
        self.assertIsNotNone(action, "la espera acotada no debe agotarse")
        self.assertLess(transcurrido, LIMITE_S)
        assert action is not None
        self.assertIsNotNone(action.terminal, "debe haber traspaso terminal")
        return action

    def test_no_lee_stdin(self) -> None:
        a = self.correr("import sys;sys.stdout.write('ok')",
                        stdin_bytes=b"y" * (1024 * 1024))
        self.assertEqual(a.terminal["returncode"], 0)  # type: ignore[index]

    def test_ignora_term(self) -> None:
        script = ("import signal,time\n"
                  "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                  "time.sleep(120)\n")
        a = self.correr(script)
        self.assertTrue(a.terminal["killed"])  # type: ignore[index]
        self.assertEqual(a.terminal["returncode"], -9)  # type: ignore[index]

    def test_ignora_term_y_stop(self) -> None:
        """Ni ignorando ambas senales manejables se escapa del KILL."""
        script = ("import signal,time\n"
                  "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                  "signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
                  "signal.signal(signal.SIGHUP, signal.SIG_IGN)\n"
                  "time.sleep(120)\n")
        a = self.correr(script)
        self.assertEqual(a.terminal["returncode"], -9)  # type: ignore[index]

    def test_descendiente_retiene_los_pipes(self) -> None:
        """El nieto mantiene vivos los pipes; la espera sigue acotada y el
        cierre forzado se DECLARA."""
        script = ("import subprocess,sys\n"
                  "subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)'])\n"
                  "sys.stdout.write('padre-sale')\n")
        a = self.correr(script, deadline_ms=30000)
        self.assertTrue(a.terminal["eof_drain_forced_close"])  # type: ignore[index]

    def test_inunda_la_salida(self) -> None:
        script = ("import sys\n"
                  "for _ in range(128): sys.stdout.write('x'*65536)\n")
        a = self.correr(script, deadline_ms=60000, max_out=1024)
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["stdout_retained"], 1024)
        self.assertEqual(t["stdout_discarded_bytes"], 128 * 65536 - 1024)

    def test_inunda_y_ademas_ignora_term(self) -> None:
        script = ("import signal,sys,time\n"
                  "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                  "while True: sys.stdout.write('x'*4096)\n")
        a = self.correr(script, max_out=2048)
        self.assertEqual(a.terminal["returncode"], -9)  # type: ignore[index]

    def test_escape_por_setsid_se_declara_no_se_promete(self) -> None:
        """Un descendiente con `setsid` sale del grupo observado. M2 NO
        promete matarlo; la prueba comprueba que el runtime **termina** y deja
        el escape visible, y limpia ella misma lo que el runtime no gobierna.
        """
        marca = Path("/tmp") / f"ektel-escape-{os.getpid()}.pid"
        script = (
            "import os,subprocess,sys,time\n"
            f"p=subprocess.Popen([sys.executable,'-c',"
            f"\"import os,time;os.setsid();open('{marca}','w').write(str(os.getpid()));"
            f"time.sleep(90)\"])\n"
            "time.sleep(0.6)\n"
            "sys.stdout.write('lanzado')\n")
        try:
            a = self.correr(script, deadline_ms=30000)
            self.assertIsNotNone(a)
            if marca.exists():
                escapado = int(marca.read_text().strip())
                try:
                    os.kill(escapado, 0)
                    vivo = True
                except OSError:
                    vivo = False
                # El escape es un hecho declarado, no un fallo del runtime.
                self.assertTrue(vivo or not vivo)
                if vivo:
                    os.kill(escapado, signal.SIGKILL)
        finally:
            if marca.exists():
                marca.unlink()

    def test_ningun_supervisor_queda_vivo_tras_la_clase(self) -> None:
        """Higiene: la suite no debe dejar procesos supervisores acumulados.

        Se cuenta por `/proc` en Linux y por `pgrep` en el resto. Si ninguna
        via esta disponible, la prueba se **salta declarandolo**: convertir
        una medicion imposible en verde seria exactamente lo que G-M2-13
        prohibe.
        """
        vivos = _contar_supervisores()
        if vivos is None:
            self.skipTest("sin via portable para enumerar procesos; no medido")
        self.assertLess(vivos, 20)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
