# TriageBench v0.2

**Status:** Public development benchmark

**Capability:** Sequential UK clinical-triage decisions

**Contact:** [labs@logarith.ms](mailto:labs@logarith.ms)

## The question

Can a model use the conversation so far to choose the next doctor-authored clinical action?

Each task presents a partial patient conversation and four plausible actions. Depending on the evidence already collected, the best action may be another question or an assessment route. The model returns one option ID.

TriageBench is not a diagnosis exam and a benchmark score is not evidence that a model is ready for patient care.

## Public task set

| Item | Count |
| --- | ---: |
| Tasks | 100 |
| Ask-another-question decisions | 50 |
| Stop-and-assess decisions | 50 |
| Next-question selection tasks | 40 |
| Assessment selection tasks | 40 |
| Stop-or-continue tasks | 20 |
| Matched stop-or-continue pairs | 10 |
| Options per task | 4 |

The development set covers nine UK clinical pathway families. Correct answer positions are balanced exactly: 25 each for A, B, C and D.

## Data origin

The source pathways were written by UK doctors before LLM-assisted data generation. They encode the questions, patient answers and assessments used by a clinical decision support system. Public v0.2 tasks preserve the conversation and decision while removing source-system identifiers, internal provenance and licensed material not required to run the benchmark.

## Task design

The model receives:

- the clinical conversation available at that decision point;
- four self-contained next actions labelled A to D; and
- an instruction to return one option ID without an explanation.

The distractors represent meaningful mistakes: asking the wrong question, stopping too early, asking after the pathway should stop, or selecting a weaker or stronger care route than the source supports.

## Scoring

The primary metric is **exact-decision accuracy**:

```text
correct = selected_option_id == correct_option_id
```

There is no LLM judge, semantic matcher or partial credit. Action-level and matched-pair results are diagnostic breakdowns, not alternate answer keys.

The random-choice baseline is 25%.

## Results

The public leaderboard records one deterministic run per configuration. All scores and evaluation coverage are in [`results/v0.2/leaderboard.json`](../results/v0.2/leaderboard.json) and [`results/v0.2/leaderboard.csv`](../results/v0.2/leaderboard.csv).

The best complete 100-task result is Claude Opus 4.8 at 45.0%. The retained GPT 5.5 xHigh result is 50.6% across 83 evaluated tasks. Cases evaluated is included with every result.

## Public and private material

Public:

- 100 development tasks and their reference option IDs on Hugging Face;
- ten matched-pair relationships;
- evaluator, scorer, schemas, synthetic fixtures and leaderboard in this repository.

Private:

- the larger licensed clinical-reasoning dataset;
- internal validation and hidden-test records;
- source provenance and provider response receipts.

## Limitations

- The first release covers UK pathways and a bounded set of complaints.
- It evaluates agreement with authored pathway decisions, not observed patient outcomes.
- The 100 tasks are transparent development data and may become contaminated after publication.
- Scores do not establish clinical efficacy, regulatory status, safety or generalisation to other healthcare systems.
- Single-run results can be affected by provider and inference variation even when configuration is pinned.
