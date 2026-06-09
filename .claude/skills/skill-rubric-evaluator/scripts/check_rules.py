#!/usr/bin/env python3
"""Deterministic rule-checks for the skill-rubric-evaluator.

Stdlib only (no PyYAML, no pytest). Emits JSON findings and computes the grade.
Usage:
    python3 check_rules.py <skill_dir>      # run 17 rule checks, print {findings, grade}
    python3 check_rules.py --grade <file>   # read a findings JSON array, print the grade
"""
import argparse
import json
import os
import re
import sys
from types import SimpleNamespace

SECTION = {1: "validity", 2: "structure", 3: "trigger",
           4: "content", 5: "resource", 6: "safety"}

RULE_CHECKS = []


def rule(fn):
    """Register a check. Each check takes ctx and returns one finding dict."""
    RULE_CHECKS.append(fn)
    return fn


def mk(id, item, severity, status, why="", how_to_fix=""):
    return {
        "id": id,
        "section": SECTION[int(id.split(".")[0])],
        "item": item,
        "severity": severity,   # BLOCKER | MAJOR | MINOR
        "status": status,       # pass | fail | na
        "checker": "rule",
        "why": why,
        "how_to_fix": how_to_fix,
    }


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _unquote(val):
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def parse_frontmatter(text):
    """Return (frontmatter dict, body str, ok bool, error str|None).

    Hand-rolled because the stdlib has no YAML parser and the project forbids
    third-party deps. Validates STRUCTURAL shape only: a block delimited by
    '---'/'---' whose lines are each classifiable as a top-level 'key: value',
    a comment, a block-scalar marker, or an indented child. Top-level keys
    (column 0) populate the dict; indented children (e.g. under 'metadata:')
    are accepted but not surfaced as top-level keys.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ({}, text, False, "missing opening '---'")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return ({}, text, False, "missing closing '---'")

    fm = {}
    error = None
    current_key = None
    in_block = False
    for raw in lines[1:end]:
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[: indent + 1]:
            error = "tab indentation is not allowed"
            break
        if in_block:
            if indent > 0:                       # block-scalar continuation line
                fm[current_key] = (fm[current_key] + " " + raw.strip()).strip()
                continue
            in_block = False                     # dedent ends the block scalar
        if indent == 0:
            if ":" not in raw:
                error = "unparseable line: %r" % raw
                break
            key, _, val = raw.partition(":")
            key = key.strip()
            val = val.strip()
            if not key:
                error = "empty key in line: %r" % raw
                break
            current_key = key
            if val in (">", "|", ">-", "|-", ">+", "|+"):
                in_block = True
                fm[key] = ""
            else:
                fm[key] = _unquote(val)
        # indent > 0 and not in a block scalar: an indented child of a mapping
        # (e.g. metadata children). Accepted, not recorded as a top-level key.
    return (fm, "\n".join(lines[end + 1:]), error is None, error)


def top_level_keys(fm):
    return list(fm.keys())


def shipped_files(skill_dir):
    """Files a skill SHIPS: SKILL.md + references/** + scripts/**. Never tests/**.

    This scope is what content scans (6.1 secrets, 5.8 placeholders) inspect, so
    the evaluator can dogfood itself without its own fixtures counting against it.
    """
    out = []
    top = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(top):
        out.append(top)
    for sub in ("references", "scripts"):
        base = os.path.join(skill_dir, sub)
        for root, _, files in os.walk(base):
            for name in files:
                out.append(os.path.join(root, name))
    return out


def build_ctx(skill_dir):
    skill_md = os.path.join(skill_dir, "SKILL.md")
    text = read_text(skill_md) if os.path.isfile(skill_md) else ""
    fm, body, ok, err = parse_frontmatter(text)
    return SimpleNamespace(
        skill_dir=skill_dir,
        skill_md_exists=os.path.isfile(skill_md),
        text=text, body=body,
        fm=fm, fm_ok=ok, fm_err=err,
        name=fm.get("name", ""), description=fm.get("description", ""),
    )


def run_checks(skill_dir):
    ctx = build_ctx(os.path.abspath(skill_dir.rstrip("/")))
    findings = [chk(ctx) for chk in RULE_CHECKS]
    findings.sort(key=lambda f: tuple(int(p) for p in f["id"].split(".")))
    return findings


def compute_grade(findings):
    blockers = sum(1 for f in findings
                   if f["status"] == "fail" and f["severity"] == "BLOCKER")
    majors = sum(1 for f in findings
                 if f["status"] == "fail" and f["severity"] == "MAJOR")
    if blockers >= 1:
        return "F"
    if majors == 0:
        return "S"
    if majors <= 2:
        return "A"
    if majors <= 4:
        return "B"
    return "C"


@rule
def check_2_1(ctx):
    item = "YAML frontmatter parses"
    if ctx.fm_ok:
        return mk("2.1", item, "BLOCKER", "pass")
    return mk("2.1", item, "BLOCKER", "fail",
              why="frontmatter is not parseable: %s" % ctx.fm_err,
              how_to_fix="ensure SKILL.md opens with '---', closes with '---', "
                         "and contains only 'key: value' lines (no tabs)")


_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@rule
def check_2_2(ctx):
    item = "name is kebab-case (<=64 chars)"
    if not ctx.fm_ok:
        return mk("2.2", item, "BLOCKER", "na", why="frontmatter unparseable")
    name = ctx.name
    if name and _KEBAB.match(name) and len(name) <= 64:
        return mk("2.2", item, "BLOCKER", "pass")
    return mk("2.2", item, "BLOCKER", "fail",
              why="name %r is not kebab-case or exceeds 64 chars" % name,
              how_to_fix="use lowercase letters, digits, and single hyphens, "
                         "e.g. 'my-skill'")


@rule
def check_2_3(ctx):
    item = "name matches folder name"
    if not ctx.fm_ok:
        return mk("2.3", item, "BLOCKER", "na", why="frontmatter unparseable")
    folder = os.path.basename(ctx.skill_dir)
    if ctx.name == folder:
        return mk("2.3", item, "BLOCKER", "pass")
    return mk("2.3", item, "BLOCKER", "fail",
              why="name %r != folder %r" % (ctx.name, folder),
              how_to_fix="rename the folder or the name so they match")


@rule
def check_2_4(ctx):
    item = "description is 1-1024 chars"
    if not ctx.fm_ok:
        return mk("2.4", item, "BLOCKER", "na", why="frontmatter unparseable")
    n = len(ctx.description)
    if 1 <= n <= 1024:
        return mk("2.4", item, "BLOCKER", "pass")
    return mk("2.4", item, "BLOCKER", "fail",
              why="description length %d is outside 1-1024" % n,
              how_to_fix="write a 1-1024 char description")


_HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")


@rule
def check_2_5(ctx):
    item = "description has no XML/HTML tags"
    if not ctx.fm_ok:
        return mk("2.5", item, "BLOCKER", "na", why="frontmatter unparseable")
    if _HTML_TAG.search(ctx.description):
        return mk("2.5", item, "BLOCKER", "fail",
                  why="description contains an angle-bracket tag",
                  how_to_fix="remove HTML/XML tags from the description")
    return mk("2.5", item, "BLOCKER", "pass")


ALLOWED_FRONTMATTER_KEYS = {
    # required
    "name", "description",
    # complete superset observed across all 409 installed skills (lean permissive:
    # a false flag on a legit key is worse than missing a typo, and 2.6 is MAJOR)
    "allowed-tools", "tools", "argument-hint", "user-invocable",
    "disable-model-invocation", "license", "homepage", "author", "repository",
    "version", "metadata", "mcp_tool", "mcp_args", "aliases",
}


@rule
def check_2_6(ctx):
    item = "only allowed frontmatter keys"
    if not ctx.fm_ok:
        return mk("2.6", item, "MAJOR", "na", why="frontmatter unparseable")
    unknown = [k for k in top_level_keys(ctx.fm) if k not in ALLOWED_FRONTMATTER_KEYS]
    if not unknown:
        return mk("2.6", item, "MAJOR", "pass")
    return mk("2.6", item, "MAJOR", "fail",
              why="unrecognized frontmatter key(s): %s" % ", ".join(unknown),
              how_to_fix="remove non-standard keys or move them under 'metadata:'")


_RESERVED = re.compile(r"(?i)\b(claude|anthropic)\b")


@rule
def check_2_7(ctx):
    item = "name/description free of claude/anthropic reserved words"
    if not ctx.fm_ok:
        return mk("2.7", item, "MAJOR", "na", why="frontmatter unparseable")
    if _RESERVED.search(ctx.name) or _RESERVED.search(ctx.description):
        return mk("2.7", item, "MAJOR", "fail",
                  why="name/description mentions a reserved word (claude/anthropic)",
                  how_to_fix="describe the task without naming the model or vendor")
    return mk("2.7", item, "MAJOR", "pass")


@rule
def check_2_8(ctx):
    item = "no redundant README.md"
    if os.path.isfile(os.path.join(ctx.skill_dir, "README.md")):
        return mk("2.8", item, "MINOR", "fail",
                  why="README.md present alongside SKILL.md",
                  how_to_fix="fold README content into SKILL.md and delete README.md")
    return mk("2.8", item, "MINOR", "pass")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Skill rubric rule-checks.")
    ap.add_argument("skill_dir", nargs="?", help="path to the skill directory")
    ap.add_argument("--grade", metavar="FILE",
                    help="read a findings JSON array from FILE and print the grade")
    args = ap.parse_args(argv)

    if args.grade:
        findings = json.loads(read_text(args.grade))
        print(compute_grade(findings))
        return 0
    if not args.skill_dir:
        ap.error("skill_dir is required unless --grade is given")
    findings = run_checks(args.skill_dir)
    print(json.dumps({"findings": findings, "grade": compute_grade(findings)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
