# Release validation guide

Use Python/toolchain from pyproject.toml. Run `uv sync --group dev` then `uv run cy --help`.
See [CLI](contracts/cli.md) and [artifacts](contracts/artifacts.md) for exact contracts.

1. Run pytest, Ruff, mypy, import-linter and applicable pre-commit checks.
2. Read the shared infrastructure run contract and project end-to-end skill. Source
   `scripts/agent_env.sh release-030`, respect room/capacity, and select CPU or device 0 explicitly.
3. Build ground truth from a tiny YOLO dataset with disjoint val/test. Train one epoch on CPU
   with raw native cfg, then a one-GPU candidate with equivalent embedded native settings.
4. In the task-owned project first confirm automatic baseline absence, then tag the baseline
   prod and compare the candidate. Exercise cy-val and cy-compare independently.
5. Download required artifacts and check file hashes/contents and one-task ownership; induce
   upload failure and interruption using isolated test tasks. Preserve dated evidence, then
   call scripts/agent_cleanup.sh and prove task-owned resource removal.
6. Build with `uv build`, install each distribution into fresh temporary environments, verify
   eight command helps and absent cy-queue/cy-init-config. Run documented examples.

Record executed commands, task identities, outcomes and artifact download evidence under
`docs/evidence/2026-09-19-release-030.md`. Real multi-GPU execution is explicitly unverified.
