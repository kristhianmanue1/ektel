"""Frontera instrumental de spawn — implementación de PRUEBA (D-P4-α;
adenda R1 regla 5; confirmada por Pinax R2).

Contabiliza cruces para el gate G2 («ningún caso inválido inicia
proceso»): tras la suite negativa y el fuzz, `total_crossings()` debe ser
coincidente con las salidas `Admitted` y **0 para entradas inválidas**.

Cero `subprocess`/`fork`/`exec`/API `start` productiva (regla 5 R1): esto
es instrumental de pruebas, no runtime. Un cruce con crash simulado
ejercita `start_failed_indeterminate` (§8.3: crash entre CAS de consumo y
spawn → token gastado, resultado indeterminado, nunca replay).

API EXPERIMENTAL (spec §16). stdlib-only. SÓLO pruebas.
"""
from __future__ import annotations

from ..domain.outcomes import Admitted


class SpawnCrossing:
    """Registro de un cruce por la frontera."""

    __slots__ = ("identity_digest", "action_id")

    def __init__(self, admitted: Admitted) -> None:
        self.identity_digest = admitted.identity_digest
        self.action_id = _action_id_of(admitted)


def _action_id_of(admitted: Admitted) -> str:
    # El action_id viaja firmado dentro del token; para el instrumental
    # basta la correlación por digest (M2 dará la semántica completa).
    return ""


class SpawnFrontierCounter:
    """Contador/registro de cruces (spy). Sin efectos, sin procesos."""

    def __init__(self) -> None:
        self.crossings: list[SpawnCrossing] = []

    def submit(self, admitted: Admitted) -> None:
        self.crossings.append(SpawnCrossing(admitted))

    def total_crossings(self) -> int:
        return len(self.crossings)

    def crossings_for(self, identity_digest: str) -> int:
        return sum(1 for c in self.crossings if c.identity_digest == identity_digest)
