"""Gate permanente de anidamiento profundo (M0-FAR-CLAUDE-01, ronda
adversarial interna).

Un documento JSON con profundidad de anidamiento mayor que la capacidad
del decodificador (aquí: 20 000 niveles, ~40 KB, dentro del techo de
64 KiB de §5.1) debe rechazarse fail-closed como `malformed_json` en
AMBOS parsers, sin excepción propagada — también al decodificar el
protected header de un sobre con MAC válida.

Nota de entorno: el test asume un límite de recursión de CPython
estándar (<= 10 000); con límites extraordinariamente mayores el
decodificador parsearía y el diagnóstico pasaría a invalid_type. El
asiento normativo (spec §5.1) manda: profundidad excesiva →
malformed_json.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "reference"))
sys.path.insert(0, str(ROOT / "contracts" / "parsers" / "clean-room"))

import ektel_ref_parser as parser_a  # noqa: E402
import ektel_cleanroom_parser as parser_b  # noqa: E402

DEEP = b"[" * 20000 + b"]" * 20000


class DeepJsonTests(unittest.TestCase):
    def test_deep_document_is_malformed_json_in_both_parsers(self):
        key = bytes(range(32))
        for wire_type in ("start-outcome", "action-request",
                          "capability-envelope", "invocation-proof"):
            for label, parser in (("A", parser_a), ("B", parser_b)):
                with self.subTest(parser=label, wire_type=wire_type):
                    r = parser.parse_wire(wire_type, DEEP, key)
                    self.assertEqual((r.verdict, r.diagnostic),
                                     ("reject", "malformed_json"))

    def test_deep_inside_signed_header_is_malformed_json(self):
        # Header anidado profundo, MAC VÁLIDA para esas cadenas: la
        # decodificación del header falla cerrada como malformed_json.
        import hashlib
        import hmac
        from base64 import urlsafe_b64encode as u64

        def b64u(b):
            return u64(b).rstrip(b"=").decode()

        def e(o):
            import json
            return json.dumps(o, sort_keys=True,
                              separators=(",", ":")).encode()

        key = bytes(range(32))
        deep_text = ("[" * 20000 + "]" * 20000).encode()
        ph = b64u(deep_text)
        pl = b64u(e({"schema_version": 1, "action_id": "a",
                     "identity_digest": "0" * 64}))
        sig = b64u(hmac.new(
            key, b"ektel/termination/v1\x00" + ph.encode() + b"." + pl.encode(),
            hashlib.sha256).digest())
        raw = e({"protected_header_b64": ph, "payload_b64": pl,
                 "signature": sig})
        for label, parser in (("A", parser_a), ("B", parser_b)):
            with self.subTest(parser=label):
                r = parser.parse_wire("termination-token", raw, key)
                self.assertEqual((r.verdict, r.diagnostic),
                                 ("reject", "malformed_json"))


if __name__ == "__main__":
    unittest.main()
