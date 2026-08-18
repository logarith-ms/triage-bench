# TriageBench

TriageBench evaluates whether a model can follow a sequential UK clinical-triage pathway: ask the right next question, or stop and return the correct assessment route.

[Benchmark overview](https://labs.logarith.ms/benchmarks/triage-bench) · [Public tasks](https://huggingface.co/datasets/logarith-ms/triage-bench) · [Research article](https://labs.logarith.ms/research/triage-bench)

## What is public

This Apache-2.0 repository contains the provider-independent evaluator, scoring code, JSON schemas, deterministic baselines and six fictional smoke-test cases. The source-derived public release contains 100 real benchmark cases and 152 counterfactual pairs on Hugging Face under CC BY 4.0 and is marked `not-for-training`.

Licensed training data, the remaining internal-validation cases and the hidden test are not public.

## Benchmark at a glance

- 4,050 sequential decision states across ten UK clinical pathways.
- 9,716 counterfactual pairs that change one patient answer.
- 100 transparent public cases: 30 question decisions and 70 assessment decisions.
- 308 additional internal-validation cases and 392 hidden-test cases.
- Primary metric: exact next-decision accuracy.
- Supporting metrics: action and target accuracy, question and assessment accuracy, valid-output rate, counterfactual consistency and 95% confidence intervals.

TriageBench measures pathway-following decisions. It is not evidence that a model is ready for patient care.

## Public leaderboard

Measured on the transparent 100-case public v0.1 set with one deterministic pass. These are development-set results, not hidden-test or clinical-validation results.

| Model | Exact decision | Action | Ask | Assess | Counterfactual |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V3.2 | **81.0%** | 93.0% | 63.3% | 88.6% | 75.0% |
| Gemma 4 31B | 80.0% | 92.0% | 60.0% | 88.6% | **76.3%** |
| Llama 4 Maverick | 79.0% | 92.0% | **66.7%** | 84.3% | 61.8% |

All three runs produced valid structured output for all 100 cases. Exact-decision 95% confidence intervals overlap, so the one-point differences should not be treated as a definitive model ranking. See the [machine-readable results](results/v0.1/public-100.json) for providers, settings, hashes, confidence intervals and costs.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then run the fictional fixture:

```bash
uv sync
uv run triage-bench-baselines --split sample
```

Download and run the 100 public cases:

```bash
hf download logarith-ms/triage-bench \
  --repo-type dataset \
  --include "cases.jsonl" "counterfactual-pairs.jsonl" "manifest.json" \
  --local-dir .local/releases/v0.1/public

export TRIAGE_BENCH_RELEASE_ROOT="$PWD/.local/releases/v0.1"
uv run triage-bench-baselines --split public
```

Score a JSONL submission:

```bash
uv run triage-bench-score /path/to/predictions.jsonl --split public
```

## OpenRouter

TriageBench uses [Inspect AI](https://inspect.aisi.org.uk/) and supports OpenRouter through Inspect's OpenAI-compatible provider.

Probe one case to identify a provider endpoint:

```bash
export OPENROUTER_API_KEY="..."
uv run triage-bench-run \
  --model openrouter/qwen/qwen3.5-9b \
  --split public \
  --limit 1 \
  --probe-provider \
  --cost-limit 1
```

Pin that provider for a scored run:

```bash
uv run triage-bench-run \
  --model openrouter/qwen/qwen3.5-9b \
  --openrouter-provider PROVIDER_SLUG \
  --split public \
  --limit 20 \
  --cost-limit 5
```

Fallback is disabled on scored OpenRouter runs. The routing policy requests no data collection and zero-data-retention processing. See [`docs/OPENROUTER_RUNBOOK.md`](docs/OPENROUTER_RUNBOOK.md).

## Reproducibility

Every model run writes:

- the provider transcript as an Inspect `.eval` log;
- strict JSONL predictions;
- benchmark scores and confidence intervals;
- a receipt containing model and provider settings, returned-model metadata, task and prompt hashes, token use, cost and Git state.

Run order and model gates are versioned in [`config/runs`](config/runs). Local runs are written under `.local/evals/` and ignored by Git.

## Authorised releases

Approved evaluators can point the same runner at a private release bundle:

```bash
export TRIAGE_BENCH_RELEASE_ROOT=/absolute/path/to/triage-bench/v0.1
uv run triage-bench-run --model PROVIDER/MODEL --split validation
```

The hidden split requires both `--split test` and `--allow-hidden-test`. It should be used once, after the model, provider, prompt and evaluation settings are frozen.

## Development

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run triage-bench-baselines --split sample
```

Read [`docs/BENCHMARK_CARD.md`](docs/BENCHMARK_CARD.md) for the contract and [`docs/scoring.md`](docs/scoring.md) for metric definitions.

## Data access

To license Clinical Triage Reasoning - UK, request bespoke expert human data or arrange an official hidden-set evaluation, contact [labs@logarith.ms](mailto:labs@logarith.ms).
