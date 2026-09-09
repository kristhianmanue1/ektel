"""Supervisor POSIX dedicado por acción — ADR-012 D-M2-1(a) y D-M2-2(a).

Topología (D-M2-2(a), alternativa (a) aceptada):

    coordinador runtime  ──IPC local──  supervisor de acción  ──  proceso ejecutado
      (dueño de handles)                 (uno por acción)          (grupo propio)

El **supervisor de acción** queda fuera del grupo del proceso ejecutado y le
crea un grupo propio con `process_group=0`, **sin `preexec_fn`**. Se rechazó la
alternativa (b) —threads en un supervisor global— porque hace global el efecto
de subreaper, introduce carreras de `waitpid` entre acciones y amplía el blast
radius de un fallo.

Este módulo es a la vez el adaptador del lado coordinador y el **punto de
entrada** del proceso supervisor (`python -m src.adapters.posix_supervisor`).

**Transferencia de salida (D-M2-1(a)).** Frames ordenados de máximo 64 KiB por
stream, con crédito y confirmación que permiten **un solo frame no confirmado
por stream**. El supervisor libera cada frame confirmado y nunca conserva una
segunda copia completa. Retiene exactamente los primeros `max_stdout_bytes` /
`max_stderr_bytes`; después **sigue drenando** y descarta, contando los bytes
descartados de forma exacta.

**Canales:** el **contenido** del plan viaja por un descriptor dedicado y nunca
por `argv`, porque `argv` es visible en el listado de procesos y §2.7 trata
stdin y entorno como material sensible. Por `argv` viaja únicamente el
**número** de ese descriptor, que no es material sensible.

**Alcance de este incremento.** INC-M2-3 cubre spawn, grupo, stdin acotado,
drenaje continuo, captura acotada y recolección del principal. La terminación
graduada TERM→KILL, el plazo y `post_kill_drain_ms` son de **INC-M2-4**: aquí
el `deadline_eff_ms` se transporta y se registra, pero **todavía no se
aplica**, y este módulo no afirma lo contrario.

API EXPERIMENTAL (spec §16). stdlib-only + ctypes declarado (ADR-006).
"""
from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..domain.start_request import ExecutionPlan
from ..ports.process_host import SpawnRejected
from . import platform_caps

#: Cota de frame de D-M2-1(a): 64 KiB por stream.
FRAME_MAX_BYTES = 65536
#: Espejos de los defaults validados en `application.config.M2Config`. Estas
#: cotas **no** se inventan aquí: el llamador las inyecta ya validadas (R1).
DEFAULT_CREDIT_TIMEOUT_MS = 30000
DEFAULT_EOF_DRAIN_TIMEOUT_MS = 3000
#: El descriptor del plan **se comunica por argv**, no se asume fijo:
#: `pass_fds` conserva el número original que devuelva `os.pipe()`, y ese
#: número depende de cuántos descriptores tenga abiertos el coordinador.
#: Fijarlo a 3 funciona sólo en un proceso recién arrancado y falla en cuanto
#: hay otros fds vivos. El número no es material sensible; el plan sí, y por
#: eso viaja por el descriptor y nunca por argv.

_STREAM_OUT = b"O"
_STREAM_ERR = b"E"


# --------------------------------------------------------------------------
# Marco de frames: local, no wire. No es un contrato publicado ni versionado
# hacia consumidores; es el canal que ADR-012 ya fijó entre nuestros procesos.
# --------------------------------------------------------------------------

def _write_frame(sink: "object", kind: bytes, stream: bytes, payload: bytes) -> None:
    header = kind + stream + f"{len(payload):08x}".encode("ascii") + b"\n"
    sink.write(header + payload)  # type: ignore[attr-defined]
    sink.flush()  # type: ignore[attr-defined]


def _read_frame(source: "object") -> Optional[tuple[bytes, bytes, bytes]]:
    header = source.readline()  # type: ignore[attr-defined]
    if not header or len(header) != 11:
        return None
    kind, stream = header[0:1], header[1:2]
    try:
        length = int(header[2:10].decode("ascii"), 16)
    except ValueError:
        return None
    if length > FRAME_MAX_BYTES:
        return None
    payload = source.read(length) if length else b""  # type: ignore[attr-defined]
    if payload is None or len(payload) != length:
        return None
    return kind, stream, payload


# --------------------------------------------------------------------------
# Lado supervisor (proceso hijo del coordinador)
# --------------------------------------------------------------------------

class _StreamPump:
    """Drena un pipe del proceso ejecutado, retiene el prefijo acotado y
    descarta el exceso contando bytes exactos."""

    def __init__(self, stream: bytes, source: "object", limit: int,
                 emit: "object", credit: threading.Semaphore,
                 credit_timeout_s: float,
                 channel_closed: threading.Event) -> None:
        self.stream = stream
        self._source = source
        self._limit = limit
        self._emit = emit
        self._credit = credit
        self._credit_timeout_s = credit_timeout_s
        self._channel_closed = channel_closed
        self.retained = 0
        self.discarded = 0
        self.truncated = False
        #: El coordinador dejó de confirmar y se pasó a descarte (H1).
        self.credit_starved = False

    def _acquire_credit(self) -> bool:
        """Espera crédito distinguiendo **canal cerrado** de **canal lento**.

        D-M2-1(a) manda descartar cuando el coordinador **deja de consumir**.
        Un coordinador simplemente lento no es eso: colapsar ambos casos en un
        único plazo corto perdía salida que cabía en `max_stdout_bytes` (R3).

        - canal cerrado (EOF de acks): señal inequívoca, degrada de inmediato;
        - canal lento: espera hasta la cota **configurada**, holgada.
        """
        deadline = time.monotonic() + self._credit_timeout_s
        while True:
            if self._channel_closed.is_set():
                return False
            if self._credit.acquire(timeout=0.05):
                return True
            if time.monotonic() >= deadline:
                return False

    def run(self) -> None:
        while True:
            try:
                # `read1` devuelve lo disponible; `read` bloquearía hasta
                # reunir el tamaño pedido o EOF, y entonces no habría drenaje
                # incremental (H4).
                chunk = self._source.read1(FRAME_MAX_BYTES)  # type: ignore[attr-defined]
            except (OSError, ValueError):
                # El pipe se cerró desde fuera para acotar la espera (H2).
                return
            if not chunk:
                return
            room = self._limit - self.retained
            rest = chunk
            if room > 0 and not self.credit_starved:
                keep, rest = chunk[:room], chunk[room:]
                if keep:
                    # Máximo un frame no confirmado por stream. Si el crédito
                    # no llega, NO se deja de leer: se degrada a descarte.
                    if self._acquire_credit():
                        self._emit(self.stream, keep)  # type: ignore[operator]
                        self.retained += len(keep)
                    else:
                        self.credit_starved = True
                        rest = chunk
            if rest:
                # Sigue drenando aunque ya no retenga: no dejar al hijo
                # bloqueado escribiendo en un pipe lleno.
                self.discarded += len(rest)
                self.truncated = True


def _supervisor_main() -> int:  # pragma: no cover - se ejercita por subproceso
    """Punto de entrada del supervisor de acción."""
    if len(sys.argv) < 2:
        return 2
    with os.fdopen(int(sys.argv[1]), "rb") as plan_fd:
        plan = json.loads(plan_fd.read().decode("utf-8"))

    subreaper_applied = False
    if plan.get("subreaper_requested"):
        subreaper_applied = platform_caps.set_child_subreaper()

    frames_out = sys.stdout.buffer
    acks_in = sys.stdin.buffer
    write_lock = threading.Lock()
    credits = {_STREAM_OUT: threading.Semaphore(1),
               _STREAM_ERR: threading.Semaphore(1)}
    # H11: la propiedad "un solo frame no confirmado por stream" se **mide**,
    # no se afirma. Aquí es donde puede observarse.
    outstanding = {_STREAM_OUT: 0, _STREAM_ERR: 0}
    unacked_peak = {_STREAM_OUT: 0, _STREAM_ERR: 0}
    counters_lock = threading.Lock()
    # EOF del canal del coordinador = solicitud de terminación del grupo.
    channel_closed = threading.Event()

    def emit(stream: bytes, payload: bytes) -> None:
        # El contador se incrementa ANTES de escribir. Al revés, el ack de ese
        # frame puede llegar antes del incremento, descartarse por
        # `outstanding == 0` y dejar un pendiente fantasma que infla el pico.
        # Lo que acota la propiedad es el semáforo —se adquiere antes de emitir
        # y sólo se libera con el ack—; este contador únicamente la observa, y
        # debe observarla sin adelantarse al hecho que mide.
        with counters_lock:
            outstanding[stream] += 1
            if outstanding[stream] > unacked_peak[stream]:
                unacked_peak[stream] = outstanding[stream]
        with write_lock:
            _write_frame(frames_out, b"F", stream, payload)

    def ack_reader() -> None:
        while True:
            token = acks_in.read(1)
            if not token:
                channel_closed.set()
                return
            credit = credits.get(token)
            if credit is not None:
                with counters_lock:
                    if outstanding[token] > 0:
                        outstanding[token] -= 1
                credit.release()

    threading.Thread(target=ack_reader, daemon=True).start()

    try:
        child = subprocess.Popen(
            [plan["command_absolute"], *plan["args"]],
            cwd=plan["cwd"],
            env=dict(plan["env"]),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            process_group=0,  # grupo propio; sin preexec_fn (D-M2-2(a))
        )
    except OSError as exc:
        with write_lock:
            _write_frame(frames_out, b"X", b"-",
                         json.dumps({"detail": f"spawn_failed:{exc.errno}"}
                                    ).encode("utf-8"))
        return 2

    stdin_bytes = base64.b64decode(plan["stdin_b64"])

    def feed_stdin() -> None:
        try:
            assert child.stdin is not None
            child.stdin.write(stdin_bytes)
            child.stdin.flush()
        except Exception:
            pass
        finally:
            try:
                assert child.stdin is not None
                child.stdin.close()
            except Exception:
                pass

    # stdin en su propio hilo: un hijo que no lee no puede bloquear al
    # supervisor (G-M2-08).
    threading.Thread(target=feed_stdin, daemon=True).start()

    def terminate_group() -> None:
        """Terminación **best-effort del grupo** del proceso ejecutado.

        D-M2-2(a): el EOF del canal del coordinador la solicita. Matar al
        supervisor en su lugar dejaría al hijo huérfano y vivo, que es lo
        contrario de lo pedido. No promete muerte universal ni alcanza a
        descendientes escapados por `setsid`.
        """
        try:
            os.killpg(os.getpgid(child.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

    def on_channel_close() -> None:
        channel_closed.wait()
        terminate_group()

    threading.Thread(target=on_channel_close, daemon=True).start()

    assert child.stdout is not None and child.stderr is not None
    credit_timeout_s = int(plan.get("credit_timeout_ms",
                                    DEFAULT_CREDIT_TIMEOUT_MS)) / 1000.0
    eof_drain_s = int(plan.get("eof_drain_timeout_ms",
                               DEFAULT_EOF_DRAIN_TIMEOUT_MS)) / 1000.0
    pump_out = _StreamPump(_STREAM_OUT, child.stdout,
                           int(plan["max_stdout_bytes"]), emit,
                           credits[_STREAM_OUT], credit_timeout_s,
                           channel_closed)
    pump_err = _StreamPump(_STREAM_ERR, child.stderr,
                           int(plan["max_stderr_bytes"]), emit,
                           credits[_STREAM_ERR], credit_timeout_s,
                           channel_closed)
    # Daemon: si un nieto retiene los pipes, el hilo puede quedar dentro de
    # `read1` y cerrar el descriptor NO lo desbloquea. No se depende de
    # desbloquearlo: el supervisor emite su terminal y sale igualmente.
    hilos = [threading.Thread(target=p.run, daemon=True)
             for p in (pump_out, pump_err)]
    for h in hilos:
        h.start()

    # Esperar al proceso principal: los pumps drenan, así que `wait` no puede
    # bloquearse contra un pipe lleno.
    returncode = child.wait()

    # Cota de EOF (H2). Un nieto que hereda y RETIENE los pipes impide el EOF
    # aunque el principal ya salió; sin esta cota la espera es ilimitada.
    eof_drain_forced_close = False
    deadline = time.monotonic() + eof_drain_s
    for h in hilos:
        h.join(timeout=max(0.0, deadline - time.monotonic()))
    if any(h.is_alive() for h in hilos):  # noqa: E501
        # No hay EOF porque alguien más retiene el extremo de escritura. Se
        # declara el cierre forzado y se continúa: los contadores publicados
        # son los observados hasta este instante, no un total que el supervisor
        # no puede conocer.
        #
        # NO se llama `pipe.close()`: cerrar un `BufferedReader` espera el lock
        # que retiene el hilo bloqueado dentro de `read1`, y eso bloquea al
        # supervisor exactamente igual que el problema que se quiere acotar.
        # Los pumps son daemon y los descriptores se cierran al salir el
        # proceso, que es inmediato tras emitir el terminal.
        eof_drain_forced_close = True
    terminal = {
        "returncode": returncode,
        "stdout_retained": pump_out.retained,
        "stderr_retained": pump_err.retained,
        "stdout_discarded_bytes": pump_out.discarded,
        "stderr_discarded_bytes": pump_err.discarded,
        "discarded_bytes": pump_out.discarded + pump_err.discarded,
        "stdout_truncation": pump_out.truncated,
        "stderr_truncation": pump_err.truncated,
        "subreaper_requested": bool(plan.get("subreaper_requested")),
        "subreaper_applied": subreaper_applied,
        "child_pid": child.pid,
        # H11: medido, no afirmado.
        "max_unacked_stdout": unacked_peak[_STREAM_OUT],
        "max_unacked_stderr": unacked_peak[_STREAM_ERR],
        "credit_starved": pump_out.credit_starved or pump_err.credit_starved,
        # Hecho DISTINTO de `post_kill_forced_pipe_close` de D-M2-3, que
        # describe el cierre forzado tras KILL (INC-M2-4). Aquí no hubo KILL:
        # se agotó la espera de EOF. Nombres casi iguales para hechos distintos
        # invitan a confundirlos (R2).
        "eof_drain_forced_close": eof_drain_forced_close,
    }
    with write_lock:
        _write_frame(frames_out, b"T", b"-",
                     json.dumps(terminal, sort_keys=True).encode("utf-8"))
    return 0


# --------------------------------------------------------------------------
# Lado coordinador
# --------------------------------------------------------------------------

@dataclass
class SupervisedAction:
    """Estado local de una acción supervisada. No se serializa."""
    handle_ref: str
    process: subprocess.Popen[bytes]
    stdout: bytearray = field(default_factory=bytearray)
    stderr: bytearray = field(default_factory=bytearray)
    terminal: Optional[dict[str, object]] = None
    failed_detail: Optional[str] = None
    termination_requested: bool = False
    done: threading.Event = field(default_factory=threading.Event)
    max_frame_seen: int = 0


class PosixSupervisorHost:
    """`ProcessHost` real: un supervisor dedicado por acción."""

    def __init__(self, *, subreaper_requested: bool = True,
                 credit_timeout_ms: int = DEFAULT_CREDIT_TIMEOUT_MS,
                 eof_drain_timeout_ms: int = DEFAULT_EOF_DRAIN_TIMEOUT_MS,
                 ) -> None:
        for name, value in (("credit_timeout_ms", credit_timeout_ms),
                            ("eof_drain_timeout_ms", eof_drain_timeout_ms)):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name}: entero exacto positivo requerido")
        self._caps = platform_caps.detect()
        self._subreaper_requested = subreaper_requested
        self._credit_timeout_ms = credit_timeout_ms
        self._eof_drain_timeout_ms = eof_drain_timeout_ms
        self._actions: dict[str, SupervisedAction] = {}
        self._lock = threading.Lock()

    @property
    def caps(self) -> platform_caps.PlatformCaps:
        return self._caps

    def spawn(self, plan: ExecutionPlan, *, deadline_eff_ms: int) -> str:
        payload = json.dumps({
            "command_absolute": plan.command_absolute,
            "args": list(plan.args),
            "cwd": plan.cwd,
            "env": dict(plan.env),
            "stdin_b64": base64.b64encode(plan.stdin_bytes).decode("ascii"),
            "max_stdout_bytes": plan.max_stdout_bytes,
            "max_stderr_bytes": plan.max_stderr_bytes,
            # Transportado y registrado; NO aplicado hasta INC-M2-4.
            "deadline_eff_ms": deadline_eff_ms,
            "subreaper_requested": (self._subreaper_requested
                                    and self._caps.subreaper_available),
            "credit_timeout_ms": self._credit_timeout_ms,
            "eof_drain_timeout_ms": self._eof_drain_timeout_ms,
        }).encode("utf-8")

        plan_r, plan_w = os.pipe()
        try:
            supervisor = subprocess.Popen(
                [sys.executable, "-m", "src.adapters.posix_supervisor",
                 str(plan_r)],
                cwd=str(_repo_root()),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                pass_fds=(plan_r,),
                close_fds=True,
            )
        except OSError as exc:
            os.close(plan_r)
            os.close(plan_w)
            raise SpawnRejected(f"supervisor_spawn:{exc.errno}") from exc
        os.close(plan_r)
        try:
            with os.fdopen(plan_w, "wb") as sink:
                sink.write(payload)
        except OSError as exc:
            # Fallo determinado y anterior al proceso ejecutado: no debe
            # degradarse a indeterminado (H9).
            try:
                supervisor.kill()
            except Exception:
                pass
            raise SpawnRejected(f"plan_channel:{exc.errno}") from exc

        handle_ref = f"{os.urandom(8).hex()}"
        action = SupervisedAction(handle_ref=handle_ref, process=supervisor)
        with self._lock:
            self._actions[handle_ref] = action
        threading.Thread(target=self._collect, args=(action,), daemon=True).start()
        return handle_ref

    def _collect(self, action: SupervisedAction) -> None:
        source = action.process.stdout
        sink = action.process.stdin
        assert source is not None and sink is not None
        try:
            while True:
                frame = _read_frame(source)
                if frame is None:
                    break
                kind, stream, payload = frame
                if kind == b"F":
                    action.max_frame_seen = max(action.max_frame_seen, len(payload))
                    target = (action.stdout if stream == _STREAM_OUT
                              else action.stderr)
                    target.extend(payload)
                    # Confirmación: devuelve el crédito de ese stream. Si el
                    # canal ya se cerró para pedir terminación, no reabrirlo.
                    if not action.termination_requested:
                        try:
                            sink.write(stream)
                            sink.flush()
                        except (BrokenPipeError, ValueError):
                            pass
                elif kind == b"T":
                    action.terminal = json.loads(payload.decode("utf-8"))
                    break
                elif kind == b"X":
                    action.failed_detail = str(
                        json.loads(payload.decode("utf-8")).get("detail"))
                    break
        except Exception:
            action.failed_detail = action.failed_detail or "channel_error"
        finally:
            # Cerrar ambos extremos: filtrar descriptores por acción agotaría
            # el coordinador tras suficientes acciones.
            for pipe in (action.process.stdin, action.process.stdout):  # noqa: E501
                try:
                    if pipe is not None:
                        pipe.close()
                except Exception:
                    pass
            try:
                action.process.wait(timeout=30)
            except Exception:
                pass
            action.done.set()

    def request_termination(self, handle_ref: str) -> None:
        """Solicita terminación best-effort **del grupo** del proceso ejecutado.

        Se hace **cerrando el canal** hacia el supervisor (D-M2-2(a): «el EOF
        del canal del coordinador solicita terminación best-effort del
        grupo»). Terminar al supervisor en su lugar dejaría al hijo huérfano y
        vivo: lo contrario de lo solicitado.

        La terminación graduada TERM→KILL es de INC-M2-4; esto es la señal, no
        una promesa de muerte.
        """
        with self._lock:
            action = self._actions.get(handle_ref)
        if action is None:
            return
        action.termination_requested = True
        try:
            if action.process.stdin is not None:
                action.process.stdin.close()
        except Exception:
            pass

    def await_terminal(self, handle_ref: str,
                       timeout: float = 30.0) -> Optional[SupervisedAction]:
        """Espera el handoff terminal. Toda espera es **acotada**."""
        with self._lock:
            action = self._actions.get(handle_ref)
        if action is None:
            return None
        if not action.done.wait(timeout):
            return None
        # H6: el registro no crece sin límite. Entregar el terminal transfiere
        # la propiedad al llamador y el coordinador deja de retenerlo.
        with self._lock:
            self._actions.pop(handle_ref, None)
        return action

    @property
    def pending_actions(self) -> int:
        """Acciones retenidas por el coordinador y todavía no entregadas."""
        with self._lock:
            return len(self._actions)


def _repo_root() -> "object":
    from pathlib import Path
    return Path(__file__).resolve().parents[2]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_supervisor_main())
