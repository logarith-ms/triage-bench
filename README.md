# TriageBench

TriageBench tests whether a model can choose the next clinical-triage action from a partial UK patient conversation: ask the right next question, or stop and choose the right assessment.

[Leaderboard](https://labs.logarith.ms/benchmarks/triage-bench) · [Public tasks](https://huggingface.co/datasets/logarith-ms/triage-bench) · [Research article](https://labs.logarith.ms/research/triage-bench)

## Public v0.2 release

- 100 development tasks drawn from doctor-authored UK clinical pathways.
- 50 ask-another-question decisions and 50 stop-and-assess decisions.
- Four plausible clinical actions per task.
- Ten matched pairs where one changed patient answer changes the expected action.
- Exact option-match scoring, with no model judge and no partial credit.
- Answer positions balanced exactly across A, B, C and D.

The pathways were written by doctors before LLM-assisted data generation. TriageBench measures agreement with those authored pathway decisions. It does not establish that a model is safe or ready for patient care.

## Leaderboard

Exact-decision accuracy from one deterministic run per configuration. The random-choice baseline is 25%.

| Rank | Model configuration | Score | Cases evaluated |
| ---: | --- | ---: | ---: |
| 1 | GPT 5.5 (xHigh reasoning) | 50.6% | 83 |
| 2 | Claude Opus 4.8 (default) | 45.0% | 100 |
| 3 | Qwen 3.5 Plus | 44.0% | 100 |
| 4 | Claude Opus 5 (default) | 43.0% | 100 |
| 5 | Gemini 3.1 Pro | 42.0% | 100 |
| 6 | GPT 5.6 Sol (default) | 42.0% | 100 |
| 7 | Qwen 3.7 Plus | 41.0% | 100 |
| 8 | Qwen 3.8 Max | 41.0% | 100 |
| 9 | Claude Opus 4.7 (default) | 40.0% | 100 |
| 10 | Claude Sonnet 5 (default) | 40.0% | 100 |

The complete 31-configuration leaderboard is available as [JSON](results/v0.2/leaderboard.json) and [CSV](results/v0.2/leaderboard.csv). Cases evaluated states how many benchmark tasks each configuration completed.

## What is public

This Apache-2.0 repository contains the v0.2 evaluator, scoring code, schemas, deterministic baselines, synthetic smoke-test tasks and public leaderboard. The 100 source-derived development tasks are published on Hugging Face under CC BY 4.0 and marked `not-for-training`.

The larger licensed training dataset, internal validation records, hidden tests and provider response receipts are not public.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then run the synthetic fixture:

```bash
uv sync
uv run triage-bench-baselines --split sample
```

Download and run the 100 public tasks:

```bash
hf download logarith-ms/triage-bench \
  --repo-type dataset \
  --include "tasks.jsonl" "matched-pairs.jsonl" "manifest.json" \
  --local-dir .local/releases/v0.2/public

export TRIAGE_BENCH_RELEASE_ROOT="$PWD/.local/releases/v0.2"
uv run triage-bench-baselines --split public
```

Score JSONL predictions:

```json
{"task_id":"triage-v02-001","selected_option_id":"B"}
```

```bash
uv run triage-bench-score /path/to/predictions.jsonl --split public
```

## Model runs

TriageBench uses [Inspect AI](https://inspect.aisi.org.uk/) and supports provider-pinned OpenRouter runs. Fallbacks are disabled for scored runs.

```bash
export OPENROUTER_API_KEY="..."
uv run triage-bench-run \
  --model openrouter/PROVIDER/MODEL \
  --openrouter-provider PROVIDER_SLUG \
  --split public \
  --cost-limit 5
```

Every run writes predictions, scores, provider metadata, task and prompt hashes, token use, cost and Git state. See [`docs/OPENROUTER_RUNBOOK.md`](docs/OPENROUTER_RUNBOOK.md).

## Development

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run triage-bench-baselines --split sample
```

Read the [benchmark card](docs/BENCHMARK_CARD.md) and [scoring contract](docs/scoring.md).

## Data access

To license Clinical Triage Reasoning - UK, request bespoke expert human data or arrange a private evaluation, contact [labs@logarith.ms](mailto:labs@logarith.ms).
