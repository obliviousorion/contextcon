"""Financial-control regressions. Run with python -m unittest discover -v."""
import unittest
from unittest.mock import patch

from engine import run_case
from intake import extract
from samples import sample


class FreightCloseTests(unittest.TestCase):
    def setUp(self):
        self.packet = sample()
        self.invoice = extract(self.packet["invoice_text"], "mock")

    def decide(self):
        return run_case(self.packet, self.invoice)

    def assert_review(self):
        decision = self.decide()
        self.assertEqual(decision["status"], "REVIEW")
        self.assertFalse(decision["payable_cents"])

    def test_demo_reconciles_every_cent(self):
        decision = self.decide()
        self.assertEqual(decision["status"], "SETTLED")
        self.assertEqual(decision["payable_cents"], 255_000)
        self.assertEqual(decision["recovered_cents"], 30_000)
        self.assertEqual(
            decision["payable_cents"] + decision["recovered_cents"],
            self.invoice["total_cents"],
        )
        self.assertTrue(decision["actions"])
        self.assertTrue(decision["trace"])
        for entry in decision["trace"]:
            self.assertTrue(entry["reason"].strip())
            self.assertTrue(all(entry["sources"]))
            self.assertGreater(len(entry["sources"]), 0)

    def test_line_items_reconcile_to_payable_and_deduction(self):
        decision = self.decide()
        lines = {line["charge"]: line for line in decision["lines"]}
        self.assertEqual(lines["Line haul"]["withheld_cents"], 0)
        self.assertEqual(lines["Detention"]["supported_cents"], 15_000)
        self.assertEqual(lines["Detention"]["withheld_cents"], 30_000)
        self.assertIn("1 billable hour", lines["Detention"]["basis"])
        self.assertEqual(sum(l["supported_cents"] for l in lines.values()), decision["payable_cents"])
        self.assertEqual(sum(l["withheld_cents"] for l in lines.values()), decision["recovered_cents"])

    def test_missing_pod_leaves_detention_line_unpriced(self):
        self.packet = sample(missing=True)
        self.invoice = extract(self.packet["invoice_text"], "mock")
        detention = self.decide()["lines"][-1]
        self.assertEqual(detention["charge"], "Detention")
        self.assertIsNone(detention["supported_cents"])
        self.assertIsNone(detention["withheld_cents"])

    def test_missing_pod_holds_then_evidence_releases(self):
        self.packet = sample(missing=True)
        self.invoice = extract(self.packet["invoice_text"], "mock")
        self.assert_review()
        self.packet["pod_minutes"] = 120
        self.assertEqual(self.decide()["payable_cents"], 255_000)

    def test_partial_hour_does_not_earn_full_hour(self):
        self.packet["pod_minutes"] = 119
        self.assertEqual(self.decide()["payable_cents"], 240_000)

    def test_free_period_has_no_negative_charge(self):
        self.packet["pod_minutes"] = 5
        self.assertEqual(self.decide()["payable_cents"], 240_000)

    def test_inconsistent_invoice_math_holds(self):
        self.invoice["total_cents"] += 1
        self.assert_review()

    def test_unrelated_po_holds(self):
        self.invoice["po_id"] = "PO-UNRELATED"
        self.assert_review()

    def test_invalid_delivery_evidence_holds(self):
        for value in [-1, True, "120", 75.5]:
            with self.subTest(value=value):
                self.packet["pod_minutes"] = value
                self.assert_review()

    def test_invalid_invoice_does_not_extract_as_payable(self):
        with self.assertRaises(ValueError):
            extract("Please pay the invoice immediately. No itemized charges.", "mock")

    def test_ambiguous_currency_and_extra_charges_hold(self):
        original = self.packet["invoice_text"]
        for text in [original.replace("USD", "EUR"), original + "\nTotal due: $2,950.00",
                     original + "\nFuel surcharge: $100.00"]:
            with self.subTest(invoice=text):
                with self.assertRaises(ValueError):
                    extract(text, "mock")

    def test_live_classification_needs_verbatim_evidence(self):
        original = self.packet["invoice_text"]
        text = original.replace("Linehaul:", "Line haul for outbound leg:")
        evidence = dict(self.invoice["sources"], base_cents="Line haul for outbound leg: $2,400.00")
        with patch("intake._model_lines", return_value=(evidence, {})):
            self.assertEqual(extract(text, "live")["base_cents"], 240000)
        evidence["base_cents"] = "Line haul for outbound leg: $3,400.00"
        with patch("intake._model_lines", return_value=(evidence, {})):
            with self.assertRaises(ValueError):
                extract(text, "live")


if __name__ == "__main__":
    unittest.main()
