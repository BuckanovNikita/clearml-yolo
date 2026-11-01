# Bug fix: native process discovery under unrelated churn

- **Slug**: cleanup-native-process-churn (resolved from the active assessment).
- **Date**: 2026-11-01
- **Assessment**: [confirmed reproduction](assessment.md)
- **Status**: applied; integrated release acceptance remains in the cleanup ledger.

## Changes

The existing identity-fenced per-thread child traversal now lives in the private
_ScopedProcessTree inside the runtime adapter. SubreaperProcessTree and the native
caller scope share it. Native discovery visits caller descendants and retained birth
identities instead of every host process. Generic LinuxProcessTree historical marker
recovery remains unchanged. No module, dependency or effect ownership was added.

Native ownership also treats zombie leaders with living threads as live groups;
recorded groups remain owned, unknown helper-adopted groups remain ambiguous and
reaping waits for the entire group. Caller/helper protection, ambiguity refusal,
pidfd/start-time fences, subreaper restoration and two-plus-eight-second deadlines
remain intact. Public function and constructor argument ASTs match upstream.

Nine deterministic cases cover unrelated churn/permissions, relevant denied access,
all-thread children, threaded zombies, PID replacement and late adoption. Two older
unit fixtures now intercept the scoped traversal seam while preserving assertions.
An initial focused run exposed those fixture seams and they were corrected before
the final passing run. No assessment deviation or ownership exemption was required.

## Local verification and documentation

The implementer recorded red topology cases, then 64 passing native/subreaper/
cancellation/capability cases. Parent repeated the same set: 64 passed in 45.97 seconds.
Scoped Ruff and strict mypy passed. Original stress reproduction and focused safety
review are recorded in [test.md](test.md). The existing process contract already owns
these failure and protection semantics; this internal discovery correction adds no
CLI/configuration changes. README and portable usage examples therefore need no
process-specific changes. Architecture acceptance uses the linked cleanup record.
