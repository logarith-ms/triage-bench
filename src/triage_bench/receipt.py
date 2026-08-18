from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import subprocess
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log

from .core import PROMPT_VERSION, parse_prediction, score_predictions, sha256_text, stable_json
from .data import load_split, repository_root


def _serialise(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    return value


def _git_state() -> dict[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository_root(), text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repository_root(), text=True
        )
        diff = subprocess.check_output(
            ["git", "diff", "--binary", "HEAD"], cwd=repository_root()
        )
        return {
            "commit": commit,
            "dirty": bool(status.strip()),
            "working_tree_diff_sha256": sha256_text(diff.decode("utf-8", errors="replace")),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None, "working_tree_diff_sha256": None}


def _usage(log: EvalLog) -> dict[str, Any]:
    input_tokens = output_tokens = total_tokens = 0
    costs: list[float] = []
    by_model: dict[str, Any] = {}
    for model, usage in log.stats.model_usage.items():
        by_model[model] = _serialise(usage)
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        total_tokens += usage.total_tokens
        if usage.total_cost is not None:
            costs.append(usage.total_cost)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "total_cost_usd": sum(costs) if costs else None,
        "by_model": by_model,
    }


def _model_call_metadata(sample: Any) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    for event in sample.events or []:
        if getattr(event, "event", None) != "model":
            continue
        call = getattr(event, "call", None)
        response = getattr(call, "response", None)
        if not isinstance(response, dict):
            continue
        metadata = {
            key: str(response[key])
            for key in ("id", "model", "provider")
            if response.get(key) is not None
        }
        if metadata:
            calls.append(metadata)
    return calls


def write_run_artifacts(log: EvalLog, split: str, output: Path) -> Path:
    benchmark = load_split(split, allow_hidden_test=True)
    cases_by_id = {case["case_id"]: case for case in benchmark.cases}
    predictions: list[dict[str, str]] = []
    responses = []
    attempted_case_ids = []
    model_inputs = []
    for sample in log.samples or []:
        case_id = str(sample.id)
        attempted_case_ids.append(case_id)
        model_inputs.append({"case_id": case_id, "input": sample.input})
        case = cases_by_id.get(case_id)
        if case is None:
            raise ValueError(f"Inspect log contains unknown case: {case_id}")
        raw = sample.output.completion if sample.output is not None else ""
        parsed = parse_prediction(raw, case["candidates"])
        prediction = parsed.as_prediction(case_id)
        model_calls = _model_call_metadata(sample)
        if prediction is not None:
            predictions.append(prediction)
        responses.append({
            "case_id": case_id,
            "raw_response": raw,
            "parsed_prediction": prediction,
            "parse_error": parsed.error,
            "returned_model": sample.output.model if sample.output is not None else None,
            "output_metadata": sample.output.metadata if sample.output is not None else None,
            "model_calls": model_calls,
            "total_time_seconds": sample.total_time,
            "model_usage": {model: _serialise(usage) for model, usage in sample.model_usage.items()},
        })
    metrics = score_predictions(
        benchmark.cases,
        benchmark.pairs,
        predictions,
        attempted_case_ids=attempted_case_ids,
    )
    prediction_body = "".join(stable_json(value) + "\n" for value in predictions)
    returned_models = sorted({response["returned_model"] for response in responses if response["returned_model"]})
    returned_providers = sorted(
        {
            call["provider"]
            for response in responses
            for call in response["model_calls"]
            if call.get("provider")
        }
    )
    requested_provider_order = (
        (log.eval.model_args or {}).get("provider", {}).get("order", [])
        if isinstance((log.eval.model_args or {}).get("provider"), dict)
        else []
    )
    receipt = {
        "benchmark": "TriageBench",
        "benchmark_version": "v0.1",
        "split": split,
        "status": log.status,
        "model": log.eval.model,
        "returned_models": returned_models,
        "returned_providers": returned_providers,
        "requested_provider_order": requested_provider_order,
        "model_base_url": log.eval.model_base_url,
        "model_args": log.eval.model_args,
        "generate_config": _serialise(log.eval.model_generate_config),
        "prompt_version": PROMPT_VERSION,
        "model_inputs_sha256": sha256_text(stable_json(model_inputs)),
        "cases_sha256": benchmark.manifest["file_sha256"]["cases.jsonl"],
        "pairs_sha256": benchmark.manifest["file_sha256"]["counterfactual-pairs.jsonl"],
        "predictions_sha256": sha256_text(prediction_body),
        "git": _git_state(),
        "inspect_ai_version": importlib.metadata.version("inspect-ai"),
        "started_at": log.stats.started_at,
        "completed_at": log.stats.completed_at,
        "log_location": log.location,
        "usage": _usage(log),
        "metrics": metrics,
        "invalid_outputs": len(responses) - len(predictions),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "predictions.jsonl").write_text(prediction_body, encoding="utf-8")
    (output / "responses.jsonl").write_text(
        "".join(stable_json(value) + "\n" for value in responses), encoding="utf-8"
    )
    (output / "score.json").write_text(stable_json(metrics, pretty=True) + "\n", encoding="utf-8")
    (output / "receipt.json").write_text(stable_json(receipt, pretty=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export TriageBench predictions and receipt")
    parser.add_argument("log", type=Path)
    parser.add_argument("--split", choices=["sample", "public", "train", "validation", "test"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    log = read_eval_log(args.log, resolve_attachments="core")
    split = args.split or (log.eval.task_args or {}).get("split") or "sample"
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or repository_root() / ".local/evals/runs" / f"{timestamp}-{split}"
    print(write_run_artifacts(log, split, output))
