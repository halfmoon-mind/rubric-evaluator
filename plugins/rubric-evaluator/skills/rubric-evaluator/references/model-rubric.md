# Model Rubric for Skill Evaluation

Use this file after deterministic rule checks have run. Create exactly 14 model findings with the same schema as rule findings. Do not re-judge deterministic failures; use rule output as context and focus on semantic quality.

## Table of Contents

- [Finding Format](#finding-format)
- [General Judgment Rules](#general-judgment-rules)
- [1.1 Repeated Workflow](#11-repeated-workflow)
- [1.2 General Applicability](#12-general-applicability)
- [1.3 Beyond Default Agent Ability](#13-beyond-default-agent-ability)
- [3.1 Description Has What and When](#31-description-has-what-and-when)
- [3.2 Trigger Keywords Are Sufficient](#32-trigger-keywords-are-sufficient)
- [3.3 Description and Body Match](#33-description-and-body-match)
- [3.4 No Body-Only Trigger](#34-no-body-only-trigger)
- [3.5 Trigger Scope Is Not Too Broad](#35-trigger-scope-is-not-too-broad)
- [3.7 Trigger Simulation Passes](#37-trigger-simulation-passes)
- [4.1 Concrete Detail Exists](#41-concrete-detail-exists)
- [4.2 Not Merely Basic Agent Advice](#42-not-merely-basic-agent-advice)
- [5.1 Core in SKILL, Details Split Out](#51-core-in-skill-details-split-out)
- [5.2 Reference Load Conditions Are Clear](#52-reference-load-conditions-are-clear)
- [5.5 Fixed Error-Prone Work Uses Scripts](#55-fixed-error-prone-work-uses-scripts)
- [Final Consistency Pass](#final-consistency-pass)

## Finding Format

Each model finding must use:

```json
{
  "id": "3.1",
  "section": "trigger",
  "item": "description includes what and when",
  "severity": "MAJOR",
  "status": "pass",
  "checker": "model",
  "why": "",
  "how_to_fix": ""
}
```

For `pass`, keep `why` and `how_to_fix` empty unless the user requests a full audit trail. For `fail`, both fields must be specific and actionable.

## General Judgment Rules

Judge the skill as an onboarding guide for another Codex instance. A skill is strong when it provides trigger clarity, reusable procedures, and bundled resources that reduce repeated reasoning errors.

Use `na` only when the target lacks enough readable material because a prerequisite rule failure prevents semantic judgment. A parsing failure in frontmatter should not make every model item fail by itself.

Prefer concrete evidence over tone. Quote short phrases only when needed; otherwise paraphrase. Do not fail a skill for being concise if it gives enough operational direction.

## 1.1 Repeated Workflow

Severity: `MAJOR`

Question: Does the skill support a workflow that a user or agent would repeat across tasks?

Pass when the skill guides recurring work such as auditing many skill folders, processing a file type, preparing a repeated report, or operating a domain workflow with stable steps.

Fail when the body is tied to a single one-off request, one temporary migration, one named local branch, or a personal errand unlikely to recur.

False-positive guard: A skill can be narrow and still pass if the narrow task repeats.

Good evidence: "Evaluate any skill directory, run rule checks, apply semantic rubric, render report."

Bad evidence: "Fix the current broken migration in this repository."

Fail wording: Explain why the task is one-off, then suggest rewriting the skill around the reusable workflow behind it.

## 1.2 General Applicability

Severity: `MAJOR`

Question: Can the skill apply beyond one private artifact, person, meeting, or repository?

Pass when the procedure can be reused for a class of similar targets, even if it has a clear domain.

Fail when it depends on a single local path, a unique internal event, a single individual, or undocumented context that another agent cannot reasonably obtain.

False-positive guard: Organization-specific skills may pass when the organization context is the intended recurring domain and the required context is bundled or discoverable.

Good evidence: "Use on any Codex skill folder containing SKILL.md."

Bad evidence: "Only use for Sanghyeon's June 9 draft file."

Fail wording: Name the overly specific dependency and describe how to generalize the input contract.

## 1.3 Beyond Default Agent Ability

Severity: `MAJOR`

Question: Does the skill add procedural knowledge, deterministic resources, or domain criteria that a general agent would not reliably reconstruct?

Pass when it includes a stable rubric, scripts, schemas, edge cases, examples, or domain rules.

Fail when it only says generic advice such as "read files carefully", "write clean code", or "ask clarifying questions".

False-positive guard: A short skill can pass if it encodes a non-obvious decision tree or strict validation process.

Good evidence: "17 rule checks, 14 model checks, fixed grade thresholds."

Bad evidence: "Be helpful and concise when reviewing skills."

Fail wording: Identify the generic content and ask for the missing specialized workflow or resource.

## 3.1 Description Has What and When

Severity: `MAJOR`

Question: Can the frontmatter description alone tell an agent what the skill does and when it should trigger?

Pass when the description contains both capability and invocation context.

Fail when it only names the domain, only lists a value proposition, or pushes trigger conditions into the body.

False-positive guard: The wording need not contain the literal words "what" or "when"; judge meaning.

Good evidence: "Evaluate skill folders with rubric checks; use when asked to grade, audit, review, or improve a skill."

Bad evidence: "A skill quality helper."

Fail wording: State which half is missing and provide a one-sentence replacement pattern.

## 3.2 Trigger Keywords Are Sufficient

Severity: `MAJOR`

Question: Would likely user wording match the description?

Pass when the description includes natural trigger phrases, task names, object names, and close synonyms.

Fail when likely prompts would not discover the skill because the description is too sparse or uses only internal jargon.

False-positive guard: Do not require every synonym. Require enough coverage for common requests.

Good evidence: "grade, audit, review, dogfood, improve, skill directory, SKILL.md, rubric score."

Bad evidence: "quality framework assistant."

Fail wording: List missing user-facing trigger phrases and suggest adding them to the description.

## 3.3 Description and Body Match

Severity: `MAJOR`

Question: Does the body implement the same scope promised by the description?

Pass when the body's workflow, resources, and output match the frontmatter capability.

Fail when the description promises a broad tool but the body covers another task, or the body omits the promised capability.

False-positive guard: The body can be more detailed than the description, but it must not contradict it.

Good evidence: Description promises skill grading; body runs rule checks, applies model rubric, and renders the grade.

Bad evidence: Description promises spreadsheet analysis; body only explains prompt writing.

Fail wording: Name the mismatch and say whether to narrow the description or expand the body.

## 3.4 No Body-Only Trigger

Severity: `BLOCKER`

Question: Are all essential invocation conditions present in the description rather than only in the body?

Pass when the description includes the contexts that should cause the skill to load.

Fail when the body has a "use this when..." style trigger list that is absent from the description.

False-positive guard: Operational preconditions may live in the body. Trigger conditions that determine skill discovery must live in the description.

Good evidence: Trigger phrases are in frontmatter and the body only explains workflow.

Bad evidence: Description says "Skill helper"; body says "Use when asked to audit SKILL.md."

Fail wording: Explain that body text is invisible until after triggering, then provide the missing trigger phrase.

## 3.5 Trigger Scope Is Not Too Broad

Severity: `MAJOR`

Question: Would the description avoid loading this skill for unrelated tasks?

Pass when it names a clear target object and task.

Fail when it uses broad claims such as "all coding tasks", "any documentation", or "quality improvement" without boundaries.

False-positive guard: A broad domain can pass when the description still identifies concrete file types, workflows, or outputs.

Good evidence: "Codex skill folders that contain SKILL.md."

Bad evidence: "Use for any review, audit, or quality task."

Fail wording: Identify the overbroad phrase and replace it with narrower target nouns and actions.

## 3.7 Trigger Simulation Passes

Severity: `MAJOR`

Question: Would the description alone actually load this skill for prompts a real user would type?

Method: Before judging, write 5 short user prompts — 3 that should trigger the skill and 2 adjacent prompts that should not. Judge each prompt against the frontmatter description only, never the body, since only the description is visible before triggering.

Pass when all 3 should-trigger prompts plausibly match the description and neither should-not prompt does.

Fail when any should-trigger prompt finds nothing to match, or a should-not prompt would load the skill.

False-positive guard: Judge matching by meaning, not exact word overlap; a close synonym in the description counts as a match.

Good evidence: Prompt "audit my skill folder" matches "audit" and "skill directory" in the description.

Bad evidence: The description only says "quality framework assistant", so the prompt "grade ./my-skill" finds nothing to match.

Fail wording: List the missed prompts (or the wrongly matched ones) and the description phrase to add or remove.

## 4.1 Concrete Detail Exists

Severity: `MINOR`

Question: Does the skill include at least one concrete detail such as numbers, commands, schemas, edge cases, or examples?

Pass when a reader can find operational specifics.

Fail when all guidance is abstract.

False-positive guard: One strong command, threshold, or schema is enough.

Good evidence: Grade thresholds, exact script commands, finding schema fields.

Bad evidence: "Assess quality and provide helpful suggestions."

Fail wording: Ask for concrete thresholds, commands, schemas, or examples.

## 4.2 Not Merely Basic Agent Advice

Severity: `MAJOR`

Question: Is most content specific to the skill's domain rather than common agent behavior?

Pass when domain criteria and workflow-specific procedures dominate.

Fail when most lines repeat general coding-agent norms with no target-specific rubric, resources, or examples.

False-positive guard: General process language is acceptable around specialized steps.

Good evidence: A named 31-item rubric with deterministic and semantic checks.

Bad evidence: "Read the code, think carefully, make a plan, run tests."

Fail wording: Identify the generic material and request domain-specific rules or reusable resources.

## 5.1 Core in SKILL, Details Split Out

Severity: `MAJOR`

Question: Is SKILL.md a concise orchestrator while detailed criteria live in load-on-demand resources?

Pass when SKILL.md explains the workflow and points to bundled details only when needed.

Fail when SKILL.md is overloaded with long tables, many examples, or large reference material that should be split out.

False-positive guard: SKILL.md may include a compact schema and essential command list.

Good evidence: SKILL.md has workflow; this file has item-level semantic criteria.

Bad evidence: SKILL.md contains every example, every long rule table, and implementation commentary.

Fail wording: Name what should move out and state the condition for loading it.

## 5.2 Reference Load Conditions Are Clear

Severity: `MINOR`

Question: When SKILL.md names a bundled reference, does it say when to read it?

Pass when each reference has a condition such as "read after rule checks" or "read for model findings."

Fail when references are listed without guidance about relevance.

False-positive guard: A single always-needed reference can pass if SKILL.md says to read it at the right workflow step.

Good evidence: "Read model-rubric after rule output is available."

Bad evidence: "See model-rubric."

Fail wording: Add the missing load condition next to the reference path in SKILL.md.

## 5.5 Fixed Error-Prone Work Uses Scripts

Severity: `MAJOR`

Question: Are deterministic, repetitive, or fragile operations delegated to scripts instead of natural-language recreation?

Pass when parsing, regex checks, grading, rendering, conversion, or other fixed work has a script.

Fail when the skill asks the agent to manually repeat precise scans, counts, or schema transforms that are easy to get wrong.

False-positive guard: Not every skill needs scripts. Pass if no fixed fragile operation exists.

Good evidence: Python scripts parse frontmatter, run syntax checks, detect safety issues, and render reports.

Bad evidence: "Manually count body lines and inspect every file for patterns."

Fail wording: Identify the fragile repeated operation and propose a small deterministic script.

## Final Consistency Pass

After writing 14 model findings, verify:

- exactly 14 model findings exist
- IDs are 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 4.1, 4.2, 5.1, 5.2, 5.5
- every finding has `checker: "model"`
- each failed finding has both `why` and `how_to_fix`
- the combined grade follows the fixed grade thresholds
