# Test Suite

`test_check_rules.py` and `test_fixtures.py` cover the deterministic rule
checks. Run them with `python3 tests/rubric-evaluator/test_<name>.py`.

## Model-check calibration

The 14 semantic checks in `references/model-rubric.md` are applied by the
evaluating model, so they cannot run under unittest. Calibrate them against
fixtures that carry an `expected-model.json` (a map of finding ID to expected
status; only listed IDs are asserted):

- `fixtures/model-strong` — a well-built skill; the listed checks must pass
- `fixtures/body-only-trigger` — trigger text only in the body; 3.1, 3.4, 3.7 must fail
- `fixtures/generic-advice` — generic agent advice; 1.3, 4.1, 4.2 must fail
- `fixtures/operational-precondition` — required input columns in the body must not be mistaken for a body-only invocation trigger
- `fixtures/overbroad-trigger` — an unrestricted description paired with a narrow workflow must fail scope and matching checks

Calibration loop:

1. Ask the agent to grade the fixture with the rubric-evaluator skill and save
   the combined findings JSON.
2. Compare against expectations:

   ```bash
   python3 tests/rubric-evaluator/compare_model_findings.py <findings.json> tests/rubric-evaluator/fixtures/<name>
   ```

3. A non-zero exit lists each miscalibrated check. Fix the rubric wording in
   `references/model-rubric.md` (not the fixture) unless the fixture itself is
   ambiguous.

Run the loop after any edit to `model-rubric.md` and before a release.

For repeated evaluations of the **same fixture**, add each run with `--repeat`:

```bash
python3 tests/rubric-evaluator/compare_model_findings.py /tmp/run1.json tests/rubric-evaluator/fixtures/model-strong --repeat /tmp/run2.json --repeat /tmp/run3.json
```

The JSON summary reports accuracy against asserted expectations, pairwise
status agreement across runs, false positives (`pass` expected, `fail`
observed), false negatives (`fail` expected, `pass` observed), missing checks,
and total mismatches. Missing and `na` answers do not silently become passes.
Missing checks do not count as agreement; repeated `na` judgments agree but
still count as mismatches against pass/fail expectations. Any mismatch exits 1.

Record the model identifier and settings alongside each run when collecting
results. Keep the fixture and rubric unchanged across a repeated-run comparison.
The comparator consumes saved outputs; it does not call a model. Unit tests
verify metric calculations and fixture presence, not semantic model accuracy.

## Result and packaging regression tests

`test_results.py` covers schema rejection, coverage reporting, content hashes,
quality gates, comparisons, batch rendering, and CLI exit codes.
`test_packaging.py` checks both marketplace paths, bundled assets, and shared
plugin metadata. All tests run through the unittest discovery command in the
repository README and the CI operating-system/Python matrix.
