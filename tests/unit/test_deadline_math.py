"""G-M2-09 — aritmética de plazo y clasificación terminal (D-M2-3, ADR-005).

Puro y determinista: relojes inyectados, sin procesos.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.domain.deadline import (  # noqa: E402
    PayloadBounds,
    payload_bounds,
    wall_sample_valid,
    ceil_exact_ms,
    compute_bounds,
    deadline_eff_ms,
    remaining_validity_ms,
    validity_exhausted,
)
from src.domain.execution_result import (  # noqa: E402
    CAUSE_DEADLINE_DURATION,
    CAUSE_DEADLINE_VALIDITY_EXHAUSTED,
    CAUSE_EXTERNAL_TERMINATION,
    CAUSE_NATURAL_EXIT,
    CAUSE_SUPERVISION_FAILURE,
    OUTCOME_SUPERVISION_FAILED,
    ExecutionResult,
    MEASUREMENT_KEYS,
    OUTCOME_DEADLINE_EXCEEDED,
    OUTCOME_EXECUTED,
    OUTCOME_SUPERVISION_FAILED,
    OUTCOME_TERMINATED,
    classify,
    freeze_measurements,
)


class CeilExactoTests(unittest.TestCase):
    """`ceil_exact_ms` nunca redondea hacia abajo: hacerlo regalaria tiempo de
    ejecucion despues de `exp`."""

    def test_redondea_hacia_arriba(self) -> None:
        self.assertEqual(ceil_exact_ms(1.0), 1000)
        self.assertEqual(ceil_exact_ms(1.0001), 1001)
        self.assertEqual(ceil_exact_ms(1.0009), 1001)

    def test_negativos_tambien_redondean_hacia_arriba(self) -> None:
        self.assertEqual(ceil_exact_ms(-1.0), -1000)
        self.assertEqual(ceil_exact_ms(-1.0001), -1000)

    def test_no_representable_devuelve_none(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf"), 1, "1", None):
            with self.subTest(value=value):
                self.assertIsNone(ceil_exact_ms(value))  # type: ignore[arg-type]


class VigenciaTests(unittest.TestCase):
    def test_vigencia_restante(self) -> None:
        self.assertEqual(remaining_validity_ms(100, 99.0), 1000)

    def test_plazo_efectivo_es_el_minimo(self) -> None:
        self.assertEqual(deadline_eff_ms(5000, 1000, 100.0), 5000)
        self.assertEqual(deadline_eff_ms(5000, 100, 99.5), 500)

    def test_vida_util_no_positiva_devuelve_none(self) -> None:
        """Rechazar ANTES de consumir: no se gasta un token para crear un
        proceso sin vida util."""
        self.assertIsNone(deadline_eff_ms(5000, 100, 100.0))
        self.assertIsNone(deadline_eff_ms(5000, 100, 101.0))

    def test_empate_duracion_vigencia_gana_vigencia(self) -> None:
        self.assertTrue(validity_exhausted(5000, 5000))
        self.assertTrue(validity_exhausted(5000, 4999))
        self.assertFalse(validity_exhausted(5000, 5001))


class CotasTests(unittest.TestCase):
    def test_formulas_de_d_m2_3(self) -> None:
        b = compute_bounds(5000, 2000)
        self.assertEqual(b.applied_grace_ms, 2000)
        self.assertEqual(b.useful_runtime_ms, 3000)
        self.assertEqual(b.soft_termination_after_start_ms, 3000)
        self.assertEqual(b.hard_deadline_after_start_ms, 5000)

    def test_gracia_mayor_o_igual_que_el_plazo_deja_vida_util_cero(self) -> None:
        for grace in (5000, 9000):
            with self.subTest(grace=grace):
                b = compute_bounds(5000, grace)
                self.assertEqual(b.applied_grace_ms, 5000)
                self.assertEqual(b.useful_runtime_ms, 0)

    def test_gracia_cero_significa_kill_directo(self) -> None:
        b = compute_bounds(5000, 0)
        self.assertEqual(b.applied_grace_ms, 0)
        self.assertEqual(b.useful_runtime_ms, 5000)

    def test_entradas_invalidas_rechazadas(self) -> None:
        for args in ((0, 1000), (-1, 1000), (1.0, 1000), (True, 1000),
                     (5000, -1), (5000, 1.0), (5000, True)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    compute_bounds(*args)  # type: ignore[arg-type]


class ClasificacionTests(unittest.TestCase):
    def test_salida_natural(self) -> None:
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=False,
                     validity_bound=False, externally_terminated=False),
            (OUTCOME_EXECUTED, CAUSE_NATURAL_EXIT))

    def test_executed_no_significa_exito(self) -> None:
        """Invariante 9: la clasificacion es por causa, no por exit status."""
        r = ExecutionResult(
            outcome=OUTCOME_EXECUTED, cause=CAUSE_NATURAL_EXIT, exit_status=1,
            duration_monotonic_ms=1, finished_at_wall=None,
            guarantees_applied=(), measurements=freeze_measurements({}))
        self.assertEqual(r.outcome, OUTCOME_EXECUTED)
        self.assertEqual(r.exit_status, 1)

    def test_deadline_gana_el_empate_con_terminacion(self) -> None:
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=False, externally_terminated=True),
            (OUTCOME_DEADLINE_EXCEEDED, CAUSE_DEADLINE_DURATION))

    def test_primer_hecho_observado_decide_la_carrera(self) -> None:
        """FIX-M2-R8 (OAI-M2-05): la causalidad terminate/deadline se decide
        por el primer hecho observado, no por una precedencia estática."""
        from src.domain.execution_result import (
            CAUSE_EXTERNAL_TERMINATION, OUTCOME_TERMINATED)
        # Terminación externa observada primero → terminated.
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=False, externally_terminated=True,
                     first_terminal_cause="external_termination"),
            (OUTCOME_TERMINATED, CAUSE_EXTERNAL_TERMINATION))
        # Deadline observado primero → deadline_exceeded.
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=False, externally_terminated=True,
                     first_terminal_cause="deadline"),
            (OUTCOME_DEADLINE_EXCEEDED, CAUSE_DEADLINE_DURATION))
        # Causalidad desconocida/empate definido → deadline (ADR-005).
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=False, externally_terminated=True,
                     first_terminal_cause=None),
            (OUTCOME_DEADLINE_EXCEEDED, CAUSE_DEADLINE_DURATION))
        # La causalidad no altera la causa de plazo por vigencia.
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=True, externally_terminated=True,
                     first_terminal_cause="deadline"),
            (OUTCOME_DEADLINE_EXCEEDED, CAUSE_DEADLINE_VALIDITY_EXHAUSTED))

    def test_vigencia_gana_la_causa_del_plazo(self) -> None:
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=True,
                     validity_bound=True, externally_terminated=False),
            (OUTCOME_DEADLINE_EXCEEDED, CAUSE_DEADLINE_VALIDITY_EXHAUSTED))

    def test_terminacion_externa(self) -> None:
        self.assertEqual(
            classify(supervision_failure=False, deadline_hit=False,
                     validity_bound=False, externally_terminated=True),
            (OUTCOME_TERMINATED, CAUSE_EXTERNAL_TERMINATION))

    def test_fallo_de_supervision_no_se_disimula(self) -> None:
        self.assertEqual(
            classify(supervision_failure=True, deadline_hit=True,
                     validity_bound=True, externally_terminated=True),
            (OUTCOME_SUPERVISION_FAILED, CAUSE_SUPERVISION_FAILURE))

    def test_vocabulario_cerrado(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionResult(outcome="ok", cause=CAUSE_NATURAL_EXIT,
                            exit_status=0, duration_monotonic_ms=0,
                            finished_at_wall=None, guarantees_applied=(),
                            measurements=freeze_measurements({}))
        with self.assertRaises(ValueError):
            ExecutionResult(outcome=OUTCOME_EXECUTED, cause="porque_si",
                            exit_status=0, duration_monotonic_ms=0,
                            finished_at_wall=None, guarantees_applied=(),
                            measurements=freeze_measurements({}))


class MedicionesTests(unittest.TestCase):
    def test_claves_congeladas_completas_y_en_orden(self) -> None:
        m = freeze_measurements({})
        self.assertEqual(tuple(m), MEASUREMENT_KEYS)

    def test_forced_pipe_close_es_entero_no_booleano(self) -> None:
        """D-M2-3 lo fija como entero `0|1`; no se 'mejora' a bool."""
        m = freeze_measurements({"post_kill_forced_pipe_close": True})
        self.assertEqual(m["post_kill_forced_pipe_close"], 1)
        self.assertIsNot(m["post_kill_forced_pipe_close"], True)

    def test_valores_no_enteros_no_contaminan(self) -> None:
        m = freeze_measurements({"useful_runtime_ms": "3000",
                                 "discarded_bytes": None})
        self.assertEqual(m["useful_runtime_ms"], 0)
        self.assertEqual(m["discarded_bytes"], 0)

    def test_las_mediciones_son_de_solo_lectura(self) -> None:
        m = freeze_measurements({})
        with self.assertRaises(TypeError):
            m["useful_runtime_ms"] = 1  # type: ignore[index]


class MuestraDeParedTests(unittest.TestCase):
    """G-M2-09: la muestra final de pared sólo alimenta `finished_at_wall`.

    Si no es finita o REGRESA respecto de la inicial, se produce
    `supervision_failed` y **no se fabrican tiempos**.
    """

    def test_muestra_normal_es_valida(self) -> None:
        self.assertTrue(wall_sample_valid(100.0, 100.5))
        self.assertTrue(wall_sample_valid(100.0, 100.0), "empate es valido")

    def test_regresion_invalida(self) -> None:
        self.assertFalse(wall_sample_valid(100.0, 99.999))
        self.assertFalse(wall_sample_valid(100.0, 0.0))
        self.assertFalse(wall_sample_valid(100.0, -1.0))

    def test_no_finita_invalida(self) -> None:
        for valor in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(valor=valor):
                self.assertFalse(wall_sample_valid(100.0, valor))
                self.assertFalse(wall_sample_valid(valor, 100.0))

    def test_tipos_hostiles_invalidos(self) -> None:
        for valor in (100, "100.0", None, True, [100.0]):
            with self.subTest(tipo=type(valor).__name__):
                self.assertFalse(wall_sample_valid(100.0, valor))

    def test_muestra_invalida_produce_supervision_failed(self) -> None:
        """Enlace con la clasificacion: no se degrada a otra causa."""
        self.assertEqual(
            classify(supervision_failure=not wall_sample_valid(100.0, 99.0),
                     deadline_hit=True, validity_bound=True,
                     externally_terminated=True),
            (OUTCOME_SUPERVISION_FAILED, CAUSE_SUPERVISION_FAILURE))


class CotasDePayloadTests(unittest.TestCase):
    """G-M2-07/G-M2-12: fórmulas literales de D-M2-1(a)."""

    def test_formulas_literales(self) -> None:
        b = payload_bounds(1000, 2000, 65536)
        self.assertEqual(b.stable_bytes, 1000 + 2000 + 2 * 65536)
        self.assertEqual(b.materialization_peak_bytes,
                         2 * (1000 + 2000) + 2 * 65536)
        self.assertEqual(b.frame_reserve_bytes, 2 * 65536)

    def test_limites_maximos_para_64_acciones(self) -> None:
        """G-M2-12: confirma ARITMETICAMENTE las cifras del gate.

        Con `max_stdout_bytes = max_stderr_bytes = 64 MiB` y 64 acciones:
        8 GiB + 8 MiB estables y 16 GiB + 8 MiB de pico.
        Esta prueba confirma la **formula publicada**; la ejecucion real a esa
        escala NO se realiza y queda declarada como laguna en la evidencia.
        """
        mib = 1024 * 1024
        gib = 1024 * mib
        b = payload_bounds(64 * mib, 64 * mib, 65536, concurrent_actions=64)
        self.assertEqual(b.stable_bytes, 8 * gib + 8 * mib)
        self.assertEqual(b.materialization_peak_bytes, 16 * gib + 8 * mib)

    def test_default_de_una_accion(self) -> None:
        mib = 1024 * 1024
        b = payload_bounds(64 * mib, 64 * mib, 65536, concurrent_actions=1)
        self.assertEqual(b.stable_bytes, 128 * mib + 128 * 1024)
        self.assertEqual(b.materialization_peak_bytes, 256 * mib + 128 * 1024)

    def test_entradas_invalidas_rechazadas(self) -> None:
        for kw in ({"max_stdout_bytes": -1}, {"max_stderr_bytes": 1.0},
                   {"max_stdout_bytes": True}, {"concurrent_actions": 0.5}):
            with self.subTest(kw=str(kw)):
                base = {"max_stdout_bytes": 1024, "max_stderr_bytes": 1024}
                base.update(kw)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    payload_bounds(**base)  # type: ignore[arg-type]

    def test_no_es_una_cota_de_rss(self) -> None:
        b = payload_bounds(1024, 1024)
        self.assertIsInstance(b, PayloadBounds)
        self.assertFalse(hasattr(b, "rss_bytes"),
                         "el payload no se presenta como memoria del proceso")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
