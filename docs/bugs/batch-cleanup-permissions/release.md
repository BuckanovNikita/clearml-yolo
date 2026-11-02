# Batch cleanup release acceptance — 2026-11-02

## Resumed outcome and scope

The user requested merging the verified fix to master and releasing it. Isolated
master fast-forwarded to `2bfe1d8`, based on upstream `73bb044`; the original dirty
checkout remains intact. The release tool predicts 0.44.8. Earlier TLS failure is
resolved outside this task: cluster capacity and dedicated ClearML authentication
now pass. This follow-up supersedes the earlier blocked release status without
rewriting its dated observations.

Only documentation and native-generated root version/changelog metadata remain.
Runtime code, dependency revisions and import contracts are unchanged since the
accepted fix review. Portable usage guidance was re-inspected at source `670b0be`;
no CLI/configuration/recovery example changed, so no companion edit is needed. The isolated checkout has no local `[tool.uv.sources]` section.

## Real native execution and readback

Two full one-epoch random-weight YOLO pipelines ran through production
`IndependentWorkerPool`: CPU baseline, then single-GPU candidate. Each command
exited zero with verified case cleanup; both actual ClearML tasks completed.
The baseline was promoted with `prod`, and the GPU pipeline used it automatically.

The disjoint train/val/test dataset contains twelve non-square images, including
one empty image per split. Source CSV and original SDK settings remained unchanged.
Both contexts inferred exactly the same four current test images. CPU had no prior
baseline; GPU produced the paired comparison and developer/business reports.

| Check | CPU | Single GPU |
| --- | --- | --- |
| Required artifacts force-downloaded and hashed | 11 | 17 |
| Native best Output Models | one | one |
| Downloaded bytes match producer best checkpoint | passed | passed |
| Downloaded checkpoint reload and CPU inference | passed | passed |
| Validation threshold for `square` | 0.012324729934334755 | 0.012323829345405102 |
| Populated strict threshold flags independently checked | 64 | 80 |

All published thresholds match their checkpoint-specific validation calibration;
all 144 flags equal `confidence < confidence_threshold`. JSON match relationships
parse, and all downloaded XLSX files open, including `Сравнение` and both reports.
The required production calibration/finalization barrier performs fresh server
model lookup, checkpoint download/hash checking and metadata readback; completed
tasks establish those actual checks. Independent evidence inspection rehashed all
28 artifacts and two models. No additional external GPU metadata read is invented.

Both verification projects were cleaned with the environment helper; tagged task
and project listings were empty afterward. Private execution commands, exact IDs,
model hashes, downloaded files, audit output and cleanup logs remain in environment
evidence. The original failed verification harness checks were corrected: readable
name suffixes are valid, and CSV flags are numeric rather than text booleans.

## Paired version and software checks

Proposed CY 0.44.8 and latest queue source `32bea01` (0.1.7) resolved normally in an
isolated source environment, without `--no-deps`, using frozen CY runtime bounds.
Installed versions/imports matched their source fixtures. Queue tests: 582 passed,
7 deselected, 19 warnings. Ruff, strict mypy (70 files), both import contracts,
`uv pip check` and installed `cy-queue --help` passed. This tests the proposed
release version; actual post-hook metadata will be refreshed and rechecked before push.

The unchanged runtime/dependency view reused successful canonical evidence:
4,703 passed, 30 skipped and 81 deselected, including architecture negative cases
and native CPU-DDP. No repeat suite is necessary for prose or strictly validated
version-only metadata. Documentation and architecture validation run before commit;
normal pre/post-commit hooks remain enabled. Publish only the native annotated Git
tag and intended master ref, then verify remote refs. No GitHub Release, distribution
asset, package publication or deployment is part of this release.

## Limits

Random-weight synthetic execution establishes behavior, not model quality or CUDA
capacity recommendations. Optional FiftyOne was disabled; its MongoDB stand is absent.
Bulk catalogue preparation used a real, project-local unavailable receipt-directory
fixture, exercising the documented nonfatal warning path without fabricating a receipt
or downloading an unrelated catalogue. No catalogue, browser interaction, physical
multi-GPU or optional publication acceptance is claimed; these unchanged contracts
are outside this process-only patch. The selected model trained from its installed YAML.
