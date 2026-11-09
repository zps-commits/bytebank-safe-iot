from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from server.api import connect, create_app


class Sprint3Tests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(TemporaryDirectory())
        self.path = Path(folder) / "test.sqlite3"
        self.app = create_app(self.path)
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=False))

    def post(self, event_id, kind, lot="A", pending=0):
        return self.client.post("/events", json={
            "event_id": event_id, "device_id": "cofre", "lote_id": lot,
            "type": kind, "pending_count": pending, "uptime_ms": 20,
        }).status_code

    def test_firmware_payload_lifecycle_and_idempotency(self):
        self.assertEqual(self.post("1", "deposit_detected", pending=1), 201)
        self.assertEqual(self.post("2", "deposit_detected", "B", 2), 201)
        self.assertEqual(self.post("3", "deposit_cancelled", "B", 1), 201)
        self.assertEqual(self.post("4", "deposit_confirmed"), 201)
        self.assertEqual(self.post("4", "deposit_confirmed"), 200)
        self.assertEqual(self.post("4", "deposit_confirmed", "B"), 409)
        self.assertEqual(self.post("5", "deposit_confirmed", "B"), 409)
        self.assertEqual(self.client.get("/events").json()["count"], 4)
        with TestClient(create_app(self.path)) as restarted:
            self.assertEqual(restarted.get("/balances/cofre").json()["envelopes_confirmados"], 1)
            self.assertEqual(restarted.get("/events").json()["count"], 4)

    def test_validation(self):
        self.assertEqual(self.client.post("/events", json={}).status_code, 422)
        self.assertEqual(self.post("1", "other"), 422)
        self.assertEqual(self.post("1", "deposit_detected", pending=True), 422)
        self.assertEqual(self.client.get("/events").json()["count"], 0)

    def test_audit_failure_rolls_back_balance_and_transaction(self):
        self.assertEqual(self.post("1", "deposit_detected", pending=1), 201)
        with closing(connect(self.path)) as db, db:
            db.execute("""
                CREATE TRIGGER simulate_failure BEFORE INSERT ON logs_auditoria
                BEGIN SELECT RAISE(ABORT, 'forced failure'); END;
            """)
        self.assertEqual(self.post("2", "deposit_confirmed"), 500)
        self.assertEqual(self.client.get("/balances/cofre").json()["envelopes_confirmados"], 0)
        with closing(connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT estado FROM transacoes").fetchone()[0], "pendente")
            db.execute("DROP TRIGGER simulate_failure")
        self.assertEqual(self.post("2", "deposit_confirmed"), 201)
