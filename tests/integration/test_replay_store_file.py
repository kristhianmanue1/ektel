"""Integración G16/G6/G11: store durable real (archivo), reinicio,
dependencia caída, TTL y límite (spec §7.4–7.5; ADR-004 A1/A2)."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from helpers_m1 import (  # noqa: E402
    MemoryReplayStore, NOW, make_service, valid_request_bytes)
from src.adapters.replay_store_file import (  # noqa: E402
    FileReplayStore, ReplayStoreError)
from src.domain.outcomes import Admitted  # noqa: E402
from src.ports.replay_store import ReserveOutcome  # noqa: E402


class FileStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _store(self, **kw) -> FileReplayStore:
        store = FileReplayStore(self.dir, **kw)
        self.addCleanup(store.close)
        return store

    def test_reserva_y_replay_en_mismo_proceso(self):
        store = self._store()
        self.assertEqual(store.reserve_nonce("op", "n1", time.time() + 3600),
                         ReserveOutcome.RESERVED)
        self.assertEqual(store.reserve_nonce("op", "n1", time.time() + 3600),
                         ReserveOutcome.ALREADY_RESERVED)
        # Ámbito del nonce §7.5: colisión entre emisores NO es replay.
        self.assertEqual(store.reserve_nonce("otro", "n1", time.time() + 3600),
                         ReserveOutcome.RESERVED)

    def test_g16_reinicio_proceso_nuevo_sigue_rechazando(self):
        store1 = self._store()
        store1.reserve_nonce("op", "n1", time.time() + 3600)
        # Proceso nuevo (instancia nueva) contra el MISMO store durable.
        store2 = FileReplayStore(self.dir)
        self.assertEqual(store2.reserve_nonce("op", "n1", time.time() + 3600),
                         ReserveOutcome.ALREADY_RESERVED)

    def test_g16_consumo_sobrevive_reinicio(self):
        from src.ports.replay_store import ConsumeOutcome
        store1 = self._store()
        self.assertEqual(store1.consume_start_token("d" * 64),
                         ConsumeOutcome.CONSUMED)
        store2 = FileReplayStore(self.dir)
        self.assertEqual(store2.consume_start_token("d" * 64),
                         ConsumeOutcome.ALREADY_SPENT)
        self.assertEqual(store2.start_token_status("d" * 64), "spent")

    def test_g16_admision_con_nonce_nuevo_es_admision_nueva(self):
        svc1 = make_service(store=self._store())
        out1 = svc1.admit(valid_request_bytes())
        self.assertIsInstance(out1, Admitted)
        # Reinicio del servicio sobre el mismo directorio.
        svc2 = make_service(store=FileReplayStore(self.dir))
        replay = svc2.admit(valid_request_bytes())  # mismo nonce
        from src.domain.outcomes import AdmissionRejected
        self.assertIsInstance(replay, AdmissionRejected)
        self.assertEqual(replay.safe_detail, "nonce_replay")
        # Nonce NUEVO (capacidad nueva emitida para él) = admisión nueva.
        from helpers_m1 import make_capability_envelope, make_request, emit_request
        nuevo = make_request(env=make_capability_envelope(nonce="c3" * 16),
                             nonce="c3" * 16)
        out2 = svc2.admit(emit_request(nuevo))
        self.assertIsInstance(out2, Admitted)
        assert isinstance(out1, Admitted) and isinstance(out2, Admitted)
        self.assertNotEqual(out1.identity_digest, out2.identity_digest)

    def test_g16_estado_durable_en_disco(self):
        store = self._store()
        store.reserve_nonce("op", "n1", time.time() + 3600)
        state_file = self.dir / "state.json"
        self.assertTrue(state_file.exists())
        import json
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertIn("op\x00n1", state["nonces"])

    def test_g6_corrupto_fallo_de_arranque(self):
        (self.dir / "state.json").write_text("{no-json", encoding="utf-8")
        with self.assertRaises(ReplayStoreError):
            self._store()

    def test_g6_directorio_inaccesible_rechaza(self):
        store = self._store()
        # Simula caída del store: estado ilegible tras el arranque.
        (self.dir / "state.json").write_text("{corrupto", encoding="utf-8")
        self.assertEqual(store.reserve_nonce("op", "n2", time.time() + 3600),
                         ReserveOutcome.UNAVAILABLE)

    def test_g6_lleno_fail_closed(self):
        store = self._store(max_nonces=1)
        self.assertEqual(store.reserve_nonce("op", "n1", time.time() + 3600),
                         ReserveOutcome.RESERVED)
        # Nonce vivo distinto con el límite alcanzado: UNAVAILABLE (A2).
        self.assertEqual(store.reserve_nonce("op", "n2", time.time() + 3600),
                         ReserveOutcome.UNAVAILABLE)

    def test_g6_lleno_tras_admit_rechaza(self):
        store = self._store(max_nonces=1)
        svc = make_service(store=store)
        self.assertIsInstance(svc.admit(valid_request_bytes()), Admitted)
        # Otro ActionRequest válido (nonce distinto) con store lleno:
        from helpers_m1 import NONCE_HEX, make_capability_envelope, make_request, emit_request
        other = make_request(env=make_capability_envelope(nonce="b2" * 16),
                             nonce="b2" * 16)
        out = svc.admit(emit_request(other))
        from src.domain.outcomes import AdmissionRejected
        self.assertIsInstance(out, AdmissionRejected)
        self.assertEqual(out.safe_detail, "replay_store_unavailable")
        self.assertTrue(out.retryable)

    def test_g11_ttl_recolecta_vencidos(self):
        store = self._store()
        store.reserve_nonce("op", "viejo", reserve_until_wall=1.0)  # vencido
        self.assertEqual(store.collect_expired(now_wall=2.0), 1)
        self.assertEqual(store.reserve_nonce("op", "viejo", time.time() + 60),
                         ReserveOutcome.RESERVED)  # re-reservable tras TTL

    def test_g11_reloj_mantenimiento_invalido_no_muta(self):
        store = self._store()
        self.assertEqual(store.reserve_nonce("op", "vivo", time.time() + 3600),
                         ReserveOutcome.RESERVED)
        for value in (float("nan"), float("inf"), float("-inf"),
                      10 ** 1000, True, "bad"):
            with self.subTest(now_wall=value), self.assertRaises(ReplayStoreError):
                store.collect_expired(value)  # type: ignore[arg-type]
            self.assertEqual(store.reserve_nonce("op", "vivo", time.time() + 3600),
                             ReserveOutcome.ALREADY_RESERVED)

    def test_configuracion_y_ttl_no_finitos_fallan_cerrado(self):
        for value in (0, -1, True, 1.5, "bad"):
            with self.subTest(max_nonces=value), self.assertRaises(ReplayStoreError):
                FileReplayStore(self.dir, max_nonces=value)  # type: ignore[arg-type]
        store = self._store()
        for value in (float("nan"), float("inf"), 10 ** 1000,
                      (1 << 53) + 1, True, "bad"):
            with self.subTest(reserve_until_wall=value):
                self.assertEqual(
                    store.reserve_nonce("op", "otro", value),  # type: ignore[arg-type]
                    ReserveOutcome.UNAVAILABLE)

        class HostileInt(int):
            def __float__(self):
                raise RuntimeError("conversion controlada")

        self.assertEqual(store.reserve_nonce("op", "hostil", HostileInt(5)),
                         ReserveOutcome.UNAVAILABLE)

    def test_g11_ttl_opportunista_bajo_limite(self):
        store = self._store(max_nonces=1)
        store.reserve_nonce("op", "viejo", reserve_until_wall=1.0)
        # La reserva nueva expulsa al vencido (recolección oportunista) y
        # cabe dentro del límite.
        import time
        self.assertEqual(store.reserve_nonce("op", "nuevo", time.time() + 60),
                         ReserveOutcome.RESERVED)

    def test_persist_durabilidad_perfil(self):
        # El perfil exige fsync de archivo y directorio; verificamos la
        # mecánica (write-tmp + rename) y que no queden temporales.
        store = self._store()
        store.reserve_nonce("op", "n1", time.time() + 3600)
        leftovers = [p.name for p in self.dir.iterdir()
                     if p.name.startswith(".state-")]
        self.assertEqual(leftovers, [])
        self.assertTrue((self.dir / "state.json").exists())

    def test_uso_tras_close_fail_closed(self):
        # Use-after-close: sin lock-file no hay sección crítica — el
        # puerto devuelve UNAVAILABLE/unknown, nunca una excepción de
        # plataforma (ValueError de flock con fd -1 en darwin).
        store = self._store()
        store.reserve_nonce("op", "n1", time.time() + 3600)
        store.close()
        self.assertEqual(store.reserve_nonce("op", "n2", time.time() + 60),
                         ReserveOutcome.UNAVAILABLE)
        from src.ports.replay_store import ConsumeOutcome
        self.assertEqual(store.consume_start_token("d" * 64),
                         ConsumeOutcome.UNAVAILABLE)
        self.assertEqual(store.start_token_status("d" * 64), "unknown")


if __name__ == "__main__":
    unittest.main()
