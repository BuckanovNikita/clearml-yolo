# Quickstart: validate the workflow

Prerequisites: `external/` populated, `uvx --from go-task-bin task local-deps` (wheelhouse and `uv.toml`), `uv sync --locked --dev`, `bash scripts/install-hooks.sh`.

1. Staging guard: edit two tracked files, stage one, `git commit` → refused, tree unchanged.
2. Message check: stage a change, `git commit -m "update stuff"` → refused.
3. Development verification: `uv run --locked task --exit-code verify` → passes; no live tests,
   no build.
4. Preflight: `uv run --locked task --exit-code infra-check` → 0 or 3 (report 3 as deferred).
5. Change acceptance on a clean tip: `uv run --locked task --exit-code acceptance`; afterwards
   `clearml.py --project clearml-yolo ls --prefix <tag>` is empty.
6. Mutation: `uv run --locked task --exit-code mutation -- --base master`.
7. Release rehearsal in a scratchpad `git clone --local` on `master` with a throwaway `fix:` commit: run
   `semantic-release version --print`, then the build command with `CY_RELEASE_CHECK=1`;
   `git diff --cached --name-only` ⊆ {pyproject.toml, uv.lock, CHANGELOG.md}; remove worktree.
8. Paired check: `uv run --locked task --exit-code paired-check` → prints both SHAs/versions.
9. Session status: `bash scripts/session_status.sh` → never fails.
