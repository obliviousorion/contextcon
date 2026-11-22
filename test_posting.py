import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

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
