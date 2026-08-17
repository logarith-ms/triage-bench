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
        candidates = list((state.metadata or {}).get("candidates", []))
        raw = state.output.completion if state.output is not None else ""
        parsed = parse_prediction(raw, candidates)
        exact = (
            parsed.valid
            and parsed.action_type == reference["action_type"]
            and parsed.target_node_id == reference["target_node_id"]
        )
        return Score(
            value=int(exact),
            answer=raw,
            explanation=parsed.error,
            metadata={
                "valid_output": parsed.valid,
                "action_correct": parsed.action_type == reference["action_type"],
                "target_correct": parsed.target_node_id == reference["target_node_id"],
            },
        )

    return score


@task(name="triage_bench")
def triage_bench(split: str = "sample", allow_hidden_test: bool = False) -> Task:
    benchmark = load_split(split, allow_hidden_test=allow_hidden_test)
    samples = [
        Sample(
            id=case["case_id"],
            input=build_prompt(case),
            target=json.dumps(
                {
                    "action_type": case["reference"]["action_type"],
                    "target_node_id": case["reference"]["target_node_id"],
                },
                sort_keys=True,
            ),
            metadata={
                "candidates": case["candidates"],
                "prompt_version": PROMPT_VERSION,
                "split": split,
            },
        )
        for case in benchmark.cases
    ]
    return Task(
        dataset=MemoryDataset(samples, name=f"triage-bench-v0.1-{split}"),
        solver=generate(),
        scorer=exact_decision(),
        version="0.1.0",
        metadata={
            "benchmark": "TriageBench",
            "benchmark_version": "v0.1",
            "split": split,
            "prompt_version": PROMPT_VERSION,
            "cases_sha256": benchmark.manifest["file_sha256"]["cases.jsonl"],
        },
    )
