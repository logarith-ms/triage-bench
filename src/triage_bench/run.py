from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import json

from inspect_ai import eval

from .data import repository_root
from .receipt import write_run_artifacts
from .task import triage_bench


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a model on TriageBench")
    parser.add_argument("--model", required=True, help="Inspect provider/model identifier")
    parser.add_argument("--model-base-url")
    parser.add_argument("--model-arg", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument(
        "--split", default="sample", choices=["sample", "train", "validation", "test"]
    )
    parser.add_argument("--allow-hidden-test", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tokens", type=int, default=120)
    parser.add_argument("--max-connections", type=int, default=10)
    parser.add_argument("--max-samples", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--cost-limit", type=float)
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--display", default="full", choices=["full", "plain", "log", "none"])
    args = parser.parse_args()

    model_args = {}
    for item in args.model_arg:
        if "=" not in item:
            parser.error(f"--model-arg must use KEY=VALUE: {item}")
        key, raw_value = item.split("=", 1)
        try:
            model_args[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            model_args[key] = raw_value

    root = repository_root()
    log_dir = root / ".local/evals/inspect-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        benchmark_task = triage_bench(split=args.split, allow_hidden_test=args.allow_hidden_test)
    except ValueError as error:
        parser.error(str(error))
    logs = eval(
        benchmark_task,
        model=args.model,
        model_base_url=args.model_base_url,
        model_args=model_args,
        log_dir=str(log_dir),
        limit=args.limit,
        display=args.display,
        max_connections=args.max_connections,
        max_samples=args.max_samples,
        max_retries=args.max_retries,
        timeout=args.timeout,
        temperature=args.temperature,
        seed=args.seed,
        max_tokens=args.max_tokens,
        cost_limit=args.cost_limit,
        reasoning_effort=args.reasoning_effort,
        fail_on_error=False,
    )
    if len(logs) != 1:
        raise RuntimeError(f"Expected one Inspect log, received {len(logs)}")
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_slug = args.model.replace("/", "-").replace(":", "-")
    output = args.output or root / ".local/evals/runs" / f"{timestamp}-{model_slug}-{args.split}"
    written = write_run_artifacts(logs[0], args.split, output)
    print(f"Run status: {logs[0].status}")
    print(f"Inspect log: {logs[0].location}")
    print(f"Receipt: {written / 'receipt.json'}")
