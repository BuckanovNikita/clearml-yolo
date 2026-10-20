# Validation sequence

Run the repository's frozen/no-sync Ruff, mypy, Vulture, lint-imports and pytest commands.
Run `uv run --frozen --no-sync python scripts/check_docs.py --all` and explicitly include new
Markdown before staging. Validate architecture plan/acceptance using the installed shared skill.
Complete the existing real feature036 acceptance before checkpoint/release. Verify original
fixture SHA-256 hashes after relocation. At cutoff verify archived paths with `git cat-file`,
validate all retained docs and use `create-new-feature.sh --dry-run --json` to prove next ID 001.
These directions specify checks; actual outcomes belong in verification evidence.
