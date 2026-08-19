from __future__ import annotations

import json
import unittest

from triage_bench.baselines import predictions_for
from triage_bench.core import build_prompt, model_input, parse_prediction, score_predictions


def sample_task(task_id: str = "task-1", correct: str = "C"):
    return {
        "task_id": task_id,
        "benchmark_version": "v0.2",
        "model_input": {
            "geography": "GB",
            "language": "en-GB",
            "conversation": [
                {"role": "assistant", "content": "What symptom concerns you?"},
                {"role": "patient", "content": "I have pain."},
            ],
            "instruction": "Choose the single best next action and return one option ID.",
            "options": [
                {"option_id": "A", "text": "Ask about duration."},
                {"option_id": "B", "text": "Recommend routine review."},
                {"option_id": "C", "text": "Ask about sudden onset."},
                {"option_id": "D", "text": "Recommend urgent review."},
            ],
        },
        "reference": {
            "correct_option_id": correct,
            "required_action": "ask_question",
            "matched_pair_id": None,
            "task_design": "next_question",
            "task_form": "next_question_selection",
        },
        "provenance": {"private": True},
    }


class CoreTests(unittest.TestCase):
    def test_prompt_exposes_options_but_not_reference(self):
        prompt = build_prompt(sample_task())
        self.assertIn("C. Ask about sudden onset.", prompt)
        self.assertIn("selected_option_id", prompt)
        self.assertNotIn('"reference"', prompt)
        self.assertNotIn("provenance", prompt)
        self.assertNotIn("private", json.dumps(model_input(sample_task())))

    def test_parser_is_strict_and_option_bound(self):
        options = sample_task()["model_input"]["options"]
        self.assertTrue(parse_prediction('{"selected_option_id":"C"}', options).valid)
        self.assertFalse(parse_prediction("```json\n{}\n```", options).valid)
        self.assertFalse(parse_prediction('{"selected_option_id":"E"}', options).valid)
        self.assertFalse(parse_prediction('{"selected_option_id":"C","reason":"x"}', options).valid)

    def test_oracle_scores_one(self):
        task = sample_task()
        prediction = {"task_id": task["task_id"], "selected_option_id": "C"}
        score = score_predictions([task], [], [prediction])
        self.assertEqual(score["exact_decision_accuracy"], 1)
        self.assertEqual(score["coverage"], 1)

    def test_invalid_attempt_counts_as_wrong(self):
        task = sample_task()
        score = score_predictions([task], [], [], attempted_task_ids=[task["task_id"]])
        self.assertEqual(score["coverage"], 1)
        self.assertEqual(score["valid_output_rate"], 0)
        self.assertEqual(score["exact_decision_accuracy"], 0)

    def test_random_baseline_is_reproducible(self):
        tasks = [sample_task("task-1"), sample_task("task-2")]
        first = predictions_for("random-option", tasks, seed=42)
        second = predictions_for("random-option", tasks, seed=42)
        self.assertEqual(first, second)


class ConfidenceIntervalTests(unittest.TestCase):
    def test_perfect_score_has_bounded_confidence_interval(self):
        task = sample_task()
        metrics = score_predictions(
            [task], [], [{"task_id": task["task_id"], "selected_option_id": "C"}]
        )
        interval = metrics["confidence_intervals_95"]["exact_decision_accuracy"]
        self.assertGreaterEqual(interval["low"], 0)
        self.assertEqual(interval["high"], 1)


if __name__ == "__main__":
    unittest.main()
