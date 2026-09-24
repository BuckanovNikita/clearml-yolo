# Release validation guide

Use Python/toolchain from pyproject.toml. Run `uv sync --group dev` then `uv run cy --help`.
See [CLI](contracts/cli.md) and [artifacts](contracts/artifacts.md) for exact contracts.

1. Run pytest, Ruff, mypy, import-linter and applicable pre-commit checks.
2. Follow the environment's setup and resource-ownership instructions. Configure an
   isolated ClearML project and select native devices explicitly.
3. Build ground truth from a tiny YOLO dataset with disjoint val/test and empty images.
   Train one epoch on CPU with raw native YAML, then a single-GPU candidate with equivalent
   embedded settings. An unavailable device leaves that release gate unverified.
4. First confirm automatic baseline absence, then tag the completed baseline `prod` and
   compare the candidate. Exercise cy-val, cy-compare and cy-report independently.
5. Download required artifacts; check contents, thresholds, paired counts and one-task
   ownership. Induce upload failure and interruption using isolated test tasks.
6. Build with `uv build`, install each distribution in a fresh environment, verify eight
   command helps and absent cy-queue/cy-init-config. Run documented examples.
7. Record dated outcomes and limitations, then remove only owned resources. Physical
   distributed execution is unverified unless actually tested.

Keep a portable summary under `docs/evidence/`. Machine-specific commands, task identities,
endpoint details and download records belong with the environment's global skill.
