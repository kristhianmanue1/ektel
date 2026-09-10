"""G-M2-01 (parte configuración) — matriz de configuración local M2.

Falsifica la promesa de que la configuración es fail-closed en el arranque:
`bool`, floats, rangos y tipos inválidos deben impedir inicializar, y
`audit_mode=required` debe rechazarse **antes de recibir solicitudes y sin
consumir tokens** (D-M2-5(a)).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.application.config import (  # noqa: E402
    AUDIT_MODE_OPTIONAL,
    M2Config,
    M2ConfigError,
)


class DefaultsTests(unittest.TestCase):
    def test_defaults_son_los_de_d_m2_2_y_3(self) -> None:
        cfg = M2Config.build()
        self.assertEqual(cfg.max_concurrent_actions, 1)
        self.assertEqual(cfg.termination_grace_ms, 2000)
        self.assertEqual(cfg.post_kill_drain_ms, 1000)
        self.assertEqual(cfg.audit_mode, AUDIT_MODE_OPTIONAL)

    def test_config_es_inmutable(self) -> None:
        cfg = M2Config.build()
        with self.assertRaises(Exception):
            cfg.max_concurrent_actions = 2  # type: ignore[misc]

    def test_limites_de_rango_aceptados(self) -> None:
        self.assertEqual(M2Config.build(max_concurrent_actions=1).max_concurrent_actions, 1)
        self.assertEqual(M2Config.build(max_concurrent_actions=64).max_concurrent_actions, 64)
        self.assertEqual(M2Config.build(termination_grace_ms=0).termination_grace_ms, 0)
        self.assertEqual(M2Config.build(termination_grace_ms=60000).termination_grace_ms, 60000)
        self.assertEqual(M2Config.build(post_kill_drain_ms=1).post_kill_drain_ms, 1)
        self.assertEqual(M2Config.build(post_kill_drain_ms=10000).post_kill_drain_ms, 10000)


class HostileTypeTests(unittest.TestCase):
    """`bool` es subclase de `int`: aceptarlo convertiria un error de tipo
    del llamador en configuracion silenciosamente valida."""

    def test_bool_rechazado_en_cada_entero(self) -> None:
        for field in ("max_concurrent_actions", "termination_grace_ms",
                      "post_kill_drain_ms", "credit_timeout_ms",
                      "eof_drain_timeout_ms"):
            for value in (True, False):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(M2ConfigError):
                        M2Config.build(**{field: value})

    def test_float_rechazado_aunque_sea_entero_exacto(self) -> None:
        for field in ("max_concurrent_actions", "termination_grace_ms",
                      "post_kill_drain_ms", "credit_timeout_ms",
                      "eof_drain_timeout_ms"):
            with self.subTest(field=field):
                with self.assertRaises(M2ConfigError):
                    M2Config.build(**{field: 1.0})

    def test_tipos_hostiles_rechazados(self) -> None:
        hostiles = ("1", None, [1], {"v": 1}, object(), 1j)
        for field in ("max_concurrent_actions", "termination_grace_ms",
                      "post_kill_drain_ms"):
            for value in hostiles:
                with self.subTest(field=field, value=type(value).__name__):
                    with self.assertRaises(M2ConfigError):
                        M2Config.build(**{field: value})

    def test_subclase_de_int_no_adquiere_autoridad(self) -> None:
        class Sneaky(int):
            pass
        with self.assertRaises(M2ConfigError):
            M2Config.build(max_concurrent_actions=Sneaky(4))


class RangeTests(unittest.TestCase):
    def test_fuera_de_rango_rechazado(self) -> None:
        casos = [
            ("max_concurrent_actions", 0), ("max_concurrent_actions", 65),
            ("max_concurrent_actions", -1),
            ("termination_grace_ms", -1), ("termination_grace_ms", 60001),
            ("post_kill_drain_ms", 0), ("post_kill_drain_ms", 10001),
            ("credit_timeout_ms", 99), ("credit_timeout_ms", 600001),
            ("eof_drain_timeout_ms", 0), ("eof_drain_timeout_ms", 10001),
        ]
        for field, value in casos:
            with self.subTest(field=field, value=value):
                with self.assertRaises(M2ConfigError):
                    M2Config.build(**{field: value})


class AuditModeFrontierTests(unittest.TestCase):
    """D-M2-5(a): frontera M2/M3."""

    def test_optional_es_el_unico_perfil_operable(self) -> None:
        self.assertEqual(M2Config.build(audit_mode="optional").audit_mode, "optional")

    def test_required_impide_inicializar(self) -> None:
        with self.assertRaises(M2ConfigError) as ctx:
            M2Config.build(audit_mode="required")
        # El diagnostico debe nombrar la causa real: M3 no autorizado.
        self.assertIn("M3", str(ctx.exception))

    def test_required_no_se_degrada_silenciosamente_a_optional(self) -> None:
        with self.assertRaises(M2ConfigError):
            M2Config.build(audit_mode="required")

    def test_valores_desconocidos_rechazados(self) -> None:
        for value in ("Required", "OPTIONAL", "", "absent", None, True, 1):
            with self.subTest(value=value):
                with self.assertRaises(M2ConfigError):
                    M2Config.build(audit_mode=value)


class CotasTemporalesTests(unittest.TestCase):
    """R1: toda cota temporal de comportamiento observable pasa por la misma
    disciplina de D-M2-3, no por constantes inventadas en un adaptador."""

    def test_defaults_declarados(self) -> None:
        cfg = M2Config.build()
        self.assertEqual(cfg.credit_timeout_ms, 30000)
        self.assertEqual(cfg.eof_drain_timeout_ms, 3000)

    def test_el_default_de_credito_es_holgado(self) -> None:
        """R3: un coordinador lento no debe perder salida; el default no puede
        ser tan corto como para castigar la lentitud normal."""
        self.assertGreaterEqual(M2Config.build().credit_timeout_ms, 10000)

    def test_el_host_rechaza_cotas_no_enteras_o_no_positivas(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        for kw in ({"credit_timeout_ms": 0}, {"credit_timeout_ms": 1.0},
                   {"credit_timeout_ms": True}, {"eof_drain_timeout_ms": -1},
                   {"eof_drain_timeout_ms": "500"}):
            with self.subTest(kw=str(kw)):
                with self.assertRaises(ValueError):
                    PosixSupervisorHost(**kw)  # type: ignore[arg-type]


class AssumptionsTests(unittest.TestCase):
    """D-M2-3/ADR-012 §2.3 congela entradas ASCII `clave=valor`: valor, orden
    y forma. FIX-M2-R7: la conformidad es con el **literal** del acta, no con
    una fórmula «matemáticamente equivalente»."""

    def test_las_assumptions_son_las_congeladas_por_adr_012(self) -> None:
        cfg = M2Config.build(termination_grace_ms=1500,
                             subreaper_requested=True)
        self.assertEqual(cfg.guarantee_assumptions(), (
            "termination_grace_ms_configured=1500",
            "useful_runtime_formula=deadline_eff_ms-applied_grace_ms",
            "supervisor_scope=per_action_process",
            "subreaper_requested=1",
        ))

    def test_claves_orden_y_forma_congelados(self) -> None:
        cfg = M2Config.build(termination_grace_ms=1500)
        entries = cfg.guarantee_assumptions()
        claves = [e.split("=", 1)[0] for e in entries]
        self.assertEqual(claves, [
            "termination_grace_ms_configured",
            "useful_runtime_formula",
            "supervisor_scope",
            "subreaper_requested",
        ])
        self.assertTrue(all(e.isascii() for e in entries))
        self.assertEqual(entries[0], "termination_grace_ms_configured=1500")
        self.assertEqual(entries[2], "supervisor_scope=per_action_process")
        self.assertEqual(entries[3], "subreaper_requested=0")

    def test_subreaper_no_solicitado_es_cero(self) -> None:
        entries = M2Config.build().guarantee_assumptions()
        self.assertEqual(entries[3], "subreaper_requested=0")


class AutoridadUnicaTests(unittest.TestCase):
    """FIX-M2-R6 (OAI-M2-03): la configuración fail-closed no puede eludirse
    ni divergir entre admisión, servicio y supervisor."""

    def test_la_construccion_directa_tambien_valida(self) -> None:
        base: dict[str, object] = {
            "max_concurrent_actions": 1, "termination_grace_ms": 2000,
            "post_kill_drain_ms": 1000, "audit_mode": "optional",
            "subreaper_requested": False, "credit_timeout_ms": 30000,
            "eof_drain_timeout_ms": 3000,
        }
        invalidos = [
            {"max_concurrent_actions": 0},
            {"max_concurrent_actions": 65},
            {"termination_grace_ms": 60001},
            {"post_kill_drain_ms": 0},
            {"credit_timeout_ms": 99},
            {"eof_drain_timeout_ms": 10001},
            {"termination_grace_ms": True},
            {"max_concurrent_actions": 1.0},
        ]
        for kw in invalidos:
            with self.subTest(kw=str(kw)):
                valores = dict(base)
                valores.update(kw)
                with self.assertRaises(M2ConfigError):
                    M2Config(**valores)  # type: ignore[arg-type]

    def test_audit_mode_required_imposible_por_cualquier_via(self) -> None:
        with self.assertRaises(M2ConfigError):
            M2Config.build(audit_mode="required")
        with self.assertRaises(M2ConfigError):
            M2Config(
                max_concurrent_actions=1, termination_grace_ms=2000,
                post_kill_drain_ms=1000, audit_mode="required",
                subreaper_requested=False, credit_timeout_ms=30000,
                eof_drain_timeout_ms=3000)

    def test_from_config_propaga_la_unica_autoridad(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        cfg = M2Config.build(termination_grace_ms=777,
                             post_kill_drain_ms=999,
                             subreaper_requested=True)
        host = PosixSupervisorHost.from_config(cfg)
        # La configuración aplicada por el host proviene del mismo objeto.
        self.assertEqual(
            (host._termination_grace_ms, host._post_kill_drain_ms,  # type: ignore[attr-defined]
             host._credit_timeout_ms, host._eof_drain_timeout_ms,
             host._subreaper_requested),  # type: ignore[attr-defined]
            (cfg.termination_grace_ms, cfg.post_kill_drain_ms,
             cfg.credit_timeout_ms, cfg.eof_drain_timeout_ms,
             cfg.subreaper_requested))
        plan_cfg = cfg.guarantee_assumptions()
        self.assertIn("termination_grace_ms_configured=777", plan_cfg)
        self.assertEqual(host.config_fingerprint, cfg.fingerprint)

    def test_fingerprint_es_canonico_determinista_y_completo(self) -> None:
        a = M2Config.build(termination_grace_ms=777)
        b = M2Config.build(termination_grace_ms=777)
        c = M2Config.build(termination_grace_ms=778)
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertRegex(a.fingerprint, r"^[0-9a-f]{64}$")
        self.assertNotEqual(a.fingerprint, c.fingerprint)

    def test_admission_acredita_el_perfil_local_sin_cambiar_wire(self) -> None:
        from src.application.admit import AdmissionService
        from tests.unit.helpers_m1 import (
            MemoryReplayStore, NOW, TEST_KEY, TEST_SALT)
        cfg = M2Config.build(termination_grace_ms=1234)
        admission = AdmissionService(
            replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, wall_clock=lambda: NOW,
            mono_clock=lambda: 0.0, m2_config=cfg)
        self.assertEqual(admission.m2_config_fingerprint, cfg.fingerprint)
        sin_m2 = AdmissionService(
            replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, wall_clock=lambda: NOW,
            mono_clock=lambda: 0.0)
        self.assertIsNone(sin_m2.m2_config_fingerprint)

    def test_2000_1500_500_se_rechaza_antes_del_cas_y_spawn(self) -> None:
        from src.application.admit import AdmissionService
        from src.application.start_service import StartService
        from src.domain.start_outcomes import StartFailed
        from src.domain.start_request import StartRequest
        from tests.unit.helpers_m1 import (
            MemoryReplayStore, NOW, TEST_KEY, TEST_KEY_ID, TEST_SALT,
            valid_request_bytes)
        from tests.unit.helpers_m2 import FakeProcessHost

        admission_cfg = M2Config.build(termination_grace_ms=2000)
        start_cfg = M2Config.build(termination_grace_ms=1500)
        host_cfg = M2Config.build(termination_grace_ms=500)
        admission = AdmissionService(
            replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
            operator_key=TEST_KEY, wall_clock=lambda: NOW,
            mono_clock=lambda: 0.0, m2_config=admission_cfg)
        raw = valid_request_bytes()
        admitted = admission.admit(raw)
        token = getattr(admitted, "admitted_action")
        store = MemoryReplayStore()
        host = FakeProcessHost(config_fingerprint=host_cfg.fingerprint)
        svc = StartService(
            replay_store=store, process_host=host, operator_key=TEST_KEY,
            active_key_id=TEST_KEY_ID, config=start_cfg,
            declared_config_fingerprint=admission.m2_config_fingerprint,
            wall_clock=lambda: float(NOW))
        out = svc.start(StartRequest(
            admitted_action=token, action_request_wire=raw))
        self.assertIsInstance(out, StartFailed)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail,
                         "config:declared_fingerprint_mismatch")
        self.assertEqual(host.spawns, [], "la divergencia precede al spawn")
        self.assertEqual(store._spent, set(), "el token no fue consumido")

    def test_host_sin_acreditacion_no_adquiere_autoridad(self) -> None:
        from src.application.start_service import StartService
        from src.domain.start_outcomes import StartFailed
        from tests.unit.helpers_m1 import (
            MemoryReplayStore, NOW, TEST_KEY, TEST_KEY_ID)
        from tests.unit.helpers_m2 import FakeProcessHost, valid_start_request
        cfg = M2Config.build()
        host = FakeProcessHost()
        svc = StartService(
            replay_store=MemoryReplayStore(), process_host=host,
            operator_key=TEST_KEY, active_key_id=TEST_KEY_ID, config=cfg,
            declared_config_fingerprint=cfg.fingerprint,
            wall_clock=lambda: float(NOW))
        out = svc.start(valid_start_request())
        self.assertIsInstance(out, StartFailed)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "config:host_fingerprint_missing")
        self.assertEqual(host.spawns, [])

    def test_host_divergente_se_rechaza_antes_del_spawn(self) -> None:
        from src.application.start_service import StartService
        from src.domain.start_outcomes import StartFailed
        from tests.unit.helpers_m1 import (
            MemoryReplayStore, NOW, TEST_KEY, TEST_KEY_ID)
        from tests.unit.helpers_m2 import FakeProcessHost, valid_start_request
        cfg = M2Config.build(termination_grace_ms=1500)
        host = FakeProcessHost(config_fingerprint=M2Config.build(
            termination_grace_ms=500).fingerprint)
        svc = StartService(
            replay_store=MemoryReplayStore(), process_host=host,
            operator_key=TEST_KEY, active_key_id=TEST_KEY_ID, config=cfg,
            declared_config_fingerprint=cfg.fingerprint,
            wall_clock=lambda: float(NOW))
        out = svc.start(valid_start_request())
        self.assertIsInstance(out, StartFailed)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "config:host_fingerprint_mismatch")
        self.assertEqual(host.spawns, [])

    def test_drift_aplicado_del_host_se_rechaza_antes_del_cas(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        from src.application.start_service import StartService
        from src.domain.start_outcomes import StartFailed
        from tests.unit.helpers_m1 import (
            MemoryReplayStore, NOW, TEST_KEY, TEST_KEY_ID)
        from tests.unit.helpers_m2 import valid_start_request
        cfg = M2Config.build(termination_grace_ms=1500)
        host = PosixSupervisorHost.from_config(cfg)
        host._termination_grace_ms = 500  # type: ignore[attr-defined]
        store = MemoryReplayStore()
        svc = StartService(
            replay_store=store, process_host=host, operator_key=TEST_KEY,
            active_key_id=TEST_KEY_ID, config=cfg,
            declared_config_fingerprint=cfg.fingerprint,
            wall_clock=lambda: float(NOW))
        out = svc.start(valid_start_request())
        self.assertIsInstance(out, StartFailed)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "config:host_fingerprint_missing")
        self.assertEqual(store._spent, set(), "el rechazo precede al CAS")

    def test_construccion_directa_incoherente_del_host_es_rechazada(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        cfg = M2Config.build(termination_grace_ms=1500)
        with self.assertRaises(ValueError):
            PosixSupervisorHost(
                termination_grace_ms=500, _validated_config=cfg)

    def test_from_config_rechaza_lo_que_no_es_config(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        for impostor in (None, 1, "cfg", object(), {"termination_grace_ms": 1}):
            with self.subTest(tipo=type(impostor).__name__):
                with self.assertRaises(ValueError):
                    PosixSupervisorHost.from_config(impostor)

    def test_el_host_valida_los_rangos_normativos_completos(self) -> None:
        from src.adapters.posix_supervisor import PosixSupervisorHost
        for kw in ({"termination_grace_ms": 60001},
                   {"termination_grace_ms": -1},
                   {"post_kill_drain_ms": 0},
                   {"post_kill_drain_ms": 10001},
                   {"credit_timeout_ms": 99},
                   {"eof_drain_timeout_ms": 10001}):
            with self.subTest(kw=str(kw)):
                with self.assertRaises(ValueError):
                    PosixSupervisorHost(**kw)  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class GuaranteePlanAditivoTests(unittest.TestCase):
    """A-M2-2/A-M2-3: la extensión de `admit.py` es estrictamente aditiva.

    Sin `m2_config` la salida debe ser idéntica a la de M1; con él, se declara
    configuración pero **no se promueve** ninguna garantía.
    """

    def setUp(self) -> None:
        from tests.unit.helpers_m1 import make_service, valid_request_bytes
        self._make_service = make_service
        self._raw = valid_request_bytes()

    def _plan(self, **kw: object) -> tuple[dict[str, object], ...]:
        service = self._make_service()
        if kw:
            from src.application.admit import AdmissionService
            from tests.unit.helpers_m1 import (
                MemoryReplayStore, NOW, TEST_KEY, TEST_SALT)
            service = AdmissionService(
                replay_store=MemoryReplayStore(), deployment_salt=TEST_SALT,
                operator_key=TEST_KEY, wall_clock=lambda: NOW,
                mono_clock=lambda: 0.0, **kw)  # type: ignore[arg-type]
        out = service.admit(self._raw)
        return tuple(getattr(out, "guarantee_plan"))

    def test_sin_m2_config_la_salida_es_la_de_m1(self) -> None:
        for entry in self._plan():
            self.assertEqual(entry["assumptions"], [])
            self.assertEqual(entry["class"], "unsupported")
            self.assertIn("no operado en M1", str(entry["mechanism"]))

    def test_con_m2_config_declara_pero_no_promueve(self) -> None:
        plan = self._plan(m2_config=M2Config.build(termination_grace_ms=1500))
        m2_entries = [e for e in plan
                      if e["magnitude"] in ("runtime_supervision", "output_bounds")]
        self.assertTrue(m2_entries)
        for entry in m2_entries:
            # Declara la configuracion congelada por D-M2-3...
            self.assertIn("termination_grace_ms_configured=1500",
                          entry["assumptions"])  # type: ignore[operator]
            self.assertIn("supervisor_scope=per_action_process",
                          entry["assumptions"])  # type: ignore[operator]
            # ...pero la clase sigue siendo unsupported: declarar no es promover.
            self.assertEqual(entry["class"], "unsupported")

    def test_audit_trail_intacto_es_magnitud_de_m3(self) -> None:
        plan = self._plan(m2_config=M2Config.build())
        audit = [e for e in plan if e["magnitude"] == "audit_trail"]
        for entry in audit:
            self.assertEqual(entry["assumptions"], [])
            self.assertEqual(entry["class"], "unsupported")

    def test_m2_config_invalido_impide_inicializar(self) -> None:
        with self.assertRaises(ValueError):
            self._plan(m2_config="no-es-config")
