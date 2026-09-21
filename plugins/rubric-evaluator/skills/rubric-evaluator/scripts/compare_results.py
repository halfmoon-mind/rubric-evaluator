#!/usr/bin/env python3
"""Compare two validated evaluation results without treating missing checks as fixes."""

import argparse
import json
import sys

from check_rules import compute_grade
from results import coverage, id_key, load_result


def compare_results(before, after):
    old_coverage = coverage(before["findings"])
    new_coverage = coverage(after["findings"])
    old = {f["id"]: f for f in before["findings"]}
    new = {f["id"]: f for f in after["findings"]}
    changes = {key: [] for key in ("resolved", "introduced", "persistent", "unverified", "newly_observed")}
    for fid in sorted(old.keys() | new.keys(), key=id_key):
        previous = old.get(fid, {}).get("status")
        current = new.get(fid, {}).get("status")
        if previous == "fail":
            key = "resolved" if current == "pass" else "persistent" if current == "fail" else "unverified"
            changes[key].append(fid)
        elif current == "fail":
            changes["introduced" if previous == "pass" else "newly_observed"].append(fid)
    warnings = []
    for key in ("rubric_version", "rubric_hash"):
        if not before.get(key) or not after.get(key):
            warnings.append(f"{key} is missing; rubric comparability is unknown")
        elif before[key] != after[key]:
            warnings.append(f"{key} changed; grades use different evaluation criteria")
    if old_coverage["status"] != "complete" or new_coverage["status"] != "complete":
        warnings.append("partial evaluation: grade changes may reflect coverage changes")
    return {
        "before_grade": compute_grade(before["findings"]),
        "after_grade": compute_grade(after["findings"]),
        "before_coverage": old_coverage,
        "after_coverage": new_coverage,
        "before_target_hash": before.get("target_hash"),
        "after_target_hash": after.get("target_hash"),
        **changes,
        "warnings": warnings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable changes")
    args = parser.parse_args(argv)
    try:
        result = compare_results(load_result(args.before), load_result(args.after))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Grade: {result['before_grade']} -> {result['after_grade']}")
        for key in ("resolved", "introduced", "persistent", "unverified", "newly_observed"):
            print(f"{key}: {len(result[key])} ({', '.join(result[key]) or 'none'})")
        for warning in result["warnings"]:
            print(f"Note: {warning}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
