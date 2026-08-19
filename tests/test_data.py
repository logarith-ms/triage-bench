from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from triage_bench.data import file_sha256, load_split


class DataTests(unittest.TestCase):
    def test_bundled_sample_is_valid(self):
        benchmark = load_split("sample")
        self.assertEqual(len(benchmark.tasks), 6)
        self.assertEqual(len(benchmark.pairs), 3)
        self.assertTrue(benchmark.manifest["fixture"])

    def test_hidden_test_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "hidden test split is locked"):
            load_split("test")


class PublicSplitTests(unittest.TestCase):
    def test_public_split_loads_from_release_root(self):
        bundled = load_split("sample")
        with tempfile.TemporaryDirectory() as temporary:
            public = Path(temporary) / "public"
            public.mkdir()
            tasks = public / "tasks.jsonl"
            pairs = public / "matched-pairs.jsonl"
            tasks.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in bundled.tasks), encoding="utf-8")
            pairs.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in bundled.pairs), encoding="utf-8")
            (public / "manifest.json").write_text(json.dumps({
                "counts": {"tasks": len(bundled.tasks)},
                "file_sha256": {"tasks.jsonl": file_sha256(tasks), "matched-pairs.jsonl": file_sha256(pairs)},
            }), encoding="utf-8")
            loaded = load_split("public", release_root=Path(temporary))
            self.assertEqual(len(loaded.tasks), 6)


if __name__ == "__main__":
    unittest.main()
