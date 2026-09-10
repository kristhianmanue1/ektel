"""Resultado terminal y portador local de salida — D-M2-1(a), ADR-005/012.

Consume el vocabulario wire v1 **ya congelado** de
`contracts/schemas/v1/execution-result.schema.json`; no lo redefine ni lo
amplía. M2 no crea schemas (acta de autorización M2, A-M2-5).

**`executed` significa salida natural, NO éxito** (invariante 9). La
clasificación es por causa, y **el deadline gana en empate** (ADR-005).

`AwaitedExecution` es el portador **local** de D-M2-1(a): el wire
`ExecutionResult v1` es cerrado y no tiene campos de stdout/stderr, así que la
salida capturada se entrega por la API local y **nunca** se escribe en replay
store, logs, recibos ni disco. Los buffers son memoria atribuida al llamador y
ektel no afirma gobernarla.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional

#: Estados terminales del wire v1.
OUTCOME_EXECUTED = "executed"
OUTCOME_DEADLINE_EXCEEDED = "deadline_exceeded"
OUTCOME_TERMINATED = "terminated"
OUTCOME_SUPERVISION_FAILED = "supervision_failed"

TERMINAL_OUTCOMES = frozenset({
    OUTCOME_EXECUTED, OUTCOME_DEADLINE_EXCEEDED,
    OUTCOME_TERMINATED, OUTCOME_SUPERVISION_FAILED,
})

#: Causas del wire v1.
CAUSE_NATURAL_EXIT = "natural_exit"
CAUSE_DEADLINE_DURATION = "deadline_duration"
CAUSE_DEADLINE_VALIDITY_EXHAUSTED = "deadline_validity_exhausted"
CAUSE_EXTERNAL_TERMINATION = "external_termination"
CAUSE_SUPERVISION_FAILURE = "supervision_failure"

TERMINAL_CAUSES = frozenset({
    CAUSE_NATURAL_EXIT, CAUSE_DEADLINE_DURATION,
    CAUSE_DEADLINE_VALIDITY_EXHAUSTED, CAUSE_EXTERNAL_TERMINATION,
    CAUSE_SUPERVISION_FAILURE,
})

#: Claves de medición congeladas localmente por ADR-012. El mapa wire queda
#: abierto; estas claves no.
MEASUREMENT_KEYS = (
    "deadline_effective_ms",
    "termination_grace_ms",
    "useful_runtime_ms",
    "soft_termination_after_start_ms",
    "hard_deadline_after_start_ms",
    "post_kill_drain_elapsed_ms",
    "post_kill_forced_pipe_close",
    "stdout_discarded_bytes",
    "stderr_discarded_bytes",
    "discarded_bytes",
)


@dataclass(frozen=True)
class ExecutionResult:
    """Resultado terminal. `finished_at_wall` y `duration_monotonic_ms` miden
    **hasta la recolección del proceso principal** (instante que fija
    ADR-009); el drenaje post-KILL sólo extiende la latencia de entrega."""
    outcome: str
    cause: str
    exit_status: Optional[int]
    duration_monotonic_ms: int
    finished_at_wall: Optional[float]
    guarantees_applied: tuple[str, ...]
    measurements: Mapping[str, int]

    def __post_init__(self) -> None:
        if self.outcome not in TERMINAL_OUTCOMES:
            raise ValueError(f"outcome invalido: {self.outcome!r}")
        if self.cause not in TERMINAL_CAUSES:
            raise ValueError(f"cause invalida: {self.cause!r}")


@dataclass(frozen=True)
class TerminalHandoff:
    """Traspaso terminal desde el supervisor al coordinador.

    `raw` son las mediciones **observadas**; el coordinador las proyecta a las
    claves congeladas y clasifica. Separar observación de clasificación evita
    que el adaptador decida semántica del contrato.
    """
    raw: Mapping[str, object]
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class AwaitedExecution:
    """Portador local de D-M2-1(a). Inmutable al entregarse."""
    result: ExecutionResult
    stdout: bytes
    stderr: bytes


def classify(*, supervision_failure: bool, deadline_hit: bool,
             validity_bound: bool, externally_terminated: bool,
             first_terminal_cause: Optional[str] = None
             ) -> tuple[str, str]:
    """Clasifica por causa con la precedencia de ADR-005, D-M2-4 y FIX-M2-R8.

    Orden: un fallo de supervisión no se disimula; cuando deadline y
    terminación externa concurren, decide el **primer hecho observado**
    (FIX-M2-R8) — `external_termination` → `terminated`; `deadline` o
    desconocido/empate → `deadline_exceeded` (el deadline gana en empate,
    ADR-005) —; y entre las dos causas de plazo, **gana vigencia** cuando la
    vigencia restante acotó la duración (FIX-M2-R1: el dato debe llegar
    realmente hasta aquí).
    """
    if supervision_failure:
        return OUTCOME_SUPERVISION_FAILED, CAUSE_SUPERVISION_FAILURE
    if deadline_hit:
        cause = (CAUSE_DEADLINE_VALIDITY_EXHAUSTED if validity_bound
                 else CAUSE_DEADLINE_DURATION)
        if externally_terminated and first_terminal_cause == "external_termination":
            return OUTCOME_TERMINATED, CAUSE_EXTERNAL_TERMINATION
        return OUTCOME_DEADLINE_EXCEEDED, cause
    if externally_terminated:
        return OUTCOME_TERMINATED, CAUSE_EXTERNAL_TERMINATION
    return OUTCOME_EXECUTED, CAUSE_NATURAL_EXIT


def freeze_measurements(raw: Mapping[str, object]) -> Mapping[str, int]:
    """Proyecta sólo las claves congeladas, como enteros exactos.

    `post_kill_forced_pipe_close` es entero `0|1` por D-M2-3, no booleano: el
    contrato lo fija así y no se «mejora» por comodidad.
    """
    projected: dict[str, int] = {}
    for key in MEASUREMENT_KEYS:
        value = raw.get(key, 0)
        if type(value) is bool:
            projected[key] = 1 if value else 0
        elif type(value) is int:
            projected[key] = value
        else:
            projected[key] = 0
    return MappingProxyType(projected)
