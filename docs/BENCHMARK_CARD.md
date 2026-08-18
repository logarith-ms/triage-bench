# TriageBench

Status: Public v0.1 harness with a private official evaluation set
Subtitle: A benchmark for sequential UK clinical-triage decisions
Contact: `labs@logarith.ms`

## The question

Can a model decide when to ask another question, when to stop, and which
doctor-authored pathway step should come next?

TriageBench evaluates models while a case is still unfolding. Each case
contains only the questions and patient answers available at that point. The
reference is the next question or assessment encoded in the source graph.

It is a triage decision benchmark, not a diagnostic exam and not evidence that
a model is ready for patient care.

## Official v0.1 evaluation set

The current build is projected deterministically from all ten source graphs in
Clinical Triage Reasoning - UK.

| Item | Count |
| --- | ---: |
| Unique decision states | 4,050 |
| Ask-another-question states | 1,136 |
| Stop-and-assess states | 2,914 |
| Counterfactual answer pairs | 9,716 |
| Mean valid actions per case | 2.83 |
| Minimum / maximum valid actions | 1 / 13 |

Counts by source graph:

| Graph | Cases |
| --- | ---: |
| Ear | 364 |
| Eye | 65 |
| Stomach | 1,148 |
| Coughs & Colds | 677 |
| Bone, Joint & Muscle | 322 |
| Headache | 730 |
| Women's Health | 70 |
| Mouth | 61 |
| Sexual Health | 569 |
| General Travel Advice | 44 |

The candidate set uses the same graph-isolated split as the licensed dataset:
3,250 training cases, 408 validation cases and 392 hidden test cases. No source
graph appears in more than one split.

## Tracks

### Current action

Choose whether the source pathway asks another question or returns an
assessment.

### Next question

When asking is correct, select the next question node encoded by the pathway.

### Assessment route

When stopping is correct, select the terminal assessment node encoded by the
pathway.

### Counterfactual consistency

Each pair holds the preceding dialogue constant and changes one answer at the
same question. The score checks whether the predicted action and destination
change when the source graph changes them, and remain stable when the source
graph does not.

## What v0.1 does not score yet

The current source supports exact graph decisions. It does not yet support a
defensible public score for:

- free-form diagnosis;
- treatment quality;
- current clinical safety;
- exact urgency where assessment text yields conflicting care-level terms;
- patient-facing writing quality.

Candidate care levels and red-flag evidence remain attached for analysis but
are not silently promoted to benchmark ground truth.

## Public and private files

This repository contains the runner, scorer, schemas, deterministic baselines
and a fictional development fixture. The authorised evaluation bundle adds the
licensed cases, counterfactual pairs, source-oracle self-test and signed
manifest. The licensed cases and hidden answers are not published.

## Reproducibility

The official build is deterministic and content-addressed. The public runner
checks every release file against hashes in its manifest before evaluation.

## Approved model-facing protocol

TriageBench v0.1 uses a closed ontology. Each case exposes the dialogue
prefix and the valid candidate questions or assessments for that state,
including their identifiers. The model selects one candidate; it does not
generate an unconstrained next question for v0.1.

This protocol keeps scoring deterministic. It measures routing within the
supplied pathway options, not the ability to formulate a new clinical question
from scratch. Candidate order is deterministic and stable for every state at
the same question, while remaining independent of source edge order.

The primary metric is **exact-decision accuracy**: both `action_type` and
`target_node_id` must match the source reference. All supporting metrics remain
mandatory in result reports.

## Submission format

One JSONL prediction is required for every evaluated case:

```json
{
  "case_id": "triage-case-example",
  "action_type": "ask_question",
  "target_node_id": "next-question-node"
}
```

Use `uv run triage-bench-score /path/to/predictions.jsonl --split sample` to
test the submission contract. Approved evaluators can point the same command
at an authorised release bundle.

## Evaluation harness

The provider-independent Python harness uses Inspect AI for model calls,
retries, token and cost records, durable logs and run resumption. The model
receives only the dialogue and valid actions. Private provenance and the
accepted action remain outside the prompt.

```bash
uv sync
uv run triage-bench-baselines --split sample
uv run triage-bench-run --model PROVIDER/MODEL --split sample
```

Every run writes strict predictions, raw responses, supporting scores and a
receipt containing the model configuration, source hashes, prompt version,
Git commit, token use and provider-reported cost. The validation split is the
default. The hidden test split requires an explicit override and must only be
used after the model and evaluation contract are frozen.

## Validation baselines

Measured on all 408 validation cases with seed `42`:

| Baseline | Exact decision | Counterfactual pair |
| --- | ---: | ---: |
| Random valid candidate | 38.0% | 52.5% |
| First displayed candidate | 38.2% | 27.1% |
| Train-majority action, then first matching candidate | 38.2% | 27.1% |
| Source oracle scorer self-test | 100.0% | 100.0% |

The oracle is a scorer check, not a model result.

## Public model results

Measured on the transparent 100-case public v0.1 set with one deterministic
pass, temperature `0` and seed `42`. These are development-set results, not
hidden-test or clinical-validation results.

| Model | Exact decision | Action | Ask | Assess | Counterfactual |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V3.2 | **81.0%** | 93.0% | 63.3% | 88.6% | 75.0% |
| Gemma 4 31B | 80.0% | 92.0% | 60.0% | 88.6% | **76.3%** |
| Llama 4 Maverick | 79.0% | 92.0% | **66.7%** | 84.3% | 61.8% |

Every response passed the structured-output validator. The exact-decision 95%
confidence intervals overlap, so the small differences are not a definitive
model ranking. The complete public metadata, including pinned providers,
settings, hashes, confidence intervals and costs, is stored in
[`results/v0.1/public-100.json`](../results/v0.1/public-100.json).

## Limitations

- It covers ten UK clinical-decision-support pathways, not all of clinical triage.
- The pathways represent authored decisions, not observed patient outcomes.
- Shared graph prefixes create related cases and require graph-aware splitting.
- Assessment text may contain outdated or internally inconsistent content.
- Exact node selection favours systems that can use the benchmark ontology.
- Performance does not establish clinical efficacy, regulatory status or
  deployment readiness.
