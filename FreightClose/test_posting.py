import json
import os
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import offline_server
import service


class PostingTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.path = str(Path(folder) / "test.sqlite3")
        self.enterContext(patch.dict(os.environ, FREIGHT_DB=self.path))
        self.enterContext(patch.object(service, "MODE", "mock"))
        self.packet = service.get_sample()

    def post(self, packet):
        return service.run({"packet": packet})

    def count(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT count(*) FROM postings").fetchone()[0]

    def test_parallel_replays_and_alias_duplicate(self):
        with ThreadPoolExecutor(4) as pool:
            result = list(pool.map(self.post, [self.packet] * 4))
        self.assertEqual(len({r["id"] for r in result}), 1)
        self.assertEqual(result[0]["payable_cents"], 255000)
        self.assertIn("2,550.00", result[0]["actions"][1]["notice_text"])
        alias = self.post({**self.packet, "case_id": "RESCAN"})
        self.assertEqual(alias["status"], "REVIEW")
        self.assertEqual(self.count(), 1)

    def test_missing_evidence_keeps_original_receipt(self):
        original = self.post(service.get_sample(True))
        self.assertEqual(self.count(), 0)
        updated = service.resolve(original["id"], {"pod_minutes": 120, "evidence_ref": "GATE-17"})
        self.assertEqual(updated["status"], "SETTLED")
        receipt = service.receipt_data(original["id"])
        self.assertEqual([r["status"] for r in receipt["attempts"]], ["REVIEW","SETTLED"])
        self.assertEqual(self.count(), 1)

    def test_authority_and_rate_outage_block_posting(self):
        case = self.post({**self.packet, "cap_paise": 20_000_000})
        self.assertEqual(case["fx"]["payable_paise"], 21_675_000)
        self.assertFalse(case["actions"])
        with patch.object(service, "assess", side_effect=ValueError("No dated quote")):
            case = self.post(self.packet)
        self.assertEqual(case["status"], "REVIEW")
        self.assertEqual(self.count(), 0)
        self.assertEqual(service.retry(case["id"])["status"], "SETTLED")

    def test_rolled_back_post_can_be_retried(self):
        with service.database(True) as db:
            db.execute("""CREATE TRIGGER fail_log BEFORE INSERT ON attempts
                          BEGIN SELECT RAISE(ABORT, 'interrupted'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.post(self.packet)
        self.assertEqual(self.count(), 0)
        with service.database(True) as db:
            db.execute("DROP TRIGGER fail_log")
        self.assertEqual(self.post(self.packet)["status"], "SETTLED")
        self.assertEqual(self.count(), 1)

    def test_replay_is_flagged_without_a_second_posting(self):
        first = self.post(self.packet)
        self.assertNotIn("replayed", first)
        again = self.post(self.packet)
        self.assertTrue(again["replayed"])
        self.assertEqual(again["id"], first["id"])
        self.assertTrue(service.retry(first["id"])["replayed"])
        self.assertNotIn("replayed", service.history()[0])
        self.assertEqual(service.status()["postings"], 1)

    def test_resubmitted_original_of_resolved_case_replays(self):
        held = self.post(service.get_sample(True))
        service.resolve(held["id"], {"pod_minutes": 120, "evidence_ref": "GL-018"})
        again = self.post(service.get_sample(True))
        self.assertTrue(again["replayed"])
        self.assertEqual(again["status"], "SETTLED")
        self.assertEqual(again["packet"]["evidence_ref"], "GL-018")
        self.assertEqual(self.count(), 1)
        changed = {**service.get_sample(True), "detention_cents_per_hour": 20_000}
        with self.assertRaises(service.ServiceError) as caught:
            self.post(changed)
        self.assertEqual(caught.exception.status_code, 409)

    def test_short_pay_notice_itemizes_each_charge(self):
        notice = self.post(self.packet)["actions"][1]["notice_text"]
        rows = {line.split()[0]: line.split()[1:] for line in notice.splitlines() if line.strip()}
        self.assertEqual(rows["Detention"], ["450.00", "150.00", "300.00"])
        self.assertEqual(rows["Total"], ["2,850.00", "2,550.00", "300.00"])

    def test_fx_mode_runs_live_without_live_invoice_reader(self):
        fake = dict(approved=True, reason="ok", sources=["ECB"], rate="94.96",
                    rate_date="2026-10-16", payable_paise=24_214_800, url="https://example.test")
        with patch.object(service, "FX_MODE", "live"), \
                patch.object(service, "assess", return_value=fake) as assess:
            case = self.post(self.packet)
        self.assertEqual(assess.call_args.args[-1], "live")
        self.assertEqual(case["calls"][0]["service"], "Fixture reader")
        self.assertEqual(case["calls"][1]["service"], "Frankfurter")
        self.assertEqual((case["mode"], case["fx_mode"]), ("mock", "live"))

    def test_status_endpoint_over_http(self):
        self.post(self.packet)
        server = ThreadingHTTPServer(("127.0.0.1", 0), offline_server.Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/status") as response:
            body = json.loads(response.read())
        self.assertEqual(body, {"mode": "mock", "fx_mode": "mock", "cases": 1, "postings": 1})

    def test_fresh_clears_only_sqlite_sandbox(self):
        self.post(self.packet)
        with patch("builtins.print"):
            offline_server.clear_sandbox()
        self.assertFalse(Path(self.path).exists())
        other = Path(self.path).with_name("ledger.csv")
        other.write_text("keep")
        with patch.dict(os.environ, FREIGHT_DB=str(other)), self.assertRaises(SystemExit):
            offline_server.clear_sandbox()
        self.assertTrue(other.exists())
