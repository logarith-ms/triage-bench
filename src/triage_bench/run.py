from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from inspect_ai import eval
from inspect_ai.model import ModelCost, ModelInfo, get_model_info, set_model_info

from .data import repository_root
from .receipt import write_run_artifacts
from .task import triage_bench


def openrouter_policy(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict[str, Any]:
    if not args.model.startswith("openrouter/"):
        if args.openrouter_provider or args.probe_provider:
            parser.error("OpenRouter routing flags require an openrouter/... model")
        return {}
    if args.probe_provider:
        if args.openrouter_provider:
            parser.error("--probe-provider cannot be combined with --openrouter-provider")
        if args.limit != 1:
            parser.error("--probe-provider requires --limit 1")
        return {"provider": {"allow_fallbacks": True, "data_collection": "deny", "zdr": True}}
    if not args.openrouter_provider:
        parser.error("OpenRouter scored runs require --openrouter-provider; probe one case first")
    return {
        "provider": {
            "order": [args.openrouter_provider],
            "allow_fallbacks": False,
            "data_collection": "deny",
            "zdr": True,
        }
    }


def register_model_cost(
    model: str,
    config_path: Path | None,
    parser: argparse.ArgumentParser,
    required: bool,
) -> None:
    if config_path is None:
        if required:
            parser.error("--cost-limit requires --model-cost-config")
        return
    try:
        cost_config = json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"Unable to read model cost config {config_path}: {error}")
    raw_cost = cost_config.get(model)
    if raw_cost is None:
        if required:
            parser.error(f"No model cost data for {model} in {config_path}")
        return

    info = get_model_info(model) or ModelInfo(
        organization=model.split("/")[-2] if "/" in model else None,
        model=model.rsplit("/", 1)[-1],
    )
    set_model_info(model, info.model_copy(update={"cost": ModelCost(**raw_cost)}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a model on TriageBench")
    parser.add_argument("--model", required=True, help="Inspect provider/model identifier")
    parser.add_argument("--model-base-url")
    parser.add_argument("--model-arg", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--openrouter-provider", help="Pinned OpenRouter provider slug")
    parser.add_argument("--probe-provider", action="store_true", help="Allow one unpinned case to discover a provider")
    parser.add_argument(
        "--split", default="sample", choices=["sample", "public", "train", "validation", "test"]
    )
    parser.add_argument("--allow-hidden-test", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--max-connections", type=int, default=10)
    parser.add_argument("--max-samples", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--cost-limit", type=float)
    parser.add_argument(
        "--model-cost-config",
        type=Path,
        default=repository_root() / "config/openrouter-costs-2026-08-18.json",
        help="Inspect model pricing in USD per million tokens",
    )
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--display", default="full", choices=["full", "plain", "log", "none"])
    args = parser.parse_args()

    model_args: dict[str, Any] = {}
    for item in args.model_arg:
        if "=" not in item:
            parser.error(f"--model-arg must use KEY=VALUE: {item}")
        key, raw_value = item.split("=", 1)
        try:
            model_args[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            model_args[key] = raw_value
    routing = openrouter_policy(args, parser)
    if "provider" in model_args and routing:
        parser.error("Use OpenRouter routing flags instead of --model-arg provider=...")
    model_args.update(routing)
    register_model_cost(args.model, args.model_cost_config, parser, args.cost_limit is not None)

    root = repository_root()
    log_dir = root / ".local/evals/inspect-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        benchmark_task = triage_bench(split=args.split, allow_hidden_test=args.allow_hidden_test)
    except (ValueError, FileNotFoundError) as error:
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


if __name__ == "__main__":
    main()
