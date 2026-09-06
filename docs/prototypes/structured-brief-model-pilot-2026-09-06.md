# Structured Brief Model Pilot

Run date: September 6, 2026

## Outcome

Tortwell has working Anthropic, OpenAI, and Google Gemini API credentials. The
tested models were `claude-opus-5`, `claude-fable-5-1`, `gpt-5.6-sol`, and
`gemini-3.8-flash`.

Four models generated one source-linked brief for each of three cases using the
production prompt, production source-packet selection, and production deterministic
validator. The candidates were kept local and were not written to Tortwell.

| Model | Valid | Average words | Average latency | Estimated candidate cost |
|---|---:|---:|---:|---:|
| `gemini-3.8-flash` | 3/3 | 625 | 13.3 s | Not calculated |
| `gpt-5.6-sol` | 3/3 | 613 | 43.0 s | $0.422 |
| `claude-fable-5-1` | 2/3 | 754 | 55.0 s | $1.459 |
| `claude-opus-5` | 1/3 | 860 | 58.1 s | $0.745 |

Cost estimates use the per-token assumptions recorded in the evaluator. They cover
the retained non-Gemini candidates, excluding truncated attempts, retries, and judging.
They should be refreshed against provider pricing before a larger run.

## Cases

| Case | Tortwell ID | Stress condition |
|---|---:|---|
| Poe v. Ullman | 106282 | Four-Justice plurality, concurrence, and multiple dissents |
| Abbott Laboratories v. Gardner | 107451 | Single lead opinion and pre-enforcement ripeness analysis |
| Regional Rail Reorganization Act Cases | 109117 | Long majority and dissent with several constitutional issues |

## Deterministic validation

`gpt-5.6-sol` and `gemini-3.8-flash` passed all three production validations. Fable
exceeded the 800-word maximum by three words on Poe. Opus exceeded the limit on Poe
and Regional Rail, and its Poe candidate also attached a non-dissent passage to a
dissent claim.

The first evaluator version allowed only 4,000 Claude output tokens. Three responses
ended mid-JSON. Those provider-limit failures were rerun with an 8,000-token limit;
the substantive and word-count failures above are from complete responses. Gemini's
first Poe attempt also exhausted an 8,000-token allowance because Google counts
internal thinking toward that limit. It produced a valid candidate with a
16,000-token allowance. The evaluator now exposes `--max-output-tokens` for this.

## Blind semantic review

Three provider models independently judged shuffled, anonymous candidates against
the supplied opinion passages. Each scored legal accuracy, claim-to-passage support,
opinion attribution, writing, and teaching value from 1 to 5.

| Candidate model | OpenAI judge | Anthropic judge | Gemini judge | Combined | Mean rank |
|---|---:|---:|---:|---:|---:|
| `claude-opus-5` | 4.00 | 4.73 | 4.80 | 4.51 | 1.56 |
| `claude-fable-5-1` | 4.00 | 4.67 | 4.53 | 4.40 | 2.11 |
| `gpt-5.6-sol` | 4.47 | 4.40 | 4.00 | 4.29 | 2.44 |
| `gemini-3.8-flash` | 3.40 | 3.53 | 3.60 | 3.51 | 3.89 |

Opus won five of the nine case-judge rankings. Fable and GPT each won two. Gemini won
none. The OpenAI judge still favored GPT on two cases, but both the Anthropic and
Gemini judges favored an Anthropic candidate on every case. Gemini did not favor its
own candidates, which makes its review a useful independent check on the original
two-provider disagreement.

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
- The Gemini candidates were exceptionally fast and concise, but frequently attached
  too few passages to compound claims. The Abbott brief had pervasive citation gaps;
  the Poe and Regional Rail briefs omitted important procedural or opinion details.
- Uncited significance paragraphs sometimes asserted later doctrinal influence that
  the supplied opinion itself cannot establish.

## Recommendation

Use `claude-opus-5` as the leading quality candidate and `gpt-5.6-sol` as the leading
single-pass reliability candidate for a larger shadow test. Opus produced the most
complete briefs and led the three-judge semantic review, but it needs a deterministic
correction pass to enforce length and opinion-part citations. GPT was the only model
to combine strong semantic scores with 3/3 validation under the standard 8,000-token
allowance.

Gemini 3.8 Flash was by far the fastest and did pass all three validations with a
provider-appropriate output allowance. Its citation support and completeness were
materially weaker under the current prompt, so this pilot does not support using it
as Tortwell's primary brief writer. It may be useful as a fast independent semantic
reviewer.

Before changing production, run 20–30 varied cases with human legal review. Improve
the brief schema and prompt first so plurality and concurrence reasoning can be
represented explicitly, and add claim-to-source entailment review rather than only
checking that source IDs and opinion parts exist.

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

Generate a Gemini candidate with enough room for thinking tokens:

```bash
.venv/bin/python scripts/eval_structured_brief_models.py \
  --models gemini-3.8-flash \
  --max-output-tokens 16000 \
  --output tmp/model-evals-gemini
```

Both scripts load credentials from the local `.env`, print no secret values, and
write their artifacts beneath the selected local output directory.

## Limits

This is a three-case, one-sample-per-model pilot. Generation used the same prompt for
all models and no corrective retry after a complete response. Automated semantic
judges are useful for finding review targets, but the sample remains too small for a
production decision without human review.
