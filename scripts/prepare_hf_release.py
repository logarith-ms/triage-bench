from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the public TriageBench Hugging Face release")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".local/hf-release"))
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    expected = {"ask_question_cases": 30, "cases": 100, "counterfactual_pairs": 152, "return_assessment_cases": 70}
    if manifest["counts"] != expected:
        raise ValueError(f"Unexpected public release counts: {manifest['counts']}")
    for filename in ("cases.jsonl", "counterfactual-pairs.jsonl"):
        if sha256(source / filename) != manifest["file_sha256"][filename]:
            raise ValueError(f"Hash mismatch: {filename}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for filename in ("cases.jsonl", "counterfactual-pairs.jsonl", "manifest.json"):
        shutil.copy2(source / filename, output / filename)
    shutil.copy2("docs/HUGGING_FACE_DATASET_CARD.md", output / "README.md")
    shutil.copy2("DATA_LICENSE", output / "DATA_LICENSE")
    schemas = output / "schemas"
    schemas.mkdir()
    for filename in ("public-case.schema.json", "counterfactual-pair.schema.json", "task-schema.json"):
        shutil.copy2(Path("schemas") / filename, schemas / filename)
    print(output)


if __name__ == "__main__":
    main()
