# Bug fix: retain independently confirmed numerically limited estimates

- Slug: `yolo-numerical-search` (from assessment context).
- Applied: 2026-10-30.
- Assessment: [assessment.md](assessment.md).
- Status: applied; final acceptance is recorded in [test.md](test.md).

## Changes

`core.batch_estimation` schedules exactly one fresh confirmation of the last fully
successful candidate after discovery-time nonfinite computation. It preserves the
memory upper bound, failed trial and numerical cause. Success becomes usable
`numerically_limited`; a failed or incomplete confirmation ends failed without
another fallback. Initial numerical failure and other discovery failures still abort.

Exact lookup and extrapolation retain the limitation; numerical status takes
precedence over ceiling and validated status. The CLI displays source diagnostics,
and the training provenance adapter retains them. The application still persists
failed/null progress snapshots for cancellation safety, with accurate pending text.

Catalogue construction now writes schema 2. Explicit schema 1 remains readable
without rewriting or promoting historical failed cases; its old status vocabulary
is enforced. Existing schema-1 terminal numerical failures with empty case-level
diagnostics remain readable. Ordinary locked atomic save upgrades the output while
preserving unrelated cases. Omitted versions retain normal model defaults and
legacy-shaped payloads remain readable. Unknown versions and corruption fail.

## Tests and architecture

The new regression first failed on the reported binary sequence: after the batch-28
failure, the old implementation returned no candidate instead of requesting 24.
After the change, 218 focused tests passed, covering the reported peaks, first
failure, every confirmation failure, incomplete optimizer/update/validation evidence,
excess memory, fresh identities, forged evidence, schema compatibility, unrelated
history, lookup bounds, mixed hardware, CLI output/cache, provenance and refresh.

No SDK numerical behavior, native finite guard, worker supervision, optimizer or
memory rule changed. Four existing modules retain their layer/effect ownership;
existing import contracts and architecture negative cases are reused. See
[architecture.json](architecture.json). No selected mutation module, selected mutation
test, dependency or fixture changed; the scoped mutation gate is not applicable.

## Documentation

Updated the batch guide, Russian README, project summary and feature-006 contract.
Final consistency inspection also updated feature 006's adjacent data-model description
to include the new status, provenance and catalogue compatibility.
The portable usage skill includes recovery, catalogue compatibility, two evaluation
cases and dated verification. Historical task ledgers and reports remain untouched.
The documented older-version workaround reruns a smaller explicit search ceiling
and still requires fresh confirmation. No physical A40 or numerical-root-cause fix
is claimed.

## Deviations and limits

The remediation addresses loss of a recommendation after an isolated numerical
failure. It does not establish why that native computation failed. The exact A40
960/batch-28 numerical failure was not reproduced on available hardware. A supervised
GPU integration attempt was rejected by existing missing-PID telemetry protection;
that guard was preserved. Successful direct native GPU probes and policy tests are
reported separately from that incomplete integration check.
