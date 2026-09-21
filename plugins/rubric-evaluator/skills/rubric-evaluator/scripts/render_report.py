#!/usr/bin/env python3
"""Render rubric findings as a concise markdown report."""

import argparse
import json
import sys
from pathlib import Path

from check_rules import compute_grade
from results import SEVERITIES, SECTIONS, coverage, load_result, validate_findings

SEVERITY_ORDER = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2}
SECTION_ORDER = ["validity", "structure", "trigger", "content", "resources", "safety"]


def read_text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def load_findings(path):
    return load_result(path)["findings"]


def failed_findings(findings):
    return [finding for finding in findings if finding.get("status") == "fail"]


def counts(findings):
    failed = failed_findings(findings)
    return {
        "BLOCKER": sum(1 for item in failed if item.get("severity") == "BLOCKER"),
        "MAJOR": sum(1 for item in failed if item.get("severity") == "MAJOR"),
        "MINOR": sum(1 for item in failed if item.get("severity") == "MINOR"),
    }


def sort_findings(findings):
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity"), 99),
            tuple(int(part) for part in item.get("id", "99.99").split(".")),
        ),
    )


def render_report(findings, skill_name="Skill"):
    status = coverage(findings)
    grade = compute_grade(findings)
    tally = counts(findings)
    lines = [
        f"TL;DR: [{skill_name}] grade {grade} ({status['status']}) | "
        f"BLOCKER {tally['BLOCKER']}, MAJOR {tally['MAJOR']}, MINOR {tally['MINOR']}",
        "",
        f"Evaluation: {status['status']} ({status['judged']}/{status['total']} judged).",
        "",
    ]
    if status["missing_ids"]:
        lines.append("Missing checks: " + ", ".join(status["missing_ids"]))
    if status["unresolved_ids"]:
        lines.append("Unresolved checks (na): " + ", ".join(status["unresolved_ids"]))
    if status["status"] == "partial":
        lines.extend(["Grade is provisional and reflects only supplied findings.", ""])

    failed = sort_findings(failed_findings(findings))
    blockers = [item for item in failed if item.get("severity") == "BLOCKER"]
    majors = [item for item in failed if item.get("severity") == "MAJOR"]
    minors = [item for item in failed if item.get("severity") == "MINOR"]

    def add_group(title, items):
        lines.append(f"{title}:")
        if not items:
            lines.append("- None")
        for item in items:
            lines.append(f"- {item.get('id')} {item.get('item')}")
            lines.append(f"  why: {item.get('why') or 'No detail provided.'}")
            lines.append(f"  how_to_fix: {item.get('how_to_fix') or 'No fix provided.'}")
        lines.append("")

    add_group("Blocking issues", blockers)
    add_group("Priority fixes", majors)
    add_group("Recommendations", minors)

    lines.append("Section summary:")
    for section in SECTION_ORDER:
        section_failed = [item for item in failed if item.get("section") == section]
        expected = {fid for fid in SEVERITIES if SECTIONS[int(fid.split('.')[0])] == section}
        judged = {f["id"] for f in findings if f["section"] == section and f["status"] != "na"}
        partial = f"PARTIAL ({len(judged)}/{len(expected)} judged)"
        if not section_failed:
            lines.append(f"- {section}: {'PASS' if judged == expected else partial}")
            continue
        section_counts = counts(section_failed)
        parts = []
        for severity in ("BLOCKER", "MAJOR", "MINOR"):
            if section_counts[severity]:
                parts.append(f"{section_counts[severity]} {severity}")
        if judged != expected:
            parts.append(partial)
        lines.append(f"- {section}: {', '.join(parts)}")

    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render rubric findings as markdown.")
    parser.add_argument("findings_json", help="JSON array or object containing findings")
    parser.add_argument("--skill-name", default="Skill", help="Display name for the report")
    args = parser.parse_args(argv)
    try:
        data = json.loads(read_text(args.findings_json))
        if isinstance(data, dict) and "results" in data:
            rows = ["| Skill | Rule grade | Evaluation | BLOCKER | MAJOR | MINOR |", "|---|---|---|---|---|---|"]
            if not isinstance(data["results"], list) or not data["results"]:
                raise ValueError("results must be a non-empty array")
            for result in data["results"]:
                if not isinstance(result, dict):
                    raise ValueError("every batch result must be an object")
                findings = validate_findings(result.get("findings"))
                status = coverage(findings)
                tally = counts(findings)
                name = str(result.get("target", "Skill")).replace("|", "\\|").replace("\n", " ")
                rows.append(f"| {name} | {compute_grade(findings)} | {status['status']} {status['judged']}/31 | {tally['BLOCKER']} | {tally['MAJOR']} | {tally['MINOR']} |")
            sys.stdout.write("\n".join(rows) + "\n")
        else:
            result = load_result(args.findings_json)
            sys.stdout.write(render_report(result["findings"], skill_name=args.skill_name))
            for key in ("rubric_version", "rubric_hash", "target_hash"):
                if key in result:
                    print(f"{key}: {result[key]}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
