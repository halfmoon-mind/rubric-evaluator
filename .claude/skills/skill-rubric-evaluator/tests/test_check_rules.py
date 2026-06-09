import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check_rules as cr  # noqa: E402


class ParseFrontmatterTests(unittest.TestCase):
    def test_basic_keys(self):
        fm, body, ok, err = cr.parse_frontmatter(
            "---\nname: my-skill\ndescription: does a thing\n---\n# Title\nhi"
        )
        self.assertTrue(ok, err)
        self.assertEqual(fm["name"], "my-skill")
        self.assertEqual(fm["description"], "does a thing")
        self.assertEqual(body.strip(), "# Title\nhi")

    def test_quoted_value(self):
        fm, _, ok, _ = cr.parse_frontmatter('---\nname: "my-skill"\n---\nbody')
        self.assertTrue(ok)
        self.assertEqual(fm["name"], "my-skill")

    def test_nested_metadata_children_not_top_level(self):
        text = "---\nname: x\nmetadata:\n  category: test\n---\nbody"
        fm, _, ok, _ = cr.parse_frontmatter(text)
        self.assertTrue(ok)
        self.assertIn("metadata", fm)
        self.assertNotIn("category", fm)  # indented child is not a top-level key

    def test_missing_opening_delimiter(self):
        _, _, ok, err = cr.parse_frontmatter("name: x\n---\nbody")
        self.assertFalse(ok)
        self.assertIn("opening", err)

    def test_missing_closing_delimiter(self):
        _, _, ok, err = cr.parse_frontmatter("---\nname: x\nbody with no close")
        self.assertFalse(ok)
        self.assertIn("closing", err)

    def test_tab_indentation_is_unparseable(self):
        _, _, ok, err = cr.parse_frontmatter("---\nname: x\n\tbad: y\n---\nbody")
        self.assertFalse(ok)
        self.assertIn("tab", err)

    def test_block_list_value(self):
        text = "---\nname: x\nallowed-tools:\n  - Bash(rm -rf /)\n  - Read\n---\nbody"
        fm, _, ok, _ = cr.parse_frontmatter(text)
        self.assertTrue(ok)
        self.assertEqual(fm["allowed-tools"], ["Bash(rm -rf /)", "Read"])

    def test_top_level_keys_listed(self):
        fm, _, ok, _ = cr.parse_frontmatter(
            "---\nname: x\ndescription: y\nallowed-tools: Read\n---\nb"
        )
        self.assertEqual(set(cr.top_level_keys(fm)), {"name", "description", "allowed-tools"})

    def test_list_valued_name_description_do_not_crash_checks(self):
        # Malformed block-list 'name'/'description' must not crash run_checks;
        # they coerce to a string view, yielding a clean 2.2 finding instead.
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "SKILL.md"), "w") as fh:
            fh.write("---\nname:\n  - foo\ndescription:\n  - bar\n---\nbody")
        ctx = cr.build_ctx(d)
        self.assertIsInstance(ctx.name, str)
        self.assertIsInstance(ctx.description, str)
        findings = cr.run_checks(d)  # must not raise
        self.assertTrue(any(x["id"] == "2.2" for x in findings))


class ComputeGradeTests(unittest.TestCase):
    def _f(self, severity, status):
        return {"severity": severity, "status": status}

    def test_blocker_is_F(self):
        self.assertEqual(cr.compute_grade([self._f("BLOCKER", "fail")]), "F")

    def test_no_fail_is_S(self):
        self.assertEqual(
            cr.compute_grade([self._f("MAJOR", "pass"), self._f("BLOCKER", "na")]), "S"
        )

    def test_one_major_is_A(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")]), "A")

    def test_three_majors_is_B(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 3), "B")

    def test_five_majors_is_C(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 5), "C")

    def test_minor_does_not_affect_grade(self):
        self.assertEqual(cr.compute_grade([self._f("MINOR", "fail")] * 9), "S")


class GradeModeCliTests(unittest.TestCase):
    def test_grade_mode_reads_combined_findings(self):
        findings = [
            {"id": "1.1", "severity": "MAJOR", "status": "fail"},
            {"id": "2.1", "severity": "BLOCKER", "status": "pass"},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(findings, fh)
            path = fh.name
        try:
            out = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "check_rules.py"),
                 "--grade", path],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.strip(), "A")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
