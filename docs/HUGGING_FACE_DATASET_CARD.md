---
license: cc-by-4.0
language:
  - en
task_categories:
  - question-answering
pretty_name: TriageBench
tags:
  - benchmark
  - clinical-triage
  - medical-reasoning
  - sequential-decision-making
  - evaluation
  - uk-healthcare
  - not-for-training
configs:
  - config_name: cases
    data_files:
      - split: test
        path: cases.jsonl
  - config_name: counterfactual_pairs
    data_files:
      - split: test
        path: counterfactual-pairs.jsonl
---

# TriageBench

TriageBench tests whether a model can follow a sequential UK clinical-triage pathway: ask the right next question, or stop and return the correct assessment route.

The public release contains 100 real decision states derived from pathways written by UK doctors before the current generative-AI era. It covers Ear and General Travel Advice pathways and includes 152 complete counterfactual pairs where a changed patient answer can change the correct next action.

## Why this matters

Clinical triage is not a single diagnosis question. A system must decide what information is still missing, ask only useful questions and stop when the pathway has enough evidence. TriageBench evaluates that next decision directly.

## Public release

- 100 cases: 30 `ask_question` and 70 `return_assessment` decisions.
- 44 General Travel Advice cases and 56 stratified Ear cases.
- 152 counterfactual pairs.
- UK English and UK care context.
- Doctor-authored source pathways, written without LLM drafting.

The public cases are for transparent benchmark development. They are tagged `not-for-training`. Separate internal-validation and hidden-test records are not published.

## Record format

Each case contains the dialogue so far, supplied next-action candidates, doctor-authored reference action and target, and pathway metadata. Private source references, graph traces, internal matching evidence and licensed training records are excluded.

## Metrics

The primary metric is exact next-decision accuracy. Supporting metrics measure action choice, target choice, question and assessment accuracy, structured-output validity, counterfactual consistency and 95% confidence intervals.

## Public leaderboard

Measured on the transparent 100-case public v0.1 set with one deterministic pass. These are development-set results, not hidden-test or clinical-validation results.

| Model | Exact decision | Action | Ask | Assess | Counterfactual |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V3.2 | **81.0%** | 93.0% | 63.3% | 88.6% | 75.0% |
| Gemma 4 31B | 80.0% | 92.0% | 60.0% | 88.6% | **76.3%** |
| Llama 4 Maverick | 79.0% | 92.0% | **66.7%** | 84.3% | 61.8% |

All three runs returned valid structured output for all 100 cases. Exact-decision 95% confidence intervals overlap. Providers, settings, hashes, confidence intervals and costs are published in the [machine-readable results](https://github.com/logarith-ms/triage-bench/blob/main/results/v0.1/public-100.json).

## Run the benchmark

```bash
hf download logarith-ms/triage-bench \
  --repo-type dataset \
  --include "cases.jsonl" "counterfactual-pairs.jsonl" "manifest.json" \
  --local-dir .local/releases/v0.1/public

export TRIAGE_BENCH_RELEASE_ROOT="$PWD/.local/releases/v0.1"
uv run triage-bench-run --model PROVIDER/MODEL --split public
```

Evaluation code: https://github.com/logarith-ms/triage-bench

Benchmark overview: https://labs.logarith.ms/benchmarks/triage-bench

Research article: https://labs.logarith.ms/research/triage-bench

## Limitations

TriageBench begins with UK clinical pathways and tests a narrow sequential-routing capability. A benchmark score is not evidence that a model is safe for patient care, is clinically validated, or generalises to other healthcare systems.

## Licensing and access

The public benchmark records are licensed under CC BY 4.0. The evaluation code is Apache-2.0. The larger Clinical Triage Reasoning - UK training dataset is licensed separately. Contact [labs@logarith.ms](mailto:labs@logarith.ms) to request access or discuss a country-specific dataset.
