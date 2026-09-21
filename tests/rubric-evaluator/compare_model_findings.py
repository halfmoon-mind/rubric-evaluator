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


def measure(runs, expected_map):
    """Measure only asserted IDs; missing results count as mismatches, not passes."""
    if not runs or not isinstance(expected_map, dict) or not expected_map:
        raise ValueError("at least one run and one expected status are required")
    if any(value not in {"pass", "fail", "na"} for value in expected_map.values()):
        raise ValueError("expected statuses must be pass, fail, or na")
    indexed = []
    for run in runs:
        if not isinstance(run, list):
            raise ValueError("each run must contain a findings array")
        by_id = {}
        for finding in run:
            if not isinstance(finding, dict) or not isinstance(finding.get("id"), str):
                raise ValueError("each finding needs an ID")
            if finding["id"] in by_id or finding.get("status") not in {"pass", "fail", "na"}:
                raise ValueError("duplicate ID or invalid status")
            by_id[finding["id"]] = finding["status"]
        indexed.append(by_id)
    matches = false_positives = false_negatives = missing = 0
    for run in indexed:
        for fid, expected in expected_map.items():
            actual = run.get(fid)
            matches += actual == expected
            false_positives += expected == "pass" and actual == "fail"
            false_negatives += expected == "fail" and actual == "pass"
            missing += actual is None
    # Pairwise agreement is separate from accuracy: repeated wrong answers can agree.
    pairs = agreements = 0
    for i, left in enumerate(indexed):
        for right in indexed[i + 1:]:
            for fid in expected_map:
                pairs += 1
                agreements += fid in left and fid in right and left[fid] == right[fid]
    total = len(runs) * len(expected_map)
    return {"runs": len(runs), "observations": total, "accuracy": matches / total,
            "agreement": agreements / pairs if pairs else None,
            "false_positives": false_positives, "false_negatives": false_negatives,
            "missing": missing, "mismatches": total - matches}


def load_findings(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    if isinstance(data, list):
        return data
    raise ValueError("Expected a JSON array or an object with a findings array.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("actual", help="JSON findings from an evaluator run")
    parser.add_argument("fixture_dir", help="Fixture directory containing expected-model.json")
    parser.add_argument("--repeat", action="append", default=[], metavar="FINDINGS_JSON", help="Add another run of the same fixture; emit accuracy and agreement metrics")
    args = parser.parse_args(argv)

    try:
        expected = json.loads(
            (Path(args.fixture_dir) / "expected-model.json").read_text(encoding="utf-8")
        )
        runs = [load_findings(path) for path in [args.actual, *args.repeat]]
        metrics = measure(runs, expected)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.repeat:
        print(json.dumps(metrics, indent=2))
        return int(metrics["mismatches"] > 0)
    mismatches = compare(runs[0], expected)
    if mismatches:
        for line in mismatches:
            print(line)
        return 1
    print("calibrated: all expected model findings match")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
