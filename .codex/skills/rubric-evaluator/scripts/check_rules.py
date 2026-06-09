#!/usr/bin/env python3
"""Deterministic rule checks for Codex skill directories."""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

SECTION = {
    1: "validity",
    2: "structure",
    3: "trigger",
    4: "content",
    5: "resources",
    6: "safety",
}

# Complete superset of top-level keys observed across all 409 installed skills.
# Lean permissive: 2.6 is MAJOR, so a false flag on a legit key is worse than
# missing a typo. `version` alone appears in 30 skills; `tools`/`aliases` in 2 each.
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "allowed-tools",
    "tools",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
    "license",
    "homepage",
    "author",
    "repository",
    "version",
    "metadata",
    "mcp_tool",
    "mcp_args",
    "aliases",
}

RESERVED_WORDS = ("claude", "anthropic")
RULE_CHECKS = []


def rule(fn):
    RULE_CHECKS.append(fn)
    return fn


def mk(id, item, severity, status, why="", how_to_fix=""):
    return {
        "id": id,
        "section": SECTION[int(id.split(".")[0])],
        "item": item,
        "severity": severity,
        "status": status,
        "checker": "rule",
        "why": why,
        "how_to_fix": how_to_fix,
    }


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _parse_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def _parse_inline_list(value):
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(part.strip()) for part in inner.split(",")]


def parse_frontmatter(text):
    """Return (frontmatter, body, ok, error). Supports flat YAML-style metadata."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text, False, "missing opening frontmatter delimiter"

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text, False, "missing opening frontmatter delimiter"

    close_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_index = index
            break
    if close_index is None:
        return {}, text, False, "missing closing frontmatter delimiter"

    raw_frontmatter = [line.rstrip("\r\n") for line in lines[1:close_index]]
    body = "".join(lines[close_index + 1 :])
    frontmatter = {}
    current_key = None

    for raw_line in raw_frontmatter:
        if not raw_line.strip():
            continue
        if "\t" in raw_line:
            return {}, body, False, "tab indentation is not supported"

        if raw_line.startswith(" "):
            stripped = raw_line.strip()
            if current_key and stripped.startswith("- "):
                if not isinstance(frontmatter.get(current_key), list):
                    frontmatter[current_key] = []
                frontmatter[current_key].append(_parse_scalar(stripped[2:].strip()))
                continue
            if current_key:
                continue
            return {}, body, False, "indented value without a parent key"

        if ":" not in raw_line:
            return {}, body, False, f"invalid frontmatter line: {raw_line}"

        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not re.match(r"^[A-Za-z0-9_.-]+$", key):
            return {}, body, False, f"invalid frontmatter key: {key}"

        current_key = key
        if value == "":
            frontmatter[key] = {}
        elif value.startswith("[") and value.endswith("]"):
            frontmatter[key] = _parse_inline_list(value)
        else:
            frontmatter[key] = _parse_scalar(value)

    return frontmatter, body, True, None


def top_level_keys(frontmatter):
    return list(frontmatter.keys())


def shipped_files(skill_dir):
    skill_dir = Path(skill_dir)
    files = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files.append(skill_md)
    for dirname in ("references", "scripts"):
        root = skill_dir / dirname
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file() and not _is_generated(path))
    return sorted(files)


def reference_files(skill_dir):
    root = Path(skill_dir) / "references"
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def script_files(skill_dir):
    root = Path(skill_dir) / "scripts"
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and not _is_generated(path))


def _is_generated(path):
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def _local_markdown_links(text):
    targets = re.findall(r"\]\(([^)]+)\)", text)
    for target in targets:
        target = target.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "#")):
            continue
        if target.endswith(".md"):
            yield target


def build_context(skill_dir):
    skill_dir = Path(skill_dir).resolve()
    skill_md = skill_dir / "SKILL.md"
    skill_text = read_text(skill_md) if skill_md.exists() else ""
    frontmatter, body, fm_ok, fm_error = parse_frontmatter(skill_text)
    return SimpleNamespace(
        skill_dir=skill_dir,
        skill_md=skill_md,
        skill_text=skill_text,
        frontmatter=frontmatter,
        body=body,
        fm_ok=fm_ok,
        fm_error=fm_error,
        shipped_files=shipped_files(skill_dir),
        references=reference_files(skill_dir),
        scripts=script_files(skill_dir),
    )


def _name_is_valid(name):
    return isinstance(name, str) and re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) and len(name) <= 64


def _description_is_present(description):
    return isinstance(description, str) and 1 <= len(description.strip()) <= 1024


def _na(id, item, severity, reason):
    return mk(id, item, severity, "na", reason, "Fix prerequisite checks first.")


@rule
def check_2_1(ctx):
    if ctx.fm_ok:
        return mk("2.1", "YAML frontmatter can be parsed", "BLOCKER", "pass")
    return mk(
        "2.1",
        "YAML frontmatter can be parsed",
        "BLOCKER",
        "fail",
        ctx.fm_error or "SKILL.md frontmatter could not be parsed.",
        "Use frontmatter enclosed by opening and closing --- lines with flat key/value entries.",
    )


@rule
def check_2_2(ctx):
    item = "name is kebab-case and at most 64 characters"
    if not ctx.fm_ok:
        return _na("2.2", item, "BLOCKER", "Frontmatter did not parse.")
    name = ctx.frontmatter.get("name")
    if _name_is_valid(name):
        return mk("2.2", item, "BLOCKER", "pass")
    return mk(
        "2.2",
        item,
        "BLOCKER",
        "fail",
        f"name {name!r} is missing, too long, or not kebab-case.",
        "Set name to lowercase letters, digits, and single hyphens only, with length at most 64.",
    )


@rule
def check_2_3(ctx):
    item = "name matches the skill folder name"
    if not ctx.fm_ok:
        return _na("2.3", item, "BLOCKER", "Frontmatter did not parse.")
    name = ctx.frontmatter.get("name")
    if not _name_is_valid(name):
        return _na("2.3", item, "BLOCKER", "name must be valid before folder matching can be judged.")
    folder_name = ctx.skill_dir.name
    if name == folder_name:
        return mk("2.3", item, "BLOCKER", "pass")
    return mk(
        "2.3",
        item,
        "BLOCKER",
        "fail",
        f"name {name!r} does not match folder {folder_name!r}.",
        "Rename the folder or update frontmatter name so they are identical.",
    )


@rule
def check_2_4(ctx):
    item = "description is 1 to 1024 characters"
    if not ctx.fm_ok:
        return _na("2.4", item, "BLOCKER", "Frontmatter did not parse.")
    description = ctx.frontmatter.get("description")
    if _description_is_present(description):
        return mk("2.4", item, "BLOCKER", "pass")
    return mk(
        "2.4",
        item,
        "BLOCKER",
        "fail",
        "description is missing, empty, not a string, or longer than 1024 characters.",
        "Add a concise description that states what the skill does and when to use it.",
    )


@rule
def check_2_5(ctx):
    item = "description contains no XML or HTML tags"
    if not ctx.fm_ok:
        return _na("2.5", item, "BLOCKER", "Frontmatter did not parse.")
    description = ctx.frontmatter.get("description")
    if not _description_is_present(description):
        return _na("2.5", item, "BLOCKER", "description must be present before tag scanning.")
    if re.search(r"<[A-Za-z][^>]*>", description):
        return mk(
            "2.5",
            item,
            "BLOCKER",
            "fail",
            "description appears to contain an XML or HTML tag.",
            "Remove markup from the description and keep trigger wording as plain text.",
        )
    return mk("2.5", item, "BLOCKER", "pass")


@rule
def check_2_6(ctx):
    item = "frontmatter uses only allowed keys"
    if not ctx.fm_ok:
        return _na("2.6", item, "MAJOR", "Frontmatter did not parse.")
    unexpected = sorted(set(top_level_keys(ctx.frontmatter)) - ALLOWED_FRONTMATTER_KEYS)
    if not unexpected:
        return mk("2.6", item, "MAJOR", "pass")
    return mk(
        "2.6",
        item,
        "MAJOR",
        "fail",
        f"Unexpected frontmatter key(s): {', '.join(unexpected)}.",
        "Remove unsupported keys or move UI-only metadata to agents/openai.yaml.",
    )


@rule
def check_2_7(ctx):
    item = "name and description avoid reserved vendor terms"
    if not ctx.fm_ok:
        return _na("2.7", item, "MAJOR", "Frontmatter did not parse.")
    name = ctx.frontmatter.get("name")
    description = ctx.frontmatter.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        return _na("2.7", item, "MAJOR", "name and description must be strings before reserved terms can be judged.")
    haystack = f"{name}\n{description}".lower()
    matched = [word for word in RESERVED_WORDS if word in haystack]
    if not matched:
        return mk("2.7", item, "MAJOR", "pass")
    return mk(
        "2.7",
        item,
        "MAJOR",
        "fail",
        f"Reserved term(s) found in name or description: {', '.join(matched)}.",
        "Use product-neutral wording in frontmatter unless a vendor-specific skill is intentional.",
    )


@rule
def check_2_8(ctx):
    item = "skill folder has no README.md"
    if (ctx.skill_dir / "README.md").exists():
        return mk(
            "2.8",
            item,
            "MINOR",
            "fail",
            "README.md adds a competing documentation surface for the skill.",
            "Move essential instructions into SKILL.md or a clearly linked reference file.",
        )
    return mk("2.8", item, "MINOR", "pass")


@rule
def check_3_6(ctx):
    item = "argument-hint exists when argument substitution is used"
    if "$ARGUMENTS" not in ctx.body:
        return mk("3.6", item, "MINOR", "pass")
    if not ctx.fm_ok:
        return _na("3.6", item, "MINOR", "Frontmatter did not parse.")
    if "argument-hint" in ctx.frontmatter:
        return mk("3.6", item, "MINOR", "pass")
    return mk(
        "3.6",
        item,
        "MINOR",
        "fail",
        "The body uses argument substitution but frontmatter has no argument-hint.",
        "Add argument-hint that tells the caller what argument shape is expected.",
    )


@rule
def check_4_3(ctx):
    item = "SKILL.md body is at most 500 lines"
    if not ctx.fm_ok:
        return _na("4.3", item, "MINOR", "Frontmatter did not parse.")
    line_count = len(ctx.body.splitlines())
    if line_count <= 500:
        return mk("4.3", item, "MINOR", "pass")
    return mk(
        "4.3",
        item,
        "MINOR",
        "fail",
        f"SKILL.md body has {line_count} lines.",
        "Move detailed criteria, examples, or long procedures into references that are loaded only when needed.",
    )


@rule
def check_5_3(ctx):
    item = "reference files do not link to other reference files"
    offenders = []
    for path in ctx.references:
        text = read_text(path)
        if any(_local_markdown_links(text)) or re.search(r"\breferences/[^)\s]+\.md\b", text):
            offenders.append(str(path.relative_to(ctx.skill_dir)))
    if not offenders:
        return mk("5.3", item, "MAJOR", "pass")
    return mk(
        "5.3",
        item,
        "MAJOR",
        "fail",
        f"Reference files contain nested markdown links: {', '.join(offenders)}.",
        "Link every loadable reference directly from SKILL.md and keep reference files one level deep.",
    )


@rule
def check_5_4(ctx):
    item = "long reference files include a table of contents"
    offenders = []
    for path in ctx.references:
        lines = read_text(path).splitlines()
        if len(lines) < 100:
            continue
        first_screen = "\n".join(lines[:40]).lower()
        toc_links = sum(1 for line in lines[:60] if re.match(r"\s*[-*]\s+\[[^\]]+\]\(#[^)]+\)", line))
        if "table of contents" not in first_screen and "목차" not in first_screen and toc_links < 3:
            offenders.append(str(path.relative_to(ctx.skill_dir)))
    if not offenders:
        return mk("5.4", item, "MINOR", "pass")
    return mk(
        "5.4",
        item,
        "MINOR",
        "fail",
        f"Long reference file(s) lack a visible table of contents: {', '.join(offenders)}.",
        "Add a table of contents near the top so agents can preview the file before reading details.",
    )


@rule
def check_5_6(ctx):
    item = "script syntax is valid"
    offenders = []
    for path in ctx.scripts:
        rel = str(path.relative_to(ctx.skill_dir))
        if path.suffix == ".py":
            try:
                ast.parse(read_text(path), filename=rel)
            except SyntaxError as exc:
                offenders.append(f"{rel}: line {exc.lineno}")
        elif path.suffix == ".sh":
            bash = shutil.which("bash")
            if bash:
                result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True)
                if result.returncode != 0:
                    detail = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "syntax error"
                    offenders.append(f"{rel}: {detail}")
    if not offenders:
        return mk("5.6", item, "MAJOR", "pass")
    return mk(
        "5.6",
        item,
        "MAJOR",
        "fail",
        f"Script syntax failed: {'; '.join(offenders)}.",
        "Fix script syntax before shipping the skill.",
    )


@rule
def check_5_7(ctx):
    item = "script paths are mentioned in SKILL.md"
    missing = []
    for path in ctx.scripts:
        rel = str(path.relative_to(ctx.skill_dir))
        if rel not in ctx.skill_text:
            missing.append(rel)
    if not missing:
        return mk("5.7", item, "MINOR", "pass")
    return mk(
        "5.7",
        item,
        "MINOR",
        "fail",
        f"Script file(s) are not mentioned in SKILL.md: {', '.join(missing)}.",
        "Mention each script path and the condition for using it in SKILL.md.",
    )


def _residue_patterns():
    return [
        ("TO" "DO", re.compile(r"\b" + "TO" + "DO" + r"\b", re.IGNORECASE)),
        ("FIX" "ME", re.compile(r"\b" + "FIX" + "ME" + r"\b", re.IGNORECASE)),
        ("T" "BD", re.compile(r"\b" + "T" + "BD" + r"\b", re.IGNORECASE)),
        ("place" "holder", re.compile(r"\b" + "place" + "holder" + r"\b", re.IGNORECASE)),
        ("lorem" " ipsum", re.compile("lorem" + r"\s+" + "ipsum", re.IGNORECASE)),
    ]


@rule
def check_5_8(ctx):
    item = "scaffold residue is absent"
    offenders = []
    for path in ctx.shipped_files:
        text = read_text(path)
        for label, pattern in _residue_patterns():
            if pattern.search(text):
                offenders.append(f"{path.relative_to(ctx.skill_dir)}: {label}")
                break
    if not offenders:
        return mk("5.8", item, "MINOR", "pass")
    return mk(
        "5.8",
        item,
        "MINOR",
        "fail",
        f"Shipped file(s) contain scaffold residue: {'; '.join(offenders)}.",
        "Replace unfinished scaffold text with final instructions or remove it.",
    )


def _secret_patterns():
    return [
        ("private key block", re.compile(r"-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----")),
        ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        (
            "credential assignment",
            re.compile(
                r"\b(?:api[_-]?key|secret|token|pass(?:word)?|passwd)\b"
                r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}",
                re.IGNORECASE,
            ),
        ),
    ]


@rule
def check_6_1(ctx):
    item = "plain credentials are absent"
    offenders = []
    for path in ctx.shipped_files:
        text = read_text(path)
        for label, pattern in _secret_patterns():
            if pattern.search(text):
                offenders.append(f"{path.relative_to(ctx.skill_dir)}: suspected {label}")
                break
    if not offenders:
        return mk("6.1", item, "BLOCKER", "pass")
    return mk(
        "6.1",
        item,
        "BLOCKER",
        "fail",
        f"Potential credential material found: {'; '.join(offenders)}.",
        "Remove credentials from shipped skill files and provide setup instructions instead.",
    )


def _allowed_tools_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def _destructive_patterns():
    return [
        re.compile(r"\brm\s+-[A-Za-z]*r[A-Za-z]*f\b"),
        re.compile(r"\brm\s+-[A-Za-z]*f[A-Za-z]*r\b"),
        re.compile(r"\bdd\s+if="),
        re.compile(r"\bmkfs(?:\.[A-Za-z0-9]+)?\b"),
        re.compile(r"\bchmod\s+-R\s+777\b"),
        re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"),
        re.compile(r">\s*/dev/sd[a-z]\b"),
    ]


@rule
def check_6_2(ctx):
    item = "allowed-tools avoids destructive command patterns"
    if not ctx.fm_ok:
        return _na("6.2", item, "BLOCKER", "Frontmatter did not parse.")
    text = _allowed_tools_text(ctx.frontmatter.get("allowed-tools"))
    if not text:
        return mk("6.2", item, "BLOCKER", "pass")
    for pattern in _destructive_patterns():
        if pattern.search(text):
            return mk(
                "6.2",
                item,
                "BLOCKER",
                "fail",
                "allowed-tools contains a destructive command pattern.",
                "Remove dangerous shell patterns from allowed-tools and require explicit user approval for risky operations.",
            )
    return mk("6.2", item, "BLOCKER", "pass")


def evaluate_skill(skill_dir):
    ctx = build_context(skill_dir)
    findings = [check(ctx) for check in RULE_CHECKS]
    findings.sort(key=lambda item: tuple(int(part) for part in item["id"].split(".")))
    return {"findings": findings, "grade": compute_grade(findings)}


def compute_grade(findings):
    failed = [finding for finding in findings if finding.get("status") == "fail"]
    if any(finding.get("severity") == "BLOCKER" for finding in failed):
        return "F"
    major_count = sum(1 for finding in failed if finding.get("severity") == "MAJOR")
    if major_count == 0:
        return "S"
    if major_count <= 2:
        return "A"
    if major_count <= 4:
        return "B"
    return "C"


def _load_findings(path):
    data = json.loads(read_text(path))
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    if isinstance(data, list):
        return data
    raise ValueError("findings file must contain a JSON array or an object with a findings array")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run deterministic Codex skill rule checks.")
    parser.add_argument("target", nargs="?", help="Skill directory or findings JSON file in --grade mode")
    parser.add_argument("--grade", action="store_true", help="Print only the grade for an existing findings file")
    args = parser.parse_args(argv)

    if args.grade:
        if not args.target:
            parser.error("--grade requires a findings JSON file")
        print(compute_grade(_load_findings(args.target)))
        return 0

    if not args.target:
        parser.error("target skill directory is required")

    result = evaluate_skill(args.target)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
