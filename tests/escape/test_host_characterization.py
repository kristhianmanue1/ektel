"""Caracterización segura de primitivas POSIX usadas por el diseño de ektel."""

from __future__ import annotations

import os
import platform
import resource
import select
import signal
import subprocess
import sys
import time
import unittest


PYTHON = sys.executable
SYSTEM = platform.system()


def _cpu_seconds(usage: resource.struct_rusage) -> float:
    return usage.ru_utime + usage.ru_stime


class HostCharacterizationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX-only characterization")
    def test_rusage_children_is_post_mortem(self) -> None:
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        child = subprocess.Popen([PYTHON, "-c", "x=0\nwhile True:x+=1"])
        try:
            time.sleep(0.75)
            live = resource.getrusage(resource.RUSAGE_CHILDREN)
        finally:
            child.kill()
            child.wait()
        after = resource.getrusage(resource.RUSAGE_CHILDREN)

        live_delta = _cpu_seconds(live) - _cpu_seconds(before)
        reaped_delta = _cpu_seconds(after) - _cpu_seconds(before)
        self.assertLess(live_delta, 0.05)
        self.assertGreater(reaped_delta, 0.25)

    @unittest.skipUnless(SYSTEM in {"Darwin", "Linux"}, "Darwin/Linux only")
    def test_rlimit_as_platform_semantics(self) -> None:
        code = """
import resource
try:
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024,) * 2)
except (OSError, ValueError):
    print("rejected")
else:
    print("accepted")
"""
        result = subprocess.run(
            [PYTHON, "-c", code],
            check=True,
            capture_output=True,
            text=True,
        )
        observed = result.stdout.strip()
        expected = "rejected" if SYSTEM == "Darwin" else "accepted"
        self.assertEqual(observed, expected)

    @unittest.skipUnless(SYSTEM in {"Darwin", "Linux"}, "Darwin/Linux only")
    def test_ignored_sigxcpu_platform_semantics(self) -> None:
        code = """
import resource
import signal
resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
signal.signal(signal.SIGXCPU, signal.SIG_IGN)
x = 0
while True:
    x += 1
"""
        child = subprocess.Popen([PYTHON, "-c", code])
        deadline = time.monotonic() + 4.0
        reaped = None
        while time.monotonic() < deadline:
            waited_pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if waited_pid:
                reaped = (status, usage)
                break
            time.sleep(0.05)

        survived = reaped is None
        if survived:
            child.kill()
            _, status, usage = os.wait4(child.pid, 0)
        else:
            status, usage = reaped
        child.returncode = os.waitstatus_to_exitcode(status)
        consumed = _cpu_seconds(usage)

        if SYSTEM == "Darwin":
            self.assertTrue(survived)
            self.assertGreater(consumed, 1.0)
            self.assertTrue(os.WIFSIGNALED(status))
        else:
            self.assertFalse(survived)
            self.assertTrue(os.WIFSIGNALED(status))

    @unittest.skipUnless(os.name == "posix", "POSIX-only characterization")
    def test_killpg_terminates_observed_group(self) -> None:
        code = """
import subprocess
import sys
import time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(child.pid, flush=True)
time.sleep(60)
"""
        leader = subprocess.Popen(
            [PYTHON, "-c", code],
            start_new_session=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert leader.stdout is not None
        int(leader.stdout.readline().strip())
        try:
            os.killpg(leader.pid, signal.SIGKILL)
            leader.wait(timeout=2)
            readable, _, _ = select.select([leader.stdout], [], [], 2.0)
            self.assertTrue(readable, "descendant kept the group pipe open")
            self.assertEqual(leader.stdout.read(), "")
        finally:
            if leader.poll() is None:
                os.killpg(leader.pid, signal.SIGKILL)
                leader.wait()
            leader.stdout.close()

    @unittest.skipUnless(SYSTEM == "Linux", "Linux /proc-only characterization")
    def test_linux_cutime_cstime_capture_reaped_children(self) -> None:
        code = """
import os
import time
for _ in range(8):
    pid = os.fork()
    if pid == 0:
        start = time.process_time()
        while time.process_time() - start < 0.06:
            pass
        os._exit(0)
for _ in range(8):
    os.wait()
print("ready", flush=True)
time.sleep(30)
"""
        parent = subprocess.Popen(
            [PYTHON, "-c", code],
            stdout=subprocess.PIPE,
            text=True,
        )
        assert parent.stdout is not None
        try:
            self.assertEqual(parent.stdout.readline().strip(), "ready")
            with open(f"/proc/{parent.pid}/stat", encoding="ascii") as stream:
                stat = stream.read()
            fields_from_state = stat[stat.rfind(")") + 2 :].split()
            cutime = int(fields_from_state[13])
            cstime = int(fields_from_state[14])
            child_cpu_seconds = (cutime + cstime) / os.sysconf("SC_CLK_TCK")
            self.assertGreater(child_cpu_seconds, 0.2)
        finally:
            parent.kill()
            parent.wait()

    @unittest.skipUnless(SYSTEM == "Linux", "PR_SET_CHILD_SUBREAPER is Linux-only")
    def test_orphaned_grandchild_cpu_is_lost_without_subreaper(self) -> None:
        code = """
import os
import resource
import time

def burn(seconds):
    start = time.process_time()
    while time.process_time() - start < seconds:
        pass

supervisor_pid = os.fork()
if supervisor_pid == 0:
    worker_pid = os.fork()
    if worker_pid == 0:
        burn(0.3)
        os._exit(0)
    os._exit(0)  # supervisor dies without reaping the worker: it is orphaned
os.waitpid(supervisor_pid, 0)  # we only ever reap our direct child
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
print(usage.ru_utime + usage.ru_stime, flush=True)
"""
        result = subprocess.run(
            [PYTHON, "-c", code],
            check=True,
            capture_output=True,
            text=True,
        )
        lost_cpu = float(result.stdout.strip())
        self.assertLess(
            lost_cpu,
            0.1,
            "el CPU del huerfano se contabilizo pese a no haber subreaper: "
            "la hipotesis de perdida no aplica en este kernel",
        )

    @unittest.skipUnless(SYSTEM in {"Darwin", "Linux"}, "Darwin/Linux only")
    def test_flush_primitive_available(self) -> None:
        """Caracteriza la disponibilidad de la primitiva de flush por plataforma.

        Base documental (clase D): en Darwin, `fsync()` no vacía la caché
        del disco; Apple exige `fcntl(F_FULLFSYNC)` para esa garantía, y aun
        así advierte que ciertos dispositivos pueden ignorarla. En Linux,
        `fsync()` estándar es la primitiva correcta y el directorio requiere
        sincronización separada. Este test sólo comprueba que la primitiva
        existe y puede invocarse; NO prueba fsync del directorio, el orden
        del protocolo creación/rename, recuperación tras crash ni
        supervivencia a corte eléctrico — eso se valida en M3. `durable`
        significa "protocolo de plataforma completado bajo supuestos
        declarados" (N5 de docs/claims-y-no-claims.md), no supervivencia
        demostrada.
        """
        import fcntl
        import tempfile

        with tempfile.TemporaryFile() as handle:
            handle.write(b"ektel-durable-probe")
            os.fsync(handle.fileno())
            if SYSTEM == "Darwin":
                self.assertTrue(
                    hasattr(fcntl, "F_FULLFSYNC"),
                    "Darwin sin F_FULLFSYNC: no hay primitiva de flush real",
                )
                fcntl.fcntl(handle.fileno(), fcntl.F_FULLFSYNC)
            # Linux: fsync estándar ya ejecutado arriba es la primitiva.

    @unittest.skipUnless(SYSTEM == "Linux", "PR_SET_CHILD_SUBREAPER is Linux-only")
    def test_subreaper_recovers_orphaned_grandchild_cpu(self) -> None:
        code = """
import ctypes
import os
import resource
import time

PR_SET_CHILD_SUBREAPER = 36
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
    raise SystemExit("prctl(PR_SET_CHILD_SUBREAPER) failed")

def burn(seconds):
    start = time.process_time()
    while time.process_time() - start < seconds:
        pass

supervisor_pid = os.fork()
if supervisor_pid == 0:
    worker_pid = os.fork()
    if worker_pid == 0:
        burn(0.3)
        os._exit(0)
    os._exit(0)  # supervisor dies; the worker reparents to us, the subreaper
os.waitpid(supervisor_pid, 0)
_, _, usage = os.wait4(-1, 0)  # reap the reparented orphan directly
print(usage.ru_utime + usage.ru_stime, flush=True)
"""
        result = subprocess.run(
            [PYTHON, "-c", code],
            check=True,
            capture_output=True,
            text=True,
        )
        recovered_cpu = float(result.stdout.strip())
        self.assertGreater(recovered_cpu, 0.2)


if __name__ == "__main__":
    unittest.main()
