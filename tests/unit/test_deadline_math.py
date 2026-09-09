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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
