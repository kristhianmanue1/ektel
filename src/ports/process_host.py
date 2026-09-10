"""Puerto de proceso/IPC estrictamente local (paquete M2 §7).

Frontera M2 del inicio de procesos. Es **paralela** a la frontera instrumental
`SpawnFrontier` de M1, que el acta de autorización M2 (A-M2-1) preserva
intacta: este puerto no la sustituye ni la retira.

Diferencia con `SpawnFrontier`: aquella recibía un `Admitted` (firma
pre-ADR-011, que no es el nuevo handoff) y sólo contabilizaba cruces. Este
puerto recibe un `ExecutionPlan` ya revalidado y es el único punto por el que
M2 puede crear un proceso.

En INC-M2-2 sólo existen dobles deterministas: no hay adaptador POSIX real
hasta INC-M2-3.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from typing import Optional

from ..domain.execution_result import TerminalHandoff
from ..domain.start_request import ExecutionPlan


class SpawnRejected(Exception):
    """Fallo **explícito y síncrono** de la primitiva **antes** de crear
    proceso (ADR-011 §2.6): produce `start_failed`, nunca indeterminado."""

    def __init__(self, safe_detail: str = "") -> None:
        super().__init__(safe_detail)
        self.safe_detail = safe_detail


@runtime_checkable
class ProcessHost(Protocol):
    """Creación y terminación de procesos supervisados, todo local."""

    @property
    def config_fingerprint(self) -> str:
        """Perfil M2 completo que el host acredita aplicar localmente."""
        ...

    def spawn(self, plan: ExecutionPlan, *, deadline_eff_ms: int,
              config_fingerprint: str | None = None,
              validity_bound: bool = False) -> str:
        """Crea el proceso bajo el plan inmutable y devuelve `handle_ref`
        (16 hex). Lanza `SpawnRejected` si falla **antes** de crearlo.

        Cualquier otra excepción se trata como indeterminada: el runtime no
        puede afirmar que no exista un proceso.
        """
        ...

    def request_termination(self, handle_ref: str) -> None:
        """Terminación best-effort del grupo observado. No promete muerte
        universal ni recuperación de procesos escapados."""
        ...

    def collect_terminal(self, handle_ref: str, *,
                         timeout: Optional[float]) -> Optional[TerminalHandoff]:
        """Espera del traspaso terminal. Con `timeout` finito, `None` si no
        llegó dentro del plazo: ausencia honesta, nunca un resultado
        fabricado. Con `timeout=None` espera hasta el cierre definitivo del
        terminal (entrega o ausencia sin resultado) — es la modalidad que usa
        el vigilante único del coordinador (FIX-M2-R2/R3).
        """
        ...
