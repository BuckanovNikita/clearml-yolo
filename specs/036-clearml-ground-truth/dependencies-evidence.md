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

Wheel availability establishes aiohttp 3.10.5, NumPy 2.1.0, SciPy 1.14.1 and
PyYAML 6.0.2 as the common tested floors. It initially permits pandas 2.2.3; the
preserved workbook contract requires pandas 3.0.0 as explained below. This evidence
establishes the tested common Linux matrix, not every possible source build or platform.
Initial PyYAML 6.0 installation failed on
both interpreters with the upstream `build_ext.cython_sources` build error. Pillow 12.2.0
and Pydantic 2.9.2 were initially imposed by the dependency graph; Pydantic needed the
additional application-specific correction below. Other retained or normalized floors
are listed in the companion JSON alongside installed versions.

Functional probes determine the SDK, schema and workbook floors:

- Published ClearML wheel source from 2.1.0 through 2.1.5 lacks the `files` parameter on
  `Dataset.get_local_copy`; 2.1.6 introduces it. The installed 2.1.6 SDK also exposes
  `list_files` and `is_final`, so `clearml>=2.1.6` is required by CSV-only retrieval.
- Pydantic 2.9.2 fails the existing offline DDP configuration/queue-composition test with
  `PydanticSchemaGenerationError` for the native `GroundTruthInput` type alias. The small
  reproducer `type Example = str | Path; TypeAdapter(Example)` fails too. Pydantic 2.10.0
  passes the reproducer and original failing test on both supported interpreters;
  the declared floor is `pydantic>=2.10.0`.
- pandas 2.2.3 fails the frozen comparison-workbook contract because its default Excel
  headers add borders and alignment. With only pandas changed to 3.0.0, that exact test
  passes. The upstream [pandas 3.0 release notes](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
  document removal of default `to_excel` styling. The declared floor is `pandas>=3.0.0`.
  That release requires openpyxl 3.1.5 for `read_excel`; the existing dashboard-read test
  reproduces its `ImportError` with openpyxl 3.1.0. pandas 3.0.0/openpyxl 3.1.5 pass the
  report and workbook suite on both Python versions, establishing `openpyxl>=3.1.5`.

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
`python -m pytest -q --basetemp <owned-directory-outside-the-repository>` with absolute
`PYTHONPATH` entries for the current checkout's `src` and `tests` and
`NO_ALBUMENTATIONS_UPDATE=1` and `UV_NO_SYNC=1`, with `UV_FROZEN` removed to allow
real hook commands that specify `--locked`. The outside-repository base directory
preserves the docs checker's non-repository fixtures and avoids concurrent pytest
retention races.

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

- Final minimum dependency suite: 3,370 passed, 30 skipped and seven
  deselected on each interpreter (Python 3.12: 686.28 seconds; Python 3.13: 675.73 seconds).
- Final report/workbook floor checks: 46 passed on each interpreter.
- Standalone ground-truth module after explicit Hydra configuration registration:
  33 passed on each interpreter before the final pandas adjustment; the final complete
  suites also cover those cases at the final floors.
- Built-wheel installation without project extras and `uv pip check`: passed in all
  four isolated environments. Final wheel metadata declares the 36 unconditional
  requirements and no extras, including the final pandas/openpyxl floors.
- Outside-checkout capability imports, all 12 command help pages and configuration
  export passed on both default environments using the integrated wheel. The final
  rebuilt wheel additionally passed installed-adapter probes in all four environments:
  an extra external-file entry is rejected before materialization; a CSV-only dataset
  preserves bytes, path, hash and provenance. Each probe imports from the environment's
  installed package with `PYTHONPATH` removed. These are fake-SDK boundary probes.
- All 184 packaged Python source files in the final wheel match the checked-out source.
  The companion JSON records their digests and the final wheel digest.
- Packaging and development-dependency boundary tests: 35 passed; focused Ruff and mypy
  checks passed.

Earlier runs are retained as diagnosis history, not final acceptance: the first full
minimum runs exposed the Pydantic alias limitation; subsequent runs stopped at the
export validation-order regression (1,547 passing tests each), then at an obsolete
constructor-signature expectation after upstream integration (3,129 passing tests each,
30 skips, seven deselections). The corrected continuation passed 352 tests and exposed
the pandas 2.2.3 workbook-style mismatch on each interpreter. The final complete matrix
runs again with pandas 3.0.0 and openpyxl 3.1.5, covering all earlier sections at the
final supported floors. The standalone Hydra registration issue was corrected in its
test setup. The frozen workbook fixtures remain unchanged.

The [companion JSON](dependencies-evidence.json) preserves exact installed distributions,
the wheel digest, published ClearML wheel probe URLs, direct requirements and check results.
Task-owned environments
and logs are retained under the ignored `.tmp/dependencies-036` directory for review.
