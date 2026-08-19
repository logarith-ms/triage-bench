---
license: cc-by-4.0
language:
  - en
task_categories:
  - question-answering
tags:
  - benchmark
  - clinical-triage
  - medical-reasoning
  - sequential-decision-making
  - evaluation
  - uk-healthcare
  - not-for-training
configs:
  - config_name: tasks
    data_files:
      - split: test
        path: tasks.jsonl
  - config_name: matched_pairs
    data_files:
      - split: test
        path: matched-pairs.jsonl
---

# TriageBench

TriageBench tests whether a model can choose the next clinical-triage action from a partial UK patient conversation: ask the right next question, or stop and choose the right assessment.

[Leaderboard](https://labs.logarith.ms/benchmarks/triage-bench) · [Evaluator](https://github.com/logarith-ms/triage-bench) · [Research article](https://labs.logarith.ms/research/triage-bench)

## Public v0.2 release

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

The tasks are derived from UK clinical pathways written by doctors before LLM-assisted data generation. Each task contains the conversation available at one decision point and four plausible next actions. Answer positions are balanced exactly across A, B, C and D.

## Scoring

The model returns one option ID. The primary metric is exact-decision accuracy:

```text
correct = selected_option_id == correct_option_id
```

There is no model judge, semantic matching or partial credit. The random-choice baseline is 25%.

The public leaderboard contains 31 model configurations. The best complete 100-task score in this release is 45.0%. Full results, including the number of cases evaluated by each configuration, are available in `leaderboard.json` and `leaderboard.csv`.

## Use

Download the release:

```bash
hf download logarith-ms/triage-bench \
  --repo-type dataset \
  --include "tasks.jsonl" "matched-pairs.jsonl" "manifest.json" \
  --local-dir .local/releases/v0.2/public
```

Run the public evaluator:

```bash
git clone https://github.com/logarith-ms/triage-bench.git
cd triage-bench
uv sync
export TRIAGE_BENCH_RELEASE_ROOT="$PWD/.local/releases/v0.2"
uv run triage-bench-baselines --split public
```

## Intended use

This is a transparent development benchmark for studying sequential clinical-triage decisions. The public tasks are marked `not-for-training` so they remain useful for evaluation.

TriageBench does not establish clinical efficacy, safety, regulatory status or readiness for patient care. It measures agreement with the doctor-authored pathway decisions represented in this release.

## Data access

The larger Clinical Triage Reasoning - UK dataset is licensed separately and is not published on Hugging Face. To request access or commission bespoke expert human data, contact [labs@logarith.ms](mailto:labs@logarith.ms).

## Licensing

The public task records and matched-pair metadata are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Evaluator code is licensed separately under Apache-2.0 in the GitHub repository.
