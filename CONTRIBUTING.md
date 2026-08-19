# Contributing

Issues and pull requests for the public runner, schemas and documentation are welcome.

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run triage-bench-baselines --split sample
```

Do not submit patient information, licensed pathway content, private evaluation cases or hidden answers. Security and data-exposure concerns should be sent privately to [labs@logarith.ms](mailto:labs@logarith.ms), not opened as public issues.
