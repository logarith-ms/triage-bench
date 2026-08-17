# TriageBench

TriageBench evaluates whether a model can follow a sequential UK clinical-triage pathway: ask the right next question, or stop and return the correct assessment route.

[Benchmark overview](https://labs.logarith.ms/benchmarks/triage-bench) · [Research article](https://labs.logarith.ms/research/triage-bench) · [Hugging Face](https://huggingface.co/datasets/logarith-ms/triage-bench)

## What is public

This repository contains the provider-independent evaluation harness, scoring code, JSON schemas, deterministic baselines and a small fictional development fixture. The fixture exists to test integrations. It is not part of the official leaderboard and is not clinical guidance.

The licensed evaluation set, hidden test cases and answer keys are not included. Official scores are produced against the frozen private evaluator.

## Benchmark at a glance

- 4,050 sequential decision states across ten UK clinical pathways.
- 9,716 counterfactual pairs that change one patient answer.
- 3,250 training cases, 408 validation cases and 392 hidden test cases.
- Primary metric: exact next-decision accuracy.
- Supporting metrics: next-question accuracy, assessment-route accuracy, valid-output rate and counterfactual consistency.

TriageBench measures pathway-following decisions. It is not evidence that a model is ready for patient care.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then run the bundled sample:

```bash
uv sync
uv run triage-bench-baselines --split sample
```

Score a JSONL submission against the sample:

```bash
uv run triage-bench-score /path/to/predictions.jsonl --split sample
```

Run a model through [Inspect AI](https://inspect.aisi.org.uk/):

```bash
uv run triage-bench-run \
  --model openai/MODEL_NAME \
  --split sample
```

Inspect reads provider credentials from the standard environment variables for the selected provider. See the [Inspect model providers](https://inspect.aisi.org.uk/models.html) documentation.

## Using an authorised benchmark release

Approved evaluators can point the same runner at an authorised release bundle:

```bash
export TRIAGE_BENCH_RELEASE_ROOT=/absolute/path/to/triage-bench/v0.1
uv run triage-bench-run --model PROVIDER/MODEL --split validation
```

The hidden split is locked by default. It requires both `--split test` and `--allow-hidden-test` and should be used only after the model and evaluation settings are frozen.

## Output

Every run writes:

- the provider transcript as an Inspect `.eval` log;
- strict JSONL predictions;
- benchmark scores;
- a reproducibility receipt with model settings, hashes, token use, cost and Git state.

Local runs are written under `.local/evals/` and ignored by Git.

## Development

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run triage-bench-baselines --split sample
```

Read [`docs/BENCHMARK_CARD.md`](docs/BENCHMARK_CARD.md) for the evaluation contract and [`docs/scoring.md`](docs/scoring.md) for metric definitions.

## Data access and official evaluation

To discuss data licensing or an official hidden-set evaluation, contact [labs@logarith.ms](mailto:labs@logarith.ms).
