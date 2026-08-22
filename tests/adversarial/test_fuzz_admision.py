"""Gate permanente G8: fuzz de admisión con oráculo (INC-5; spec §15 M1
«fuzzing sin aceptación ambigua»).

Congela: bases, mutaciones por clase, fingerprint del corpus de bases.
Verifica SENSIBILIDAD (definición de terminado del paquete §9):

1. DIVERGENCIA ARTIFICIAL: oráculo saboteado (expectativa cambiada para
   una clase) → el gate falla.
2. ERROR COMÚN: implementación saboteada con el diagnóstico incorrecto
   (todo → malformed_descriptor) → el gate lo detiene (el oráculo se
   comprueba contra la implementación por separado).
3. CRASH: implementación que lanza RuntimeError → el gate lo reporta
   como crash, nunca lo propaga.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

import fuzz_admision as fz  # noqa: E402
from src.domain.outcomes import AdmissionRejected  # noqa: E402

# Congelados del fuzz de admisión (INC-5, 2026-08-22; re-basable por
# diseño si cambia el corpus de bases):
BASES = 2
TOTAL_MUTATIONS = 63            # 21 clases x 3 pasadas
FINGERPRINT = "795c3a962546b0fcae01271233bf85e9900a116f5cce7a8ba3132894b3ee8ee3"
PER_CLASS = 3                   # cada clase, en cada una de las 3 pasadas
CLASSES = 21


class FuzzAdmisionGateTests(unittest.TestCase):
    def test_congelado(self):
        results = fz.run_admission_fuzz()
        self.assertEqual(results["bases"], BASES)
        self.assertEqual(results["total_mutations"], TOTAL_MUTATIONS)
        self.assertEqual(results["fingerprint"], FINGERPRINT)
        self.assertEqual(len(results["per_class"]), CLASSES)
        self.assertTrue(all(c == PER_CLASS for c in results["per_class"].values()))
        self.assertEqual(results["base_errors"], [])
        self.assertEqual(results["oracle_failures"], [])
        self.assertEqual(results["crashes"], [])

    def test_sensibilidad_divergencia_artificial(self):
        # Oráculo saboteado: la expectativa de una clase se cambia; el
        # gate DEBE fallar (detecta la divergencia).
        original = fz.ORACLE["cap_mac"]
        fz.ORACLE["cap_mac"] = ("reject", "malformed_descriptor")
        try:
            results = fz.run_admission_fuzz()
            self.assertTrue(results["oracle_failures"],
                            "el oráculo saboteado debe producir fallos")
        finally:
            fz.ORACLE["cap_mac"] = original

    def test_sensibilidad_error_comun(self):
        # Implementación saboteada: TODO rechazo con el diagnóstico
        # incorrecto (malformed_descriptor). Un "acuerdo" no existiría;
        # el ORÁCULO debe detenerlo (lección B9/M0).
        class Saboteado:
            def admit(self, raw):
                return AdmissionRejected(reason_code="malformed_descriptor",
                                         safe_detail="sabotaje")

        results = fz.run_admission_fuzz(svc_admit=Saboteado())
        self.assertTrue(results["oracle_failures"],
                        "el error común debe ser detectado por el oráculo")
        clases = {f["clase"] for f in results["oracle_failures"]}
        self.assertIn("cap_mac", clases)
        self.assertIn("policy_deny", clases)

    def test_sensibilidad_crash(self):
        # Implementación que revienta: el gate reporta CRASH, nunca
        # propaga la excepción.
        class Explosivo:
            def admit(self, raw):
                raise RuntimeError("boom")

        results = fz.run_admission_fuzz(svc_admit=Explosivo())
        self.assertTrue(results["crashes"])
        self.assertTrue(all(c["excepcion"] == "RuntimeError"
                            for c in results["crashes"]))
        # Y las mutaciones "exitosas" son 0: todo reportado como crash.
        self.assertEqual(results["total_mutations"], 0)

    def test_g2_frontera_solo_admitted(self):
        # Complemento del zoo G2 (14 inválidos → 0 cruces, asentado en
        # test_policy_spawn_frontier): la frontera sólo acepta Admitted;
        # el fuzz corre con sus propios servicios y su rechazo total ya
        # queda asentado por el oráculo. Aquí: camino feliz cruza 1 vez.
        from src.adapters.spawn_frontier_counter import SpawnFrontierCounter
        from helpers_m1 import make_service, valid_request_bytes
        spy = SpawnFrontierCounter()
        svc = make_service()
        # (El oráculo del fuzz ya asienta que ninguna mutación produce
        # Admitted; la evidencia G2 de inválidos es el zoo de 14.)
        from src.domain.outcomes import Admitted
        out = svc.admit(valid_request_bytes())
        self.assertIsInstance(out, Admitted)
        spy.submit(out)
        self.assertEqual(spy.total_crossings(), 1)


if __name__ == "__main__":
    unittest.main()
