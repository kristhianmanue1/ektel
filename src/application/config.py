"""Configuración local M2 validada — D-M2-2, D-M2-3 y D-M2-5 (ADR-012).

Configuración **local, no wire**: ningún valor de este módulo viaja en un
documento ni aparece en un schema. Los tipos son exactos y la validación es
fail-closed **en el arranque**, no por petición: `bool`, floats, valores
fuera de rango y tipos hostiles impiden inicializar el servicio, antes de
recibir solicitudes y sin consumir tokens.

`bool` se rechaza explícitamente aunque sea subclase de `int`: aceptar
`True` como `max_concurrent_actions=1` convertiría un error de tipo del
llamador en una configuración silenciosamente válida.

**Frontera M2/M3 (D-M2-5(a)):** `audit_mode` sólo acepta `optional`.
`required` se **reconoce** para rechazar la inicialización, porque exige un
evento durable previo al inicio y `RuntimeEvent`/`AuditSink` son entregables
de M3. M2 no crea eventos, sink, recibos ni un puerto sustituto con semántica
inventada. Esto **no** elimina la obligación normativa de emitir el evento:
`audit_mode=optional` evita el bloqueo por durabilidad, pero la obligación y
su prueba quedan pendientes de M3 (G-M2-10), no satisfechas ficticiamente.

**Capacidad, no memoria baja (D-M2-2(a)):** `max_concurrent_actions` es una
cota de capacidad. Con límites wire máximos, el default `1` permite
128 MiB + 128 KiB estables y un pico transitorio de hasta 256 MiB + 128 KiB;
el máximo `64` permite 8 GiB + 8 MiB estables y un pico de 16 GiB + 8 MiB,
más overhead de objetos, pipes y kernel. El perfil de despliegue debe
publicar ambos límites y la caracterización de RSS: **está prohibido
presentar este rango como garantía de RSS baja**.

API EXPERIMENTAL (spec §16). stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Único perfil de auditoría que M2 puede operar (D-M2-5(a)).
AUDIT_MODE_OPTIONAL = "optional"
#: Reconocido sólo para rechazar la inicialización hasta que M3 esté autorizado.
AUDIT_MODE_REQUIRED = "required"
AUDIT_MODES = (AUDIT_MODE_OPTIONAL, AUDIT_MODE_REQUIRED)

MAX_CONCURRENT_ACTIONS_RANGE = (1, 64)
TERMINATION_GRACE_MS_RANGE = (0, 60000)
POST_KILL_DRAIN_MS_RANGE = (1, 10000)

#: Alcance del supervisor fijado por D-M2-2(a): uno dedicado por acción.
SUPERVISOR_SCOPE_PER_ACTION = "per_action"


class M2ConfigError(ValueError):
    """Configuración local inválida. Impide inicializar el servicio."""


def _exact_int_in_range(value: object, name: str, low: int, high: int) -> int:
    """Entero exacto dentro de rango. `bool` y floats se rechazan."""
    if type(value) is not int:
        return _reject(name, "tipo exacto int requerido")
    if not low <= value <= high:
        return _reject(name, f"fuera de rango [{low}, {high}]")
    return value


def _reject(name: str, detail: str) -> int:
    raise M2ConfigError(f"{name}: {detail}")


@dataclass(frozen=True)
class M2Config:
    """Configuración local validada de la supervisión M2.

    Construir esta clase directamente **no** valida; use `M2Config.build()`.
    """
    max_concurrent_actions: int
    termination_grace_ms: int
    post_kill_drain_ms: int
    audit_mode: str
    subreaper_requested: bool

    @staticmethod
    def build(
        *,
        max_concurrent_actions: object = 1,
        termination_grace_ms: object = 2000,
        post_kill_drain_ms: object = 1000,
        audit_mode: object = AUDIT_MODE_OPTIONAL,
        subreaper_requested: object = False,
    ) -> "M2Config":
        """Valida y construye. Fail-closed: cualquier defecto es excepción,
        nunca un `StartFailed` ni un valor por defecto silencioso."""
        concurrent = _exact_int_in_range(
            max_concurrent_actions, "max_concurrent_actions",
            *MAX_CONCURRENT_ACTIONS_RANGE)
        grace = _exact_int_in_range(
            termination_grace_ms, "termination_grace_ms",
            *TERMINATION_GRACE_MS_RANGE)
        drain = _exact_int_in_range(
            post_kill_drain_ms, "post_kill_drain_ms",
            *POST_KILL_DRAIN_MS_RANGE)
        if type(audit_mode) is not str or audit_mode not in AUDIT_MODES:
            raise M2ConfigError(
                f"audit_mode: valor invalido; se esperaba uno de {AUDIT_MODES}")
        if type(subreaper_requested) is not bool:
            raise M2ConfigError("subreaper_requested: tipo exacto bool requerido")
        if audit_mode == AUDIT_MODE_REQUIRED:
            # Frontera M2/M3: no se degrada a optional ni se finge soporte.
            raise M2ConfigError(
                "audit_mode: 'required' exige RuntimeEvent y AuditSink, que son "
                "entregables de M3; M3 no esta autorizado")
        return M2Config(
            max_concurrent_actions=concurrent,
            termination_grace_ms=grace,
            post_kill_drain_ms=drain,
            audit_mode=audit_mode,
            subreaper_requested=subreaper_requested,
        )

    def guarantee_assumptions(
        self, supervisor_scope: str = SUPERVISOR_SCOPE_PER_ACTION,
        subreaper_requested: bool | None = None,
    ) -> tuple[str, ...]:
        """Entradas ASCII `clave=valor` congeladas por D-M2-3 para
        `GuaranteePlan.assumptions`. Orden fijo; sin texto libre.

        `subreaper_requested` toma por defecto el valor de la configuración;
        el parámetro sólo existe para pruebas que ejerciten ambos valores.
        """
        requested = (self.subreaper_requested if subreaper_requested is None
                     else subreaper_requested)
        return (
            f"termination_grace_ms_configured={self.termination_grace_ms}",
            "useful_runtime_formula=useful_runtime_ms="
            "deadline_eff_ms-min(termination_grace_ms,deadline_eff_ms)",
            f"supervisor_scope={supervisor_scope}",
            f"subreaper_requested={'1' if requested else '0'}",
        )
