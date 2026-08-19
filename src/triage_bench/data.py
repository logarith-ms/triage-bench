from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SPLITS = {"sample", "public", "train", "validation", "test"}


def repository_root() -> Path:
    configured = os.environ.get("TRIAGE_BENCH_REPOSITORY_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    current = Path.cwd().resolve()
    if (current / ".git").exists() or (current / "pyproject.toml").exists():
        return current
    return Path(__file__).resolve().parents[2]


def default_release_root() -> Path:
    configured = os.environ.get("TRIAGE_BENCH_RELEASE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parent / "sample_data" / "v0.2"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@dataclass(frozen=True)
class BenchmarkSplit:
    name: str
    directory: Path
    tasks: list[dict[str, Any]]
    pairs: list[dict[str, Any]]
    manifest: dict[str, Any]


def load_split(
    split: str = "sample",
    *,
    allow_hidden_test: bool = False,
    release_root: Path | None = None,
) -> BenchmarkSplit:
    if split not in SPLITS:
        raise ValueError(f"Unknown split: {split}")
    if split == "test" and not allow_hidden_test:
        raise ValueError(
            "The hidden test split is locked. Use validation for development. "
            "A final test run requires --allow-hidden-test."
        )
    if split == "sample" and release_root is None and not os.environ.get("TRIAGE_BENCH_RELEASE_ROOT"):
        directory = default_release_root() / split
    else:
        root = release_root or Path(
            os.environ.get("TRIAGE_BENCH_RELEASE_ROOT", repository_root() / ".local/releases/v0.2")
        ).expanduser().resolve()
        directory = root / split

    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing benchmark release at {directory}. "
            "Use the bundled sample or set TRIAGE_BENCH_RELEASE_ROOT."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for filename in ("tasks.jsonl", "matched-pairs.jsonl"):
        expected = manifest["file_sha256"][filename]
        observed = file_sha256(directory / filename)
        if observed != expected:
            raise ValueError(f"Hash mismatch for {directory / filename}")

    tasks = load_jsonl(directory / "tasks.jsonl")
    pairs = load_jsonl(directory / "matched-pairs.jsonl")
    seen: set[str] = set()
    for task in tasks:
        task_id = task["task_id"]
        if task_id in seen:
            raise ValueError(f"Duplicate benchmark task: {task_id}")
        seen.add(task_id)
        options = task["model_input"].get("options")
        if not isinstance(options, list) or [option["option_id"] for option in options] != ["A", "B", "C", "D"]:
            raise ValueError(f"Task {task_id} must expose options A-D")
        if task["reference"]["correct_option_id"] not in {option["option_id"] for option in options}:
            raise ValueError(f"Task {task_id} has an invalid answer key")
    if len(tasks) != manifest["counts"]["tasks"]:
        raise ValueError(f"Task count does not match {manifest_path}")
    return BenchmarkSplit(split, directory, tasks, pairs, manifest)
