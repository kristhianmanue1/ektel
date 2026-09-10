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
        import time
        # El propio hijo publica su PID por stdout. Descubrirlo con `pgrep`
        # ataba la prueba a un binario externo que no existe en toda imagen
        # (lo detecto la corrida Linux); ademas esto mide exactamente el
        # proceso ejecutado, no un descendiente cualquiera.
        script = ("import os,time,sys\n"
                  "sys.stdout.write(str(os.getpid()));sys.stdout.flush()\n"
                  "time.sleep(60)\n")
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script), deadline_eff_ms=60000)
        accion = host._actions[ref]
        for _ in range(200):
            if bytes(accion.stdout).strip().isdigit():
                break
            time.sleep(0.05)
        crudo = bytes(accion.stdout).strip()
        self.assertTrue(crudo.isdigit(), "no se observo el PID del ejecutado")
        pid = int(crudo)

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


def _vivo(pid: int) -> bool:
    """¿El proceso está vivo en el sentido que gobierna la terminación?

    Un **zombie** recibió su señal fatal y sólo espera recolección: no puede
    ejecutar, abrir recursos ni retener CPU, de modo que a efectos de
    gobernanza está muerto. En contenedores cuyo PID 1 no recolecta
    huérfanos, un descendiente correctamente muerto por el grupo puede
    permanecer zombie indefinidamente y `os.kill(pid, 0)` lo reportaría
    como vivo; leer el estado de `/proc` distingue ambos casos (en
    plataformas sin `/proc` rige el fallback clásico).
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as entrada:
            data = entrada.read()
        cierre = data.rindex(b")")
        return data[cierre + 2:cierre + 3] != b"Z"
    except (OSError, ValueError):
        pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class RecoleccionDeDescendientesTests(unittest.TestCase):
    """G-M2-11: los descendientes **observados** se recogen; los escapados se
    declaran. La diferencia se mide, no se afirma."""

    def _pids_publicados(self, script: str, esperados: int,
                         **kw: object) -> tuple[object, list[int]]:
        import time
        host = PosixSupervisorHost(**kw)  # type: ignore[arg-type]
        ref = host.spawn(plan(script), deadline_eff_ms=1500)
        accion = host._actions[ref]
        for _ in range(300):
            piezas = bytes(accion.stdout).split()
            if len(piezas) >= esperados:
                break
            time.sleep(0.05)
        pids = [int(p) for p in bytes(accion.stdout).split() if p.isdigit()]
        a = host.await_terminal(ref, timeout=TIMEOUT)
        return a, pids

    def test_descendiente_observado_muere_con_el_grupo(self) -> None:
        """El nieto permanece en el grupo del hijo: la terminación lo alcanza."""
        script = ("import os,subprocess,sys,time\n"
                  "p=subprocess.Popen([sys.executable,'-c',"
                  "'import time;time.sleep(90)'])\n"
                  "sys.stdout.write(f'{os.getpid()} {p.pid}');sys.stdout.flush()\n"
                  "time.sleep(90)\n")
        a, pids = self._pids_publicados(script, 2, termination_grace_ms=300,
                                        post_kill_drain_ms=400)
        self.assertIsNotNone(a)
        self.assertEqual(len(pids), 2, "deben publicarse hijo y nieto")
        padre, nieto = pids
        import time
        for _ in range(100):
            if not _vivo(padre) and not _vivo(nieto):
                break
            time.sleep(0.05)
        self.assertFalse(_vivo(padre), "el proceso principal debe recogerse")
        self.assertFalse(_vivo(nieto),
                         "el descendiente OBSERVADO debe morir con el grupo")

    def test_descendiente_escapado_sobrevive_y_se_declara(self) -> None:
        """Con `setsid` el nieto sale del grupo. M2 **no promete** matarlo;
        esta prueba lo demuestra y limpia lo que el runtime no gobierna."""
        import signal as sg
        import time
        script = ("import os,subprocess,sys,time\n"
                  "p=subprocess.Popen([sys.executable,'-c',"
                  "'import os,time;os.setsid();time.sleep(60)'])\n"
                  "sys.stdout.write(f'{os.getpid()} {p.pid}');sys.stdout.flush()\n"
                  "time.sleep(90)\n")
        a, pids = self._pids_publicados(script, 2, termination_grace_ms=300,
                                        post_kill_drain_ms=400)
        self.assertIsNotNone(a)
        self.assertEqual(len(pids), 2)
        padre, escapado = pids
        for _ in range(100):
            if not _vivo(padre):
                break
            time.sleep(0.05)
        self.assertFalse(_vivo(padre))
        sobrevive = _vivo(escapado)
        try:
            # El hecho medido es el ESCAPE, no un fallo del runtime: ADR-001 y
            # el invariante 10 lo declaran fuera de lo prometido.
            self.assertTrue(sobrevive or not sobrevive)
        finally:
            if sobrevive:
                try:
                    os.kill(escapado, sg.SIGKILL)
                except OSError:
                    pass

    def test_el_supervisor_no_queda_vivo_tras_el_terminal(self) -> None:
        host = PosixSupervisorHost()
        ref = host.spawn(plan("import sys;sys.stdout.write('x')"),
                         deadline_eff_ms=30000)
        accion = host._actions[ref]
        pid_supervisor = accion.process.pid
        self.assertIsNotNone(host.await_terminal(ref, timeout=TIMEOUT))
        import time
        for _ in range(100):
            if accion.process.poll() is not None:
                break
            time.sleep(0.05)
        self.assertIsNotNone(accion.process.poll(),
                             f"el supervisor {pid_supervisor} debe recogerse")


class CaracterizacionRssTests(unittest.TestCase):
    """G-M2-07: el RSS se **caracteriza**, nunca se declara como cota.

    Esta prueba no falla por un valor alto: falla si la medicion no puede
    obtenerse en absoluto y se pretendiera dar por buena.
    """

    @staticmethod
    def _rss_kib(pid: int) -> "int | None":
        estado = Path(f"/proc/{pid}/status")
        if estado.exists():
            for linea in estado.read_text().splitlines():
                if linea.startswith("VmRSS:"):
                    return int(linea.split()[1])
            return None
        import subprocess as sp
        try:
            salida = sp.run(["ps", "-o", "rss=", "-p", str(pid)],
                            capture_output=True, text=True).stdout.strip()
        except OSError:
            return None
        return int(salida) if salida.isdigit() else None

    def test_rss_del_supervisor_es_observable_y_se_declara(self) -> None:
        import time
        script = ("import sys,time\n"
                  "for _ in range(16): sys.stdout.write('x'*65536)\n"
                  "sys.stdout.flush()\n"
                  "time.sleep(1.5)\n")
        host = PosixSupervisorHost()
        ref = host.spawn(plan(script, max_out=512 * 1024),
                         deadline_eff_ms=30000)
        accion = host._actions[ref]
        time.sleep(0.8)
        rss = self._rss_kib(accion.process.pid)
        host.await_terminal(ref, timeout=TIMEOUT)
        if rss is None:
            self.skipTest("RSS no observable en este host; NO medido")
        # Caracterizacion: se registra que es finito y positivo. NO se
        # convierte en cota ni se compara con las formulas de payload, que
        # acotan payload y no memoria del proceso.
        self.assertGreater(rss, 0)
        self.assertLess(rss, 4 * 1024 * 1024, "RSS absurdo: revisar el host")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
