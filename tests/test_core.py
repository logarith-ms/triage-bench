from __future__ import annotations

import json
import unittest

from triage_bench.baselines import predictions_for
from triage_bench.core import build_prompt, model_input, parse_prediction, score_predictions


def sample_case(case_id: str = "case-1"):
    return {
        "case_id": case_id,
        "benchmark_version": "v0.1",
        "geography": "GB",
        "language": "en-GB",
        "pathway": {"family": "synthetic", "entry_complaint": "test"},
        "dialogue_prefix": [
            {"role": "assistant", "content": "Question?"},
            {"role": "patient", "content": "Answer"},
        ],
        "candidates": [
            {"action_type": "ask_question", "response_mode": "question", "target_node_id": "2", "content": {"text": "Next?"}},
            {"action_type": "return_assessment", "response_mode": "assessment", "target_node_id": "3", "content": {"summary": "Stop"}},
        ],
        "reference": {"action_type": "return_assessment", "target_node_id": "3"},
        "graph_trace": {"private": True},
    }


class CoreTests(unittest.TestCase):
    def test_prompt_exposes_candidates_but_not_reference(self):
        prompt = build_prompt(sample_case())
        self.assertIn("target_node_id: 3", prompt)
        self.assertNotIn('"reference"', prompt)
        self.assertNotIn("graph_trace", prompt)
        self.assertNotIn("private", json.dumps(model_input(sample_case())))

    def test_parser_is_strict_and_candidate_bound(self):
        candidates = sample_case()["candidates"]
        valid = parse_prediction('{"action_type":"return_assessment","target_node_id":"3"}', candidates)
        self.assertTrue(valid.valid)
        self.assertFalse(parse_prediction("```json\n{}\n```", candidates).valid)
        self.assertFalse(parse_prediction('{"action_type":"return_assessment","target_node_id":"999"}', candidates).valid)
        self.assertFalse(parse_prediction('{"action_type":"return_assessment","target_node_id":"3","reason":"x"}', candidates).valid)

    def test_oracle_scores_one(self):
        case = sample_case()
        predictions = [{"case_id": case["case_id"], **case["reference"]}]
        score = score_predictions([case], [], predictions)
        self.assertEqual(score["exact_decision_accuracy"], 1)
        self.assertEqual(score["coverage"], 1)

    def test_invalid_attempt_counts_as_wrong(self):
        case = sample_case()
        score = score_predictions([case], [], [], attempted_case_ids=[case["case_id"]])
        self.assertEqual(score["coverage"], 1)
        self.assertEqual(score["valid_output_rate"], 0)
        self.assertEqual(score["exact_decision_accuracy"], 0)

    def test_random_baseline_is_reproducible(self):
        cases = [sample_case("case-1"), sample_case("case-2")]
        first = predictions_for("random-candidate", cases, majority_action="return_assessment", seed=42)
        second = predictions_for("random-candidate", cases, majority_action="return_assessment", seed=42)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
