"""ektel adapters — borde reemplazable (spec v1.2 §4/§18).

M1: `operator_key` (carga segura, regla 3 final de la adenda). Replay
store durable y adaptador de política de prueba llegan en INC-4.

API EXPERIMENTAL (spec §16).
"""
from .operator_key import KEY_LEN, OperatorKeyError, load_operator_key

__all__ = ["KEY_LEN", "OperatorKeyError", "load_operator_key"]
