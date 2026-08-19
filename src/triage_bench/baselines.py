from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

from .core import PROMPT_VERSION, score_predictions, stable_json
from .data import load_split, repository_root


def _select_first(task: dict[str, Any], _: int) -> str:
    return task["model_input"]["options"][0]["option_id"]


def _select_random(task: dict[str, Any], seed: int) -> str:
    options = task["model_input"]["options"]
    digest = hashlib.sha256(f"{seed}|{task['task_id']}".encode()).digest()
    return options[int.from_bytes(digest[:8], "big") % len(options)]["option_id"]


def _select_oracle(task: dict[str, Any], _: int) -> str:
    return task["reference"]["correct_option_id"]


def predictions_for(name: str, tasks: list[dict[str, Any]], *, seed: int) -> list[dict[str, str]]:
    selectors = {
        "first-option": _select_first,
        "random-option": _select_random,
        "oracle-self-test": _select_oracle,
    }
    selector = selectors[name]
    return [
        {"task_id": task["task_id"], "selected_option_id": selector(task, seed)}
        for task in tasks
    ]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(stable_json(value, pretty=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text("".join(stable_json(value) + "\n" for value in values), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic TriageBench baselines")
    parser.add_argument("--split", default="sample", choices=["sample", "public", "train", "validation", "test"])
    parser.add_argument("--allow-hidden-test", action="store_true")
    parser.add_argument("--baseline", action="append", choices=["first-option", "random-option", "oracle-self-test"])
    parser.add_argument("--self-test", action="store_true", help="Allow the oracle scorer self-test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    names = args.baseline or ["random-option", "first-option"]
    if "oracle-self-test" in names and not args.self_test:
        parser.error("oracle-self-test requires --self-test and must never be reported as a model result")
    benchmark = load_split(args.split, allow_hidden_test=args.allow_hidden_test)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output or repository_root() / ".local/evals/baselines"

    for name in names:
        output = output_root / f"{timestamp}-{name}-{args.split}"
        output.mkdir(parents=True, exist_ok=False)
        predictions = predictions_for(name, benchmark.tasks, seed=args.seed)
        metrics = score_predictions(benchmark.tasks, benchmark.pairs, predictions)
        receipt = {
            "benchmark": "TriageBench",
            "benchmark_version": "v0.2",
            "run_type": "oracle_self_test" if name == "oracle-self-test" else "baseline",
            "baseline": name,
            "split": args.split,
            "seed": args.seed,
            "prompt_version": PROMPT_VERSION,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "tasks_sha256": benchmark.manifest["file_sha256"]["tasks.jsonl"],
            "pairs_sha256": benchmark.manifest["file_sha256"]["matched-pairs.jsonl"],
            "metrics": metrics,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "cost_usd": 0,
        }
        _write_jsonl(output / "predictions.jsonl", predictions)
        _write_json(output / "score.json", metrics)
        _write_json(output / "receipt.json", receipt)
        print(f"{name}: {metrics['exact_decision_accuracy']:.6f} -> {output}")


if __name__ == "__main__":
    main()
