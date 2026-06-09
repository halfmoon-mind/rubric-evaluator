---
name: skill-rubric-evaluator
description: Use when reviewing, auditing, or grading a skill's quality — evaluates a skill directory against a 30-item rubric and reports a grade (S/A/B/C/F) with fixes. Trigger on "evaluate this skill", "skill 품질", "rubric", "grade my skill", "is this skill good".
---

# skill-rubric-evaluator

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
   sh scripts/run_checks.sh <target_dir>
   ```
   The wrapper tries `python3`, then `python`, then the Windows `py -3` launcher
   (or call `python3 scripts/check_rules.py <target_dir>` directly if you know the
   interpreter). This prints `{"findings": [...17 rule findings...], "grade":
   <rule-only grade>}`. Each finding follows the schema below. If no interpreter is
   found, read `references/fallbacks.md` and continue in provisional mode.

3. **Apply the model-checks (13):** Read `references/model-rubric.md` now — it holds the
   criteria and good/bad examples for the semantic checks. Read the target's `SKILL.md`,
   `references/`, and `scripts/`, then produce one finding per model item using the same
   schema, with `"checker": "model"`.

4. **Combine + grade deterministically.** Concatenate the 17 rule findings and 13 model
   findings into one JSON array, write it to a temp file, and compute the final grade:
   ```bash
   sh scripts/run_checks.sh --grade /tmp/all_findings.json
   ```
   The wrapper forwards arguments, so this runs through the same interpreter ladder.
   Use that grade verbatim. Do not recompute it by hand — the only exception is the
   provisional no-Python path in `references/fallbacks.md`.

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
`severity`: BLOCKER | MAJOR | MINOR. `status`: pass | fail | na. `checker`: rule | model. Emit `severity`, `status`, and `section` in exactly this case — the grade is computed by literal match, so a casing slip would be silently miscounted.

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

## Fallbacks
Read `references/fallbacks.md` when `scripts/run_checks.sh` fails, no Python
interpreter is available, the skill is run from an unpacked repo, or the target is
outside the writable workspace. It documents the interpreter ladder and a
provisional manual mode (apply rules by eye where evidence is direct, mark the rest
`na`, hand-grade, and label the TL;DR `PROVISIONAL`). Hand-grading is allowed **only**
in that provisional mode — never on the normal path.

## Notes
- The script is stdlib-only; no install step.
- Content scans inspect only shipped files (SKILL.md, references/, scripts/) — not tests/.
- By default the full 30-item report is produced even if a BLOCKER is present, so the
  author sees every issue at once.
