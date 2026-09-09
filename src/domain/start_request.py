"""`StartRequest` y plan de ejecución inmutable (ADR-011 §2.1 y §2.3.7).

ADR-011 sustituyó la firma incompleta `start(AdmittedAction)`: el
`admitted_action` v1 sólo autentica
`{identity_digest, action_id, exp, issuer_id}` y no contiene comando,
argumentos, entorno, cwd, stdin, límites de salida ni `deadline_ms`. El
llamador reenvía el `ActionRequest` bajo el techo global de 64 KiB:

    StartRequest { admitted_action: str, action_request_wire: bytes }

`StartRequest` es un **tipo local experimental del núcleo**, no un documento
JSON ni una capacidad. Si en el futuro cruza un límite de proceso o red
deberá obtener un wire contract versionado propio; ADR-011 no reserva esa
forma y este módulo no la anticipa.

`ExecutionPlan` es el resultado del paso 7 de ADR-011 §2.3: se construye a
partir de **una única instantánea validada** y es inmutable. Nada posterior
al plan puede reabrir la validación ni releer una fuente mutable.

**Garantía exacta (ADR-011 §2.2):** equivalencia revalidada, no identidad de
bytes. El plan demuestra que el material ejecutable ligado por el contrato
volvió a superar todas las validaciones determinantes; **no** demuestra
igualdad byte-a-byte del documento exterior. Ningún claim puede llamar a
estos campos «bytes originales».

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

#: Techo global del documento exterior (spec §5; ADR-011 §2.1).
MAX_ACTION_REQUEST_BYTES = 65536


@dataclass(frozen=True)
class StartRequest:
    """Par local que el llamador entrega a `start`. Los tipos son exactos:
    una subclase de `str`/`bytes` no adquiere autoridad en esta frontera."""
    admitted_action: str
    action_request_wire: bytes


@dataclass(frozen=True)
class ExecutionPlan:
    """Instantánea validada e inmutable de la ejecución autorizada.

    Contiene sólo lo que el proceso necesitará: el entorno revalidado, cwd,
    argv y stdin autorizados (invariante 8: no hereda secretos ni descriptores
    ajenos), más la identidad autenticada para la reconciliación CAS.
    """
    identity_digest: str
    action_id: str
    issuer_id: str
    exp_wall: int
    command_absolute: str
    args: tuple[str, ...]
    cwd: str
    env: Mapping[str, str]
    stdin_bytes: bytes
    deadline_ms: int
    max_stdout_bytes: int
    max_stderr_bytes: int

    @staticmethod
    def freeze_env(env: Mapping[str, str]) -> Mapping[str, str]:
        """Vista de sólo lectura del entorno revalidado."""
        return MappingProxyType(dict(env))
