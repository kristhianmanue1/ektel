"""G-M2-01 y G-M2-02 — revalidación pura de `start` (ADR-011 §2.3).

G-M2-01: token o request malformados, MAC rota, campos cruzados, request
ejecutable distinto, tipos hostiles, request >64 KiB y expiración producen
**cero CAS y cero procesos**. En INC-M2-1 no existe todavía capa de CAS ni de
spawn: la propiedad se acredita mostrando que la revalidación devuelve
`StartFailed` y no alcanza el plan.

G-M2-02: durante la revalidación hay **cero** `reserve_nonce`, **cero**
`PolicyPort.evaluate` y **cero** emisión de token.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain import admission_token as admission_token_mod  # noqa: E402
from src.domain.revalidation import (  # noqa: E402
    revalidate_start_request,
    verify_admission_token,
)
from src.domain.start_outcomes import (  # noqa: E402
    REASON_CAPABILITY_REJECTED,
    StartFailed,
)
from src.domain.start_request import (  # noqa: E402
    MAX_ACTION_REQUEST_BYTES,
    ExecutionPlan,
)
from tests.unit.helpers_m1 import (  # noqa: E402
    EXP,
    MemoryReplayStore,
    NOW,
    ScriptedPolicy,
    TEST_KEY,
    TEST_KEY_ID,
    emit_request,
    make_request,
    make_service,
)
from tests.unit.helpers_m2 import valid_start_pair  # noqa: E402
from src.ports.policy_port import Allow  # noqa: E402


def revalidate(token: object, raw: object, *, key: bytes = TEST_KEY,
               key_id: str = TEST_KEY_ID, now: float = float(NOW),
               skew: float = 30.0) -> object:
    return revalidate_start_request(token, raw, operator_key=key,
                                    active_key_id=key_id, now_wall=now,
                                    skew_tolerance_s=skew)


class HappyPathTests(unittest.TestCase):
    def test_par_coherente_produce_plan_inmutable(self) -> None:
        token, raw = valid_start_pair()
        plan = revalidate(token, raw)
        self.assertIsInstance(plan, ExecutionPlan)
        assert isinstance(plan, ExecutionPlan)
        self.assertEqual(plan.action_id, "action-0001")
        self.assertEqual(plan.exp_wall, EXP)
        with self.assertRaises(Exception):
            plan.command_absolute = "/bin/sh"  # type: ignore[misc]

    def test_env_del_plan_es_de_solo_lectura(self) -> None:
        token, raw = valid_start_pair()
        plan = revalidate(token, raw)
        assert isinstance(plan, ExecutionPlan)
        with self.assertRaises(TypeError):
            plan.env["PATH"] = "/evil"  # type: ignore[index]

    def test_args_del_plan_es_tupla(self) -> None:
        token, raw = valid_start_pair()
        plan = revalidate(token, raw)
        assert isinstance(plan, ExecutionPlan)
        self.assertIsInstance(plan.args, tuple)


class Paso1TipoYTechoTests(unittest.TestCase):
    """Paso 1: tipos exactos y techo **antes** del parseo."""

    def test_tipos_hostiles_en_admitted_action(self) -> None:
        _, raw = valid_start_pair()
        for value in (None, 1, b"bytes", ["x"], {"a": 1}, object(), True):
            with self.subTest(tipo=type(value).__name__):
                out = revalidate(value, raw)
                self.assertIsInstance(out, StartFailed)
                assert isinstance(out, StartFailed)
                self.assertEqual(out.safe_detail, "request:admitted_action-type")

    def test_subclase_de_str_no_adquiere_autoridad(self) -> None:
        token, raw = valid_start_pair()

        class Sneaky(str):
            pass
        out = revalidate(Sneaky(token), raw)
        self.assertIsInstance(out, StartFailed)

    def test_tipos_hostiles_en_wire(self) -> None:
        token, _ = valid_start_pair()
        for value in (None, 1, "cadena", ["x"], bytearray(b"ab"), memoryview(b"ab")):
            with self.subTest(tipo=type(value).__name__):
                out = revalidate(token, value)
                self.assertIsInstance(out, StartFailed)
                assert isinstance(out, StartFailed)
                self.assertEqual(out.safe_detail, "request:action_request_wire-type")

    def test_request_sobre_64_kib_rechazado_antes_de_parsear(self) -> None:
        token, _ = valid_start_pair()
        oversized = b"{" + b"a" * MAX_ACTION_REQUEST_BYTES
        out = revalidate(token, oversized)
        self.assertIsInstance(out, StartFailed)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "request:action_request_wire-too-large")

    def test_exactamente_64_kib_no_se_rechaza_por_techo(self) -> None:
        token, _ = valid_start_pair()
        out = revalidate(token, b"x" * MAX_ACTION_REQUEST_BYTES)
        assert isinstance(out, StartFailed)
        self.assertNotEqual(out.safe_detail, "request:action_request_wire-too-large")


class Paso2TokenTests(unittest.TestCase):
    """Paso 2: forma, canonicalidad, MAC, payload cerrado y vigencia."""

    def test_token_no_canonico_rechazado(self) -> None:
        token, raw = valid_start_pair()
        out = revalidate(token + "=", raw)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "token:b64-noncanonical")

    def test_token_vacio_rechazado(self) -> None:
        _, raw = valid_start_pair()
        out = revalidate("", raw)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "token:b64-noncanonical")

    def test_mac_rota_rechazada(self) -> None:
        token, raw = valid_start_pair()
        otra_clave = bytes(range(1, 33))
        out = revalidate(token, raw, key=otra_clave)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "token:mac-invalid")

    def test_expirado_es_estricto_y_sin_skew(self) -> None:
        """Invariante 6: el skew de admision no concede tiempo de ejecucion."""
        token, raw = valid_start_pair()
        # Justo en `exp`: `now < exp` es falso, luego expira aunque el skew
        # de admision fuese generoso.
        out = revalidate(token, raw, now=float(EXP), skew=3600.0)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "token:expired")

    def test_un_instante_antes_de_exp_sigue_vigente(self) -> None:
        token, raw = valid_start_pair()
        out = revalidate(token, raw, now=float(EXP) - 1.0)
        self.assertIsInstance(out, ExecutionPlan)

    def test_reloj_no_finito_rechazado(self) -> None:
        token, raw = valid_start_pair()
        for now in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(now=now):
                out = revalidate(token, raw, now=now)
                assert isinstance(out, StartFailed)
                self.assertEqual(out.safe_detail, "token:clock-invalid")

    def test_todo_rechazo_usa_capability_rejected(self) -> None:
        _, raw = valid_start_pair()
        out = revalidate("no-es-un-token", raw)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_CAPABILITY_REJECTED)

    def test_verificador_de_token_devuelve_payload_cerrado(self) -> None:
        token, _ = valid_start_pair()
        payload = verify_admission_token(token, TEST_KEY, float(NOW))
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertEqual(set(payload), {
            "schema_version", "identity_digest", "action_id", "exp", "issuer_id"})


class Paso3a6CoherenciaTests(unittest.TestCase):
    def test_wire_malformado_rechazado(self) -> None:
        token, _ = valid_start_pair()
        for raw in (b"", b"{", b"null", b"[]", b'{"a":1}'):
            with self.subTest(raw=raw[:8]):
                out = revalidate(token, raw)
                assert isinstance(out, StartFailed)
                self.assertTrue(out.safe_detail.startswith("contract:"))

    def test_request_ejecutable_distinto_rechazado(self) -> None:
        """El token de una accion no autoriza otro ejecutable."""
        token, _ = valid_start_pair()
        otro = emit_request(make_request(command="/usr/bin/false"))
        out = revalidate(token, otro)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_CAPABILITY_REJECTED)

    def test_campos_cruzados_entre_dos_admisiones(self) -> None:
        """Token de la accion A + descriptor de la accion B: rechazado."""
        token_a, _ = valid_start_pair()
        raw_b = emit_request(make_request(action_id="action-0002"))
        out = revalidate(token_a, raw_b)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.reason_code, REASON_CAPABILITY_REJECTED)

    def test_key_id_inactivo_rechazado(self) -> None:
        token, raw = valid_start_pair()
        out = revalidate(token, raw, key_id="0" * 16)
        assert isinstance(out, StartFailed)
        self.assertEqual(out.safe_detail, "key_id_mismatch")


class PurezaTests(unittest.TestCase):
    """G-M2-02: cero reserve_nonce, cero PolicyPort.evaluate, cero token."""

    def test_revalidacion_no_toca_store_ni_politica_ni_emite_token(self) -> None:
        store = MemoryReplayStore()
        policy = ScriptedPolicy(Allow(decision_id="d1", valid_until_wall=float(EXP)))
        raw = emit_request(make_request())
        service = make_service(store=store, policy_port=policy, policy_mode="required")
        admitted = service.admit(raw)
        token = getattr(admitted, "admitted_action")

        # Instrumentacion: contar cruces a partir de aqui.
        reservas: list[tuple[str, str]] = []
        original_reserve = store.reserve_nonce

        def contando_reserve(issuer_id: str, nonce: str,
                             until: float) -> object:
            reservas.append((issuer_id, nonce))
            return original_reserve(issuer_id, nonce, until)

        store.reserve_nonce = contando_reserve  # type: ignore[assignment]
        policy.calls.clear()

        emisiones: list[str] = []
        original_build = admission_token_mod.build_admission_token

        def contando_build(operator_key: bytes, identity_digest: str,
                           action_id: str, exp_wall: int,
                           issuer_id: str) -> str:
            emisiones.append("build")
            return original_build(operator_key, identity_digest, action_id,
                                  exp_wall, issuer_id)

        admission_token_mod.build_admission_token = contando_build
        try:
            plan = revalidate(token, raw)
        finally:
            admission_token_mod.build_admission_token = original_build

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertEqual(reservas, [], "start no puede reservar nonce")
        self.assertEqual(policy.calls, [], "start no puede evaluar PolicyPort")
        self.assertEqual(emisiones, [], "start no puede emitir otro token")

    def test_la_firma_no_admite_puertos(self) -> None:
        """Pureza estructural: la revalidacion no recibe puertos, luego no
        puede producir un efecto durable aunque el codigo cambiara."""
        import inspect
        params = set(inspect.signature(revalidate_start_request).parameters)
        for prohibido in ("replay_store", "policy_port", "store", "clock",
                          "wall_clock", "audit_sink"):
            self.assertNotIn(prohibido, params)

    def test_revalidar_dos_veces_da_el_mismo_plan(self) -> None:
        """Determinismo: sin efectos, revalidar es idempotente."""
        token, raw = valid_start_pair()
        primero = revalidate(token, raw)
        segundo = revalidate(token, raw)
        self.assertEqual(primero, segundo)


class SinSpawnTests(unittest.TestCase):
    """INC-M2-1 no crea procesos: ni en el camino feliz ni en el de fallo."""

    def test_ningun_subproceso_en_el_modulo(self) -> None:
        import src.domain.revalidation as mod
        fuente = Path(mod.__file__).read_text(encoding="utf-8")
        for prohibido in ("subprocess", "os.fork", "os.exec", "posix_spawn",
                          "multiprocessing"):
            self.assertNotIn(prohibido, fuente)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
