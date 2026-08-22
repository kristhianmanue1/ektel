"""Frontera instrumental de spawn — D-P4-α (orden del dueño, adenda R1
regla 5; confirmada por Pinax R2).

ÚNICO punto por el que una salida `Admitted` puede cruzar hacia una futura
creación de proceso (M2). En M1 NO existe implementación productiva: cero
`subprocess`, `fork`, `exec`, proceso real, API `start`, `ProcessHost` o
supervisión en el runtime de producción (adenda R1 regla 5). El puerto
existe para que las pruebas (y el gate G2 de INC-5) instrumenten un
spy/test double que contabilice cruces: ante entradas inválidas, cero
cruces («ningún caso inválido inicia proceso», spec §15 M1).

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from typing import Protocol

from ..domain.outcomes import Admitted


class SpawnFrontier(Protocol):
    """Compuerta instrumental de pruebas (D-P4-α). Sin implementación en
    producción M1."""

    def submit(self, admitted: Admitted) -> None:
        """Registra el cruce de una admisión aceptada hacia la frontera de
        spawn. Sólo un `Admitted` puede cruzar (tipado); nada de M1 lo
        invoca fuera de pruebas."""
        ...
