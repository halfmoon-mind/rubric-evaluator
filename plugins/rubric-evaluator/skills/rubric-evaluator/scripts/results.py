"""Shared findings validation, coverage, provenance, and quality gates."""

import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1
RUBRIC_VERSION = "1.0.0"
SECTIONS = {1: "validity", 2: "structure", 3: "trigger", 4: "content", 5: "resources", 6: "safety"}
MODEL_IDS = set("1.1 1.2 1.3 3.1 3.2 3.3 3.4 3.5 3.7 4.1 4.2 5.1 5.2 5.5".split())
SEVERITIES = {
    **dict.fromkeys("2.1 2.2 2.3 2.4 2.5 3.4 6.1 6.2".split(), "BLOCKER"),
    **dict.fromkeys("1.1 1.2 1.3 2.6 2.7 3.1 3.2 3.3 3.5 3.7 4.2 5.1 5.3 5.5 5.6".split(), "MAJOR"),
    **dict.fromkeys("2.8 3.6 4.1 4.3 5.2 5.4 5.7 5.8".split(), "MINOR"),
}


def id_key(value):
    return tuple(int(part) for part in value.split("."))


def validate_findings(findings):
    if not isinstance(findings, list) or not findings:
        raise ValueError("findings must be a non-empty array")
    seen = set()
    fields = ("id", "section", "item", "severity", "status", "checker", "why", "how_to_fix")
    for finding in findings:
        if not isinstance(finding, dict) or any(not isinstance(finding.get(k), str) for k in fields):
            raise ValueError("every finding must have string fields: " + ", ".join(fields))
        fid = finding["id"]
        if fid not in SEVERITIES or fid in seen:
            raise ValueError(f"unknown or duplicate finding ID: {fid}")
        seen.add(fid)
        if finding["severity"] != SEVERITIES[fid]:
            raise ValueError(f"{fid}: severity must be {SEVERITIES[fid]}")
        if finding["section"] != SECTIONS[int(fid.split(".")[0])]:
            raise ValueError(f"{fid}: incorrect section")
        checkers = {"model"} if fid in MODEL_IDS else {"rule"}
        if fid == "6.1":
            checkers.add("model")
        if finding["checker"] not in checkers or finding["status"] not in {"pass", "fail", "na"}:
            raise ValueError(f"{fid}: invalid checker or status")
        if not finding["item"].strip():
            raise ValueError(f"{fid}: item must not be empty")
        if finding["status"] == "fail" and any(not finding[k].strip() for k in ("why", "how_to_fix")):
            raise ValueError(f"{fid}: failed findings need why and how_to_fix")
        if finding["status"] == "na" and not finding["why"].strip():
            raise ValueError(f"{fid}: na needs a reason")
    return findings


def load_result(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        data = {"findings": data}
    if not isinstance(data, dict):
        raise ValueError("expected an object with findings or a findings array")
    if "schema_version" in data and data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    validate_findings(data.get("findings"))
    return data


def coverage(findings):
    validate_findings(findings)
    present = {f["id"] for f in findings}
    missing = sorted(SEVERITIES.keys() - present, key=id_key)
    unresolved = sorted((f["id"] for f in findings if f["status"] == "na"), key=id_key)
    return {
        "status": "partial" if missing or unresolved else "complete",
        "judged": len(present) - len(unresolved),
        "total": len(SEVERITIES),
        "missing_ids": missing,
        "unresolved_ids": unresolved,
    }


def tree_hash(root):
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root)
        if any(p in {".git", "__pycache__", ".pytest_cache"} for p in rel.parts):
            continue
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(rel.as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def provenance(target):
    return {
        "schema_version": SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "rubric_hash": tree_hash(Path(__file__).resolve().parent.parent),
        "target": str(Path(target).resolve()),
        "target_hash": tree_hash(target),
    }


def gate_failed(findings, fail_on=None, require_complete=False):
    status = coverage(findings)
    levels = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2}
    if require_complete and status["status"] != "complete":
        return True
    return bool(fail_on and any(
        f["status"] == "fail" and levels[f["severity"]] <= levels[fail_on.upper()]
        for f in findings
    ))
