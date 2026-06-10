import json
import os
import sys
import unittest

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TEST_ROOT))
SKILL_ROOT = os.path.join(REPO_ROOT, "plugins", "rubric-evaluator", "skills", "rubric-evaluator")
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

import check_rules as cr  # noqa: E402


FIXTURES = os.path.join(TEST_ROOT, "fixtures")


class FixtureTests(unittest.TestCase):
    def test_fixture_expectations(self):
        for name in sorted(os.listdir(FIXTURES)):
            fixture_dir = os.path.join(FIXTURES, name)
            expected_path = os.path.join(fixture_dir, "expected.json")
            if not os.path.isdir(fixture_dir) or not os.path.exists(expected_path):
                continue
            with self.subTest(fixture=name):
                with open(expected_path, "r", encoding="utf-8") as fh:
                    expected = json.load(fh)
                result = cr.evaluate_skill(fixture_dir)
                actual_fail = sorted(
                    finding["id"] for finding in result["findings"] if finding["status"] == "fail"
                )
                self.assertEqual(actual_fail, sorted(expected["expected_fail"]))
                self.assertEqual(result["grade"], expected["expected_grade"])
                self.assertEqual(len(result["findings"]), 17)


if __name__ == "__main__":
    unittest.main()
