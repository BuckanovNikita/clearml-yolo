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

## Application delivery

The unchanged normal hook retry passed, including full pytest, and created feature
commit `3b95fbaae4bc2440e239e7b01a3c47755475ac8f`. The automatic release hook then
ran the normal checks again for its version commit, including the full pytest
hook, and completed successfully. No hook or test selection was bypassed.

Application version **0.39.0** is published as annotated tag `v0.39.0`:

- Release commit: `6cae69e7c31204f1b2266ec064075711426bb6c4`.
- Annotated tag object: `952237d1dd27caa78eae6526163fd0e9ed76bc47`.
- The atomic push updated `master` and that specific tag. Remote branch, tag
  object and peeled tag commit matched their local identities on readback.

The version commit is the direct child of the feature commit and changes only
`CHANGELOG.md`, `pyproject.toml` and `uv.lock`. Parsed TOML comparison confirmed
only the project/root-package version changed. The exact pre-existing local
sources were restored unstaged, and neither commit contains them. No pending
release-recovery record or crash dump remains.

Fresh read-only release audit accepted source and release preparation, including
all 69 committed paths, dependency preservation and the companion's eight paths.
It closed the incompatible-wrapper finding after inspecting the passing normal
hook result. Final version/tag/remote verification was performed by the parent.
The native 39/45 limitation and incomplete architecture acceptance remain as
disclosed; the release request did not turn them into passing evidence.

## Companion delivery and closeout

The usage collection is published as annotated tag **v0.4.4**:

- Release commit: `af6c7e4bb9c4db95349ebbae301a99548a8b3474`.
- Annotated tag object: `974a3b4082040c225cf43432ed0d9bd9d3daa922`.
- The atomic push updated `main` and that tag; remote branch, tag object and
  peeled tag commit matched their local identities.

GitHub redirected the legacy `corp-skills` remote to
[custom-opencode-skills](https://github.com/BuckanovNikita/custom-opencode-skills/tree/v0.4.4).
Direct readback at the canonical repository returned the same verified refs.
The release contains exactly the reviewed eight paths. Its guidance identifies
the published CY v0.39.0 implementation and preserves the native acceptance gap.
Skill discovery, metadata/duplicate-key checks, local links, Markdown validation,
no-impact architecture validation and whitespace checks passed. The original
checkout's unrelated edits remain untouched; no installed skill was replaced.

Application and companion delivery are complete under the scoped instruction.
Native T014/T015 and the complete-acceptance portion of T020 remain open; T022
records the completed Git-only delivery. Final documentation/link checks cover
this receipt. All owned native runs were already cleaned, release/test processes
finished, and the only retained application worktree override is the original
unstaged local dependency-source section.
