"""G-M2-11 y G-M2-13 — caracterización del supervisor por plataforma.

Mide lo que **esta** plataforma hace realmente. Un skip o una degradación no
se convierte en verde equivalente: se declara.

Lo que se declara aquí y NO se promete:

- el grupo de procesos propio es **contención de terminación, no
  aislamiento**;
- `PR_SET_CHILD_SUBREAPER` es Linux-only; en Darwin la contabilidad
  multi-nivel es `unsupported` y **no hay mitigación conocida**;
- la recolección de descendientes **escapados** (`setsid`, double-fork) no se
  promete: se declara como escape conocido.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters import platform_caps  # noqa: E402
from src.adapters.posix_supervisor import PosixSupervisorHost  # noqa: E402
from src.domain.start_request import ExecutionPlan  # noqa: E402

IS_LINUX = sys.platform.startswith("linux")
TIMEOUT = 60.0


def plan(script: str, *, max_out: int = 65536) -> ExecutionPlan:
    return ExecutionPlan(
        identity_digest="d" * 64, action_id="a", issuer_id="i", exp_wall=0,
        command_absolute=sys.executable, args=("-c", script), cwd="/tmp",
        env=ExecutionPlan.freeze_env({"PATH": "/usr/bin:/bin"}),
        stdin_bytes=b"", deadline_ms=60000,
        max_stdout_bytes=max_out, max_stderr_bytes=4096)


def run(p: ExecutionPlan, *, subreaper: bool = True) -> object:
    host = PosixSupervisorHost(subreaper_requested=subreaper)
    ref = host.spawn(p, deadline_eff_ms=60000)
    return host.await_terminal(ref, timeout=TIMEOUT)


class GrupoDeProcesosTests(unittest.TestCase):
    def test_el_hijo_tiene_grupo_propio(self) -> None:
        """D-M2-2(a): grupo propio, creado con `process_group=0` y sin
        `preexec_fn`."""
        script = "import os,sys;sys.stdout.write(f'{os.getpid()} {os.getpgid(0)}')"
        a = run(plan(script))
        assert a is not None
        pid_s, pgid_s = bytes(a.stdout).decode().split()  # type: ignore[attr-defined]
        self.assertEqual(pid_s, pgid_s,
                         "el hijo debe ser lider de su propio grupo")

    def test_el_supervisor_no_esta_en_el_grupo_del_hijo(self) -> None:
        script = "import os,sys;sys.stdout.write(str(os.getpgid(0)))"
        a = run(plan(script))
        assert a is not None
        pgid_hijo = int(bytes(a.stdout).decode())  # type: ignore[attr-defined]
        self.assertNotEqual(pgid_hijo, os.getpgid(0),
                            "el supervisor queda fuera del grupo del hijo")

    def test_el_grupo_es_contencion_no_aislamiento(self) -> None:
        """El hijo sigue viendo el filesystem: M2 no hace sandboxing."""
        script = ("import os,sys;"
                  "sys.stdout.write('1' if os.path.exists('/tmp') else '0')")
        a = run(plan(script))
        assert a is not None
        self.assertEqual(bytes(a.stdout), b"1")  # type: ignore[attr-defined]


class SubreaperTests(unittest.TestCase):
    def test_capacidades_declaradas_coinciden_con_la_plataforma(self) -> None:
        caps = platform_caps.detect()
        self.assertEqual(caps.subreaper_available, IS_LINUX)
        self.assertEqual(caps.declares_multilevel, IS_LINUX)

    def test_subreaper_aplicado_solo_donde_esta_disponible(self) -> None:
        a = run(plan("import sys;sys.stdout.write('ok')"), subreaper=True)
        assert a is not None
        t = a.terminal  # type: ignore[attr-defined]
        self.assertEqual(t["subreaper_requested"], IS_LINUX)
        self.assertEqual(t["subreaper_applied"], IS_LINUX)

    def test_no_solicitarlo_nunca_lo_aplica(self) -> None:
        a = run(plan("import sys;sys.stdout.write('ok')"), subreaper=False)
        assert a is not None
        t = a.terminal  # type: ignore[attr-defined]
        self.assertFalse(t["subreaper_requested"])
        self.assertFalse(t["subreaper_applied"])

    @unittest.skipIf(IS_LINUX, "Darwin-only: declara la ausencia de garantia")
    def test_darwin_declara_multinivel_unsupported(self) -> None:
        caps = platform_caps.detect()
        self.assertEqual(caps.multilevel_accounting,
                         platform_caps.MULTILEVEL_UNSUPPORTED)
        self.assertFalse(platform_caps.set_child_subreaper(),
                         "no hay mitigacion conocida en Darwin")

    @unittest.skipUnless(IS_LINUX, "Linux-only: PR_SET_CHILD_SUBREAPER")
    def test_linux_activa_subreaper_realmente(self) -> None:
        self.assertTrue(platform_caps.set_child_subreaper())


class EscapesDeclaradosTests(unittest.TestCase):
    """Los escapes se **declaran**, no se mitigan (invariante 10, G-M2-08)."""

    def test_descendiente_en_el_grupo_se_observa(self) -> None:
        script = (
            "import subprocess,sys,os\n"
            "c=subprocess.run([sys.executable,'-c',"
            "\"import os,sys;sys.stdout.write(str(os.getpgid(0)))\"],"
            "capture_output=True)\n"
            "sys.stdout.write(c.stdout.decode()+' '+str(os.getpgid(0)))\n")
        a = run(plan(script))
        assert a is not None
        nieto_pgid, hijo_pgid = bytes(a.stdout).decode().split()  # type: ignore[attr-defined]
        self.assertEqual(nieto_pgid, hijo_pgid,
                         "un descendiente normal hereda el grupo del hijo")

    def test_setsid_escapa_del_grupo_y_se_declara(self) -> None:
        """`setsid` saca al descendiente del grupo observado. M2 NO promete
        protección universal frente a esto; lo declara."""
        script = (
            "import subprocess,sys,os\n"
            "c=subprocess.run([sys.executable,'-c',"
            "\"import os,sys;os.setsid();sys.stdout.write(str(os.getpgid(0)))\"],"
            "capture_output=True)\n"
            "sys.stdout.write(c.stdout.decode()+' '+str(os.getpgid(0)))\n")
        a = run(plan(script))
        assert a is not None
        salida = bytes(a.stdout).decode().split()  # type: ignore[attr-defined]
        if len(salida) == 2:
            escapado, hijo = salida
            self.assertNotEqual(escapado, hijo,
                                "setsid crea sesion y grupo nuevos: es un escape")
        else:  # pragma: no cover - depende del host
            self.skipTest("setsid no observable en este host; escape declarado")



class RegresionH3TerminacionDelGrupoTests(unittest.TestCase):
    """H3 de la ronda adversarial: `request_termination` debe terminar el
    GRUPO del proceso ejecutado, no al supervisor. Antes lo dejaba huerfano."""

    def test_request_termination_no_deja_al_hijo_huerfano(self) -> None:
        import subprocess as sp
        import time
        script = "import time,sys\nsys.stdout.write('vivo');sys.stdout.flush()\ntime.sleep(60)\n"
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script), deadline_eff_ms=60000)
        # Esperar a que exista el proceso ejecutado.
        accion = host._actions[ref]
        hijos: list[str] = []
        for _ in range(100):
            hijos = sp.run(["pgrep", "-P", str(accion.process.pid)],
                           capture_output=True, text=True).stdout.split()
            if hijos:
                break
            time.sleep(0.05)
        self.assertTrue(hijos, "no se observo el proceso ejecutado")
        pid = int(hijos[0])

        host.request_termination(ref)

        def vivo(p: int) -> bool:
            try:
                os.kill(p, 0)
                return True
            except OSError:
                return False

        for _ in range(100):
            if not vivo(pid):
                break
            time.sleep(0.05)
        self.assertFalse(vivo(pid),
                         "el proceso ejecutado quedo huerfano y vivo")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
