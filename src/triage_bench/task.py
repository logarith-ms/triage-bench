from __future__ import annotations

import json

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState, generate

from .core import PROMPT_VERSION, build_prompt, parse_prediction
from .data import load_split


@scorer(metrics=[accuracy(), stderr()])
def exact_decision():
    async def score(state: TaskState, target: Target) -> Score:
        reference = json.loads(target.text)
        options = list((state.metadata or {}).get("options", []))
        raw = state.output.completion if state.output is not None else ""
        parsed = parse_prediction(raw, options)
        exact = parsed.valid and parsed.selected_option_id == reference["correct_option_id"]
        return Score(
            value=int(exact),
            answer=raw,
            explanation=parsed.error,
            metadata={
                "valid_output": parsed.valid,
                "selected_option_id": parsed.selected_option_id,
            },
        )

    return score


@task(name="triage_bench")
def triage_bench(split: str = "sample", allow_hidden_test: bool = False) -> Task:
    benchmark = load_split(split, allow_hidden_test=allow_hidden_test)
    samples = [
        Sample(
            id=record["task_id"],
            input=build_prompt(record),
            target=json.dumps(
                {"correct_option_id": record["reference"]["correct_option_id"]},
                sort_keys=True,
            ),
            metadata={
                "options": record["model_input"]["options"],
                "prompt_version": PROMPT_VERSION,
                "split": split,
            },
        )
        for record in benchmark.tasks
    ]
    return Task(
        dataset=MemoryDataset(samples, name=f"triage-bench-v0.2-{split}"),
        solver=generate(),
        scorer=exact_decision(),
        version="0.2.0",
        metadata={
            "benchmark": "TriageBench",
            "benchmark_version": "v0.2",
            "split": split,
            "prompt_version": PROMPT_VERSION,
            "tasks_sha256": benchmark.manifest["file_sha256"]["tasks.jsonl"],
        },
    )
