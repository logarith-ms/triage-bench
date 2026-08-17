# TriageBench v0.1 Scoring

The v0.1 scorer measures only decisions that can be reproduced exactly from
the doctor-authored source graphs.

## Prediction

Each prediction contains:

- `case_id`;
- `action_type`: `ask_question` or `return_assessment`;
- `target_node_id`: the predicted next question or assessment node.

The model selects from the valid doctor-authored actions supplied with the
case. It does not generate a new pathway action in v0.1.

Unknown case IDs and duplicate predictions are rejected. Missing predictions
reduce coverage.

For direct model runs, malformed JSON and selections outside the supplied
candidates count as incorrect. The run receipt reports both attempted-case
coverage and valid-output rate.

## Metrics

### Primary metric

**Exact-decision accuracy** is the primary TriageBench v0.1 metric. A
prediction is correct only when both its action type and destination node match
the source reference.

Changing the primary metric requires a new benchmark version.

### Coverage

The proportion of benchmark cases attempted in a model run. For an offline
prediction file, this is the proportion containing one valid prediction.

### Valid-output rate

The proportion of attempted cases that return contract-valid JSON selecting
one supplied action.

### Current-action accuracy

The proportion that correctly chooses ask versus stop-and-assess.

### Target-node accuracy

The proportion that selects the exact next pathway decision.

### Exact-decision accuracy

The proportion with both the correct action and correct target node.

### Next-question accuracy

Target-node accuracy over ask-another-question cases only.

### Assessment-route accuracy

Target-node accuracy over stop-and-assess cases only.

### Counterfactual-pair accuracy

For sibling-answer pairs, the scorer checks whether predicted actions and
destinations change exactly when the source graph says they change.

## Graph oracle

The build writes source-graph predictions as a scorer self-test. Every metric
must equal `1.0`; otherwise the benchmark build or scorer is invalid.

## Not scored in v0.1

Urgency, red-flag recall, diagnosis, treatment and communication quality are
not scored until their labels and evaluation contracts are separately frozen.
They must not be inferred from ambiguous assessment prose.

## Command

```bash
uv run triage-bench-score /absolute/path/to/predictions.jsonl --split sample
uv run triage-bench-run --model PROVIDER/MODEL --split sample
```

Approved evaluators can select an authorised split by setting
`TRIAGE_BENCH_RELEASE_ROOT` to its release bundle.
