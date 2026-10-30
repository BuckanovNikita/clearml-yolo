# Verification: persistent YOLO weights directory

Date: 2026-10-30. Status: implementation verified and accepted for the authorized Git release.

## Original failure and focused checks

A fresh-process reproduction loaded the pre-fix asset adapter from the preserved
starting snapshot, placed a named checkpoint in its reported cache, then changed
into a trial directory. Native attempt_download_asset attempted a blocked download
even though the prepared file existed. The same isolated SDK probe confirmed that
settings.update changes the saved weights_dir but leaves utils.WEIGHTS_DIR stale.
Source inspection confirms selected-model lookup uses SETTINGS while AMP uses
that separate constant. The corresponding post-fix path passed with real checkpoints.

`uv run --frozen --no-sync pytest tests/test_yolo_weights_settings.py tests/test_weight_preparation.py tests/test_native_assets.py tests/test_batch_probe.py -q`
passed: 112 tests, with existing Hydra/Pydantic warnings. Focused Ruff, formatting
and strict mypy passed. Fixtures keep real user settings untouched.

## Real offline checkpoint loading

Using installed Ultralytics 8.4.184 and isolated settings/cache/trial directories,
configured a relative cache through the production helper, changed cwd, then loaded
both real cached checkpoints with YOLO. Repeated in a fresh Python process started
from the empty worker directory. Socket connections and native downloads were
blocked. Both processes loaded both models with nonempty parameters. A repeated
setup left the settings mtime unchanged, and cached bytes matched original files.

| Checkpoint | SHA-256 |
| --- | --- |
| yolo11n.pt | 0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1 |
| yolo26n.pt (installed AMP lookup) | 9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef |

This is real CPU checkpoint loading and path discovery, not GPU AMP numerical,
training, interrupted execution, or ClearML publication acceptance. No service,
GPU workload, real user settings or existing checkpoint was changed.

## Inert command and documentation checks

In fresh processes with isolated pre-existing settings containing a relative
weights_dir, cy-download-weights --help, cy-batch-estimate --help,
cy-train --cfg job and cy-init-config --help each exited zero. Settings bytes
and nanosecond mtime stayed unchanged, and no CY settings lock was created.
The canonical documentation check passed for all governed Markdown and new bug
artifacts. The packaged operations tutorial was regenerated with render_docs.py.

## Paired current-source verification

Fetched latest defaults: CY master 3636404eafaf0c32312fddb4269b8aad0e2b12eb,
0.44.1, and cy-queue main 397753c123f379ade50f06a2babf5e4b1476b9d2, 0.1.5.
In an isolated environment, normal uv pip install resolution (without --no-deps)
installed both source trees with unchanged approved external dependencies. Checked
pip compatibility, actual import paths, source/installed version equality and CLI
help. The ordinary queue suite passed 518 tests with 7 physical DDP cases
intentionally deselected and 19 upstream deprecation warnings. Queue Ruff,
formatting, strict mypy and both import contracts passed.

Repeated normal installation and the full queue suite with the actual proposed
CY implementation and temporary source version 0.44.2: 518 passed, 7 deselected,
19 warnings; metadata, pip check, CLI, mypy and import contracts passed. Runtime
Python files match the release candidate. Source dependencies remain
digital-metrics 6e801be1564dce458294eb23592cc1aa0939c4d9 and
report-generator d10aa395d08f738e92e04e076cee93b3a993bf8f. The original user
installation and sibling checkout were preserved. Final post-hook version metadata
will be refreshed and checked before pushing.

## Canonical execution and environment stabilization

The integrated canonical run passed Ruff, strict mypy, Vulture and import-linter.
Its full pytest run passed 4482 tests, skipped 30 optional tests and deselected 81
physical/opt-in cases, with 182 warnings in 1025.62 seconds. This includes real
CPU-DDP and injected negative architecture cases. The verifier then refused its
success receipt because the installed input inventory changed during that run.

A timestamp inventory of governed sources and installed dependencies found only
pi_heif 1.4.0 files added during the suite. This optional decoder was present in
the original prepared-environment constraint inventory but absent from the fresh
runtime/dev install; the SDK installed it on first use. No project or approved
external source changed. The environment now has that prerequisite. A fresh stable
canonical run is required before acceptance; the passing pytest run alone does
not satisfy the canonical gate. The first environment that reused a site-packages
path was also replaced with fully independent runtime/dev installs before this run.

## Final stable acceptance

With pi_heif already present, the unmodified canonical verifier reran Ruff, strict
mypy, Vulture, import-linter and the complete ordinary pytest suite. All passed:
4482 tests passed, 30 skipped, 81 deselected, 182 warnings in 1008.08 seconds.
The verifier confirmed unchanged inputs and issued its successful application
receipt. The negative architecture cases and real CPU-DDP tests passed in this run.
No project dependency declarations, locked versions or approved external sources changed.

Final Markdown/local-link validation passed, and all seven affected Python files
passed Ruff formatting. [Independent review](review.md) found no blocking code or
documentation findings and covered the portable explanation-only cases. The
architecture record reconciles the complete task delta and its declared checks;
acceptance validation is required before commit.

The original checkout audit found only task-owned changes, with its pre-existing
package metadata, lockfile, instructions and unrelated work preserved. The three
runtime adapters and focused regression tests match the isolated release source.
The isolated source is based on latest master 3636404 and targets patch 0.44.2.
The portable companion is based on collection main c985e12 and targets 0.6.5.

Git delivery follows the native hooks after acceptance. Post-hook installation,
source/installed metadata and remote commit/tag ref checks remain delivery steps;
the release handoff reports their actual outcome. No package or release asset
publication, installed-skill update or GPU training outcome is claimed.
