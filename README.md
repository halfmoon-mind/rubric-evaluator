# Rubric Evaluator

![Rubric Evaluator project image](assets/project-image.png)

Grade a skill directory (one that contains a `SKILL.md`) against a 6-section,
30-item rubric. Deterministic structural and safety checks run as a stdlib-only
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

## Develop / test

The checker is stdlib-only (no install step). Run the test suite with:

```
python3 -m unittest discover -s tests/rubric-evaluator -p "test_*.py"
```
