# Integrated verification, 2026-10-23–24

This record covers feature `004-custom-augmentation` against base commit
`d8a3695eb481cdcf9fd523a17fee53a411bcf514`. Implementation and independent source
review are complete. Native acceptance remains incomplete; this document does not
claim release completion.

Subsequent Git delivery under the user's explicit release instruction is recorded
in [release.md](release.md). That delivery does not change the incomplete native
acceptance results preserved below.

## Local integration

The complete ordinary suite, including real two/four-rank CPU DDP, finished with
**3,226 passed, 30 skipped and 47 opt-in cases deselected** in 705.46 seconds
after the final harness/backbone-option changes:

```bash
uv run --frozen --no-sync pytest -q --durations=10
```

The retained complete log is `cy004-final-suite-with-harness.log`. An earlier
complete run passed 3,203 tests before the additional harness regressions
(`cy004-all-tests-final.log`). The selected opt-in physical
GPU/DDP and Severstal scenarios are separate gates. An earlier ordinary run exposed
five stale configuration-inventory/test-marker assertions; those were corrected,
passed their 96-test focused rerun, and are included in the successful complete run.
No skipped or deselected check is counted as executed native acceptance.

Ruff and Vulture passed after the harness corrections; strict mypy reported no
issues in 346 source files. The two new observer/environment regressions and the
complete Severstal tooling module passed (80 tests after the naming and local-backbone
regressions). Documentation validation checked the maintained Markdown and new
evidence files without issues; the final evidence reconciliation is validated separately.

The implementation also passed 43 import-linter contracts and their architecture
negative cases. Focused checks cover standard JSON, nested composition, all bbox
formats, preserved metadata, empty crops, donor selection, all 15 composed model
profiles, generated configuration switching, native disable values, malformed
configuration rejection, frozen file-independent replay, and native dataset bridges.
Real CPU DDP checks exercised custom Mosaic with the production cloudpickled trainer
class, after deleting the source JSON, with synchronized parameters and owner-only
publication behavior. They do not establish physical multi-GPU execution.

The installed queue package composed one immutable mixed-preset sweep of all 15
models. After deleting its source JSON, each frozen configuration was restored and
written as an execution configuration successfully. No queue job was submitted.
The independent [dependency-floor evidence](dependencies.md) records isolated
resolution on both supported Python minors and its bounded runtime coverage.

## Review correction

Independent review reproduced a YOLO raw-reader EXIF geometry mismatch. The adapter
now applies EXIF transposition before RGB conversion, matching the native image
reader. All five YOLO integration tests passed after the correction, including
orientations 2, 6 and 8. Independent rechecking confirmed the correction.

A proposed native checkpoint-resume regression was subsequently found outside the
supported interface: CY already rejects truthy `resume` before trainer execution.
The exploratory test was removed and no new resume behavior was introduced.

## Official dataset and CPU execution

The official Kaggle archive was downloaded after the user restored authentication
and accepted competition access. Conversion retained all 12,568 training images,
including backgrounds, and one tight half-open box per 8-connected mask component.
No tiny-component filter was introduced. The grouped seed-zero split contains
10,056/1,256/1,256 images; its frozen smoke subset contains 160/40/40.

Manifest SHA-256:
`1d0f169f2202684f8d6bbee543a149330645dc9c28c026fdb3e1dfa51c2379f9`.

A real CPU YOLO26n JSON+Mosaic pipeline completed one epoch with two observed
optimizer updates and changed parameters. ClearML readback verified finite loss
series, all 80 held-out images, canonical configuration, required downloaded
artifacts, the single native best Output Model, checkpoint hash equality, and actual
reload/inference from downloaded bytes. Checkpoint SHA-256:
`3a272e9bfcff8ebdbb60f320aa6bafd11dd5b277d24b9eaf33b3c59c66576acb`.
This used the actual pipeline and shared verification functions through a CPU driver;
the opt-in GPU worker itself correctly requires CUDA. It is CPU evidence only.

The task-owned run outputs were archived before cleanup. Tag-scoped cleanup removed
the CPU project's tasks/models/artifacts and invocation directory; readback returned
zero matching projects and tasks. Official source data and prepared fixtures remain
outside the removed invocation directory.

## GPU acceptance adjustments

The first GPU native-default YOLO run exposed an observer error: fused optimizers
invoke step hooks even when GradScaler supplies `found_inf` and the optimizer skips
the update. A real CPU fused-AdamW/GradScaler regression reproduced the failure.
The observer now records skipped steps separately, still requiring a non-skipped
step, changed parameters and finite published loss. A fake-credential regression
also protects environment representations in failed pytest tracebacks.

After that correction, YOLO's tiny one-epoch AMP run completed but correctly failed
acceptance: both attempted updates were skipped during loss-scale adjustment.
The matrix therefore explicitly uses FP32 for every variant, preserving one epoch,
batch one, native preset resolution, seed zero and per-preset initialization. This
changes the acceptance recipe only; production AMP defaults remain unchanged.
Mixed-precision training is not established by the FP32 matrix.

Native DEIMv2-S default completed 160 optimizer updates with changed parameters,
finite losses, all held-out predictions and downloaded checkpoint reload. Its first
readback attempt exposed a harness assumption: paired model/task name collision
resolution legitimately appends a readable suffix. The harness now admits that
suffix, filters by ownership tags, and verifies the canonical requested task name.
A regression checks exact literal names and rejects unrelated names. Re-verifying
the already completed run passed without repeating or fabricating training.

One FP32 YOLO attempt failed in SDK model metadata readback after successful
training. The server model and associations remained intact; independent direct
API and repeated SDK probes passed. The metadata-only instrumented rerun passed the complete pipeline and
checkpoint verification, with two optimizer updates and no empty model responses.
The original failure could not be reproduced; its exact cause remains unknown.
No production retry or upstream modification was introduced. A later RF-DETR Nano
JSON run similarly failed a project lookup during publication even though the
project remained present. Fresh raw/SDK queries succeeded. A fresh native rerun
passed with 160 optimizer updates; all 136 metadata-only traced API responses
matched their requested endpoints. These intermittent failures remain recorded,
with no confirmed cause or production fix claimed. Faster R-CNN DINOv2 JSON+Mosaic
later encountered the same empty model readback after training. Its instrumented
native rerun passed all shared checks with 160 optimizer updates; all 136 traced
responses matched their endpoints. The failed attempt and successful rerun are
both retained. These observations do not establish a root cause.

DEIMv2-L/X pretrained initialization is currently blocked by HTTP 403 from the
official Meta DINOv3 asset endpoint. The matching Small/Small+ native weights were
not present in the inspected caches. The user was asked for authorized local files
or download access while other presets continue. The test harness now accepts
repeatable local backbone selectors, validated before native execution, so all
three variants use the same supplied input. This does not substitute random or
unrelated detector weights for the requested pretrained backbone.

## Native matrix checkpoint, 2026-10-24

**39 of 45 required GPU scenarios passed**: all three variants for YOLO26n,
DEIMv2-S/M, all four RF-DETR presets and all six Faster R-CNN presets. Each pass
includes a real optimizer update with changed parameters, finite published losses,
all 80 held-out images, required force-downloaded artifacts, matching best-checkpoint
hashes, downloaded checkpoint reload/inference and matched per-preset initialization.
The six DEIMv2-L/X pretrained scenarios remain blocked on authorized Small/Small+
DINOv3 inputs. Neither composition tests nor random-initialization runs count toward
these six cases.

Fresh independent source/architecture review accepted the integrated code; see
[review.md](review.md). Complete native acceptance, architecture acceptance and
Git-only delivery remain pending. No feature commit, version tag or push has been
made; the companion usage source is validated but remains unreleased.

Per-preset results and initialization/checkpoint identities are recorded in
[native-smoke.json](native-smoke.json). Pending entries are acceptance gaps, not passes.

Six additional DEIMv2-L/X runs used `model.train.pretrained=false` in a separate
project and scenario directory solely to explore architecture execution without
the gated assets. All six failed before the first optimizer update at upstream
`generalized_box_iou`'s prediction-box assertion, including both native-default
variants. No augmentation-specific cause or upstream fix is established. These
failures are retained separately and contribute zero pretrained acceptance passes.

## Evidence preservation and remaining gate

Before cleanup, all GPU scenario outputs, failed-attempt logs, API-probe metadata
and verification logs were archived outside the invocation directory. Archive
verification rehashed the retained native checkpoint and every downloaded artifact
against all 39 successful receipts. The six-file reviewed companion source was
also preserved with its upstream base identity. Generated dataset/source caches
were excluded; the official dataset and prepared splits remain available.

Tag-scoped cleanup then deleted both owned GPU projects and their tasks, models
and artifacts. The final listing reported zero matching projects and zero matching
tasks, and the owned invocation directory was removed. No native training workers
remained. CPU cleanup was completed separately as recorded above.

The architecture plan validator passed. Acceptance validation exited 1 solely
because the native check lacks complete passing evidence. Its recorded result
explicitly identifies the six gated pretrained scenarios; this is an acceptance
gap, not a successful gate. All 67 changed tracked/untracked paths were reconciled
with the declared scope, preserving the pre-existing local dependency overrides.
Final Markdown/link checks and whitespace checks cover this closeout evidence.
