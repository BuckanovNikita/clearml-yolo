# Validation guide

Use an idle cache. Preview before applying:

```bash
uv run cy-dedup --help
uv run cy-dedup --dry-run
uv run cy-dedup /path/to/cache
uv run pytest tests/test_dedup.py tests/test_dedup_cli.py
```

See the [CLI contract](contracts/cli.md). The native test uses temporary fixtures,
requires actual reflink support and checks independent writes; unsupported storage is
an explicit skip. No GPU, ClearML credentials or downloaded datasets are required.
