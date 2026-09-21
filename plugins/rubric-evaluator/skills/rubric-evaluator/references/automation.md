# Evaluation automation

Run these commands from the installed skill's directory. Save output outside
the evaluated skill directory so report files do not change its target hash.

## Validated results and coverage

```bash
python3 scripts/check_rules.py /path/to/my-skill > /tmp/rules.json
python3 scripts/check_rules.py /tmp/combined.json --finalize > /tmp/final.json
python3 scripts/render_report.py /tmp/final.json --skill-name my-skill
```

Create `combined.json` by adding the 14 semantic findings to the rule result's
`findings` array, retaining its provenance. Resolve a rule 6.1 `na` in place
after reviewing the suspected credential. Finalization validates the findings
and recomputes `grade` and `coverage`; it does not run semantic evaluation.

Every finding requires the eight string fields documented in SKILL.md. IDs,
sections, severities, and checker ownership must match the rubric. Failed
findings need a reason and a fix; `na` needs a reason. Unknown IDs, duplicate
IDs, empty arrays, and invalid field values are rejected.

Missing IDs are allowed for partial evaluations. `coverage.status` is
`complete` only when all 31 checks are present and none is `na`. Grades on
partial results reflect only supplied findings and remain provisional.
Legacy arrays are accepted when findings have the full schema, but their
provenance is unknown. Finalization never invents provenance for older data.

## Compare evaluations

```bash
python3 scripts/compare_results.py /tmp/before.json /tmp/after.json
python3 scripts/compare_results.py /tmp/before.json /tmp/after.json --json
```

Compare the same logical skill before and after editing. Resolved means
`fail -> pass`; introduced means `pass -> fail`. A failure that becomes
missing or `na` is unverified. A failure with no previous pass/fail judgment
is newly observed. Persistent failures appear separately.

Grades are recomputed, not trusted from the saved `grade` field. Partial
coverage and differing or absent rubric metadata produce comparison notes.

## Batch evaluation and CI

```bash
python3 scripts/check_rules.py /path/to/skills --batch > /tmp/batch.json
python3 scripts/render_report.py /tmp/batch.json
python3 scripts/check_rules.py /path/to/my-skill --fail-on major
python3 scripts/check_rules.py /tmp/final.json --grade --fail-on major --require-complete
```

Batch mode finds SKILL.md recursively, skipping hidden paths, and emits a
`results` array. Each result includes its target, findings, grade, coverage,
and provenance. The renderer produces a summary table. An empty search or
unreadable target is an input error; the batch does not silently skip it.

`--fail-on blocker|major|minor` fails at that severity or higher. Without a
gate, findings do not change the successful exit code. `--require-complete`
fails for missing or `na` checks, so rule-only scans always fail this gate.
It can be combined with `--grade` or `--finalize` on combined results.

Exit codes: 0 = valid execution and gates passed; 1 = a quality gate failed;
2 = invalid input or usage. Gate failures still emit the result. A complete
report only means all checks were judged; it does not mean they all passed.

## Provenance

`schema_version` identifies the result format. `rubric_version` identifies
the criteria version; bump it when criteria or grade policy change.
`rubric_hash` hashes the bundled evaluator directory so implementation and
instruction edits are visible even without a version bump. `target_hash`
hashes the evaluated directory. Hashes include relative file names and file
contents, excluding `.git`, `__pycache__`, `.pytest_cache`, `.pyc`, and `.pyo`.
They exclude timestamps and the directory's absolute location.

Provenance records a snapshot, not an authenticity guarantee. Keep it intact
when adding model findings and rerun evaluation if the target changes.
