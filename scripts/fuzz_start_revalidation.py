#!/usr/bin/env python3
"""Fuzz de la revalidación de `start` con oráculo (G-M2-01, ADR-011 §2.3).

Disciplina heredada del fuzz M0/M1: **bases verificadas antes de mutar**,
oráculo comprobado por separado y **crash = fallo del gate**, nunca excepción
propagada. Una revalidación que lanza en vez de devolver un `StartFailed` es
un defecto: la ruta es fail-closed por valor de retorno.

Oráculo, deliberadamente conservador para no fabricar una promesa que ADR-011
no hace:

1. la revalidación **nunca lanza**;
2. si devuelve `StartFailed`, su `reason_code` pertenece al vocabulario
   cerrado y su `safe_detail` no filtra bytes del descriptor, del entorno ni
   de stdin;
3. si devuelve `ExecutionPlan`, los campos **autenticados** —`identity_digest`,
   `action_id`, `issuer_id`, `exp`— coinciden exactamente con los de la base.

El punto 3 es lo que importa: ADR-011 §2.2 garantiza **equivalencia
revalidada, no identidad de bytes**, y `metadata_opaque` no está autenticado
por `identity_digest`. Por eso una mutación de ese campo **puede** producir un
plan válido, y exigir lo contrario seria inventar una garantía inexistente. Lo
que jamás puede ocurrir es que una mutación produzca un plan con identidad
distinta: eso sería falsificación.

Uso:
    python3 scripts/fuzz_start_revalidation.py [--iteraciones N] [--semilla S]

Salida: JSON con conteos y divergencias. Código 1 si el gate falla.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.revalidation import revalidate_start_request  # noqa: E402
from src.domain.start_outcomes import (  # noqa: E402
    START_FAILURE_REASONS, MAX_SAFE_DETAIL, StartFailed)
from src.domain.start_request import ExecutionPlan  # noqa: E402
from tests.unit.helpers_m1 import EXP, NOW, TEST_KEY, TEST_KEY_ID  # noqa: E402
from tests.unit.helpers_m2 import valid_start_pair  # noqa: E402

#: Bytes que jamás deben aparecer en un diagnóstico saneado.
SECRETOS = (b"inline-secreto", b"VALOR_SENSIBLE")


def revalidar(token: object, wire: object) -> object:
    return revalidate_start_request(
        token, wire, operator_key=TEST_KEY, active_key_id=TEST_KEY_ID,
        now_wall=float(NOW), skew_tolerance_s=30.0)


def mutar_bytes(rng: random.Random, data: bytes) -> tuple[str, bytes]:
    clase = rng.choice(("flip", "truncar", "insertar", "duplicar", "vaciar"))
    if not data or clase == "vaciar":
        return "wire_vaciar", b""
    i = rng.randrange(len(data))
    if clase == "flip":
        return "wire_flip", data[:i] + bytes([data[i] ^ (1 << rng.randrange(8))]) + data[i + 1:]
    if clase == "truncar":
        return "wire_truncar", data[:i]
    if clase == "insertar":
        return "wire_insertar", data[:i] + bytes([rng.randrange(256)]) + data[i:]
    return "wire_duplicar", data + data[:i]


def mutar_token(rng: random.Random, token: str) -> tuple[str, object]:
    clase = rng.choice(("char", "recortar", "padding", "tipo", "vacio"))
    if clase == "char" and token:
        i = rng.randrange(len(token))
        alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "token_char", token[:i] + rng.choice(alfabeto) + token[i + 1:]
    if clase == "recortar":
        return "token_recortar", token[:max(0, len(token) - rng.randrange(1, 8))]
    if clase == "padding":
        return "token_padding", token + "=" * rng.randrange(1, 3)
    if clase == "tipo":
        return "token_tipo", rng.choice([None, 1, b"bytes", ["x"], {"a": 1}, True])
    return "token_vacio", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteraciones", type=int, default=2000)
    parser.add_argument("--semilla", type=int, default=20260909)
    args = parser.parse_args()
    rng = random.Random(args.semilla)

    # Base verificada ANTES de mutar: si la base no revalida, el gate falla.
    token_base, wire_base = valid_start_pair()
    base = revalidar(token_base, wire_base)
    if not isinstance(base, ExecutionPlan):
        print(json.dumps({"gate": "FALLA", "motivo": "base_no_revalida",
                          "detalle": repr(base)}, ensure_ascii=False))
        return 1

    conteo: dict[str, int] = {}
    planes = 0
    nulas = 0
    divergencias: list[dict[str, object]] = []
    crashes: list[dict[str, object]] = []

    for _ in range(args.iteraciones):
        if rng.random() < 0.5:
            clase, token = mutar_token(rng, token_base)
            wire: object = wire_base
        else:
            clase, wire = mutar_bytes(rng, wire_base)
            token = token_base
        conteo[clase] = conteo.get(clase, 0) + 1
        # Una mutacion puede resultar en la entrada original (por ejemplo,
        # cambiar un caracter por si mismo). Contarla como "aceptada" seria
        # sugerir que una mutacion real burlo la validacion.
        if token == token_base and wire == wire_base:
            nulas += 1
        try:
            salida = revalidar(token, wire)
        except BaseException as exc:  # oráculo 1: nunca lanza
            crashes.append({"clase": clase, "excepcion": type(exc).__name__})
            continue
        if isinstance(salida, StartFailed):
            # oráculo 2: vocabulario cerrado y diagnóstico saneado
            if salida.reason_code not in START_FAILURE_REASONS:
                divergencias.append({"clase": clase, "motivo": "reason_code",
                                     "valor": salida.reason_code})
            if len(salida.safe_detail) > MAX_SAFE_DETAIL:
                divergencias.append({"clase": clase, "motivo": "safe_detail_largo"})
            crudo = salida.safe_detail.encode("utf-8", "replace")
            for secreto in SECRETOS:
                if secreto in crudo:
                    divergencias.append({"clase": clase, "motivo": "fuga"})
        elif isinstance(salida, ExecutionPlan):
            planes += 1
            if token != token_base or wire != wire_base:
                # Aceptar una mutacion REAL solo es admisible si toca campos no
                # autenticados (ADR-011 §2.2: `metadata_opaque` no lo esta).
                divergencias.append({"clase": clase,
                                     "motivo": "mutacion_real_aceptada"})
            # oráculo 3: ninguna mutación puede cambiar la identidad autenticada
            for campo in ("identity_digest", "action_id", "issuer_id", "exp_wall"):
                if getattr(salida, campo) != getattr(base, campo):
                    divergencias.append({"clase": clase, "motivo": "identidad",
                                         "campo": campo})
        else:
            divergencias.append({"clase": clase, "motivo": "tipo_desconocido",
                                 "valor": type(salida).__name__})

    ok = not divergencias and not crashes
    print(json.dumps({
        "gate": "OK" if ok else "FALLA",
        "iteraciones": args.iteraciones,
        "semilla": args.semilla,
        "mutaciones_por_clase": dict(sorted(conteo.items())),
        "planes_aceptados": planes,
        "mutaciones_nulas": nulas,
        "divergencias": divergencias[:20],
        "crashes": crashes[:20],
        "exp_base": EXP,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
