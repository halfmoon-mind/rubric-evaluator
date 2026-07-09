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
