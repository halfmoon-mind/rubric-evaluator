import os
import sys
import unittest

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TEST_ROOT)

import compare_model_findings as cmf  # noqa: E402


class CompareTests(unittest.TestCase):
    def test_repeat_metrics_separate_accuracy_and_agreement(self):
        runs = [
            [{"id": "3.4", "status": "pass"}, {"id": "4.1", "status": "fail"}],
            [{"id": "3.4", "status": "pass"}, {"id": "4.1", "status": "pass"}],
        ]
        metrics = cmf.measure(runs, {"3.4": "fail", "4.1": "pass"})
        self.assertEqual(metrics["accuracy"], 0.25)
        self.assertEqual(metrics["agreement"], 0.5)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 2)

    def test_missing_runs_do_not_count_as_agreement(self):
        metrics = cmf.measure([[], []], {"3.4": "fail"})
        self.assertEqual(metrics["missing"], 2)
        self.assertEqual(metrics["agreement"], 0)
        self.assertIsNone(cmf.measure([[]], {"3.4": "fail"})["agreement"])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            cmf.measure([[{"id": "3.4", "status": "pass"}] * 2], {"3.4": "pass"})

    def test_matching_statuses_return_no_mismatches(self):
        actual = [{"id": "3.4", "status": "fail"}, {"id": "4.1", "status": "pass"}]
        self.assertEqual(cmf.compare(actual, {"3.4": "fail", "4.1": "pass"}), [])

    def test_wrong_status_is_reported(self):
        actual = [{"id": "3.4", "status": "pass"}]
        mismatches = cmf.compare(actual, {"3.4": "fail"})
        self.assertEqual(len(mismatches), 1)
        self.assertIn("3.4", mismatches[0])
        self.assertIn("fail", mismatches[0])

    def test_missing_id_is_reported(self):
        mismatches = cmf.compare([], {"1.1": "pass"})
        self.assertEqual(len(mismatches), 1)
        self.assertIn("1.1", mismatches[0])

    def test_ids_not_in_expected_are_ignored(self):
        actual = [{"id": "5.2", "status": "na"}, {"id": "3.4", "status": "fail"}]
        self.assertEqual(cmf.compare(actual, {"3.4": "fail"}), [])


class FixtureExpectationTests(unittest.TestCase):
    def test_calibration_fixtures_have_expected_model(self):
        for name in ("model-strong", "body-only-trigger", "generic-advice", "operational-precondition", "overbroad-trigger"):
            path = os.path.join(TEST_ROOT, "fixtures", name, "expected-model.json")
            self.assertTrue(os.path.exists(path), f"missing {path}")


if __name__ == "__main__":
    unittest.main()
