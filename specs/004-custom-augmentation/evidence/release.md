# Release authorization and delivery, 2026-10-24

After receiving the completed implementation status, 39/45 native pretrained
results, the six gated DEIMv2-L/X cases and the uncommitted release status, the
user explicitly requested: **“make a release”**.

This authorizes Git-only delivery with that disclosed native verification gap.
It is a task-scoped release exception, not a change to the normal acceptance
policy or a claim that the remaining scenarios passed. The architecture record
retains its incomplete native result; complete architecture acceptance remains
unavailable. T014/T015 and the acceptance part of T020 remain open for the six
pretrained scenarios. T022 records this separately authorized delivery.

The release includes the shared JSON/Mosaic pipeline, all 15 model integrations,
conflict validation and visible native disable values, frozen worker/replay
configuration, official Severstal conversion and opt-in native tests, documentation
and examples. The independent source review is recorded in [review.md](review.md).

## Known verification limits

- The ordinary suite passed 3,226 tests; the retained native evidence covers 39
  pretrained GPU scenarios and a CPU YOLO JSON+Mosaic pipeline.
- DEIMv2-L/X's six pretrained cases require authorized DINOv3 Small/Small+ files.
  Separate random-initialization probes failed at the upstream prediction-box
  assertion before an optimizer update and establish no passing replacement.
- Intermittent ClearML SDK readback failures passed instrumented native reruns;
  their cause remains unconfirmed and no production fix is claimed.
- Physical multi-GPU execution and full-dataset training are not established.

See [verification.md](verification.md) and [native-smoke.json](native-smoke.json)
for results, failed attempts, dependency-floor scope and completed owned cleanup.

## Delivery procedure

The normal application pre-commit and post-commit release hooks remain enabled.
The exact pre-existing local `tool.uv.sources` section is preserved, removed for
each commit and automatic release commit, and restored unstaged afterward. The
prepared environment is used without dependency resolution or changes to the
approved external dependency revisions.

Only task-owned changes are staged. The native release helper chooses the next
semantic version, creates its checked version commit and annotated tag, and the
intended branch/tag are pushed explicitly and verified remotely. The usage
companion follows its own documented Git-only release workflow from an isolated
checkout, preserving unrelated edits in the older checkout. No package publication,
GitHub Release object, installation or deployment is part of this delivery.

Actual commit, version, hook results and remote-ref verification will be appended
after those operations complete.

## Release-check investigation

The first wrapper attempt supplied incompatible `UV_FROZEN` and `--locked`
settings. It was interrupted before pytest; the exact local sources were restored.
The corrected wrapper keeps `UV_NO_SYNC` and leaves `UV_FROZEN` unset. Changelog,
Ruff, mypy, import-linter and Vulture then passed without a hook bypass.

That attempt's full pytest process terminated with SIGILL during garbage
collection in a local HTTP handler, while running the asset read-timeout test.
It produced no contributor commit. The failing test and asset transport have no
feature changes. The original traceback and failed hook log are retained.

The isolated asset module passed 11 tests. After full-suite collection/imports,
the asset/loading selection passed 31 tests; the exact timeout case also passed
with Python's debug allocator and development mode. Independent read-only
diagnosis found no established source defect or transport resource leak. The
stack identifies where collection began, not the native object that caused the
signal. No application, dependency or test workaround was introduced; the normal
full hooks must pass on retry before delivery. A passing retry does not establish
the cause of the earlier interpreter crash.
