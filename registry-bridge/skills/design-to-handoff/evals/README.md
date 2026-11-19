# design-to-handoff evals

Layer 1 of the bridge evals: XStack's files in, a `service-handoff.yaml` out, graded against a hand-written ground truth. In the style of `skills/form-to-spec/evals/`.

| Eval | Service | Prototype | Level | Ground truth |
|---|---|---|---|---|
| 1 | Household Support Grant (Kestria, a fictional country) | `prototype-1-once-only`, iteration 4 | alpha | `registry-bridge/pilots/household-support-grant/service-handoff.yaml` |

## Files

- `evals.json`: prompts, expected output, and the ground truth for each eval
- `grade.py`: the scripted checks. It validates the file against the contract, then compares it with the ground truth: level, prototype and iteration, missing parts, question coverage (matched by attribute key, then form controls, then id), known, derived or ask, attribute keys, no keys outside the profile's data catalogue, tags kept, form controls, fallbacks, page order, branches, what each page asks and shows, back-office rows, open items, gap status and unresolved rows.

Labels, notes and the wording of open items are not scored. They need a person or a grader agent.

## Running them

Run the prompt in `evals.json` from the repo root, with the skill, saving `service-handoff.yaml`. Then:

```bash
uv run registry-bridge/skills/design-to-handoff/evals/grade.py path/to/service-handoff.yaml --eval-id 1
```

`uv` installs `jsonschema` and `pyyaml` from the script header. The grader's own tests are in `registry-bridge/tests/`.

## Results: iteration 1 (2026-11-19)

One run, by the same agent that wrote the ground truth and the skill, so it is not independent. Treat it as a check that the skill and grader work together, not as a measure of quality.

| | With skill |
|---|---|
| Valid on first write | No: 5 YAML errors (`yes` and `no` read as booleans, unquoted commas). Fixed in the skill's validate loop. |
| Scripted checks (18) | 13 / 18 (72%) |

What failed, and why:

- **Coverage, form controls, page asks:** the skill said a known fact's controls include those on its fallback pages. So "How many people live in your household?" and "How should we pay you?" were folded into `household` and `payout-account`, where the ground truth has them as their own ask rows.
- **Tags, unresolved:** the skill said to read the shared question map only when the iteration has none. The iteration's map has no tags and no nearest Citizen Service Centre row, so `[VERIFY WITH DATA]` on the address and the unresolved nearest-CSC row were lost.
- **Not failed but noted:** one back-office row of ten was missed (switching from another programme), and gap 13 was marked `designed` where the ground truth says `default`. Both are within the thresholds.

The skill was changed after this run: fallback questions are their own ask rows, both question maps are read, and a note on YAML quoting was added. **The changed skill has not been re-measured.** The next run should be by an agent that has not seen the ground truth, and a no-skill baseline is still to do.
