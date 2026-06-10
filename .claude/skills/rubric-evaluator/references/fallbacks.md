# Fallbacks

Read this only when the normal workflow in `SKILL.md` cannot run cleanly — the
wrapper fails, no Python interpreter exists, the skill is run from an unpacked
repo instead of an installed skill, or the target is outside the writable
workspace.

## Runtime ladder

Try these in order; stop at the first that works:

1. `scripts/run_checks.sh <target_dir>` — the portable wrapper (python3 → python → `py -3`).
2. A specific interpreter directly: `python3 scripts/check_rules.py <target_dir>`, then `python …`, then `py -3 …`.
3. If none of the above run, drop to **provisional manual mode** below.

The wrapper forwards arguments, so the grade step has the same ladder:
`scripts/run_checks.sh --grade /tmp/all_findings.json`.

## Provisional manual mode (no Python)

When no interpreter is available, you can still produce a report — but it is
**provisional**, never deterministic. Do this:

1. Read the target `SKILL.md`.
2. Inspect only shipped files: `SKILL.md`, `references/**`, `scripts/**`. Never `tests/**`.
3. Apply the 17 rule IDs by hand **only where the evidence is direct** (frontmatter
   shape, kebab-case name, char/line counts, file presence, literal markers,
   shell-command safety). Use the same finding schema as `SKILL.md`.
4. Set any rule finding you cannot determine by eye to `na`. Do **not** fabricate
   deterministic confidence — guessing at the secret-scan or syntax checks is worse
   than an honest `na`.
5. Apply the 13 model checks normally — they never needed Python.
6. Compute the grade by hand using the **Grade rule** in `SKILL.md`. Because this is
   eyeballed rather than computed, it is provisional.
7. Put `PROVISIONAL` in the TL;DR and state that deterministic rule automation did
   not run.

> The normal workflow says the grade is computed deterministically and never
> eyeballed. Hand-grading is allowed **only** in this provisional mode, and only
> when it is labeled `PROVISIONAL`. Never hand-grade on the normal path.

## Partial failures

- **Only the grade step failed, findings exist:** rerun the grade through the
  wrapper (`scripts/run_checks.sh --grade …`). If that still fails, compute the
  grade by hand from the Grade rule and mark the report `PROVISIONAL`.
- **A copied `SKILL.md` with no `scripts/`/`references/`:** run a provisional
  report and state that bundled resources are missing.
- **Target outside the writable workspace:** evaluate the read-only files normally.
  Do not copy, install, or rewrite the target unless the user asks for edits.
- **Multiple matching directories:** pick the one whose folder name matches the
  requested skill; if still ambiguous, ask for the exact path.

## What a fallback report must state

- the fallback reason (e.g. "no Python runtime found"),
- which checks ran normally vs. which were marked `na`,
- residual risk (what a deterministic run would still catch),
- the smallest next step to restore deterministic evaluation (usually: install
  Python and rerun `scripts/run_checks.sh`).
