from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import score_predictions, stable_json
from .data import load_split


def load_predictions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        values = [json.loads(line) for line in handle if line.strip()]
    required = {"task_id", "selected_option_id"}
    for line, value in enumerate(values, start=1):
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError(f"Invalid prediction contract on record {line}")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Score TriageBench JSONL predictions")
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--split", default="sample", choices=["sample", "public", "train", "validation", "test"])
    parser.add_argument("--allow-hidden-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    benchmark = load_split(args.split, allow_hidden_test=args.allow_hidden_test)
    predictions = load_predictions(args.predictions)
    metrics = score_predictions(benchmark.tasks, benchmark.pairs, predictions)
    rendered = stable_json(metrics, pretty=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
