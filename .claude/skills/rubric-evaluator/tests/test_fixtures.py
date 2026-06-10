import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
CHECK = os.path.join(ROOT, "scripts", "check_rules.py")


def run_check(skill_dir):
    out = subprocess.run([sys.executable, CHECK, skill_dir],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("check_rules failed: " + out.stderr)
    return json.loads(out.stdout)


class FixtureTests(unittest.TestCase):
    pass


def _make_test(name):
    def test(self):
        fixture_dir = os.path.join(FIXTURES, name)
        with open(os.path.join(fixture_dir, "expected.json")) as fh:
            expected = json.load(fh)
        result = run_check(fixture_dir)
        actual_fail = sorted(f["id"] for f in result["findings"]
                             if f["status"] == "fail")
        self.assertEqual(actual_fail, sorted(expected["expected_fail"]),
                         "%s: fail-set mismatch" % name)
        self.assertEqual(result["grade"], expected["expected_grade"],
                         "%s: grade mismatch" % name)
    return test


for _name in sorted(os.listdir(FIXTURES)) if os.path.isdir(FIXTURES) else []:
    if os.path.isdir(os.path.join(FIXTURES, _name)):
        setattr(FixtureTests, "test_" + _name.replace("-", "_"), _make_test(_name))


if __name__ == "__main__":
    unittest.main()
