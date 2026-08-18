import json
from argparse import ArgumentParser, Namespace
from unittest import TestCase

from triage_bench.data import repository_root
from inspect_ai.model import get_model_info

from triage_bench.run import openrouter_policy, register_model_cost


class OpenRouterPolicyTests(TestCase):
    def test_scored_run_requires_pinned_provider(self) -> None:
        args = Namespace(
            model="openrouter/qwen/qwen3.5-9b",
            openrouter_provider=None,
            probe_provider=False,
            limit=20,
        )
        with self.assertRaises(SystemExit):
            openrouter_policy(args, ArgumentParser())

    def test_scored_run_disables_fallback_and_data_collection(self) -> None:
        args = Namespace(
            model="openrouter/qwen/qwen3.5-9b",
            openrouter_provider="Together",
            probe_provider=False,
            limit=20,
        )
        self.assertEqual(
            openrouter_policy(args, ArgumentParser()),
            {
                "provider": {
                    "order": ["Together"],
                    "allow_fallbacks": False,
                    "data_collection": "deny",
                    "zdr": True,
                }
            },
        )

    def test_probe_is_limited_to_one_case(self) -> None:
        args = Namespace(
            model="openrouter/qwen/qwen3.5-9b",
            openrouter_provider=None,
            probe_provider=True,
            limit=2,
        )
        with self.assertRaises(SystemExit):
            openrouter_policy(args, ArgumentParser())

    def test_every_staged_openrouter_model_has_cost_data(self) -> None:
        root = repository_root()
        costs = json.loads(
            (root / "config/openrouter-costs-2026-08-18.json").read_text()
        )
        models = set()
        for manifest in (root / "config/runs").glob("*.json"):
            models.update(json.loads(manifest.read_text()).get("models", []))

        for model in models:
            with self.subTest(model=model):
                self.assertIn(model, costs)
                self.assertEqual(
                    set(costs[model]),
                    {"input", "output", "input_cache_write", "input_cache_read"},
                )
                self.assertTrue(all(value >= 0 for value in costs[model].values()))

    def test_unknown_openrouter_model_can_receive_cost_data(self) -> None:
        model = "openrouter/mistralai/ministral-3b-2512"
        register_model_cost(
            model,
            repository_root() / "config/openrouter-costs-2026-08-18.json",
            ArgumentParser(),
            required=True,
        )
        info = get_model_info(model)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertIsNotNone(info.cost)
        assert info.cost is not None
        self.assertEqual(info.cost.input, 0.1)
        self.assertEqual(info.cost.output, 0.1)
