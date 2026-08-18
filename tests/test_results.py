from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublishedResultsTests(unittest.TestCase):
    def test_public_results_match_frozen_run_configuration(self):
        results = json.loads((ROOT / "results/v0.1/public-100.json").read_text())
        config = json.loads((ROOT / "config/runs/public-100.json").read_text())

        self.assertEqual(results["benchmark_version"], config["benchmark_version"])
        self.assertEqual(results["cases"], config["cases"])
        self.assertEqual(results["settings"]["epochs"], config["epochs"])
        self.assertEqual(results["settings"]["seed"], config["seed"])
        self.assertEqual(results["settings"]["max_tokens"], config["max_tokens"])
        self.assertEqual(
            {result["model"] for result in results["results"]},
            set(config["models"]),
        )
        for result in results["results"]:
            self.assertEqual(result["provider"], config["providers"][result["model"]])

    def test_public_results_are_complete_and_ranked(self):
        release = json.loads((ROOT / "results/v0.1/public-100.json").read_text())
        results = release["results"]

        self.assertEqual([result["rank"] for result in results], [1, 2, 3])
        self.assertEqual(
            [result["metrics"]["exact_decision_accuracy"] for result in results],
            sorted(
                (result["metrics"]["exact_decision_accuracy"] for result in results),
                reverse=True,
            ),
        )
        for result in results:
            self.assertEqual(result["metrics"]["valid_output_rate"], 1.0)
            self.assertEqual(len(result["predictions_sha256"]), 64)
            self.assertEqual(len(result["source_receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
