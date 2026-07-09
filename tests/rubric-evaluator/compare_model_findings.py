#!/usr/bin/env python3
"""Compare model findings produced by an evaluator run against a fixture's expected-model.json.

Usage: python3 compare_model_findings.py <actual-findings.json> <fixture-dir>

expected-model.json maps finding IDs to expected statuses, e.g. {"3.4": "fail"}.
Only listed IDs are compared, so fixtures assert only their unambiguous checks.
Exit code 0 when everything matches, 1 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path


def compare(actual_findings, expected_map):
    """Return a list of mismatch descriptions; empty means calibrated."""
    by_id = {finding.get("id"): finding for finding in actual_findings}
    mismatches = []
    for finding_id, want in sorted(expected_map.items()):
        got = by_id.get(finding_id)
        if got is None:
            mismatches.append(f"{finding_id}: missing from actual findings (expected {want})")
        elif got.get("status") != want:
            mismatches.append(f"{finding_id}: expected {want}, got {got.get('status')}")
    return mismatches


def load_findings(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    if isinstance(data, list):
        return data
    raise ValueError("Expected a JSON array or an object with a findings array.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("actual", help="JSON findings from an evaluator run")
    parser.add_argument("fixture_dir", help="Fixture directory containing expected-model.json")
    args = parser.parse_args(argv)

    expected = json.loads(
        (Path(args.fixture_dir) / "expected-model.json").read_text(encoding="utf-8")
    )
    mismatches = compare(load_findings(args.actual), expected)
    if mismatches:
        for line in mismatches:
            print(line)
        return 1
    print("calibrated: all expected model findings match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
