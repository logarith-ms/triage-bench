from __future__ import annotations

import unittest

from triage_bench.data import load_split


class DataTests(unittest.TestCase):
    def test_bundled_sample_is_valid(self):
        benchmark = load_split("sample")
        self.assertEqual(len(benchmark.cases), 6)
        self.assertEqual(len(benchmark.pairs), 3)
        self.assertTrue(benchmark.manifest["fixture"])

    def test_hidden_test_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "hidden test split is locked"):
            load_split("test")


if __name__ == "__main__":
    unittest.main()
