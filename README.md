# Rubric Evaluator

Grade a skill directory (one that contains a `SKILL.md`) against a 6-section,
30-item rubric. Deterministic structural and safety checks run as a stdlib-only
Python script; semantic checks are applied from a bundled rubric reference. The
headline grade (S/A/B/C/F) is computed deterministically, never eyeballed.

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
