# Model Rubric — 13 semantic checks

Apply these by reading the target skill's `SKILL.md`, `references/`, and `scripts/`.
Emit one finding per item using the shared schema (see SKILL.md). `checker` is always
`"model"`. Use `na` when the item genuinely does not apply, never to avoid judgment.
Set each finding's `section` to the script's canonical token for that item — `validity` (§1), `trigger` (§3), `content` (§4), `resource` (§5) — matching the rule findings' `section` values, not the plural section headings.

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
