# Verification interface

`uv run --frozen --no-sync python scripts/verify.py` runs Ruff, mypy, Vulture, import-linter and one ordinary pytest unless matching success is reusable. `--force` executes fresh checks. `--docs` validates documentation with separate inputs and evidence. Hooks use this same entrypoint; partial/path-limited commit views cannot reuse a different view.

Mutation testing is a separate explicit acceptance command, selected by source module/function and governed by the development guide. It is never part of contributor/version hooks. Logs and receipt records do not publish secrets; test-affecting environment values contribute identity without being persisted as plaintext.
