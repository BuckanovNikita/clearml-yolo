# Release validation guide

Use Python/toolchain from pyproject.toml. Run `git submodule update --init --recursive`,
then `uv sync --locked --group dev` and `uv run cy --help`. Both external dependencies
are installed editable from `external/`. For installations without submodules, select
Git sources using the [installation instructions](../../README.md#установка).
See [CLI](contracts/cli.md) and [artifacts](contracts/artifacts.md) for exact contracts.

1. Run pytest, Ruff, mypy, import-linter and applicable pre-commit checks.
2. Follow the environment's setup and resource-ownership instructions. Configure an
   isolated ClearML project and select native devices explicitly.
3. Build ground truth from a tiny YOLO dataset with disjoint val/test and empty images.
   Train one epoch on CPU through `ultralytics/default.yaml`, then run a single-GPU candidate
   with equivalent top-level group overrides. An unavailable device leaves that gate unverified.
4. First confirm automatic baseline absence, then tag the completed baseline `prod` and
   compare the candidate. Exercise cy-val, cy-compare and cy-report independently.
5. Download required artifacts; check contents, thresholds, paired counts and one-task
   ownership. Induce upload failure and interruption using isolated test tasks.
6. Build with `uv build`, install each distribution in a fresh environment, verify nine
   command helps and absent cy-queue. Run `cy-init-config` into a fresh directory, check
   all eight command examples and both native group files compose as applicable; verify
   overwrite protection. Run documented examples.
7. Record dated outcomes and limitations, then remove only owned resources. Physical
   distributed execution is unverified unless tested.

Keep a portable summary under `docs/evidence/`. Machine-specific commands, task identities,
endpoint details and download records belong with the environment's global skill.
