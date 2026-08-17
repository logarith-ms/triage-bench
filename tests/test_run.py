from argparse import ArgumentParser, Namespace
from unittest import TestCase

from triage_bench.run import openrouter_policy


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
