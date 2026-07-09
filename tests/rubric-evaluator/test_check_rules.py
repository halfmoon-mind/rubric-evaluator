import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TEST_ROOT))
SKILL_ROOT = os.path.join(REPO_ROOT, "plugins", "rubric-evaluator", "skills", "rubric-evaluator")
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

import check_rules as cr  # noqa: E402
import render_report  # noqa: E402


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
        self.assertNotIn("category", fm)

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

    def test_folded_scalar_joins_lines_with_spaces(self):
        text = (
            "---\n"
            "name: x\n"
            "description: >-\n"
            "  Evaluate spreadsheets and generate charts.\n"
            "  Use when asked to analyze xlsx files.\n"
            "---\nbody"
        )
        fm, _, ok, err = cr.parse_frontmatter(text)
        self.assertTrue(ok, err)
        self.assertEqual(
            fm["description"],
            "Evaluate spreadsheets and generate charts. Use when asked to analyze xlsx files.",
        )

    def test_literal_scalar_keeps_newlines(self):
        text = "---\nname: x\ndescription: |\n  line one\n  line two\n---\nbody"
        fm, _, ok, err = cr.parse_frontmatter(text)
        self.assertTrue(ok, err)
        self.assertEqual(fm["description"], "line one\nline two")

    def test_folded_scalar_key_after_block(self):
        text = "---\ndescription: >-\n  folded text\nname: x\n---\nbody"
        fm, _, ok, err = cr.parse_frontmatter(text)
        self.assertTrue(ok, err)
        self.assertEqual(fm["description"], "folded text")
        self.assertEqual(fm["name"], "x")

    def test_top_level_keys_listed(self):
        fm, _, ok, _ = cr.parse_frontmatter(
            "---\nname: x\ndescription: y\nallowed-tools: Read\n---\nb"
        )
        self.assertTrue(ok)
        self.assertEqual(set(cr.top_level_keys(fm)), {"name", "description", "allowed-tools"})


class ComputeGradeTests(unittest.TestCase):
    def _f(self, severity, status):
        return {"severity": severity, "status": status}

    def test_blocker_is_f(self):
        self.assertEqual(cr.compute_grade([self._f("BLOCKER", "fail")]), "F")

    def test_no_fail_is_s(self):
        self.assertEqual(
            cr.compute_grade([self._f("MAJOR", "pass"), self._f("BLOCKER", "na")]), "S"
        )

    def test_one_major_is_a(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")]), "A")

    def test_three_majors_is_b(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 3), "B")

    def test_five_majors_is_c(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 5), "C")

    def test_minor_does_not_affect_grade(self):
        self.assertEqual(cr.compute_grade([self._f("MINOR", "fail")] * 9), "S")


class SecretCheckTests(unittest.TestCase):
    def _eval_6_1(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = os.path.join(tmp, "sample-skill")
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write(
                    "---\nname: sample-skill\n"
                    "description: Summarize sample data. Use when asked to summarize samples.\n"
                    "---\n\n# Sample\n\n" + body
                )
            result = cr.evaluate_skill(skill_dir)
        finding = next(f for f in result["findings"] if f["id"] == "6.1")
        return finding, result["grade"]

    def test_private_key_block_fails(self):
        finding, grade = self._eval_6_1("-----BEGIN RSA PRIVATE KEY-----\n")
        self.assertEqual(finding["status"], "fail")
        self.assertEqual(grade, "F")

    def test_aws_access_key_fails(self):
        finding, grade = self._eval_6_1("AKIAIOSFODNN7EXAMPLE\n")
        self.assertEqual(finding["status"], "fail")
        self.assertEqual(grade, "F")

    def test_credential_assignment_is_na_for_model_review(self):
        finding, grade = self._eval_6_1('api_key = "your-real-api-key-goes-here"\n')
        self.assertEqual(finding["status"], "na")
        self.assertIn("SKILL.md", finding["why"])
        self.assertNotEqual(grade, "F")

    def test_clean_body_passes(self):
        finding, _ = self._eval_6_1("No credentials here.\n")
        self.assertEqual(finding["status"], "pass")


class CliTests(unittest.TestCase):
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
                [
                    sys.executable,
                    os.path.join(SKILL_ROOT, "scripts", "check_rules.py"),
                    "--grade",
                    path,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.strip(), "A")
        finally:
            os.unlink(path)

    def test_render_report_shows_grade_and_fix(self):
        findings = [
            {
                "id": "3.4",
                "section": "trigger",
                "item": "body-only trigger anti-pattern absent",
                "severity": "BLOCKER",
                "status": "fail",
                "checker": "model",
                "why": "The trigger is only in the body.",
                "how_to_fix": "Move the trigger into the description.",
            }
        ]
        report = render_report.render_report(findings, skill_name="Example")
        self.assertIn("grade F", report)
        self.assertIn("3.4", report)
        self.assertIn("Move the trigger", report)

    def test_run_checks_wrapper_runs_clean_fixture(self):
        if not shutil.which("sh"):
            self.skipTest("sh is not available")
        out = subprocess.run(
            [
                "sh",
                os.path.join(SKILL_ROOT, "scripts", "run_checks.sh"),
                os.path.join(TEST_ROOT, "fixtures", "clean"),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["grade"], "S")


class SkillSurfaceTests(unittest.TestCase):
    def test_fallback_resources_are_discoverable(self):
        skill_md = cr.read_text(os.path.join(SKILL_ROOT, "SKILL.md"))
        self.assertIn("scripts/run_checks.sh", skill_md)
        self.assertIn("references/fallbacks.md", skill_md)
        self.assertIn("provisional", skill_md.lower())


if __name__ == "__main__":
    unittest.main()
