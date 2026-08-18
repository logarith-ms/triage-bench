from types import SimpleNamespace
from unittest import TestCase

from triage_bench.receipt import _model_call_metadata, _sample_error_message


class ModelCallMetadataTests(TestCase):
    def test_reads_provider_from_raw_model_response(self) -> None:
        sample = SimpleNamespace(
            events=[
                SimpleNamespace(event="state"),
                SimpleNamespace(
                    event="model",
                    call=SimpleNamespace(
                        response={
                            "id": "gen-123",
                            "model": "qwen/qwen3.5-9b",
                            "provider": "DeepInfra",
                        }
                    ),
                ),
            ]
        )

        self.assertEqual(
            _model_call_metadata(sample),
            [
                {
                    "id": "gen-123",
                    "model": "qwen/qwen3.5-9b",
                    "provider": "DeepInfra",
                }
            ],
        )

    def test_ignores_model_events_without_response_metadata(self) -> None:
        sample = SimpleNamespace(
            events=[SimpleNamespace(event="model", call=SimpleNamespace(response=None))]
        )

        self.assertEqual(_model_call_metadata(sample), [])


class SampleErrorTests(TestCase):
    def test_reads_sample_error_without_copying_traceback(self) -> None:
        sample = SimpleNamespace(
            error=SimpleNamespace(message="No zero-retention endpoint", traceback="private")
        )

        self.assertEqual(
            _sample_error_message(sample),
            "No zero-retention endpoint",
        )

    def test_missing_sample_error_is_none(self) -> None:
        self.assertIsNone(_sample_error_message(SimpleNamespace(error=None)))
