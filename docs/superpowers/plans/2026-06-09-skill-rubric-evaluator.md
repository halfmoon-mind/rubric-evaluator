# rubric-evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that grades any skill against a 6-section / 30-item rubric (S/A/B/C/F) using deterministic Python rule-checks plus model-based semantic checks, and emits an improvement report.

**Architecture:** Hybrid skill. `scripts/check_rules.py` (Python stdlib only, zero deps) runs the 17 deterministic rule-checks and emits JSON findings + computes the grade. `references/model-rubric.md` holds the criteria for the 13 semantic checks that Claude applies by reading the target. `SKILL.md` orchestrates: run script → apply model checks → combine 30 findings → compute deterministic grade → render report. The evaluator is built to pass its own rubric at grade **S** (dogfooding).

**Tech Stack:** Python 3.14 (standard library only — no PyYAML, no pytest), `unittest` for tests, Markdown for skill content.

---

## Conventions (read once before Task 1)

These rules are referenced by many tasks. They are decisions, not suggestions.

**1. Shipped-surface scope (dogfooding-critical).**
Content scans (secrets `6.1`, placeholder residue `5.8`) inspect only the files a skill *ships*: `SKILL.md`, everything under `references/`, and everything under `scripts/`. They **never** scan `tests/`. This single rule lets the evaluator dogfood itself: its own `tests/fixtures/secret-leak/`, `destructive-tool/`, and `placeholder-residue/` fixtures hold deliberate violations that must NOT count against the evaluator. Implemented as `shipped_files()` in Task 1.

**2. Fixture isolation principle.**
Each fixture under `tests/fixtures/` breaks **exactly one** rule check. Craft the frontmatter so no collateral check fails. In particular: the fixture folder name must equal its frontmatter `name:` (so `2.3` passes) UNLESS the fixture is specifically testing `2.3`. Keep descriptions free of `<...>` (so `2.5` passes) and ≤1024 chars (so `2.4` passes) unless that is the target.

**3. Self-reference avoidance (dogfooding-critical).**
The evaluator's own shipped files describe the very tokens its checks hunt for. To avoid the `5.8` placeholder scan flagging the evaluator's own source, the placeholder token list in `check_rules.py` is assembled from adjacent string fragments (e.g. `"TO" "DO"` is the string `"TODO"` at parse time but the source bytes never contain `TODO`). Secret regexes use character classes that do not match their own pattern source (verified in Task 9 dogfood). Never paste a realistic secret value into a shipped file; keep those only in `tests/fixtures/`.

**4. `expected.json` schema (every fixture has one).**
```json
{ "expected_fail": ["2.2"], "expected_grade": "F" }
```
- `expected_fail`: the exact set of rule IDs whose `status == "fail"` (includes MINOR fails).
- `expected_grade`: the **rule-only** grade (model checks do not run in unit tests). So `clean/` → `S`, a single-MAJOR fixture → `A`, any BLOCKER fixture → `F`.
The harness asserts the actual fail-set equals `expected_fail` (catching false positives AND false negatives) and the grade equals `expected_grade`.

**5. Running tests.**
```bash
python3 -m unittest discover -s tests -v
```

---

## File Structure

**Implementation location (agent-separated):** the Claude Code build lives under
`.claude/skills/rubric-evaluator/`. A parallel Codex implementation lives separately
under `.codex/skills/rubric-evaluator/` and is out of scope for this plan — do not
edit it. **All file paths in the tasks below are relative to the skill root**
`.claude/skills/rubric-evaluator/` (e.g. `scripts/check_rules.py` means
`.claude/skills/rubric-evaluator/scripts/check_rules.py`). Create the directory at
implementation time; this plan only specifies the layout.

```
.claude/skills/rubric-evaluator/   # skill root — all task paths are relative to here
├── SKILL.md                            # orchestration (Task 8)
├── scripts/
│   └── check_rules.py                  # 17 rule checks + compute_grade + CLI (Tasks 1–6)
├── references/
│   └── model-rubric.md                 # 13 model-check criteria + good/bad examples (Task 7)
└── tests/
    ├── test_check_rules.py             # unit tests: parser, compute_grade, --grade mode (Task 1)
    ├── test_fixtures.py                # generic fixture harness, auto-discovers fixtures (Task 1)
    └── fixtures/
        ├── clean/                      # Task 1  → grade S, no fails
        ├── bad_kebab/                  # Task 2  → 2.2
        ├── name-folder-mismatch/       # Task 2  → 2.3
        ├── desc-too-long/              # Task 2  → 2.4
        ├── desc-html/                  # Task 2  → 2.5
        ├── bad-frontmatter/            # Task 2  → 2.1
        ├── extra-key/                  # Task 3  → 2.6
        ├── reserved-word/              # Task 3  → 2.7
        ├── has-readme/                 # Task 3  → 2.8
        ├── missing-arg-hint/           # Task 4  → 3.6
        ├── body-too-long/              # Task 4  → 4.3
        ├── nested-references/          # Task 5  → 5.3
        ├── no-toc-reference/           # Task 5  → 5.4
        ├── bad-script-syntax/          # Task 5  → 5.6
        ├── script-not-mentioned/       # Task 5  → 5.7
        ├── placeholder-residue/        # Task 5  → 5.8
        ├── secret-leak/                # Task 6  → 6.1
        └── destructive-tool/           # Task 6  → 6.2
```

`check_rules.py` grows by *appending* check functions across Tasks 2–6. Each check is registered with an `@rule` decorator, so tasks add functions without editing a central list. Findings are sorted by ID before output, so registration order is irrelevant.

---

## Task 1: Engine skeleton — finding model, frontmatter parser, grading, CLI, test harness

**Files:**
- Create: `scripts/check_rules.py`
- Create: `tests/test_check_rules.py`
- Create: `tests/test_fixtures.py`
- Create: `tests/fixtures/clean/SKILL.md`
- Create: `tests/fixtures/clean/expected.json`

This task builds everything except the individual checks: the `RULE_CHECKS` registry is empty, so `clean/` (and only `clean/`) passes with zero findings → grade `S`. Later tasks fill the registry.

- [ ] **Step 1: Write the frontmatter-parser unit tests (failing)**

Create `tests/test_check_rules.py`:

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check_rules as cr  # noqa: E402


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
        self.assertNotIn("category", fm)  # indented child is not a top-level key

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

    def test_top_level_keys_listed(self):
        fm, _, ok, _ = cr.parse_frontmatter(
            "---\nname: x\ndescription: y\nallowed-tools: Read\n---\nb"
        )
        self.assertEqual(set(cr.top_level_keys(fm)), {"name", "description", "allowed-tools"})


class ComputeGradeTests(unittest.TestCase):
    def _f(self, severity, status):
        return {"severity": severity, "status": status}

    def test_blocker_is_F(self):
        self.assertEqual(cr.compute_grade([self._f("BLOCKER", "fail")]), "F")

    def test_no_fail_is_S(self):
        self.assertEqual(
            cr.compute_grade([self._f("MAJOR", "pass"), self._f("BLOCKER", "na")]), "S"
        )

    def test_one_major_is_A(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")]), "A")

    def test_three_majors_is_B(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 3), "B")

    def test_five_majors_is_C(self):
        self.assertEqual(cr.compute_grade([self._f("MAJOR", "fail")] * 5), "C")

    def test_minor_does_not_affect_grade(self):
        self.assertEqual(cr.compute_grade([self._f("MINOR", "fail")] * 9), "S")


class GradeModeCliTests(unittest.TestCase):
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
                [sys.executable, os.path.join(ROOT, "scripts", "check_rules.py"),
                 "--grade", path],
                capture_output=True, text=True,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.strip(), "A")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `python3 -m unittest tests.test_check_rules -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_rules'` (file not created yet).

- [ ] **Step 3: Create `scripts/check_rules.py` skeleton**

```python
#!/usr/bin/env python3
"""Deterministic rule-checks for the rubric-evaluator.

Stdlib only (no PyYAML, no pytest). Emits JSON findings and computes the grade.
Usage:
    python3 check_rules.py <skill_dir>      # run 17 rule checks, print {findings, grade}
    python3 check_rules.py --grade <file>   # read a findings JSON array, print the grade
"""
import argparse
import json
import os
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
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `python3 -m unittest tests.test_check_rules -v`
Expected: PASS (all `ParseFrontmatterTests`, `ComputeGradeTests`, `GradeModeCliTests`).

- [ ] **Step 5: Create the generic fixture harness `tests/test_fixtures.py`**

```python
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
CHECK = os.path.join(ROOT, "scripts", "check_rules.py")


def run_check(skill_dir):
    out = subprocess.run([sys.executable, CHECK, skill_dir],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("check_rules failed: " + out.stderr)
    return json.loads(out.stdout)


class FixtureTests(unittest.TestCase):
    pass


def _make_test(name):
    def test(self):
        fixture_dir = os.path.join(FIXTURES, name)
        with open(os.path.join(fixture_dir, "expected.json")) as fh:
            expected = json.load(fh)
        result = run_check(fixture_dir)
        actual_fail = sorted(f["id"] for f in result["findings"]
                             if f["status"] == "fail")
        self.assertEqual(actual_fail, sorted(expected["expected_fail"]),
                         "%s: fail-set mismatch" % name)
        self.assertEqual(result["grade"], expected["expected_grade"],
                         "%s: grade mismatch" % name)
    return test


for _name in sorted(os.listdir(FIXTURES)) if os.path.isdir(FIXTURES) else []:
    if os.path.isdir(os.path.join(FIXTURES, _name)):
        setattr(FixtureTests, "test_" + _name.replace("-", "_"), _make_test(_name))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Create the `clean/` fixture**

Create `tests/fixtures/clean/SKILL.md`:

```markdown
---
name: clean
description: Use when you need a minimal valid skill example to confirm the evaluator reports no findings on a well-formed skill.
---

# Clean

## Overview
A minimal, well-formed skill used to verify the evaluator produces zero rule findings.

## Steps
1. Do the first concrete thing.
2. Do the second concrete thing.
```

Create `tests/fixtures/clean/expected.json`:

```json
{ "expected_fail": [], "expected_grade": "S" }
```

- [ ] **Step 7: Run the fixture harness to verify it passes**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: PASS — `test_clean` passes (registry is empty, so zero findings, grade `S`).

- [ ] **Step 8: Commit**

```bash
git add scripts/check_rules.py tests/test_check_rules.py tests/test_fixtures.py tests/fixtures/clean
git commit -m "feat: engine skeleton — finding model, frontmatter parser, grading, fixture harness"
```

---

## Task 2: Structure BLOCKER checks (2.1–2.5)

**Files:**
- Modify: `scripts/check_rules.py` (append 5 check functions)
- Create: `tests/fixtures/bad_kebab/`, `name-folder-mismatch/`, `desc-too-long/`, `desc-html/`, `bad-frontmatter/`

All five are BLOCKERs, so each fixture grades `F`. The dependent checks (2.2–2.5 read `name`/`description`) must return `na` when frontmatter is unparseable, so `bad-frontmatter/` fails ONLY `2.1`.

- [ ] **Step 1: Create the five fixtures (failing tests)**

`tests/fixtures/bad_kebab/SKILL.md` (folder name uses an underscore so `name == folder` but `name` is not kebab — isolates 2.2):

```markdown
---
name: bad_kebab
description: A skill whose name uses an underscore so it is not kebab-case.
---

# Bad Kebab
## Overview
Used to trigger rule 2.2 only.
```
`tests/fixtures/bad_kebab/expected.json`:
```json
{ "expected_fail": ["2.2"], "expected_grade": "F" }
```

`tests/fixtures/name-folder-mismatch/SKILL.md` (valid kebab name that differs from the folder — isolates 2.3):
```markdown
---
name: a-different-name
description: A skill whose name does not match its folder name.
---

# Mismatch
## Overview
Used to trigger rule 2.3 only.
```
`tests/fixtures/name-folder-mismatch/expected.json`:
```json
{ "expected_fail": ["2.3"], "expected_grade": "F" }
```

`tests/fixtures/desc-too-long/SKILL.md` — description must exceed 1024 characters. Generate it so the file is exact:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/desc-too-long"
os.makedirs(d, exist_ok=True)
desc = "Use when " + ("x" * 1100)  # > 1024 chars, no angle brackets
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("---\nname: desc-too-long\ndescription: %s\n---\n\n# Too Long\n## Overview\nTriggers 2.4 only.\n" % desc)
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["2.4"], "expected_grade": "F" }\n')
PY
```

`tests/fixtures/desc-html/SKILL.md` (angle-bracket tag in description — isolates 2.5):
```markdown
---
name: desc-html
description: Use when you need a <b>bold</b> tag in the description to trip the HTML check.
---

# Desc HTML
## Overview
Triggers 2.5 only.
```
`tests/fixtures/desc-html/expected.json`:
```json
{ "expected_fail": ["2.5"], "expected_grade": "F" }
```

`tests/fixtures/bad-frontmatter/SKILL.md` (tab-indented line makes frontmatter unparseable — isolates 2.1; dependents go `na`):
```
---
name: bad-frontmatter
description: valid line
	bad: tab-indented-line
---

# Bad Frontmatter
## Overview
Triggers 2.1 only.
```
> NOTE: the 4th line must begin with a literal TAB character, not spaces.

`tests/fixtures/bad-frontmatter/expected.json`:
```json
{ "expected_fail": ["2.1"], "expected_grade": "F" }
```

- [ ] **Step 2: Run the harness to verify the new fixtures fail**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: FAIL — the five new `test_*` cases fail because no checks are registered yet, so `actual_fail` is `[]` while `expected_fail` is non-empty.

- [ ] **Step 3: Append the 2.1–2.5 checks to `check_rules.py`**

Add near the top of `check_rules.py`, after the imports:
```python
import re
```
Append after `mk(...)` / before `main()` (anywhere among the other checks):
```python
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
```

- [ ] **Step 4: Run the harness + unit tests to verify pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — `clean`, `bad_kebab`, `name_folder_mismatch`, `desc_too_long`, `desc_html`, `bad_frontmatter` all pass; parser/grade unit tests still pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_rules.py tests/fixtures
git commit -m "feat: structure BLOCKER checks 2.1-2.5 with fixtures"
```

---

## Task 3: Structure checks 2.6–2.8 (allowed keys, reserved words, README)

**Files:**
- Modify: `scripts/check_rules.py` (append 3 checks + the key whitelist)
- Create: `tests/fixtures/extra-key/`, `reserved-word/`, `has-readme/`

The frontmatter-key whitelist is the **complete** set of top-level keys observed across all 409 installed skills on disk (16 keys) — a superset of the design's draft list, adding `metadata`, `version`, `disable-model-invocation`, `tools`, and `aliases`. 2.6 is MAJOR — bias permissive: a false flag on a legit key is worse than missing a typo, so the whitelist matches the empirical superset to guarantee zero false positives on currently-installed skills (verified by Task 9 Step 3). Keys observed only via the partial sample would have been missed, so the list below is derived from a full scan.

- [ ] **Step 1: Create the three fixtures (failing)**

`tests/fixtures/extra-key/SKILL.md`:
```markdown
---
name: extra-key
description: A skill that declares an unrecognized frontmatter key.
foobar: not-a-real-key
---

# Extra Key
## Overview
Triggers 2.6 only.
```
`tests/fixtures/extra-key/expected.json`:
```json
{ "expected_fail": ["2.6"], "expected_grade": "A" }
```

`tests/fixtures/reserved-word/SKILL.md` (reserved word in the *description*, so 2.2 stays clean):
```markdown
---
name: reserved-word
description: Use when you want to help Claude do something, which trips the reserved-word check.
---

# Reserved Word
## Overview
Triggers 2.7 only.
```
`tests/fixtures/reserved-word/expected.json`:
```json
{ "expected_fail": ["2.7"], "expected_grade": "A" }
```

`tests/fixtures/has-readme/SKILL.md`:
```markdown
---
name: has-readme
description: A skill that ships a redundant README.md alongside SKILL.md.
---

# Has Readme
## Overview
Triggers 2.8 only.
```
`tests/fixtures/has-readme/README.md`:
```markdown
# Redundant readme
This should not exist; SKILL.md is sufficient.
```
`tests/fixtures/has-readme/expected.json`:
```json
{ "expected_fail": ["2.8"], "expected_grade": "S" }
```

- [ ] **Step 2: Run the harness to verify the new fixtures fail**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: FAIL — `test_extra_key`, `test_reserved_word`, `test_has_readme` fail (no fails detected yet).

- [ ] **Step 3: Append the 2.6–2.8 checks**

```python
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
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all fixtures including the three new ones; `extra-key` grades `A` (1 MAJOR), `reserved-word` grades `A`, `has-readme` grades `S` (MINOR only).

- [ ] **Step 5: Commit**

```bash
git add scripts/check_rules.py tests/fixtures
git commit -m "feat: structure checks 2.6-2.8 (key whitelist, reserved words, README)"
```

---

## Task 4: Trigger & content rule checks (3.6, 4.3)

**Files:**
- Modify: `scripts/check_rules.py` (append 2 checks)
- Create: `tests/fixtures/missing-arg-hint/`, `body-too-long/`

- [ ] **Step 1: Create the two fixtures (failing)**

`tests/fixtures/missing-arg-hint/SKILL.md` (body uses `$ARGUMENTS` but frontmatter omits `argument-hint`):
```markdown
---
name: missing-arg-hint
description: A skill that consumes arguments but declares no argument-hint.
---

# Missing Arg Hint
## Overview
This skill processes $ARGUMENTS but never declares an argument-hint, tripping 3.6.
```
`tests/fixtures/missing-arg-hint/expected.json`:
```json
{ "expected_fail": ["3.6"], "expected_grade": "S" }
```

`tests/fixtures/body-too-long/` — generate a >500-line body:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/body-too-long"
os.makedirs(d, exist_ok=True)
lines = ["---", "name: body-too-long",
         "description: A skill whose body exceeds 500 lines.", "---", "", "# Body Too Long", ""]
lines += ["Filler line %d." % i for i in range(1, 520)]
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("\n".join(lines) + "\n")
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["4.3"], "expected_grade": "S" }\n')
PY
```

- [ ] **Step 2: Run the harness to verify failure**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: FAIL — `test_missing_arg_hint`, `test_body_too_long`.

- [ ] **Step 3: Append the 3.6 and 4.3 checks**

```python
@rule
def check_3_6(ctx):
    item = "$ARGUMENTS use requires argument-hint"
    uses_args = "$ARGUMENTS" in ctx.text
    if not uses_args:
        return mk("3.6", item, "MINOR", "na", why="skill does not use $ARGUMENTS")
    if "argument-hint" in ctx.fm:
        return mk("3.6", item, "MINOR", "pass")
    return mk("3.6", item, "MINOR", "fail",
              why="$ARGUMENTS is used but argument-hint is missing",
              how_to_fix="add an 'argument-hint:' frontmatter key describing expected args")


@rule
def check_4_3(ctx):
    item = "body is <=500 lines"
    n = len(ctx.body.strip("\n").split("\n")) if ctx.body.strip() else 0
    if n <= 500:
        return mk("4.3", item, "MINOR", "pass")
    return mk("4.3", item, "MINOR", "fail",
              why="body is %d lines (>500)" % n,
              how_to_fix="move detail into references/ and keep SKILL.md lean")
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — both new fixtures grade `S` (MINOR fails only).

- [ ] **Step 5: Commit**

```bash
git add scripts/check_rules.py tests/fixtures
git commit -m "feat: trigger/content checks 3.6 and 4.3"
```

---

## Task 5: Resource rule checks (5.3, 5.4, 5.6, 5.7, 5.8)

**Files:**
- Modify: `scripts/check_rules.py` (append 5 checks + placeholder token list built from fragments)
- Create: `tests/fixtures/nested-references/`, `no-toc-reference/`, `bad-script-syntax/`, `script-not-mentioned/`, `placeholder-residue/`

- [ ] **Step 1: Create the five fixtures (failing)**

`nested-references/` — a 3-deep reference chain (a→b→c) triggers 5.3:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/nested-references"
os.makedirs(os.path.join(d, "references"), exist_ok=True)
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("---\nname: nested-references\n"
            "description: A skill with a 3-level reference chain.\n---\n\n"
            "# Nested References\n## Overview\nSee references/a.md for details.\n")
with open(os.path.join(d, "references", "a.md"), "w") as f:
    f.write("# A\nNext, read [B](b.md).\n")
with open(os.path.join(d, "references", "b.md"), "w") as f:
    f.write("# B\nNext, read [C](c.md).\n")
with open(os.path.join(d, "references", "c.md"), "w") as f:
    f.write("# C\nLeaf document.\n")
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["5.3"], "expected_grade": "A" }\n')
PY
```

`no-toc-reference/` — a >=100-line reference with no table of contents triggers 5.4:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/no-toc-reference"
os.makedirs(os.path.join(d, "references"), exist_ok=True)
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("---\nname: no-toc-reference\n"
            "description: A skill with a long reference that lacks a table of contents.\n---\n\n"
            "# No TOC Reference\n## Overview\nSee references/long.md.\n")
body = ["# Long Reference", ""] + ["Paragraph line %d." % i for i in range(1, 140)]
with open(os.path.join(d, "references", "long.md"), "w") as f:
    f.write("\n".join(body) + "\n")
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["5.4"], "expected_grade": "S" }\n')
PY
```

`bad-script-syntax/` — invalid Python triggers 5.6; SKILL.md mentions the script so 5.7 stays clean:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/bad-script-syntax"
os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("---\nname: bad-script-syntax\n"
            "description: A skill shipping a Python script that fails to parse.\n---\n\n"
            "# Bad Script Syntax\n## Overview\nRun scripts/broken.py to do the work.\n")
with open(os.path.join(d, "scripts", "broken.py"), "w") as f:
    f.write("def broken(:\n    return 1\n")  # syntax error
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["5.6"], "expected_grade": "A" }\n')
PY
```

`script-not-mentioned/` — valid script never referenced from SKILL.md triggers 5.7:
```bash
python3 - <<'PY'
import os
d = "tests/fixtures/script-not-mentioned"
os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
with open(os.path.join(d, "SKILL.md"), "w") as f:
    f.write("---\nname: script-not-mentioned\n"
            "description: A skill shipping a script that SKILL.md never references.\n---\n\n"
            "# Script Not Mentioned\n## Overview\nThe body never names the helper.\n")
with open(os.path.join(d, "scripts", "helper.py"), "w") as f:
    f.write("def helper():\n    return 42\n")
with open(os.path.join(d, "expected.json"), "w") as f:
    f.write('{ "expected_fail": ["5.7"], "expected_grade": "S" }\n')
PY
```

`placeholder-residue/` — a literal `TODO:` marker in shipped content triggers 5.8:
```markdown
---
name: placeholder-residue
description: A skill that left an unfinished placeholder marker in its body.
---

# Placeholder Residue
## Overview
TODO: finish writing this section before shipping.
```
`tests/fixtures/placeholder-residue/expected.json`:
```json
{ "expected_fail": ["5.8"], "expected_grade": "S" }
```

- [ ] **Step 2: Run the harness to verify failure**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: FAIL — the five new `test_*` cases.

- [ ] **Step 3: Append the resource checks**

```python
import ast  # add to imports at top of file

_MD_LINK = re.compile(r"\]\(([^)]+)\)")


def _reference_files(skill_dir):
    base = os.path.join(skill_dir, "references")
    out = []
    for root, _, files in os.walk(base):
        for name in files:
            if name.endswith(".md"):
                out.append(os.path.join(root, name))
    return out


@rule
def check_5_3(ctx):
    item = "no nested reference chain (A->B->C)"
    refs = _reference_files(ctx.skill_dir)
    if not refs:
        return mk("5.3", item, "MAJOR", "na", why="no reference files")
    names = {os.path.basename(p): p for p in refs}
    graph = {}
    for path in refs:
        targets = set()
        for link in _MD_LINK.findall(read_text(path)):
            tgt = os.path.basename(link.split("#")[0].strip())
            if tgt in names and tgt != os.path.basename(path):
                targets.add(tgt)
        graph[os.path.basename(path)] = targets
    # a chain of depth 3 exists if a -> b -> c with distinct nodes
    for a, bs in graph.items():
        for b in bs:
            for c in graph.get(b, ()):
                if c not in (a, b):
                    return mk("5.3", item, "MAJOR", "fail",
                              why="reference chain %s -> %s -> %s" % (a, b, c),
                              how_to_fix="flatten references so SKILL.md links each "
                                         "reference directly (max depth 2)")
    return mk("5.3", item, "MAJOR", "pass")


def _has_toc(text):
    head = text.split("\n")[:40]
    joined = "\n".join(head).lower()
    if "table of contents" in joined or "## 목차" in "\n".join(head):
        return True
    return any("](#" in line for line in head)  # anchor links near the top


@rule
def check_5_4(ctx):
    item = "references >=100 lines have a table of contents"
    refs = _reference_files(ctx.skill_dir)
    offenders = []
    for path in refs:
        text = read_text(path)
        if len(text.split("\n")) >= 100 and not _has_toc(text):
            offenders.append(os.path.basename(path))
    if not refs:
        return mk("5.4", item, "MINOR", "na", why="no reference files")
    if offenders:
        return mk("5.4", item, "MINOR", "fail",
                  why="long reference(s) without a TOC: %s" % ", ".join(offenders),
                  how_to_fix="add a '## Table of Contents' with anchor links")
    return mk("5.4", item, "MINOR", "pass")


def _script_files(skill_dir):
    base = os.path.join(skill_dir, "scripts")
    out = []
    for root, _, files in os.walk(base):
        for name in files:
            out.append(os.path.join(root, name))
    return out


@rule
def check_5_6(ctx):
    item = "Python scripts parse (valid syntax)"
    scripts = [p for p in _script_files(ctx.skill_dir) if p.endswith(".py")]
    if not scripts:
        return mk("5.6", item, "MAJOR", "na", why="no Python scripts")
    broken = []
    for path in scripts:
        try:
            ast.parse(read_text(path))
        except SyntaxError as exc:
            broken.append("%s (%s)" % (os.path.basename(path), exc.msg))
    if broken:
        return mk("5.6", item, "MAJOR", "fail",
                  why="script(s) fail to parse: %s" % "; ".join(broken),
                  how_to_fix="fix the syntax error so the script imports/runs")
    return mk("5.6", item, "MAJOR", "pass")


@rule
def check_5_7(ctx):
    item = "shipped scripts are referenced from SKILL.md"
    scripts = _script_files(ctx.skill_dir)
    if not scripts:
        return mk("5.7", item, "MINOR", "na", why="no scripts")
    missing = []
    for path in scripts:
        rel = "scripts/" + os.path.basename(path)
        if rel not in ctx.text and os.path.basename(path) not in ctx.text:
            missing.append(os.path.basename(path))
    if missing:
        return mk("5.7", item, "MINOR", "fail",
                  why="script(s) not mentioned in SKILL.md: %s" % ", ".join(missing),
                  how_to_fix="reference each script path from SKILL.md so it is discoverable")
    return mk("5.7", item, "MINOR", "pass")


# Tokens built from adjacent string fragments so this source file never contains
# the assembled literal -> the 5.8 scan does not flag check_rules.py itself.
PLACEHOLDER_TOKENS = [
    "TO" "DO", "FIX" "ME", "X" "XX", "PLACE" "HOLDER",
    "lorem ipsum", "implement later", "coming soon",
    "INSERT_" "HERE", "FILL_" "IN", "<your-",
]


@rule
def check_5_8(ctx):
    item = "no placeholder/TODO residue in shipped files"
    hits = []
    for path in shipped_files(ctx.skill_dir):
        text = read_text(path)
        for token in PLACEHOLDER_TOKENS:
            if token in text:
                hits.append("%s:%s" % (os.path.basename(path), token))
                break
    if hits:
        return mk("5.8", item, "MINOR", "fail",
                  why="placeholder residue found: %s" % ", ".join(hits),
                  how_to_fix="remove leftover scaffolding markers and finish the content")
    return mk("5.8", item, "MINOR", "pass")
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — `nested-references` grades `A` (1 MAJOR); `no-toc-reference`, `script-not-mentioned`, `placeholder-residue` grade `S`; `bad-script-syntax` grades `A`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_rules.py tests/fixtures
git commit -m "feat: resource checks 5.3-5.8 (nesting, TOC, AST, mentions, placeholders)"
```

---

## Task 6: Safety BLOCKER checks (6.1 secrets, 6.2 destructive tools)

**Files:**
- Modify: `scripts/check_rules.py` (append 2 checks + secret/destructive patterns)
- Create: `tests/fixtures/secret-leak/`, `destructive-tool/`

Both are BLOCKERs → grade `F`. `secret-leak/` and `destructive-tool/` live under `tests/`, so per the shipped-surface rule they never count against the evaluator's own dogfood.

- [ ] **Step 1: Create the two fixtures (failing)**

`tests/fixtures/secret-leak/SKILL.md` (fake-but-realistic AWS key in a shipped doc):
```markdown
---
name: secret-leak
description: A skill that hardcodes a credential in its shipped content.
---

# Secret Leak
## Overview
Deploy with key AKIAIOSFODNN7EXAMPLE to the bucket.
```
`tests/fixtures/secret-leak/expected.json`:
```json
{ "expected_fail": ["6.1"], "expected_grade": "F" }
```

`tests/fixtures/destructive-tool/SKILL.md` (`allowed-tools` permits a destructive command):
```markdown
---
name: destructive-tool
description: A skill that allow-lists a destructive shell command.
allowed-tools: Bash(rm -rf /)
---

# Destructive Tool
## Overview
Triggers 6.2 only.
```
`tests/fixtures/destructive-tool/expected.json`:
```json
{ "expected_fail": ["6.2"], "expected_grade": "F" }
```

- [ ] **Step 2: Run the harness to verify failure**

Run: `python3 -m unittest tests.test_fixtures -v`
Expected: FAIL — `test_secret_leak`, `test_destructive_tool`.

- [ ] **Step 3: Append the safety checks**

```python
# (regex char-classes ensure these patterns do not match their own source text)
SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*[A-Za-z0-9/+]{20,}"), "AWS secret key"),
    (re.compile(r"-----BEGIN(?:[A-Z ]+)?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*"
                r"['\"][^'\"]{8,}['\"]"), "hardcoded credential"),
]


@rule
def check_6_1(ctx):
    item = "no plaintext secrets/credentials"
    hits = []
    for path in shipped_files(ctx.skill_dir):
        text = read_text(path)
        for pat, label in SECRET_PATTERNS:
            if pat.search(text):
                hits.append("%s:%s" % (os.path.basename(path), label))
    if hits:
        return mk("6.1", item, "BLOCKER", "fail",
                  why="possible secret(s): %s" % ", ".join(sorted(set(hits))),
                  how_to_fix="remove the secret; load credentials from env vars at runtime")
    return mk("6.1", item, "BLOCKER", "pass")


DESTRUCTIVE_PATTERNS = [
    re.compile(r"rm\s+-[a-z]*[rf][a-z]*\b"),     # rm -rf / rm -fr / rm -r etc.
    re.compile(r"rm\s+--no-preserve-root"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b"),
    re.compile(r"chmod\s+-R\s+777|chmod\s+777\s+-R"),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # fork bomb
    re.compile(r">\s*/dev/sd[a-z]"),
]


def _allowed_tools_text(ctx):
    val = ctx.fm.get("allowed-tools", "")
    return val if isinstance(val, str) else " ".join(map(str, val))


@rule
def check_6_2(ctx):
    item = "allowed-tools has no destructive patterns"
    text = _allowed_tools_text(ctx)
    if not text:
        return mk("6.2", item, "BLOCKER", "na", why="no allowed-tools declared")
    for pat in DESTRUCTIVE_PATTERNS:
        if pat.search(text):
            return mk("6.2", item, "BLOCKER", "fail",
                      why="allowed-tools permits a destructive command: %r" % text,
                      how_to_fix="remove the destructive command from allowed-tools")
    return mk("6.2", item, "BLOCKER", "pass")
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all 18 fixtures pass; `secret-leak` and `destructive-tool` grade `F`.

- [ ] **Step 5: Verify the full rule-check count is 17**

Run: `python3 -c "import sys; sys.path.insert(0,'scripts'); import check_rules; print(len(check_rules.RULE_CHECKS))"`
Expected: `17`

- [ ] **Step 6: Commit**

```bash
git add scripts/check_rules.py tests/fixtures
git commit -m "feat: safety BLOCKER checks 6.1 (secrets) and 6.2 (destructive tools)"
```

---

## Task 7: `references/model-rubric.md` — the 13 model-check criteria

**Files:**
- Create: `references/model-rubric.md`

This is the rubric Claude applies (by reading the target) for the 13 semantic checks. It must be loaded only when running an evaluation (a "when to read" condition stated in SKILL.md, Task 8). Keep each item to: the question, what counts as pass/fail, severity, and one good + one bad example. Add a Table of Contents (the file will exceed 100 lines, so 5.4 applies to the evaluator itself).

> Self-reference note (Convention 3): describe checks without pasting realistic secret values or the literal placeholder tokens from Task 5. This file describes the 13 MODEL checks only — it does not list rule-check token internals, so it stays clean.

- [ ] **Step 1: Write `references/model-rubric.md`**

````markdown
# Model Rubric — 13 semantic checks

Apply these by reading the target skill's `SKILL.md`, `references/`, and `scripts/`.
Emit one finding per item using the shared schema (see SKILL.md). `checker` is always
`"model"`. Use `na` when the item genuinely does not apply, never to avoid judgment.

## Table of Contents
- [Section 1 — Validity (1.1, 1.2, 1.3)](#section-1--validity)
- [Section 3 — Triggers (3.1–3.5)](#section-3--triggers)
- [Section 4 — Content (4.1, 4.2)](#section-4--content)
- [Section 5 — Resources (5.1, 5.2, 5.5)](#section-5--resources)

## Section 1 — Validity

### 1.1 Recurring workflow? — MAJOR
Pass: the skill automates a task a user hits repeatedly. Fail: a one-off task.
- Good: "commit and split changes into logical commits" (done constantly).
- Bad: "set up this one repo's CI for the 2026 migration" (happens once).

### 1.2 General-purpose? — MAJOR
Pass: usable across projects/users. Fail: hardcoded to one private repo/path/team.
- Good: "review a diff for bugs."
- Bad: "deploy acme-internal-api using /home/bob/secrets."

### 1.3 Not replaceable by base agent ability? — MAJOR
Pass: encodes non-obvious procedure, domain rules, or tool orchestration the agent
would otherwise get wrong. Fail: restates what a competent agent already does.
- Good: a debugging discipline that forces reproduce-before-fix.
- Bad: "to read a file, use the Read tool."

## Section 3 — Triggers

### 3.1 description has WHAT + WHEN — MAJOR
Pass: states both the capability and the situation that should invoke it.
- Good: "Use when committing changes to split them into logical commits."
- Bad: "A helpful commit tool." (no WHEN)

### 3.2 Enough trigger keywords — MAJOR
Pass: includes the words/phrases a user would actually say. Fail: vague.
- Good: lists "commit", "split commits", "organize changes".
- Bad: "handles version control stuff."

### 3.3 description matches the body — MAJOR
Pass: what the body does is what the description promises. Fail: drift.
- Bad: description says "formats SQL"; body migrates databases.

### 3.4 No body-only trigger — BLOCKER
Pass: invocation conditions live in `description` (frontmatter). Fail: the only place
that says when to use the skill is the markdown body — the model cannot trigger on it.
- Bad: description is "A utility."; the body alone says "use this whenever tests fail."

### 3.5 Trigger scope not over-broad — MAJOR
Pass: fires for its real use case. Fail: so broad it would hijack unrelated requests.
- Bad: "Use for any coding task."

## Section 4 — Content

### 4.1 Specificity >= 1 — MINOR
Pass: contains at least one of: a number/threshold, real code, a "why", or a concrete
scenario. Fail: all generic prose.

### 4.2 Not just base coding knowledge — MAJOR
Pass: teaches something beyond what a strong coding agent already knows. Fail: a list
of language basics or generic best-practice platitudes.

## Section 5 — Resources

### 5.1 Core in SKILL.md, detail in references/ — MAJOR
Pass: SKILL.md is the lean orchestration; deep detail is split into references.
Fail: everything dumped into one giant SKILL.md, or trivia split into many files.

### 5.2 reference links state WHEN to read — MINOR
Pass: each `references/...` link says the condition for loading it ("read X when Y").
Fail: bare links with no loading condition.

### 5.5 Error-prone fixed steps live in scripts/ — MAJOR
Pass: deterministic, easy-to-botch procedures (counts, regex, parsing) are scripts the
agent runs, not prose it executes by hand. Fail: asks the model to do mechanical work
it will get wrong.
````

- [ ] **Step 2: Verify the reference has a TOC and is well-formed**

Run: `python3 -c "t=open('references/model-rubric.md').read(); print('lines', len(t.splitlines())); print('toc', 'Table of Contents' in t)"`
Expected: `lines` ≥ 100 (or near it) and `toc True`. (If under 100 lines the TOC is optional, but keep it — the evaluator's own 5.4 then passes regardless.)

- [ ] **Step 3: Commit**

```bash
git add references/model-rubric.md
git commit -m "docs: model-rubric.md with the 13 semantic check criteria"
```

---

## Task 8: `SKILL.md` — orchestration, grade rule, report format

**Files:**
- Create: `SKILL.md`

SKILL.md ties it together: how to find the target, run the script, apply the model rubric, combine 30 findings, compute the deterministic grade via the `--grade` mode, and render the report. It must itself pass the rubric (kebab name == folder `rubric-evaluator`, WHAT+WHEN description, mentions `scripts/check_rules.py` for 5.7, links `references/model-rubric.md` with a WHEN condition for 5.2, stays ≤500 lines for 4.3, no placeholder tokens for 5.8, and **no "claude"/"anthropic" in the name or description for 2.7** — describe the task without naming the platform).

- [ ] **Step 1: Write `SKILL.md`**

````markdown
---
name: rubric-evaluator
description: Use when reviewing, auditing, or grading a skill's quality — evaluates a skill directory against a 30-item rubric and reports a grade (S/A/B/C/F) with fixes. Trigger on "evaluate this skill", "skill 품질", "rubric", "grade my skill", "is this skill good".
---

# rubric-evaluator

Grade a skill against a 6-section / 30-item rubric. Deterministic checks run as a
Python script; semantic checks are applied by reading the target. The headline grade
is computed deterministically — never eyeballed.

## When to use
A user wants to know whether a skill is well-built, or asks for a review/audit/grade of
a skill directory that contains a `SKILL.md`.

## Inputs
The target skill directory. If the user did not name one, ask which directory to evaluate.

## Procedure

1. **Confirm the target.** Resolve the path to a directory containing `SKILL.md`.

2. **Run the deterministic rule-checks (17):**
   ```bash
   python3 scripts/check_rules.py <target_dir>
   ```
   This prints `{"findings": [...17 rule findings...], "grade": <rule-only grade>}`.
   Each finding follows the schema below.

3. **Apply the model-checks (13):** Read `references/model-rubric.md` now — it holds the
   criteria and good/bad examples for the semantic checks. Read the target's `SKILL.md`,
   `references/`, and `scripts/`, then produce one finding per model item using the same
   schema, with `"checker": "model"`.

4. **Combine + grade deterministically.** Concatenate the 17 rule findings and 13 model
   findings into one JSON array, write it to a temp file, and compute the final grade:
   ```bash
   python3 scripts/check_rules.py --grade /tmp/all_findings.json
   ```
   Use that grade verbatim. Do not recompute it by hand.

5. **Render the report** (format below).

## Finding schema
```json
{
  "id": "2.2",
  "section": "structure",
  "item": "name is kebab-case (<=64 chars)",
  "severity": "BLOCKER",
  "status": "fail",
  "checker": "rule",
  "why": "name 'MySkill' is not kebab-case",
  "how_to_fix": "rename to 'my-skill' and match the folder"
}
```
`severity`: BLOCKER | MAJOR | MINOR. `status`: pass | fail | na. `checker`: rule | model.

## Grade rule (same as `compute_grade`)
- BLOCKER ≥ 1 → **F** (do not ship; rewrite)
- BLOCKER 0, MAJOR 0 → **S**
- BLOCKER 0, MAJOR 1–2 → **A**
- BLOCKER 0, MAJOR 3–4 → **B**
- BLOCKER 0, MAJOR 5+ → **C**
- MINOR never changes the grade (advisory only).

## Report format
```
TL;DR: [<skill type>] | Grade <X> | Top fixes:
- <item>: <why it's a problem> -> <how to fix>
- ...

| id | section | item | severity | status | comment |
|----|---------|------|----------|--------|---------|
| ... full 30-row table sorted by id ... |
```
For each failing item, the comment is the finding's `why` then `how_to_fix`. List passes
compactly; spend detail on fails. If the grade is F, lead with the BLOCKER(s).

## The 30 items
Sections: 1 validity (3) · 2 structure (8) · 3 triggers (6) · 4 content (3) ·
5 resources (8) · 6 safety (2). 17 are rule-checked by the script; 13 are model-checked
via `references/model-rubric.md`. 8 are BLOCKERs: 2.1–2.5, 3.4, 6.1, 6.2.

## Notes
- The script is stdlib-only; no install step.
- Content scans inspect only shipped files (SKILL.md, references/, scripts/) — not tests/.
- By default the full 30-item report is produced even if a BLOCKER is present, so the
  author sees every issue at once.
````

- [ ] **Step 2: Verify SKILL.md passes the rule-checks against itself**

Run: `python3 scripts/check_rules.py . | python3 -c "import json,sys; d=json.load(sys.stdin); f=[x for x in d['findings'] if x['status']=='fail']; print('grade', d['grade']); print('fails', [x['id'] for x in f])"`
Expected: `grade S` and `fails []`. If any rule fails, fix SKILL.md (or, if a `5.8`/`6.1` self-reference slipped in, fragment the token per Convention 3 — never weaken the check).

- [ ] **Step 3: Confirm the unit + fixture suite still passes**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (unchanged).

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "feat: SKILL.md orchestration, grade rule, and report format"
```

---

## Task 9: Verification — dogfood + real-skill false-positive check

**Files:** none created; this task verifies and records evidence.

- [ ] **Step 1: Dogfood the rule-checks on the evaluator itself**

Run: `python3 scripts/check_rules.py . | python3 -c "import json,sys; d=json.load(sys.stdin); print('grade', d['grade']); print('fails', [x['id'] for x in d['findings'] if x['status']=='fail'])"`
Expected: `grade S`, `fails []`. The evaluator's `tests/fixtures/*` violations are excluded because content scans use `shipped_files()`. If a real fail appears, fix the offending shipped file (fragment a self-referenced token, remove a stray secret-looking string); do not loosen a check to make the grade green.

- [ ] **Step 2: Apply the 13 model-checks to the evaluator (full dogfood)**

Read `references/model-rubric.md` and the evaluator's own `SKILL.md`/`references`/`scripts`, produce the 13 model findings, combine with the 17 rule findings, write to `/tmp/eval_self.json`, and grade:
Run: `python3 scripts/check_rules.py --grade /tmp/eval_self.json`
Expected: `S`. Record the 30-item report. If a model item legitimately fails, either fix the evaluator or note the deviation explicitly — do not fabricate a pass.

- [ ] **Step 3: False-positive check against 2–3 mature real skills**

Pick installed skills known to be high quality, e.g.:
```bash
python3 scripts/check_rules.py ~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/writing-plans \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['grade'], [x['id'] for x in d['findings'] if x['status']=='fail'])"
```
Repeat for two more mature skills (e.g. `superpowers/.../test-driven-development`, `.../systematic-debugging`).
Expected: **eyeball the full fail list, not just the grade.** Rule-check false positives on mature skills are usually MAJOR/MINOR (e.g. a real skill ships a `README.md` → 2.8, or an over-eager 2.6 key flag) and never reach `F`, so "grade ≠ F" alone would miss them. For each skill, inspect every `fail` id and confirm it is a genuine defect; any fail you judge spurious means the checker is wrong — investigate and tighten it (the checker is wrong, not the skill). Record which skills were checked, their grades, and the full fail lists.

- [ ] **Step 4: Run the whole suite one final time**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all unit tests and all 18 fixtures.

- [ ] **Step 5: Commit any fixes from this task**

```bash
git add -A
git commit -m "test: dogfood evaluator to grade S and verify no false positives on mature skills"
```
(If steps 1–4 required no changes, skip the commit and note that verification passed clean.)

---

## Self-Review (performed against the spec)

**Spec coverage:**
- §4 product structure (SKILL.md, scripts/check_rules.py, references/model-rubric.md, tests/fixtures) → Tasks 1–8. ✓
- §5 flow (confirm target → run script → model checks → combine → grade → report) → Task 8 Procedure. ✓
- §6 finding schema → Task 1 `mk()` + Task 8 documented schema (identical fields). ✓
- §7 grade thresholds → Task 1 `compute_grade` + unit tests + Task 8 doc. ✓
- §8 all 30 items: 17 rule checks (2.1–2.8, 3.6, 4.3, 5.3/5.4/5.6/5.7/5.8, 6.1/6.2) → Tasks 2–6; 13 model checks → Task 7. Count verified in Task 6 Step 5 (== 17). ✓
- §8 the 8 BLOCKERs (2.1–2.5, 3.4, 6.1, 6.2): rule BLOCKERs implemented (2.1–2.5, 6.1, 6.2); 3.4 is model BLOCKER in model-rubric.md. ✓
- §8 2.6 whitelist resolved (observed-on-disk superset; Task 3). ✓
- §9 verification: synthetic fixtures (Tasks 1–6), dogfood to S (Task 9 Steps 1–2), real-skill FP check (Task 9 Step 3). ✓
- §3 zero-dependency: stdlib-only parser + `unittest`; no PyYAML/pytest. ✓

**Placeholder scan:** No "TBD/TODO/implement later" steps; every code step shows complete code; fixture content is fully specified or generated by an exact inline script.

**Type/name consistency:** `mk`, `rule`, `parse_frontmatter`, `top_level_keys`, `shipped_files`, `compute_grade`, `run_checks`, `build_ctx` are defined in Task 1 and used unchanged thereafter. Finding fields (`id/section/item/severity/status/checker/why/how_to_fix`) are identical in `mk()` and the SKILL.md schema. Grade letters S/A/B/C/F consistent across `compute_grade`, fixtures, and SKILL.md.

**One known limitation (documented, not a gap):** `parse_frontmatter` validates structural YAML shape only (it is not a full YAML parser — none exists in the stdlib). `2.1` is scoped to that contract and its boundary cases are pinned by the `bad-frontmatter/` fixture and parser unit tests.
