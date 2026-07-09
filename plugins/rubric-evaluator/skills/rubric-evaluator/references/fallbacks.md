# Fallbacks and Hardening Queue

Use this reference only when the normal evaluator workflow cannot run cleanly or when the user asks what to harden next.

## Runtime Fallbacks

1. Prefer `scripts/run_checks.sh <target-skill-dir>`.
2. If the wrapper is unavailable, try an interpreter directly in this order: `python3`, `python`, `py -3`.
3. If Codex desktop exposes bundled workspace runtimes, use the bundled Python path only after confirming it exists.
4. If no Python-compatible runtime exists, continue with a provisional manual report:

- Read the target `SKILL.md`.
- Inspect only shipped files: `SKILL.md`, files under `references/`, and files under `scripts/`.
- Apply the 17 rule IDs manually where evidence is direct.
- Set uncertain rule findings to `na`; do not fabricate deterministic confidence.
- Apply the 14 model checks from the normal workflow.
- Put `PROVISIONAL` in the TL;DR and explain that deterministic rule automation did not run.

## Installation Fallbacks

If the skill is not installed but the repo is present, run scripts relative to the repo root and follow this `SKILL.md` directly. If only a copied `SKILL.md` is available without `scripts/` and `references/`, do a provisional report and state that bundled resources are missing.

If the target skill is outside the writable workspace, evaluate read-only files normally. Do not attempt to copy, install, or rewrite the target unless the user asks for edits.

If multiple skill directories match the user request, choose the directory whose folder name matches the requested skill name. If ambiguity remains, ask for the exact path.

## Reporting Fallbacks

When fallback mode is used, include:

- fallback reason
- checks that ran normally
- checks marked `na`
- residual risk
- the smallest next step to restore deterministic evaluation

If only the report renderer fails but findings are available, render the report manually with the same ordering: failed `BLOCKER`, failed `MAJOR`, failed `MINOR`, then section summary.

## Hardening Queue

Prefer these follow-up tasks when the user asks for the next reliability pass:

1. Add an install smoke test that copies the skill to a temporary skill directory and runs the wrapper from that location.
2. Add fixtures for multiline frontmatter lists, metadata maps, non-UTF-8 bytes, symlinked resources, and missing `SKILL.md`.
3. Add a machine-readable `--provisional` report mode for manual fallback findings.
4. Add a small compatibility matrix for macOS, Linux, Windows launcher behavior, and Codex desktop bundled runtimes.
5. Add a release checklist that runs unit tests, dogfood rule checks, quick validation, and one intentionally failing fixture.
