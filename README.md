# Rubric Evaluator

![Rubric Evaluator project image](assets/project-image.png)

Grade a skill directory (one that contains a `SKILL.md`) against a 6-section,
31-item rubric. Deterministic structural and safety checks run as a stdlib-only
Python script; semantic checks are applied from a bundled rubric reference. The
headline grade (S/A/B/C/F) is computed deterministically, never eyeballed.

The rubric is based on Toss Tech's article
[Skill 품질 관리를 위한 Rubric 설계와 시스템 구현](https://toss.tech/article/skill-quality-rubric).

The same skill bundle ships for two hosts from one source of truth at
`plugins/rubric-evaluator/`:

- **Claude Code** — `.claude-plugin/plugin.json` + the marketplace at the repo root
- **Codex** — `.codex-plugin/plugin.json` + `.agents/plugins/marketplace.json`

## Install (Claude Code)

```
/plugin marketplace add halfmoon-mind/rubric-evaluator
/plugin install rubric-evaluator@rubric-evaluator
```

Then ask Claude to evaluate a skill, e.g. *"grade the skill directory at ./my-skill"*.

To try it without installing (single session, from a local checkout):

```
claude --plugin-dir ./plugins/rubric-evaluator
```

## Install (Codex)

Add this repository as a Codex marketplace source, then install the plugin:

```
codex plugin marketplace add halfmoon-mind/rubric-evaluator
codex plugin add rubric-evaluator@rubric-evaluator
```

To install from a local checkout instead, add the repo root as the local
marketplace source:

```
codex plugin marketplace add .
codex plugin add rubric-evaluator@rubric-evaluator
```

Start a new Codex thread after installing, then ask Codex to evaluate a skill,
e.g. *"Use $rubric-evaluator to grade the skill directory at ./my-skill"*.

## Usage

Point the skill at any directory that contains a `SKILL.md`. There is nothing
to run by hand — describe what you want in natural language and the skill
triggers on requests to grade, audit, review, dogfood, or improve a skill.

Example prompts:

- *"Grade the skill directory at ./my-skill"*
- *"Audit the SKILL.md in ./plugins/foo/skills/foo and tell me what to fix"*
- *"Review ./my-skill against the rubric"*

On Codex, prefix with the plugin handle, e.g. *"Use $rubric-evaluator to grade
./my-skill"*.

To try it against a bundled example, point it at one of the test fixtures:

- *"Grade tests/rubric-evaluator/fixtures/clean"* — a well-formed skill, grades **S**
- *"Grade tests/rubric-evaluator/fixtures/secret-leak"* — trips a safety `BLOCKER`, grades **F**

Behind the scenes the skill runs the deterministic checks, applies the semantic
model checks, computes the grade, and returns a report (see
[What you get](#what-you-get)).

## What you get

A grade plus a per-item report. For every failing item it states why it matters
and how to fix it:

- `BLOCKER` ≥ 1 → **F**
- no `BLOCKER`, 0 `MAJOR` → **S** · 1–2 → **A** · 3–4 → **B** · 5+ → **C**
- `MINOR` items are advisory and never change the grade

## Automation

The commands below use the bundled scripts directly from a checkout. No extra
Python packages are required.

```bash
# Rule checks with a CI gate (BLOCKER or MAJOR failures exit 1).
python3 plugins/rubric-evaluator/skills/rubric-evaluator/scripts/check_rules.py ./my-skill --fail-on major

# Evaluate all skills under a directory and render a summary table.
python3 plugins/rubric-evaluator/skills/rubric-evaluator/scripts/check_rules.py ./skills --batch > /tmp/batch.json
python3 plugins/rubric-evaluator/skills/rubric-evaluator/scripts/render_report.py /tmp/batch.json

# Compare saved evaluations; add --json for structured output.
python3 plugins/rubric-evaluator/skills/rubric-evaluator/scripts/compare_results.py /tmp/before.json /tmp/after.json

# Validate combined rule + model findings and refresh the saved grade/coverage.
python3 plugins/rubric-evaluator/skills/rubric-evaluator/scripts/check_rules.py /tmp/combined.json --finalize --require-complete > /tmp/final.json
```

Rule-only grades are **provisional**: they cover 17 of the 31 checks. Reports
show missing and unresolved (`na`) checks instead of marking them PASS. Full
evaluation requires all 31 checks with no `na`; completion does not imply a
passing grade. Empty findings, duplicate or unknown IDs, incorrect severities,
and malformed fields are rejected.

Results include rubric version/hash and target hash. Preserve these fields
when adding semantic findings; finalization recalculates grade and coverage.
Save reports outside the target directory to avoid changing its hash.
Legacy finding arrays remain readable when every finding has the full schema.

Comparisons distinguish resolved, introduced, persistent, unverified, and
newly observed failures. A missing check never counts as a resolved issue.
Changed rubric metadata and partial coverage are reported alongside grades.

Exit codes are **0** for success, **1** for an unmet quality gate, and **2** for
invalid input. `--fail-on blocker|major|minor` includes higher severities;
`--require-complete` also rejects partial evaluation. Without gate flags,
valid evaluation continues to exit 0 regardless of findings.

## Develop / test

The checker is stdlib-only (no install step). Run the test suite with:

```
python3 -m unittest discover -s tests/rubric-evaluator -p "test_*.py"
```

GitHub Actions runs the suite on Linux, macOS, and Windows with Python 3.10,
3.13, and 3.14, including Unicode/space paths, UTF-8 BOM input, deterministic
hash ordering, and plugin manifest/version/path consistency checks. Semantic
model judgments require separate calibration; see
[the test guide](tests/rubric-evaluator/README.md) for repeated-run metrics.

Python 3.10+ is supported. On Windows PowerShell or Command Prompt without a
POSIX shell, run the Python scripts directly (`python` or `py -3`); the shell
wrapper requires `sh`, such as Git Bash. Shell syntax checks require Bash;
if it is missing, check 5.6 is unresolved (`na`) instead of passing. Python
checks still run. CLI output is UTF-8; saved JSON may include a UTF-8 BOM.
Use PowerShell 7+ for the redirection examples (Windows PowerShell 5.1 can
write UTF-16 files, which this tool does not accept). Repository text files
use LF on checkout to keep shell scripts and evaluator hashes consistent.

## License

[MIT](LICENSE)
