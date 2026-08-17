from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

PROMPT_VERSION = "triage-bench-v0.1-prompt-1"
ALLOWED_ACTIONS = {"ask_question", "return_assessment"}
FORBIDDEN_VISIBLE_KEYS = {
    "reference", "graph_trace", "source", "source_edge_id",
    "spreadsheet_match", "red_flag_evidence",
}


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


def model_input(case: dict[str, Any]) -> dict[str, Any]:
    visible = {
        "case_id": case["case_id"],
        "benchmark_version": case["benchmark_version"],
        "geography": case["geography"],
        "language": case["language"],
        "pathway": case["pathway"],
        "dialogue_prefix": case["dialogue_prefix"],
        "candidates": case["candidates"],
    }
    visible_text = stable_json(visible)
    for key in FORBIDDEN_VISIBLE_KEYS:
        if f'"{key}"' in visible_text:
            raise ValueError(f"Private field leaked into model input: {key}")
    return visible


def _candidate_content(candidate: dict[str, Any]) -> str:
    lines = []
    for label, value in candidate["content"].items():
        clean_label = label.replace("_", " ").strip().capitalize()
        lines.append(f"{clean_label}: {value}")
    return "\n".join(lines)


def build_prompt(case: dict[str, Any]) -> str:
    visible = model_input(case)
    dialogue = "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in visible["dialogue_prefix"]
    )
    candidates = "\n\n".join(
        f"Candidate {index}\n"
        f"action_type: {candidate['action_type']}\n"
        f"target_node_id: {candidate['target_node_id']}\n"
        f"{_candidate_content(candidate)}"
        for index, candidate in enumerate(visible["candidates"], start=1)
    )
    return f"""You are completing a clinical-triage benchmark.

Choose the single doctor-authored next action that follows from the dialogue.
Use only one supplied candidate. Do not add medical advice or prose.

Dialogue so far:
{dialogue}

Valid next actions:
{candidates}

Return exactly one JSON object with these two keys:
{{"action_type":"ask_question or return_assessment","target_node_id":"candidate target_node_id"}}
"""


@dataclass(frozen=True)
class ParsedPrediction:
    action_type: str | None
    target_node_id: str | None
    error: str | None

    @property
    def valid(self) -> bool:
        return self.error is None

    def as_prediction(self, case_id: str) -> dict[str, str] | None:
        if not self.valid or self.action_type is None or self.target_node_id is None:
            return None
        return {
            "case_id": case_id,
            "action_type": self.action_type,
            "target_node_id": self.target_node_id,
        }


def parse_prediction(raw: str, candidates: list[dict[str, Any]]) -> ParsedPrediction:
    try:
        value = json.loads(raw.strip())
    except (json.JSONDecodeError, AttributeError) as error:
        return ParsedPrediction(None, None, f"invalid_json: {error}")
    if not isinstance(value, dict):
        return ParsedPrediction(None, None, "prediction_must_be_an_object")
    if set(value) != {"action_type", "target_node_id"}:
        return ParsedPrediction(None, None, "prediction_keys_must_match_contract")
    action_type = value.get("action_type")
    target_node_id = value.get("target_node_id")
    if action_type not in ALLOWED_ACTIONS or not isinstance(target_node_id, str):
        return ParsedPrediction(None, None, "prediction_values_are_invalid")
    matching = [
        candidate for candidate in candidates
        if candidate["target_node_id"] == target_node_id
        and candidate["action_type"] == action_type
    ]
    if len(matching) != 1:
        return ParsedPrediction(None, None, "prediction_is_not_a_valid_candidate")
    return ParsedPrediction(action_type, target_node_id, None)


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
    cases: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    predictions: Iterable[dict[str, str]],
    *,
    attempted_case_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    cases_by_id = {case["case_id"]: case for case in cases}
    predictions_by_id: dict[str, dict[str, str]] = {}
    for prediction in predictions:
        case_id = prediction["case_id"]
        if case_id not in cases_by_id:
            raise ValueError(f"Unknown case_id: {case_id}")
        if case_id in predictions_by_id:
            raise ValueError(f"Duplicate prediction: {case_id}")
        predictions_by_id[case_id] = prediction
    attempted = set(attempted_case_ids) if attempted_case_ids is not None else set(predictions_by_id)
    unknown_attempts = attempted - cases_by_id.keys()
    if unknown_attempts:
        raise ValueError(f"Unknown attempted case_id: {sorted(unknown_attempts)[0]}")
    if not predictions_by_id.keys() <= attempted:
        raise ValueError("A valid prediction cannot exist outside the attempted case set")

    action_correct = target_correct = exact_correct = 0
    ask_cases = ask_correct = assessment_cases = assessment_correct = 0
    for case in cases:
        if case["case_id"] not in attempted:
            continue
        prediction = predictions_by_id.get(case["case_id"])
        if case["reference"]["action_type"] == "ask_question":
            ask_cases += 1
        else:
            assessment_cases += 1
        if prediction is None:
            continue
        action_matches = prediction["action_type"] == case["reference"]["action_type"]
        target_matches = prediction["target_node_id"] == case["reference"]["target_node_id"]
        action_correct += int(action_matches)
        target_correct += int(target_matches)
        exact_correct += int(action_matches and target_matches)
        if case["reference"]["action_type"] == "ask_question":
            ask_correct += int(target_matches)
        else:
            assessment_correct += int(target_matches)

    evaluated_pairs = pair_correct = 0
    for pair in pairs:
        if pair["baseline"]["case_id"] not in attempted or pair["counterfactual"]["case_id"] not in attempted:
            continue
        evaluated_pairs += 1
        baseline = predictions_by_id.get(pair["baseline"]["case_id"])
        counterfactual = predictions_by_id.get(pair["counterfactual"]["case_id"])
        if baseline is None or counterfactual is None:
            continue
        destination_changed = baseline["target_node_id"] != counterfactual["target_node_id"]
        action_changed = baseline["action_type"] != counterfactual["action_type"]
        pair_correct += int(
            destination_changed == pair["expected_effect"]["destination_changed"]
            and action_changed == pair["expected_effect"]["transition_kind_changed"]
        )

    submitted = len(attempted)
    valid_predictions = len(predictions_by_id)
    return {
        "benchmark_version": "v0.1",
        "submitted_cases": submitted,
        "valid_predictions": valid_predictions,
        "total_cases": len(cases),
        "coverage": _rate(submitted, len(cases)),
        "valid_output_rate": _rate(valid_predictions, submitted),
        "current_action_accuracy": _rate(action_correct, submitted),
        "target_node_accuracy": _rate(target_correct, submitted),
        "exact_decision_accuracy": _rate(exact_correct, submitted),
        "next_question_accuracy": _rate(ask_correct, ask_cases),
        "assessment_route_accuracy": _rate(assessment_correct, assessment_cases),
        "counterfactual_pair_accuracy": _rate(pair_correct, evaluated_pairs),
        "confidence_intervals_95": {
            "coverage": _wilson_interval(submitted, len(cases)),
            "valid_output_rate": _wilson_interval(valid_predictions, submitted),
            "current_action_accuracy": _wilson_interval(action_correct, submitted),
            "target_node_accuracy": _wilson_interval(target_correct, submitted),
            "exact_decision_accuracy": _wilson_interval(exact_correct, submitted),
            "next_question_accuracy": _wilson_interval(ask_correct, ask_cases),
            "assessment_route_accuracy": _wilson_interval(assessment_correct, assessment_cases),
            "counterfactual_pair_accuracy": _wilson_interval(pair_correct, evaluated_pairs),
        },
        "evaluated_pairs": evaluated_pairs,
        "total_pairs": len(pairs),
    }
