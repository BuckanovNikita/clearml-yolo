# Dependency acceptance — 2026-10-20

The standard installation declares all 36 runtime requirements, including the former
`queue-ui`, `detectors`, and `export` requirements. The project advertises no extras.
Upstream `rfdetr[train]` and `pandera[pandas]` extras remain enabled; development tools
remain in the development group.

## Minimum-version method

The matrix uses Python 3.12.13 and 3.13.14 on Linux x86_64 and uv 0.11.32.
Runtime input requirements were generated from the current `pyproject.toml`; unchanged
approved `digital-metrics` and `report-generator` source copies were built into wheels
and supplied locally. Source-directory inputs caused uv to treat those projects'
requirements as direct dependencies too; wheel inputs keep this investigation scoped
to this project's direct requirements.

Separate `uv pip compile --resolution lowest-direct --python <interpreter>` resolutions
select minimum direct versions with compatible transitive requirements. They do not
replace the normal project lock. Python 3.13 wheel availability was checked with
`--only-binary aiohttp,pandas,numpy,scipy,pyyaml,pydantic-core`, then the common supported
floors were tested on both interpreters. The final resolutions use the declared floors
without supplemental constraints. All direct versions remain at those resolutions during
testing; the release-tooling transitive adjustment is recorded below.
See [uv resolution strategy](https://docs.astral.sh/uv/concepts/resolution/#resolution-strategy).

The common wheel-backed floors are aiohttp 3.10.5, NumPy 2.1.0, pandas 2.2.3,
SciPy 1.14.1 and PyYAML 6.0.2. This evidence establishes the tested common Linux matrix,
not every possible source build or platform. Initial PyYAML 6.0 installation failed on
both interpreters with the upstream `build_ext.cython_sources` build error. Pillow 12.2.0
and Pydantic 2.9.2 were initially imposed by the dependency graph; Pydantic needed the
additional application-specific correction below. Other retained or normalized floors
are listed in the companion JSON alongside installed versions.

Two functional probes determine the important SDK/schema floors:

- Published ClearML wheel source from 2.1.0 through 2.1.5 lacks the `files` parameter on
  `Dataset.get_local_copy`; 2.1.6 introduces it. The installed 2.1.6 SDK also exposes
  `list_files` and `is_final`, so `clearml>=2.1.6` is required by CSV-only retrieval.
- Pydantic 2.9.2 fails the existing offline DDP configuration/queue-composition test with
  `PydanticSchemaGenerationError` for the native `GroundTruthInput` type alias. The small
  reproducer `type Example = str | Path; TypeAdapter(Example)` fails too. Pydantic 2.10.0
  passes the reproducer and original failing test on both supported interpreters;
  the declared floor is `pydantic>=2.10.0`.

The protected `digital-metrics>=0.6.1` reference remains unchanged. Verification uses the
approved source revision, whose package metadata identifies version 0.7.0. This is not
a claim that an arbitrary registry distribution at 0.6.1 implements the approved APIs.
Both external dependency lock records are unchanged. Normal lock third-party package
identities, versions and sources are unchanged. Root-package requirements/extras metadata
changes, and integration of upstream commit `41a4036` advances the root version to 0.35.0.

## Verification procedure

The minimum environments install the compiled runtime set, the built application wheel,
and the separate test tools pytest, Hypothesis, pytest-cov, import-linter, pre-commit and
python-semantic-release. The latter two are required by the repository's real hook and
release-preservation tests. Their normal locked versions are used: pre-commit 4.6.1 and
python-semantic-release 10.7.0. The semantic-release tool requires Deprecated below 2,
so only that transitive runtime selection changes from 3.0.0 to the normal lock's 1.3.1
in the minimum test environments. All direct minima and every other resolved runtime
version remain unchanged. Test tools are not introduced into application runtime
requirements or the separate default-install environments. The complete matrix invokes
`python -m pytest -x -q --basetemp <owned-directory-outside-the-repository>` with absolute
`PYTHONPATH` entries for the current checkout's `src` and `tests` and
`NO_ALBUMENTATIONS_UPDATE=1` and `UV_FROZEN=1`. The outside-repository base directory preserves the docs
checker's non-repository fixtures and avoids concurrent pytest retention races.

Independent empty environments install the application wheel without extras together
with the two approved external wheels, constrained by
`uv export --frozen --no-dev --no-emit-project --no-emit-package digital-metrics
--no-emit-package report-generator --no-hashes`. This retains the established external
source prerequisite while proving that the application wheel itself requests every
runtime capability by default.

Outside the checkout, the installed wheel is checked for absent `Provides-Extra` and
unconditional requirements. Smoke checks import Torch, torchvision, timm, RF-DETR,
PyTorch Lightning, ONNX, ONNX Runtime, Albumentations, FiftyOne and the queue TUI; inspect
the ClearML selective-download API; run all 12 installed command help pages; and export
configuration to an isolated directory under `CY_HOME`. FiftyOne services are disabled
for this import-only probe. These checks do not claim real model export, GPU execution,
FiftyOne publication or ClearML server retrieval.

## Results

- Built-wheel installation without project extras: passed on Python 3.12.13 and 3.13.14.
- `uv pip check`: passed in all four isolated environments.
- Outside-checkout default-wheel imports, 12 command help pages and configuration export:
  passed on both interpreters.
- Packaging and development-dependency boundary tests: 35 passed; focused Ruff and mypy
  checks passed.
- The initial focused minimum runtime matrix passed 311 tests per interpreter; one
  subprocess fixture failed because its initial relative `PYTHONPATH` could not locate
  the application after changing directories. Installing the wheel and using absolute
  source paths corrected that setup issue.
- The full minimum matrix with Pydantic 2.10.0 reached 1,547 passing tests, one skip and
  seven deselected physical GPU cases on each interpreter before stopping at
  `test_export_workflow.py::test_missing_inputs_fail_before_task_creation`. This matches
  the normal-environment application regression, subsequently fixed by validating
  export inputs before task creation. No dependency-floor workaround was applied.
- After the export fix and upstream integration, each complete minimum-suite invocation
  reached 3,129 passing tests, 30 skips and seven deselections before stopping at the
  old exact `WorkflowDependencies` constructor expectation in
  `test_shared_comparison.py`. The feature adds a repository port; correction of that
  compatibility contract and its regression expectations is tracked by the parent.
  These stopped runs alone do not establish complete acceptance.

The companion JSON preserves exact installed distributions, the wheel digest, published
ClearML wheel probe URLs, direct requirements and check results. Task-owned environments
and logs are retained under the ignored `.tmp/dependencies-036` directory for review.
