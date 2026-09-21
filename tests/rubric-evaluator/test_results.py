import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins/rubric-evaluator/skills/rubric-evaluator/scripts"
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import check_rules as cr
import compare_results as diff
import render_report
import results


def finding(fid, status="pass"):
    return {
        "id": fid, "section": results.SECTIONS[int(fid.split(".")[0])],
        "item": "Example criterion", "severity": results.SEVERITIES[fid],
        "status": status, "checker": "model" if fid in results.MODEL_IDS else "rule",
        "why": "Example evidence" if status != "pass" else "",
        "how_to_fix": "Example correction" if status == "fail" else "",
    }


class ResultsTests(unittest.TestCase):
    def test_complete_and_partial_coverage(self):
        all_findings = [finding(fid) for fid in results.SEVERITIES]
        self.assertEqual(len(all_findings), 31)
        self.assertEqual(results.coverage(all_findings)["status"], "complete")
        all_findings[0]["status"] = "na"
        all_findings[0]["why"] = "Needs review"
        self.assertEqual(results.coverage(all_findings)["judged"], 30)
        self.assertEqual(results.coverage(all_findings)["status"], "partial")

    def test_reject_invalid_findings(self):
        bad_cases = [[], {}, [None], [finding("2.1"), finding("2.1")]]
        for field, value in [("id", "9.9"), ("status", "PASS"), ("severity", "MINOR"),
                             ("section", "safety"), ("checker", "model"), ("item", " "), ("why", None)]:
            bad_cases.append([{**finding("2.1"), field: value}])
        bad_cases.append([{**finding("2.1", "fail"), "how_to_fix": ""}])
        bad_cases.append([{**finding("2.1", "na"), "why": ""}])
        for case in bad_cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                results.validate_findings(case)

    def test_rule_result_has_provenance_and_coverage(self):
        result = cr.evaluate_skill(FIXTURES / "clean")
        self.assertEqual(result["coverage"]["judged"], 17)
        self.assertEqual(len(result["coverage"]["missing_ids"]), 14)
        self.assertEqual(result["coverage"]["status"], "partial")
        self.assertEqual(len(result["target_hash"]), 64)
        self.assertEqual(len(result["rubric_hash"]), 64)
        self.assertEqual(result["target_hash"], cr.evaluate_skill(FIXTURES / "clean")["target_hash"])

    def test_hash_tracks_content_and_names_but_not_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "SKILL.md"
            file.write_text("one")
            first = results.tree_hash(root)
            (root / "__pycache__").mkdir()
            (root / "__pycache__/cache.pyc").write_bytes(b"cache")
            self.assertEqual(first, results.tree_hash(root))
            file.write_text("two")
            second = results.tree_hash(root)
            self.assertNotEqual(first, second)
            file.rename(root / "OTHER.md")
            self.assertNotEqual(second, results.tree_hash(root))

    def test_hash_uses_identical_case_sensitive_order_on_all_platforms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = hashlib.sha256()
            for name in ("Z.md", "a.md"):
                (root / name).write_bytes(b"content")
                expected.update(name.encode() + b"\0")
                expected.update(hashlib.sha256(b"content").digest())
            self.assertEqual(results.tree_hash(root), expected.hexdigest())

    def test_missing_bash_is_unresolved_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts/check.sh").write_text("echo valid\n", encoding="utf-8")
            with patch.object(cr.shutil, "which", return_value=None):
                result = cr.check_5_6(cr.build_context(root))
            self.assertEqual(result["status"], "na")
            self.assertIn("Bash is unavailable", result["why"])

    def test_report_does_not_pass_unchecked_sections(self):
        report = render_report.render_report([finding("2.1")])
        self.assertIn("validity: PARTIAL (0/3 judged)", report)
        self.assertIn("structure: PARTIAL (1/8 judged)", report)
        self.assertIn("provisional", report)
        complete = render_report.render_report([finding(fid) for fid in results.SEVERITIES])
        self.assertNotIn("PARTIAL", complete)

    def test_gates_include_higher_severities_and_completeness(self):
        self.assertTrue(results.gate_failed([finding("2.1", "fail")], "major"))
        self.assertFalse(results.gate_failed([finding("2.8", "fail")], "major"))
        self.assertTrue(results.gate_failed([finding("2.8", "fail")], "minor"))
        self.assertTrue(results.gate_failed([finding("2.1")], require_complete=True))

    def test_comparison_requires_positive_resolution(self):
        before = {"findings": [finding("2.1", "fail"), finding("2.2", "fail"), finding("2.3", "fail"), finding("2.4"), finding("2.5", "na")]}
        after = {"findings": [finding("2.1"), finding("2.2", "na"), finding("2.4", "fail"), finding("2.5", "fail")]}
        comparison = diff.compare_results(before, after)
        self.assertEqual(comparison["resolved"], ["2.1"])
        self.assertEqual(comparison["unverified"], ["2.2", "2.3"])
        self.assertEqual(comparison["introduced"], ["2.4"])
        self.assertEqual(comparison["newly_observed"], ["2.5"])
        self.assertTrue(comparison["warnings"])

    def test_comparison_recomputes_grade_and_detects_rubric_change(self):
        before = {"findings": [finding("2.1", "fail")], "grade": "S", "rubric_version": "1", "rubric_hash": "a"}
        after = copy.deepcopy(before)
        after["rubric_hash"] = "b"
        comparison = diff.compare_results(before, after)
        self.assertEqual(comparison["before_grade"], "F")
        self.assertIn("rubric_hash changed", " ".join(comparison["warnings"]))


class WorkflowCliTests(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, encoding="utf-8")

    def test_unicode_space_paths_and_bom_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "한글 경로"
            root.mkdir()
            target = root / "clean"
            shutil.copytree(FIXTURES / "clean", target)
            installed = root / "설치 경로"
            shutil.copytree(SCRIPTS, installed, ignore=shutil.ignore_patterns("__pycache__"))
            command = [sys.executable, "-B", str(installed / "check_rules.py"), str(target)]
            output = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    env={**os.environ, "PYTHONIOENCODING": "ascii"})
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertEqual(json.loads(output.stdout)["grade"], "S")
            saved = root / "결과.json"
            saved.write_text(output.stdout, encoding="utf-8-sig")
            report = self.run_cli("render_report.py", saved, "--skill-name", "한글 스킬")
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn("한글 스킬", report.stdout)
            self.assertEqual(self.run_cli("check_rules.py", saved, "--grade").returncode, 0)
            self.assertEqual(self.run_cli("compare_results.py", saved, saved).returncode, 0)
            if shutil.which("sh"):
                wrapper = subprocess.run(["sh", (installed / "run_checks.sh").as_posix(), str(target)],
                                         capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
                self.assertEqual(json.loads(wrapper.stdout)["grade"], "S")

    def test_gate_exit_codes(self):
        clean = self.run_cli("check_rules.py", FIXTURES / "clean", "--fail-on", "major")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        bad = self.run_cli("check_rules.py", FIXTURES / "missing-description", "--fail-on", "major")
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(json.loads(bad.stdout)["grade"], "F")
        partial = self.run_cli("check_rules.py", FIXTURES / "clean", "--require-complete")
        self.assertEqual(partial.returncode, 1)
        invalid = self.run_cli("check_rules.py", FIXTURES / "does-not-exist")
        self.assertEqual(invalid.returncode, 2)
        self.assertNotIn("Traceback", invalid.stderr)

    def test_batch_report_and_empty_directory(self):
        batch = self.run_cli("check_rules.py", FIXTURES, "--batch")
        self.assertEqual(batch.returncode, 0, batch.stderr)
        items = json.loads(batch.stdout)["results"]
        self.assertGreater(len(items), 3)
        with tempfile.TemporaryDirectory() as tmp:
            empty = self.run_cli("check_rules.py", tmp, "--batch")
            self.assertEqual(empty.returncode, 2)
            path = Path(tmp) / "batch.json"
            path.write_text(batch.stdout)
            report = self.run_cli("render_report.py", path)
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn("| Rule grade |", report.stdout)
            self.assertIn("partial", report.stdout)

    def test_grade_validates_input_and_labels_full_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            for data in ([], [{"id": "2.1"}], {"schema_version": 999, "findings": [finding("2.1")]}):
                path.write_text(json.dumps(data))
                self.assertEqual(self.run_cli("check_rules.py", path, "--grade").returncode, 2)
            path.write_text(json.dumps([finding(fid) for fid in results.SEVERITIES]))
            complete = self.run_cli("check_rules.py", path, "--grade", "--require-complete")
            self.assertEqual(complete.returncode, 0, complete.stderr)
            self.assertEqual(complete.stdout.strip(), "S")

    def test_finalize_preserves_provenance_and_refreshes_stale_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            result = cr.evaluate_skill(FIXTURES / "clean")
            result["findings"].extend(finding(fid) for fid in results.MODEL_IDS)
            result["grade"] = "F"
            path.write_text(json.dumps(result))
            output = self.run_cli("check_rules.py", path, "--finalize", "--require-complete")
            self.assertEqual(output.returncode, 0, output.stderr)
            final = json.loads(output.stdout)
            self.assertEqual(final["grade"], "S")
            self.assertEqual(final["coverage"]["status"], "complete")
            self.assertEqual(final["target_hash"], result["target_hash"])

    def test_compare_cli_and_invalid_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / "before.json"
            after = Path(tmp) / "after.json"
            before.write_text(json.dumps([finding("2.1", "fail")]))
            after.write_text(json.dumps([finding("2.1")]))
            output = self.run_cli("compare_results.py", before, after, "--json")
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertEqual(json.loads(output.stdout)["resolved"], ["2.1"])
            for bad in ({"results": [None]}, [], {"findings": "bad"}):
                after.write_text(json.dumps(bad))
                output = self.run_cli("render_report.py", after)
                self.assertEqual(output.returncode, 2)
                self.assertNotIn("Traceback", output.stderr)


if __name__ == "__main__":
    unittest.main()
