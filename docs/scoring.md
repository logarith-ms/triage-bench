# Scoring contract

TriageBench v0.2 uses deterministic exact-match scoring.

## Prediction format

Submit one JSON object per line:

```json
{"task_id":"triage-v02-001","selected_option_id":"B"}
```

`selected_option_id` must be one of the option IDs shown in that task.

## Primary metric

```text
correct = selected_option_id == correct_option_id
exact_decision_accuracy = correct_predictions / attempted_tasks
```

Invalid or missing output is incorrect. There is no model judge, semantic matcher or partial credit.

## Diagnostic metrics

The scorer also reports:

- coverage: attempted tasks divided by available tasks;
- valid-output rate: valid predictions divided by attempted tasks;
- accuracy for ask-another-question decisions;
- accuracy for stop-and-assess decisions;
- matched-pair accuracy; and
- 95% Wilson confidence intervals.

A matched pair is correct only when both tasks in the pair are answered correctly.

## Baselines

- Random option: 25% in expectation because every task has four options.
- First option: a position-bias diagnostic, not a capability baseline.
- Oracle: an evaluator self-test that reads the reference answer; it is not a model result.
