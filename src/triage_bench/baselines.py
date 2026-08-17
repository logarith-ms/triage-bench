from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

from .core import PROMPT_VERSION, score_predictions, stable_json
from .data import load_split, repository_root


def _select_first(case: dict[str, Any], _: str, __: int) -> dict[str, Any]:
    return case["candidates"][0]


def _select_random(case: dict[str, Any], _: str, seed: int) -> dict[str, Any]:
    digest = hashlib.sha256(f"{seed}|{case['case_id']}".encode()).digest()
    index = int.from_bytes(digest[:8], "big") % len(case["candidates"])
    return case["candidates"][index]


def _select_majority(case: dict[str, Any], majority_action: str, _: int) -> dict[str, Any]:
    matches = [candidate for candidate in case["candidates"] if candidate["action_type"] == majority_action]
    return matches[0] if matches else case["candidates"][0]


def _select_oracle(case: dict[str, Any], _: str, __: int) -> dict[str, Any]:
    return case["reference"]


def predictions_for(
    name: str,
    cases: list[dict[str, Any]],
    *,
    majority_action: str,
    seed: int,
) -> list[dict[str, str]]:
    selectors = {
        "first-candidate": _select_first,
        "random-candidate": _select_random,
        "train-majority-action": _select_majority,
        "always-ask": lambda case, _majority, seed: _select_majority(case, "ask_question", seed),
        "always-assess": lambda case, _majority, seed: _select_majority(case, "return_assessment", seed),
        "oracle-self-test": _select_oracle,
    }
    selector = selectors[name]
    predictions = []
    for case in cases:
        selected = selector(case, majority_action, seed)
        predictions.append({
            "case_id": case["case_id"],
            "action_type": selected["action_type"],
            "target_node_id": selected["target_node_id"],
        })
    return predictions


def _write_json(path: Path, value: Any) -> None:
    path.write_text(stable_json(value, pretty=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text("".join(stable_json(value) + "\n" for value in values), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic TriageBench baselines")
    parser.add_argument(
        "--split", default="sample", choices=["sample", "public", "train", "validation", "test"]
    )
    parser.add_argument("--allow-hidden-test", action="store_true")
    parser.add_argument("--baseline", action="append", choices=[
        "first-candidate", "random-candidate", "train-majority-action", "always-ask", "always-assess", "oracle-self-test"
    ])
    parser.add_argument("--self-test", action="store_true", help="Allow the oracle scorer self-test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    names = args.baseline or ["random-candidate", "always-ask", "always-assess"]
    if "oracle-self-test" in names and not args.self_test:
        parser.error("oracle-self-test requires --self-test and must never be reported as a model result")
    benchmark = load_split(args.split, allow_hidden_test=args.allow_hidden_test)
    training_split = "sample" if args.split == "sample" else "public" if args.split == "public" else "train"
    train = load_split(training_split)
    action_counts: dict[str, int] = {}
    for case in train.cases:
        action = case["reference"]["action_type"]
        action_counts[action] = action_counts.get(action, 0) + 1
    majority_action = max(action_counts, key=action_counts.get)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output or repository_root() / ".local/evals/baselines"

    for name in names:
        output = output_root / f"{timestamp}-{name}-{args.split}"
        output.mkdir(parents=True, exist_ok=False)
        predictions = predictions_for(
            name, benchmark.cases, majority_action=majority_action, seed=args.seed
        )
        metrics = score_predictions(benchmark.cases, benchmark.pairs, predictions)
        receipt = {
            "benchmark": "TriageBench",
            "benchmark_version": "v0.1",
            "run_type": "oracle_self_test" if name == "oracle-self-test" else "baseline",
            "baseline": name,
            "split": args.split,
            "seed": args.seed,
            "prompt_version": PROMPT_VERSION,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "cases_sha256": benchmark.manifest["file_sha256"]["cases.jsonl"],
            "pairs_sha256": benchmark.manifest["file_sha256"]["counterfactual-pairs.jsonl"],
            "train_majority_action": majority_action,
            "metrics": metrics,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "cost_usd": 0,
        }
        _write_jsonl(output / "predictions.jsonl", predictions)
        _write_json(output / "score.json", metrics)
        _write_json(output / "receipt.json", receipt)
        print(f"{name}: {metrics['exact_decision_accuracy']:.6f} -> {output}")
