"""Gate permanente de fuzz diferencial A/B con oráculo (acta de corrección
M0 §4.1; FIX-AND-RETRY 1 punto 4; FIX-AND-RETRY 2 B9; FIX-AND-RETRY 3
B9.1/B9.2).

Congela: conteo y fingerprint sha256 del corpus, conteo exacto de bases
accept y de mutaciones por clase del fuzz semántico. Verifica la matriz
del oráculo (sv/extra/missing/patrón/longitudes) contra A y B por
separado, el acuerdo diferencial A/B, y la SENSIBILIDAD del gate tanto a
divergencia artificial (sólo A saboteado) como a ERROR COMÚN (A y B
saboteados con el mismo diagnóstico incorrecto: debe detenerlo el
oráculo, no el acuerdo A/B).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fuzz_diferencial as fz  # noqa: E402

# Congelados del corpus (M0-FAR-CLAUDE-01, 2026-08-21):
CORPUS_COUNT = 90
CORPUS_FINGERPRINT = "1c8412fec52ea6a457397a1f8a55c86bcc4503728ff2e3da882f6ffe640ddd89"
BYTES_TOTAL = 1530         # 90 vectores x 17 mutaciones
SEMANTIC_BASES = 18        # sólo vectores accept
SEMANTIC_TOTAL = 165
SEMANTIC_PER_CLASS = {
    "payload_sv_2": 4, "payload_sv_0": 4, "payload_sv_neg": 4,
    "payload_sv_true": 4, "payload_extra": 4, "payload_missing": 4,
    "payload_pattern_nl": 4, "header_sv_2": 4, "header_extra": 4,
    "header_typ_int": 4,
    "doc_sv_2": 14, "doc_sv_0": 14, "doc_sv_neg": 14, "doc_sv_true": 14,
    "doc_extra": 14, "doc_missing": 14, "doc_pattern_nl": 10,
    "doc_maxitems": 4, "doc_args_257": 4, "doc_minlength": 4,
    "doc_array_max_65": 4,
    "doc_disc_type_confusion": 5, "doc_enum_item_type": 4, "doc_const_type": 4,
    "pop_nonce_len_plus_mac_recomputed": 1,
    "pop_payload_digest_len_plus_mac_recomputed": 1,
}


class FuzzDiferencialTests(unittest.TestCase):
    def test_corpus_frozen(self):
        _, corpus = fz.load_corpus()
        self.assertEqual(len(corpus), CORPUS_COUNT)
        self.assertEqual(fz.corpus_fingerprint(corpus), CORPUS_FINGERPRINT)

    def test_semantic_bases_are_accepts_only(self):
        _, corpus = fz.load_corpus()
        accepts = [v for v in corpus if v[3].get("verdict") == "accept"]
        self.assertEqual(len(accepts), SEMANTIC_BASES)
        result = fz.run_semantic_fuzz()
        self.assertEqual(result["bases"], SEMANTIC_BASES)
        self.assertEqual(result["base_errors"], [])

    def test_zero_divergences_bytes(self):
        result = fz.run_fuzz()
        self.assertEqual(result["divergence_count"], 0,
                         f"divergencias A/B: {result['divergences'][:5]}")
        self.assertEqual(result["total_mutations"], BYTES_TOTAL)
        self.assertEqual(result["seed"], 20260820)

    def test_semantic_oracle_and_agreement_frozen(self):
        result = fz.run_semantic_fuzz()
        self.assertEqual(result["divergence_count"], 0,
                         f"divergencias A/B: {result['divergences'][:5]}")
        self.assertEqual(result["oracle_failure_count"], 0,
                         f"fallos de oráculo: {result['oracle_failures'][:5]}")
        self.assertEqual(result["total_mutations"], SEMANTIC_TOTAL)
        self.assertEqual(result["per_class"], SEMANTIC_PER_CLASS)

    def test_gate_detects_artificial_divergence(self):
        """Sensibilidad a divergencia: sólo A saboteado (acepta doc_extra).
        El acuerdo diferencial A/B DEBE reportar la divergencia."""
        original = fz.parser_a.parse_wire

        def saboteado(wire_type, raw, key):
            r = original(wire_type, raw, key)
            if b"zz_semantic_extra" in raw:
                return fz.parser_a.ParseResult("accept", "ok", value=None)
            return r

        fz.parser_a.parse_wire = saboteado
        try:
            result = fz.run_semantic_fuzz()
        finally:
            fz.parser_a.parse_wire = original
        self.assertGreater(result["divergence_count"], 0,
                           "el detector no capturó la divergencia artificial")
        self.assertTrue(all(d["class"] == "doc_extra"
                            for d in result["divergences"]))

    def test_gate_detects_common_error_via_oracle(self):
        """Sensibilidad a ERROR COMÚN (B9.2.7): A y B saboteados para
        producir el MISMO diagnóstico incorrecto (schema_version_unsupported
        reescrito como invalid_value). El acuerdo A/B ve concordancia
        total; el ORÁCULO debe hacer fallar el gate."""
        def common_wrong(parser_mod):
            original = parser_mod.parse_wire

            def saboteado(wire_type, raw, key):
                r = original(wire_type, raw, key)
                if r.diagnostic == "schema_version_unsupported":
                    return parser_mod.ParseResult(
                        "reject", "invalid_value",
                        identity_digest=r.identity_digest, value=r.value)
                return r
            return original, saboteado

        orig_a, wrapped_a = common_wrong(fz.parser_a)
        orig_b, wrapped_b = common_wrong(fz.parser_b)
        fz.parser_a.parse_wire = wrapped_a
        fz.parser_b.parse_wire = wrapped_b
        try:
            result = fz.run_semantic_fuzz()
        finally:
            fz.parser_a.parse_wire = orig_a
            fz.parser_b.parse_wire = orig_b
        # Error común: A==B en todo (sin divergencia)…
        self.assertEqual(result["divergence_count"], 0)
        # …pero el oráculo detecta el diagnóstico incorrecto en A y en B.
        self.assertGreater(result["oracle_failure_count"], 0,
                           "el oráculo no capturó el error común A/B")
        sv_classes = {"doc_sv_2", "header_sv_2", "payload_sv_2"}
        self.assertTrue(all(f["class"] in sv_classes
                            for f in result["oracle_failures"]))
        self.assertEqual({f["parser"] for f in result["oracle_failures"]},
                         {"A", "B"})

    def test_gate_detects_common_error_on_type_confusion(self):
        """Sensibilidad a ERROR COMÚN en la clase nueva (M0-FAR-CLAUDE-01):
        A y B saboteados para clasificar typ=1 igual de mal
        (invalid_type → invalid_value). El acuerdo A/B no ve nada; el
        oráculo con la clase de confusión de tipos DEBE detenerlo."""
        def common_wrong(parser_mod):
            original = parser_mod.parse_wire

            def saboteado(wire_type, raw, key):
                r = original(wire_type, raw, key)
                if r.diagnostic == "invalid_type":
                    return parser_mod.ParseResult(
                        "reject", "invalid_value",
                        identity_digest=r.identity_digest, value=r.value)
                return r
            return original, saboteado

        orig_a, wrapped_a = common_wrong(fz.parser_a)
        orig_b, wrapped_b = common_wrong(fz.parser_b)
        fz.parser_a.parse_wire = wrapped_a
        fz.parser_b.parse_wire = wrapped_b
        try:
            result = fz.run_semantic_fuzz()
        finally:
            fz.parser_a.parse_wire = orig_a
            fz.parser_b.parse_wire = orig_b
        self.assertEqual(result["divergence_count"], 0)
        self.assertGreater(result["oracle_failure_count"], 0)
        tc_classes = {"header_typ_int", "doc_enum_item_type"}
        self.assertTrue(all(f["class"] in tc_classes
                            for f in result["oracle_failures"]))
        self.assertEqual({f["parser"] for f in result["oracle_failures"]},
                         {"A", "B"})

    def test_gate_detects_crash(self):
        """Sensibilidad a CRASH (M0-FAR-CLAUDE-01): si un parser lanza una
        excepción sobre entrada mutada, el gate DEBE reportarlo como fallo
        (crash), no propagarlo ni ignorarlo."""
        original = fz.parser_a.parse_wire

        def saboteado(wire_type, raw, key):
            if b'"zz_semantic_extra"' in raw:
                raise RuntimeError("crash artificial")
            return original(wire_type, raw, key)

        fz.parser_a.parse_wire = saboteado
        try:
            result = fz.run_semantic_fuzz()
        finally:
            fz.parser_a.parse_wire = original
        crashes = [f for f in result["oracle_failures"] if "crash" in f]
        self.assertGreater(len(crashes), 0,
                           "el gate no capturó el crash artificial")
        self.assertTrue(all(f["parser"] == "A" and f["got"] == ["CRASH"]
                            for f in crashes))
        # el exit del main sería 1: oracle_failure_count > 0
        self.assertGreater(result["oracle_failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
