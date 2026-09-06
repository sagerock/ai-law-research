# Structured Brief Model Pilot

Run date: September 6, 2026

## Outcome

Tortwell has working Anthropic and OpenAI API credentials. The account can call
`claude-opus-5`, `claude-fable-5-1`, and `gpt-5.6-sol`. No Gemini or Google API
credential is configured, so Gemini was not included.

Three models generated one source-linked brief for each of three cases using the
production prompt, production source-packet selection, and production deterministic
validator. The candidates were kept local and were not written to Tortwell.

| Model | Valid | Average words | Average latency | Estimated candidate cost |
|---|---:|---:|---:|---:|
| `gpt-5.6-sol` | 3/3 | 613 | 43.0 s | $0.422 |
| `claude-fable-5-1` | 2/3 | 754 | 55.0 s | $1.459 |
| `claude-opus-5` | 1/3 | 860 | 58.1 s | $0.745 |

Cost estimates use the per-token assumptions recorded in the evaluator. They cover
the nine retained candidates, excluding truncated attempts, retries, and judging.
They should be refreshed against provider pricing before a larger run.

## Cases

| Case | Tortwell ID | Stress condition |
|---|---:|---|
| Poe v. Ullman | 106282 | Four-Justice plurality, concurrence, and multiple dissents |
| Abbott Laboratories v. Gardner | 107451 | Single lead opinion and pre-enforcement ripeness analysis |
| Regional Rail Reorganization Act Cases | 109117 | Long majority and dissent with several constitutional issues |

## Deterministic validation

`gpt-5.6-sol` was the only model to pass all three first-pass production validations.
Fable exceeded the 800-word maximum by three words on Poe. Opus exceeded the limit
on Poe and Regional Rail, and its Poe candidate also attached a non-dissent passage
to a dissent claim.

The first evaluator version allowed only 4,000 Claude output tokens. Three responses
ended mid-JSON. Those provider-limit failures were rerun with an 8,000-token limit;
the substantive and word-count failures above are from complete responses.

## Blind semantic review

Two models independently judged shuffled, anonymous candidates against the supplied
opinion passages. Each scored legal accuracy, claim-to-passage support, opinion
attribution, writing, and teaching value from 1 to 5.

| Candidate model | OpenAI judge | Anthropic judge | Combined mean |
|---|---:|---:|---:|
| `gpt-5.6-sol` | 4.47 | 4.07 | 4.27 |
| `claude-opus-5` | 3.80 | 4.73 | 4.27 |
| `claude-fable-5-1` | 3.87 | 4.47 | 4.17 |

The OpenAI judge ranked the OpenAI candidate first in all three cases. The Anthropic
judge ranked an Anthropic candidate first in all three and ranked the OpenAI
candidate last in all three. Every candidate model therefore had the same combined
average rank of 2.0. The provider-correlated disagreement is too strong to treat
either automated judge as an objective winner.

The judges did agree on useful defects:

- All three Poe briefs presented Frankfurter's plurality analysis under
  `majority_reasoning` and omitted the separate concurrence that supplied the fifth
  vote for dismissal.
- Several claims cited real but incomplete passages. The IDs existed and had the
  expected opinion part, yet the cited text supported only part of the claim.
- The Claude candidates generally preserved more procedural and separate-opinion
  detail, but that detail increased length and citation mismatches.
- The GPT candidates were more concise and consistently satisfied the current
  schema, but sometimes omitted procedural or separate-opinion detail.
- Uncited significance paragraphs sometimes asserted later doctrinal influence that
  the supplied opinion itself cannot establish.

## Recommendation

Use `gpt-5.6-sol` as the leading candidate for a larger shadow test because it was
the only model with 3/3 deployable outputs and was fastest and least expensive under
the evaluator's assumptions. This pilot does not show a meaningful semantic-quality
lead over Opus; the two-judge aggregate is effectively tied.

Before changing production, run 20–30 varied cases with human legal review. Improve
the brief schema and prompt first so plurality and concurrence reasoning can be
represented explicitly, and add claim-to-source entailment review rather than only
checking that source IDs and opinion parts exist. A Gemini key would enable a useful
third-provider generator and judge, especially because the two current judges show
clear provider preference.

## Reproduction

Generate candidates without writing to Tortwell:

```bash
.venv/bin/python scripts/eval_structured_brief_models.py \
  --output tmp/model-evals
```

Run a blind source-grounded judge:

```bash
.venv/bin/python scripts/judge_structured_brief_models.py \
  --input tmp/model-evals \
  --judge-model gpt-6-astra
```

Both scripts load credentials from the local `.env`, print no secret values, and
write their artifacts beneath the selected local output directory.

## Limits

This is a three-case, one-sample-per-model pilot. Generation used the same prompt for
all models and no corrective retry after a complete response. Automated semantic
judges are useful for finding review targets, but their provider preference in this
run makes human review necessary for a production decision.
