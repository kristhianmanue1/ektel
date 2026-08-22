"""Replay store durable sobre archivo (spec §7.4–7.5, ADR-004).

Perfil `posix-fsync-dir/v1` con corrección por plataforma (§11.3/ADR-007
punto 3): en cada mutación, fsync del archivo Y del directorio; en Darwin,
`fcntl(F_FULLFSYNC)` cuando esté disponible (fsync() no vacía la caché del
disco) y fsync estándar como fallback declarado.

Diseño (determinista, stdlib-only, un único proceso supervisor por
despliegue — ADR-001 «un host, un operador»):

- Estado completo del store en un único archivo JSON `state.json`
  (`nonces`: {issuer_id\x00nonce: reserve_until_wall}, `spent`: {digest:
  true}), reescrito íntegro con write-to-temp + fsync + rename atómico +
  fsync del directorio. Un archivo simplifica el CAS y la carga al
  inicializar; el rename garantiza que un crash a mitad de escritura nunca
  deja un estado parcial (o el viejo o el nuevo).
- CAS bajo doble exclusión: `threading.Lock` (hilos de la instancia) +
  `flock` sobre un lock-file del directorio (instancias distintas, mismo
  proceso u otro): el tramo reload→check→persist es atómico entre
  instancias sobre el mismo estado durable (sin TOCTOU).
- **Carga al inicializar** (G16): el constructor lee el estado durable;
  los registros cargados siguen rechazando replays tras reiniciar el
  proceso. Sin archivo → estado vacío nuevo (primer arranque).
- **TTL** (G11/ADR-004 consecuencia): `collect_expired(now_wall)` elimina
  nonces con `reserve_until_wall < now`; lo llama quien configura el
  servicio (recolección explícita, sin hilo de fondo en M1).
- **Límite de tamaño** (ADR-004 A2): `max_nonces` declarado; al alcanzarlo
  sin recolección posible, `reserve_nonce` devuelve `UNAVAILABLE`
  (fail-closed; nunca expulsión silenciosa).
- Errores de I/O/fsync → `UNAVAILABLE` (la aplicación ya mapea a rechazo,
  INC-3); constructor corrupto → `ReplayStoreError` (arranque fail-closed).

API EXPERIMENTAL (spec §16). stdlib-only (ADR-006).
"""
from __future__ import annotations

import fcntl
import json
import math
import os
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..ports.replay_store import ConsumeOutcome, ReserveOutcome

# Estado durable: {"nonces": {clave: reserve_until_float},
#                  "spent": {digest: True}} — escrito/leído sólo aquí.
_State = dict[str, Any]

_IS_DARWIN = sys.platform == "darwin"


class ReplayStoreError(Exception):
    """Fallo de arranque del store (corrupción/IO). Mensaje safe."""


def _fsync_file(fd: int) -> None:
    """fsync con corrección Darwin (F_FULLFSYNC cuando exista)."""
    if _IS_DARWIN:
        full = getattr(fcntl, "F_FULLFSYNC", None)
        if full is not None:
            fcntl.fcntl(fd, full)
            return
    os.fsync(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(os.fspath(path), os.O_RDONLY)
    try:
        _fsync_file(fd)
    finally:
        os.close(fd)


class FileReplayStore:
    """Adaptador durable del puerto ReplayStore (§7.4).

    Exclusión mutua en dos niveles: `threading.Lock` serializa los hilos
    de ESTA instancia, y `flock` sobre un lock-file del directorio
    serializa INSTANCIAS distintas (mismo proceso u otro) sobre el mismo
    estado durable — el tramo reload→check→persist es atómico entre
    instancias, sin el TOCTOU de un lock meramente intraproceso.
    """

    STATE_FILENAME = "state.json"
    LOCK_FILENAME = ".lock"

    def __init__(self, directory: Path, max_nonces: int = 1_000_000) -> None:
        self._dir = Path(directory)
        self._max_nonces = max_nonces
        self._lock = threading.Lock()
        self._state_path = self._dir / self.STATE_FILENAME
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._lock_fd = os.open(os.fspath(self._dir / self.LOCK_FILENAME),
                                    os.O_CREAT | os.O_RDWR, 0o600)
        except OSError as exc:
            self._lock_fd = -1
            raise ReplayStoreError(f"init:{type(exc).__name__}") from exc
        try:
            with self._critical():
                self._state = self._load_or_init()
        except Exception:
            self.close()  # no filtrar el fd si el arranque falla
            raise

    def close(self) -> None:
        """Cierra el lock-file (higiene de pruebas; idempotente)."""
        fd = getattr(self, "_lock_fd", -1)
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
            self._lock_fd = -1

    @contextmanager
    def _critical(self) -> Iterator[None]:
        """Sección crítica: lock de hilo + flock inter-instancias."""
        with self._lock:
            if self._lock_fd < 0:
                # Store cerrado: sin lock-file no hay sección crítica
                # posible — fail-closed, no excepción de plataforma.
                raise ReplayStoreError("lock:closed")
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
            except (OSError, ValueError) as exc:
                # ValueError: fd inválido (p. ej. cerrado) en darwin.
                raise ReplayStoreError(f"lock:{type(exc).__name__}") from exc
            try:
                yield
            finally:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                except (OSError, ValueError):
                    pass

    # -- carga durable (G16) ------------------------------------------------

    def _load_or_init(self) -> _State:
        if not self._state_path.exists():
            return {"nonces": {}, "spent": {}}
        try:
            raw = self._state_path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise ReplayStoreError(f"state_corrupt:{type(exc).__name__}") from exc
        if (not isinstance(state, dict)
                or not isinstance(state.get("nonces"), dict)
                or not isinstance(state.get("spent"), dict)):
            raise ReplayStoreError("state_corrupt:shape")
        nonces: dict[str, Any] = state["nonces"]
        spent: dict[str, Any] = state["spent"]
        if (any(not isinstance(v, (int, float)) or isinstance(v, bool)
                or not math.isfinite(v)
                for v in nonces.values())
                or any(v is not True for v in spent.values())):
            raise ReplayStoreError("state_corrupt:values")
        return state

    def _persist(self, state: _State) -> None:
        """write-to-temp + fsync + rename + fsync-dir (posix-fsync-dir/v1)."""
        payload = json.dumps(state, sort_keys=True, separators=(",", ":"))
        fd, tmp_name = tempfile.mkstemp(dir=self._dir, prefix=".state-", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                _fsync_file(handle.fileno())
            os.replace(tmp, self._state_path)
            _fsync_dir(self._dir)
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ReplayStoreError(f"persist_failed:{type(exc).__name__}") from exc

    def _reload(self) -> _State:
        """Relee el estado durable bajo lock (CAS entre instancias)."""
        try:
            self._state = self._load_or_init()
        except ReplayStoreError:
            raise
        return self._state

    # -- puerto --------------------------------------------------------------

    def reserve_nonce(self, issuer_id: str, nonce: str,
                      reserve_until_wall: float) -> ReserveOutcome:
        # Claves planas: NUL en issuer/nonce podría aliasar registros
        # (fail-closed ante entradas imposibles de serializar sin ambigüedad).
        if "\x00" in issuer_id or "\x00" in nonce:
            return ReserveOutcome.UNAVAILABLE
        # NaN/inf nunca vencerían y no son JSON estándar (fail-closed).
        if not math.isfinite(reserve_until_wall):
            return ReserveOutcome.UNAVAILABLE
        key = f"{issuer_id}\x00{nonce}"
        try:
            with self._critical():
                self._reload()
                if key in self._state["nonces"]:
                    return ReserveOutcome.ALREADY_RESERVED
                # Recolección de TTL oportunista antes del límite (G11):
                now = time.time()
                expired = [k for k, until in self._state["nonces"].items()
                           if until < now]
                for k in expired:
                    del self._state["nonces"][k]
                if len(self._state["nonces"]) >= self._max_nonces:
                    return ReserveOutcome.UNAVAILABLE
                self._state["nonces"][key] = float(reserve_until_wall)
                self._persist(self._state)
                return ReserveOutcome.RESERVED
        except ReplayStoreError:
            return ReserveOutcome.UNAVAILABLE

    def consume_start_token(self, identity_digest: str) -> ConsumeOutcome:
        try:
            with self._critical():
                self._reload()
                if identity_digest in self._state["spent"]:
                    return ConsumeOutcome.ALREADY_SPENT
                self._state["spent"][identity_digest] = True
                self._persist(self._state)
                return ConsumeOutcome.CONSUMED
        except ReplayStoreError:
            return ConsumeOutcome.UNAVAILABLE

    def start_token_status(self, identity_digest: str) -> str:
        try:
            with self._critical():
                self._reload()
                if identity_digest in self._state["spent"]:
                    return "spent"
                return "unspent"
        except ReplayStoreError:
            return "unknown"

    # -- mantenimiento --------------------------------------------------------

    def collect_expired(self, now_wall: float) -> int:
        """Recolección explícita de nonces vencidos (G11); devuelve cuántos."""
        with self._critical():
            self._reload()
            expired = [k for k, until in self._state["nonces"].items()
                       if until < now_wall]
            for k in expired:
                del self._state["nonces"][k]
            if expired:
                self._persist(self._state)
            return len(expired)

    @property
    def nonce_count(self) -> int:
        """Sólo tests/diagnóstico."""
        return len(self._state["nonces"])
