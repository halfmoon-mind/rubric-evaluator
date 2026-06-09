---
name: skill-rubric-evaluator
description: Evaluate Codex skill folders that contain SKILL.md with a 6-section rubric, deterministic rule checks, semantic model checks, S/A/B/C/F grades, and fixable reports. Use when asked to grade, audit, review, dogfood, or improve a Codex skill, skill directory, SKILL.md, skill rubric score, trigger quality, resource structure, or safety gate.
---

# Skill Rubric Evaluator

Evaluate a Codex skill directory with a 6-section, 30-item rubric. Use deterministic scripts for structural and safety checks, then apply semantic model checks from the bundled rubric reference. If the runtime or installation path is incomplete, use the fallback playbook and label the result as provisional.

## Workflow

1. Confirm the target is a directory containing `SKILL.md`. If the path is missing or ambiguous, ask for the exact skill directory.
2. Run the deterministic checks with the portable wrapper:

   ```bash
   scripts/run_checks.sh <target-skill-dir>
   ```

   The wrapper tries `python3`, then `python`, then the Windows `py -3` launcher. If the wrapper cannot run, read `references/fallbacks.md` and continue in the documented degraded mode.

3. If the wrapper is unavailable but a Python interpreter is known, run the script directly:

   ```bash
   python3 scripts/check_rules.py <target-skill-dir>
   ```

   The script returns JSON with `findings` and a rule-only `grade`.

4. Read `references/model-rubric.md` after the rule output is available. Apply all 13 model checks and produce findings with the same schema as the rule findings.
5. Combine rule and model findings. Keep every finding, including `pass` and `na`, so the final grade is auditable.
6. Compute the final grade from failed findings:

   - Any failed `BLOCKER` means `F`.
   - No failed `BLOCKER` and no failed `MAJOR` means `S`.
   - No failed `BLOCKER` and 1-2 failed `MAJOR` means `A`.
   - No failed `BLOCKER` and 3-4 failed `MAJOR` means `B`.
   - No failed `BLOCKER` and 5 or more failed `MAJOR` means `C`.
   - Failed `MINOR` findings do not affect the grade.

7. Render the report. If you have written combined findings to a JSON file, run:

   ```bash
   python3 scripts/render_report.py <combined-findings.json> --skill-name <skill-name>
   ```

   If no file is written, mirror the same report structure manually.

## Fallbacks

Read `references/fallbacks.md` when `scripts/run_checks.sh` fails, Python is unavailable, the skill is being used from an unpacked repo instead of an installed skill, the target path is outside the current workspace, or the user needs a clear next-hardening plan.

When fallback mode is used, state it in the TL;DR. Do not pretend a manual scan is equivalent to the deterministic rule script. If deterministic rule checks cannot run, mark the report as `provisional`, keep any uncertain rule findings as `na`, and list the missing runtime or installation condition as residual risk.

## Finding Schema

Use this schema for every rule and model finding:

```json
{
  "id": "3.4",
  "section": "trigger",
  "item": "body-only trigger anti-pattern absent",
  "severity": "BLOCKER",
  "status": "fail",
  "checker": "model",
  "why": "The description does not include the invocation condition.",
  "how_to_fix": "Move both the skill capability and trigger condition into the description."
}
```

Allowed values:

- `severity`: `BLOCKER`, `MAJOR`, `MINOR`
- `status`: `pass`, `fail`, `na`
- `checker`: `rule`, `model`

## Report Rules

Lead with the grade and failed finding counts. Put failed `BLOCKER` findings first, failed `MAJOR` findings second, and failed `MINOR` findings last. For each failed finding, include both:

- why the issue matters
- how to fix it

Keep passed findings collapsed into section summaries unless the user asks for the full matrix.

## Resource Use

- Use `scripts/check_rules.py` for deterministic checks, rule-only grading, and JSON output.
- Use `scripts/run_checks.sh` as the first-choice launcher for deterministic checks across common Python command names.
- Use `scripts/render_report.py` when combined findings are available as JSON and a markdown report is useful.
- Read `references/model-rubric.md` only after running deterministic checks or when authoring model findings; it contains the 13 semantic checks, pass/fail criteria, examples, and wording guidance.
- Read `references/fallbacks.md` only when runtime, installation, path, or platform constraints prevent the normal workflow, or when the user asks for follow-up hardening work.
