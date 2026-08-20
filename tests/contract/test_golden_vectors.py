"""Pruebas de contrato M0: los dos parsers de referencia contra todos los
vectores dorados (spec v1.2 §5.4, §15/M0 con enmienda R5).

Un parser es `contracts/parsers/reference/`; el otro es clean-room
(`contracts/parsers/clean-room/`), escrito desde la spec y los vectores sin
leer el código del primero. Ambos deben producir veredicto, diagnóstico y
digest idénticos para cada vector.
"""
import json
import sys
import unittest
from base64 import b64decode
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "reference"))
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "clean-room"))

import ektel_ref_parser as parser_a  # noqa: E402
import ektel_cleanroom_parser as parser_b  # noqa: E402

VECTORS = ROOT / "contracts" / "vectors" / "v1"

GROUP_TO_WIRE_TYPES = {
    "capability-envelope": ["capability-envelope"],
    "admission-token": ["admission-token"],
    "termination-token": ["termination-token"],
    "invocation-proof": ["invocation-proof"],
    "action-request": ["action-request"],
    "outcomes": ["admission-outcome", "start-outcome", "termination-outcome", "execution-result"],
}


def load_vectors():
    index = json.loads((VECTORS / "index.json").read_text(encoding="utf-8"))
    key = bytes.fromhex(index["test_key_hex"])
    cases = []
    for group_file in sorted(VECTORS.glob("*.vectors.json")):
        doc = json.loads(group_file.read_text(encoding="utf-8"))
        group = doc["wire_type_group"]
        known = set(GROUP_TO_WIRE_TYPES[group])
        for v in doc["vectors"]:
            wire_type = v["wire_type"]
            assert wire_type in known, f"{v['id']}: wire_type {wire_type} fuera del grupo {group}"
            cases.append((group, v))
    return key, cases


class GoldenVectorsTests(unittest.TestCase):
    def test_both_parsers_agree_on_all_vectors(self):
        key, cases = load_vectors()
        self.assertGreaterEqual(len(cases), 25)
        for group, v in cases:
            raw = b64decode(v["bytes"] + "=" * ((-len(v["bytes"])) % 4))
            with self.subTest(vector=v["id"]):
                ra = parser_a.parse_wire(v["wire_type"], raw, key)
                rb = parser_b.parse_wire(v["wire_type"], raw, key)
                for label, r in (("A", ra), ("B", rb)):
                    self.assertEqual(
                        (v["expect"]["verdict"], v["expect"]["diagnostic"]),
                        (r.verdict, r.diagnostic),
                        f"parser {label} diverge del vector {v['id']}",
                    )
                self.assertEqual(ra.verdict, rb.verdict, v["id"])
                self.assertEqual(ra.diagnostic, rb.diagnostic, v["id"])
                expected_digest = v["expect"].get("identity_digest")
                if expected_digest:
                    self.assertEqual(expected_digest, ra.identity_digest, v["id"])
                    self.assertEqual(expected_digest, rb.identity_digest, v["id"])

    def test_wire_types_coverage(self):
        declared = set(parser_a.WIRE_TYPES)
        self.assertEqual(declared, set(parser_b.WIRE_TYPES))
        for group, types in GROUP_TO_WIRE_TYPES.items():
            for t in types:
                self.assertIn(t, declared)


if __name__ == "__main__":
    unittest.main()
