#!/usr/bin/env python3
"""Medición de latencia de admisión (G13; ADR-004 consecuencia: la
escritura durable síncrona del replay store está en el camino crítico).

Método (declarado): medición real repetida en esta máquina — N admisiones
independientes, cada una con SU store durable real en un directorio tmp y
SU nonce (sin replay), reloj monotónico (`time.perf_counter_ns`); se
reportan min/p50/p95/max en milisegundos. Clase de evidencia: L (ejecución
local única, esquema M0). No es una promesa de plataforma: es la
declaración exigida por ADR-004 («M1 debe medirla y declararla en
métricas»); la latencia con fsync real es visible por diseño.

API EXPERIMENTAL (spec §16). stdlib-only. Herramienta de medición.
"""
from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))


def measure(n: int = 200) -> dict:
    from helpers_m1 import (make_capability_envelope, make_request,
                            emit_request, make_service)
    from src.adapters.replay_store_file import FileReplayStore
    from src.domain.outcomes import Admitted

    samples_ms: list[float] = []
    with tempfile.TemporaryDirectory(prefix="ektel-g13-") as tmp:
        base_dir = Path(tmp)
        for i in range(n):
            nonce = f"{i:02x}" * 16
            env = make_capability_envelope(nonce=nonce)
            doc = make_request(env=env, nonce=nonce)
            payload = emit_request(doc)
            store = FileReplayStore(base_dir / f"s{i}")
            svc = make_service(store=store)
            t0 = time.perf_counter_ns()
            out = svc.admit(payload)
            t1 = time.perf_counter_ns()
            store.close()
            if not isinstance(out, Admitted):
                raise SystemExit(f"admisión {i} no fue Admitted: {out!r}")
            samples_ms.append((t1 - t0) / 1e6)

    def pct(p: float) -> float:
        ordered = sorted(samples_ms)
        k = min(len(ordered) - 1, int(round(p / 100.0 * (len(ordered) - 1))))
        return ordered[k]

    return {
        "n": n,
        "min_ms": min(samples_ms),
        "p50_ms": statistics.median(samples_ms),
        "p95_ms": pct(95),
        "max_ms": max(samples_ms),
        "mean_ms": statistics.fmean(samples_ms),
    }


def main() -> int:
    import json
    results = measure()
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
