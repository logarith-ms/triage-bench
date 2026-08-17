# OpenRouter evaluation runbook

## 1. Fetch the public tasks

```bash
hf download logarith-ms/triage-bench \
  --repo-type dataset \
  --include "cases.jsonl" "counterfactual-pairs.jsonl" "manifest.json" \
  --local-dir .local/releases/v0.1/public
export TRIAGE_BENCH_RELEASE_ROOT="$PWD/.local/releases/v0.1"
```

## 2. Probe and pin a provider

Run exactly one public task without a provider pin. Inspect the response metadata and choose the endpoint for the scored run.

```bash
export OPENROUTER_API_KEY="..."
uv run triage-bench-run \
  --model openrouter/qwen/qwen3.5-9b \
  --split public \
  --limit 1 \
  --probe-provider \
  --cost-limit 1
```

## 3. Run the diagnostic set

```bash
uv run triage-bench-run \
  --model openrouter/qwen/qwen3.5-9b \
  --openrouter-provider PROVIDER_SLUG \
  --split public \
  --limit 20 \
  --cost-limit 5
```

Provider fallback is disabled. Data collection is denied and zero-data-retention routing is requested. The receipt records the requested model, provider policy, returned model metadata, hashes, usage and cost.

The evaluator loads `config/openrouter-costs-2026-08-18.json` so Inspect can
enforce `--cost-limit` before and during a run. Prices are expressed in USD per
million tokens and must be refreshed from OpenRouter before a new scored
campaign. Pass `--model-cost-config PATH` to use a newer reviewed snapshot.

## 4. Freeze before scaling

Review invalid JSON, impossible choices, unexpected routing, unclear cases and counterfactual failures. Freeze the prompt, parser, selector, task hashes, model IDs and provider IDs before running all 100 cases. The manifests in `config/runs/` define the order through the final hidden test.
