#!/usr/bin/env python3
"""Render skill rubric findings as a concise markdown report."""

import argparse
import json
import sys
from pathlib import Path

from check_rules import compute_grade

SEVERITY_ORDER = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2}
SECTION_ORDER = ["validity", "structure", "trigger", "content", "resources", "safety"]


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def load_findings(path):
    data = json.loads(read_text(path))
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    if isinstance(data, list):
        return data
    raise ValueError("Expected a JSON array or an object with a findings array.")


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
    grade = compute_grade(findings)
    tally = counts(findings)
    lines = [
        f"TL;DR: [{skill_name}] grade {grade} | "
        f"BLOCKER {tally['BLOCKER']}, MAJOR {tally['MAJOR']}, MINOR {tally['MINOR']}",
        "",
    ]

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
        if not section_failed:
            lines.append(f"- {section}: PASS")
            continue
        section_counts = counts(section_failed)
        parts = []
        for severity in ("BLOCKER", "MAJOR", "MINOR"):
            if section_counts[severity]:
                parts.append(f"{section_counts[severity]} {severity}")
        lines.append(f"- {section}: {', '.join(parts)}")

    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render skill rubric findings as markdown.")
    parser.add_argument("findings_json", help="JSON array or object containing findings")
    parser.add_argument("--skill-name", default="Skill", help="Display name for the report")
    args = parser.parse_args(argv)
    findings = load_findings(args.findings_json)
    sys.stdout.write(render_report(findings, skill_name=args.skill_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
