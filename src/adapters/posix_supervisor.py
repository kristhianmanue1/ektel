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

**Terminación graduada (INC-M2-4, D-M2-3).** Al alcanzarse
`soft_termination_after_start_ms` se envía TERM **al grupo**; al alcanzarse
`hard_deadline_after_start_ms`, KILL. El plazo post-KILL **no amplía** el
deadline: sólo acota la latencia adicional de recolección de pipes antes de
entregar el resultado, y al expirar se declara `post_kill_forced_pipe_close`.

`finished_at_wall` y `duration_monotonic_ms` miden **hasta la recolección del
proceso principal**. Si la muestra final de reloj de pared no es finita o
regresa respecto de la inicial, se produce `supervision_failed` **sin fabricar
tiempos**.

API EXPERIMENTAL (spec §16). stdlib-only + ctypes declarado (ADR-006).
"""
from __future__ import annotations

import base64
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..domain.deadline import compute_bounds, payload_bounds, wall_sample_valid
from ..domain.execution_result import TerminalHandoff
from ..domain.start_request import ExecutionPlan
from ..ports.process_host import SpawnRejected
from ..application.config import M2Config
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

    start_mono = time.monotonic()
    start_wall = time.time()
    deadline_hit = threading.Event()
    killed = threading.Event()
    externally_terminated = threading.Event()
    # FIX-M2-R8: el orden de observación de los hechos terminales se registra
    # —dos booleanos finales no pueden preservar la causalidad que D-M2-4
    # exige («primer hecho observado gana; empate → deadline»).
    order_lock = threading.Lock()
    first_terminal_cause: list[str] = []

    def record_first(kind: str) -> None:
        with order_lock:
            if not first_terminal_cause:
                first_terminal_cause.append(kind)

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

    # FIX-M2-R9: el PGID del grupo gobernado se captura una sola vez, con el
    # líder vivo. Resolverlo con `getpgid(child.pid)` en el instante del KILL
    # fallaría si el líder ya fue recogido y dejaría a los descendientes del
    # grupo sin el KILL que la escalación les alcanza.
    governed_pgid = os.getpgid(child.pid)

    def terminate_group() -> None:
        """Terminación **best-effort del grupo** del proceso ejecutado.

        D-M2-2(a): el EOF del canal del coordinador la solicita. Matar al
        supervisor en su lugar dejaría al hijo huérfano y vivo, que es lo
        contrario de lo pedido. No promete muerte universal ni alcanza a
        descendientes escapados por `setsid`.
        """
        try:
            os.killpg(governed_pgid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

    def kill_group() -> None:
        try:
            os.killpg(governed_pgid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

    def on_channel_close() -> None:
        channel_closed.wait()
        externally_terminated.set()
        record_first("external_termination")
        terminate_group()

    threading.Thread(target=on_channel_close, daemon=True).start()

    # Terminación graduada por plazo (D-M2-3). El watchdog no toca el reloj de
    # pared: los plazos se miden en monotónico (§7.1, nunca se cruzan).
    bounds = compute_bounds(int(plan["deadline_eff_ms"]),
                            int(plan.get("termination_grace_ms", 2000)))

    def deadline_watchdog() -> None:
        soft_at = start_mono + bounds.soft_termination_after_start_ms / 1000.0
        hard_at = start_mono + bounds.hard_deadline_after_start_ms / 1000.0
        while time.monotonic() < soft_at:
            if child.poll() is not None:
                return
            time.sleep(0.02)
        if child.poll() is not None:
            return
        deadline_hit.set()
        record_first("deadline")
        terminate_group()          # TERM al grupo
        # FIX-M2-R9: la escalación ya comenzó; el KILL del grupo se intenta
        # al vencer el hard deadline **aunque el líder ya haya muerto con el
        # TERM** — los descendientes del grupo gobernado que ignoran TERM no
        # escapan del KILL. No confundir con `setsid`, que sigue siendo escape
        # declarado (fuera del grupo gobernado).
        while time.monotonic() < hard_at:
            time.sleep(0.02)
        killed.set()
        kill_group()

    watchdog = threading.Thread(target=deadline_watchdog, daemon=True)
    watchdog.start()
    assert child.stdout is not None and child.stderr is not None
    credit_timeout_s = int(plan.get("credit_timeout_ms",
                                    DEFAULT_CREDIT_TIMEOUT_MS)) / 1000.0
    eof_drain_s = int(plan.get("eof_drain_timeout_ms",
                               DEFAULT_EOF_DRAIN_TIMEOUT_MS)) / 1000.0
    post_kill_drain_s = int(plan.get("post_kill_drain_ms", 1000)) / 1000.0
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
    _payload = payload_bounds(int(plan["max_stdout_bytes"]),
                              int(plan["max_stderr_bytes"]), FRAME_MAX_BYTES)
    returncode = child.wait()
    # Recolección del proceso principal: este instante fija los tiempos
    # (ADR-009). Lo que venga después sólo es latencia de entrega.
    collected_mono = time.monotonic()
    duration_ms = int((collected_mono - start_mono) * 1000)
    end_wall = time.time()

    # FIX-M2-R9: el terminal debe reflejar la escalación completa. Si el
    # líder murió durante la gracia del TERM, el watchdog aún debe llegar al
    # hard deadline para ejecutar el KILL del grupo; se le espera de forma
    # acotada (nunca más allá del propio hard deadline más un margen mínimo)
    # para que `killed` y `post_kill_forced_pipe_close` sean deterministas.
    hard_deadline_mono = (start_mono
                          + bounds.hard_deadline_after_start_ms / 1000.0)
    watchdog.join(timeout=max(0.0, hard_deadline_mono - time.monotonic()) + 0.5)

    # Cota de EOF. Tras KILL rige `post_kill_drain_ms` (D-M2-3); en el resto
    # de los casos, la cota general de drenaje. Son hechos distintos.
    eof_drain_forced_close = False
    drain_budget_s = post_kill_drain_s if killed.is_set() else eof_drain_s
    deadline = time.monotonic() + drain_budget_s
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
    drain_elapsed_ms = int((time.monotonic() - collected_mono) * 1000)

    # Muestra final de pared: sólo alimenta `finished_at_wall`. Si no es
    # finita o regresa respecto de la inicial, se declara fallo de supervisión
    # y NO se fabrican tiempos (D-M2-3).
    wall_ok = wall_sample_valid(start_wall, end_wall)
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
        # Cotas de payload publicadas (D-M2-1(a)). NO son cotas de RSS.
        "payload_stable_bytes": _payload.stable_bytes,
        "payload_peak_bytes": _payload.materialization_peak_bytes,
        # INC-M2-4: plazo y terminación graduada.
        "deadline_effective_ms": bounds.deadline_effective_ms,
        "termination_grace_ms": bounds.termination_grace_ms,
        "useful_runtime_ms": bounds.useful_runtime_ms,
        "soft_termination_after_start_ms": bounds.soft_termination_after_start_ms,
        "hard_deadline_after_start_ms": bounds.hard_deadline_after_start_ms,
        "post_kill_drain_elapsed_ms": drain_elapsed_ms if killed.is_set() else 0,
        "post_kill_forced_pipe_close": (
            1 if (killed.is_set() and eof_drain_forced_close) else 0),
        "deadline_hit": deadline_hit.is_set(),
        "killed": killed.is_set(),
        "externally_terminated": externally_terminated.is_set(),
        # FIX-M2-R8: primer hecho terminal observado, no sólo el estado final.
        "first_terminal_cause": (first_terminal_cause[0]
                                 if first_terminal_cause else None),
        "duration_monotonic_ms": duration_ms,
        "finished_at_wall": end_wall if wall_ok else None,
        "wall_sample_invalid": not wall_ok,
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
    validity_bound: bool = False
    done: threading.Event = field(default_factory=threading.Event)
    max_frame_seen: int = 0


class PosixSupervisorHost:
    """`ProcessHost` real: un supervisor dedicado por acción.

    FIX-M2-R6: los rangos que este adaptador valida son los espejo exactos de
    D-M2-2/3 (la autoridad normativa es `M2Config`/ADR-012). La vía
    recomendada de composición es `PosixSupervisorHost.from_config(config)`,
    que revalida en esta frontera y garantiza que la configuración declarada
    en el `GuaranteePlan` es la misma que aplica el supervisor.
    """

    #: Espejo de los rangos congelados (D-M2-3): la validación se aplica
    #: también en la construcción directa del adaptador.
    _GRACE_RANGE = (0, 60000)
    _POST_KILL_RANGE = (1, 10000)
    _CREDIT_RANGE = (100, 600000)
    _EOF_RANGE = (1, 10000)

    @classmethod
    def from_config(cls, config: M2Config) -> "PosixSupervisorHost":
        """Composición desde la única autoridad de configuración (R6).

        Acepta el `M2Config` validado del despliegue y revalida sus valores
        en esta frontera: la configuración declarada en el `GuaranteePlan` y
        la aplicada por el supervisor no pueden divergir por construcción.
        """
        if not isinstance(config, M2Config):
            raise ValueError("from_config exige un M2Config validado")
        return cls(
            subreaper_requested=config.subreaper_requested,
            credit_timeout_ms=config.credit_timeout_ms,
            eof_drain_timeout_ms=config.eof_drain_timeout_ms,
            termination_grace_ms=config.termination_grace_ms,
            post_kill_drain_ms=config.post_kill_drain_ms,
        )

    def __init__(self, *, subreaper_requested: bool = True,
                 credit_timeout_ms: int = DEFAULT_CREDIT_TIMEOUT_MS,
                 eof_drain_timeout_ms: int = DEFAULT_EOF_DRAIN_TIMEOUT_MS,
                 termination_grace_ms: int = 2000,
                 post_kill_drain_ms: int = 1000,
                 ) -> None:
        for name, value, (low, high) in (
                ("credit_timeout_ms", credit_timeout_ms, self._CREDIT_RANGE),
                ("eof_drain_timeout_ms", eof_drain_timeout_ms, self._EOF_RANGE),
        ):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(
                    f"{name}: entero exacto en rango [{low}, {high}] requerido")
        if type(termination_grace_ms) is not int or not (
                self._GRACE_RANGE[0] <= termination_grace_ms
                <= self._GRACE_RANGE[1]):
            raise ValueError(
                "termination_grace_ms: entero exacto en rango [0, 60000]")
        if type(post_kill_drain_ms) is not int or not (
                self._POST_KILL_RANGE[0] <= post_kill_drain_ms
                <= self._POST_KILL_RANGE[1]):
            raise ValueError(
                "post_kill_drain_ms: entero exacto en rango [1, 10000]")
        self._caps = platform_caps.detect()
        self._subreaper_requested = subreaper_requested
        self._credit_timeout_ms = credit_timeout_ms
        self._eof_drain_timeout_ms = eof_drain_timeout_ms
        self._termination_grace_ms = termination_grace_ms
        self._post_kill_drain_ms = post_kill_drain_ms
        self._actions: dict[str, SupervisedAction] = {}
        self._lock = threading.Lock()

    @property
    def caps(self) -> platform_caps.PlatformCaps:
        return self._caps

    def spawn(self, plan: ExecutionPlan, *, deadline_eff_ms: int,
              validity_bound: bool = False) -> str:
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
            "termination_grace_ms": self._termination_grace_ms,
            "post_kill_drain_ms": self._post_kill_drain_ms,
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
        action.validity_bound = validity_bound
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
                       timeout: Optional[float] = 30.0
                       ) -> Optional[SupervisedAction]:
        """Espera el handoff terminal. Con `timeout` finito, toda espera es
        **acotada**; con `None`, espera hasta el cierre definitivo (modalidad
        del vigilante único del coordinador, FIX-M2-R2/R3).

        FIX-M2-R2: la entrega es única y está linealizada en el `pop`. Dos
        llamadores que esperen el mismo `handle_ref` no pueden obtener ambos
        la acción: sólo quien extraiga la entrada la recibe; el otro obtiene
        `None` (ausencia honesta). Antes del pop, una relectura bajo cerrojo
        confirma que la entrada registrada es exactamente esta acción.
        """
        with self._lock:
            action = self._actions.get(handle_ref)
        if action is None:
            return None
        if not action.done.wait(timeout):
            return None
        with self._lock:
            if self._actions.get(handle_ref) is not action:
                return None
            self._actions.pop(handle_ref, None)
        return action

    def collect_terminal(self, handle_ref: str, *,
                         timeout: Optional[float]) -> Optional[TerminalHandoff]:
        """Vista del puerto sobre el traspaso terminal. `await_terminal`
        conserva la vista rica del adaptador para su propia caracterización.

        FIX-M2-R1: la causalidad de vigencia calculada pre-CAS por el
        coordinador viaja en el `raw` del traspaso — sin esta fusión,
        `deadline_validity_exhausted` es inalcanzable end-to-end.
        """
        action = self.await_terminal(handle_ref, timeout=timeout)
        if action is None or action.terminal is None:
            return None
        raw = dict(action.terminal)
        raw["validity_bound"] = action.validity_bound
        return TerminalHandoff(raw=raw,
                               stdout=bytes(action.stdout),
                               stderr=bytes(action.stderr))

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
