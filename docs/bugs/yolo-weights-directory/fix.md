# Bug fix: persistent YOLO weights directory

- Slug: yolo-weights-directory
- Fixed: 2026-10-30
- Assessment: [approved remediation](assessment.md)
- Status: applied; acceptance tracked in [verification](test.md)

## Changes

The YOLO asset adapter now explicitly configures the native weights directory under
an adjacent FileLock. It reads the latest saved mapping, resolves only a relative
weights_dir against invocation cwd, invokes the SDK update API when needed, then
verifies the entire saved mapping. It preserves unrelated persisted values and
restores unrelated in-memory overrides around the SDK's whole-mapping write.
Only after successful verification does it synchronize live settings and WEIGHTS_DIR.
No rewrite occurs for an already absolute, correct setting.

Catalogue preparation calls this boundary before discovery and before completed
receipt reuse. NativeBatchProbe calls it on its YOLO path before worker launch.
Settings failures are actionable preparation findings or failed trial diagnostics;
workers are not launched after setup failure. Existing trial directories, public
commands and report records are unchanged. Non-YOLO probe paths remain unchanged.

## Tests and documentation

Focused regressions cover relative/absolute/literal-tilde paths, latest disk values,
process-only overrides, concurrent processes, suppressed writer failures, invalid
settings, repeated calls, discovery/receipt/worker ordering, inert help and fresh
process lookup. Tests isolate SDK settings and never configure the user's file.
The SDK investigation reproduced the stale WEIGHTS_DIR before implementation; the
new test file was written concurrently and first ran after the helper landed, so
no pre-implementation failing regression-test run is claimed.

Updated README, cache/filesystem/project contracts, batch/runtime guidance, current
contract navigation, packaged operations tutorial and its generated HTML. Appended
superseding notes to completed 007 spec/command/quickstart without erasing history.
Portable usage/evaluation references receive matching migration and failure cases.

## Deviations and integration

The original checkout is older than the current remote and contains substantial
pending work. Inspection found task prerequisites already published on master at
3636404eafaf0c32312fddb4269b8aad0e2b12eb (0.44.1). The task delta was applied to an
isolated current-source clone; unchanged prerequisite modules match that source.
README context was merged against its newer wording, preserving both histories.
The target release is therefore 0.44.2. The original checkout and unrelated edits
are preserved; no dependency source changes or unrelated fixes are included.

The doc audit also found explicit cache-exception links needed in batch estimation
and runtime isolation, and an obsolete packaged tutorial statement. These are
within the approved cache/setup documentation scope and included in the architecture
scope. Existing pure mutation-selected modules, tests and dependencies are unchanged.

## Architecture verification amendment

The first canonical run passed Ruff, mypy and Vulture, then rejected the new
batch_probe -> yolo.assets import. The design requires this explicit composition
edge; .importlinter will declare that exact pair. Added negative cases reject
batch_profiles -> yolo.assets and batch_probe -> yolo.inference, preserving both
caller and target isolation. The architecture record now includes the changed
contract and its tests; no broad peer or SDK exception is introduced.
