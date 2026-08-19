from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

PROMPT_VERSION = "triage-bench-v0.2-prompt-1"
OPTION_IDS = {"A", "B", "C", "D"}


def stable_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def model_input(task: dict[str, Any]) -> dict[str, Any]:
    visible = task["model_input"]
    visible_text = stable_json(visible).lower()
    for key in (
        "reference",
        "correct_option",
        "option_rubric",
        "provenance",
        "source_case",
        "source_transition",
    ):
        if key in visible_text:
            raise ValueError(f"Private field leaked into model input: {key}")
    return visible


def build_prompt(task: dict[str, Any]) -> str:
    visible = model_input(task)
    dialogue = "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in visible["conversation"]
    )
    options = "\n".join(
        f"{option['option_id']}. {option['text']}"
        for option in visible["options"]
    )
    return f"""You are completing a clinical-triage benchmark.

{visible['instruction']}

Clinical context: {visible['geography']} · {visible['language']}

Conversation:
{dialogue}

Options:
{options}

Return exactly one JSON object:
{{"selected_option_id":"A, B, C or D"}}
"""


@dataclass(frozen=True)
class ParsedPrediction:
    selected_option_id: str | None
    error: str | None

    @property
    def valid(self) -> bool:
        return self.error is None

    def as_prediction(self, task_id: str) -> dict[str, str] | None:
        if not self.valid or self.selected_option_id is None:
            return None
        return {"task_id": task_id, "selected_option_id": self.selected_option_id}


def parse_prediction(raw: str, options: list[dict[str, Any]]) -> ParsedPrediction:
    try:
        value = json.loads(raw.strip())
    except (json.JSONDecodeError, AttributeError) as error:
        return ParsedPrediction(None, f"invalid_json: {error}")
    if not isinstance(value, dict) or set(value) != {"selected_option_id"}:
        return ParsedPrediction(None, "prediction_keys_must_match_contract")
    selected = value.get("selected_option_id")
    if not isinstance(selected, str):
        return ParsedPrediction(None, "selected_option_id_must_be_a_string")
    selected = selected.strip().upper()
    visible_ids = {option["option_id"] for option in options}
    if selected not in OPTION_IDS or selected not in visible_ids:
        return ParsedPrediction(None, "prediction_is_not_a_valid_option")
    return ParsedPrediction(selected, None)


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float] | None:
    if total == 0:
        return None
    proportion = successes / total
    denominator = 1 + (z * z / total)
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return {"low": max(0.0, centre - margin), "high": min(1.0, centre + margin)}


def score_predictions(
    tasks: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    predictions: Iterable[dict[str, str]],
    *,
    attempted_task_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    tasks_by_id = {task["task_id"]: task for task in tasks}
    predictions_by_id: dict[str, dict[str, str]] = {}
    for prediction in predictions:
        task_id = prediction["task_id"]
        if task_id not in tasks_by_id:
            raise ValueError(f"Unknown task_id: {task_id}")
        if task_id in predictions_by_id:
            raise ValueError(f"Duplicate prediction: {task_id}")
        predictions_by_id[task_id] = prediction

    attempted = set(attempted_task_ids) if attempted_task_ids is not None else set(predictions_by_id)
    unknown_attempts = attempted - tasks_by_id.keys()
    if unknown_attempts:
        raise ValueError(f"Unknown attempted task_id: {sorted(unknown_attempts)[0]}")
    if not predictions_by_id.keys() <= attempted:
        raise ValueError("A valid prediction cannot exist outside the attempted task set")

    correct = 0
    by_action = {
        "ask_question": {"correct": 0, "total": 0},
        "return_assessment": {"correct": 0, "total": 0},
    }
    for task_id in attempted:
        task = tasks_by_id[task_id]
        action = task["reference"]["required_action"]
        by_action[action]["total"] += 1
        prediction = predictions_by_id.get(task_id)
        is_correct = bool(
            prediction
            and prediction["selected_option_id"] == task["reference"]["correct_option_id"]
        )
        correct += int(is_correct)
        by_action[action]["correct"] += int(is_correct)

    evaluated_pairs = pair_correct = 0
    for pair in pairs:
        left_id, right_id = pair["task_ids"]
        if left_id not in attempted or right_id not in attempted:
            continue
        evaluated_pairs += 1
        left = predictions_by_id.get(left_id)
        right = predictions_by_id.get(right_id)
        if not left or not right:
            continue
        left_correct = left["selected_option_id"] == tasks_by_id[left_id]["reference"]["correct_option_id"]
        right_correct = right["selected_option_id"] == tasks_by_id[right_id]["reference"]["correct_option_id"]
        pair_correct += int(left_correct and right_correct)

    submitted = len(attempted)
    valid = len(predictions_by_id)
    for values in by_action.values():
        values["accuracy"] = _rate(values["correct"], values["total"])
    return {
        "benchmark_version": "v0.2",
        "total_tasks": len(tasks),
        "submitted_tasks": submitted,
        "valid_predictions": valid,
        "coverage": _rate(submitted, len(tasks)),
        "valid_output_rate": _rate(valid, submitted),
        "exact_decision_accuracy": _rate(correct, submitted),
        "by_required_action": by_action,
        "matched_pair_accuracy": _rate(pair_correct, evaluated_pairs),
        "evaluated_pairs": evaluated_pairs,
        "confidence_intervals_95": {
            "exact_decision_accuracy": _wilson_interval(correct, submitted),
            "valid_output_rate": _wilson_interval(valid, submitted),
            "matched_pair_accuracy": _wilson_interval(pair_correct, evaluated_pairs),
        },
    }
