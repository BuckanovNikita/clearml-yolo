---
name: release
description: Use when releasing clearml-yolo or recovering held locks, moved refs, prepared version changes or failed publishing.
---

# Release clearml-yolo

Read `docs/development.md` (Local releases and External dependencies).
`Taskfile.ops.yml` and `pyproject.toml` own commands and versions.
Paths start at the repository root.

1. Establish authorization: `release-local` integrates locally and creates versions/tags;
   `--publish` or later `release-publish` needs separate publishing authorization.
   An implementation request alone authorizes neither a release nor publishing.
2. Inspect the clean proposed tip and current CY/cy-queue sources; resolve prerequisites.
   Confirm fresh independent review and `running-end-to-end-tests` evidence for CPU/single-GPU,
   direct/queued and publication outcomes. Automated stages do not prove manual
   observations. Check host capacity before GPU work.
3. Invoke Task with the full immutable `--expected-tip` SHA. Task owns gates, locking,
   fast-forward integration, semantic-release, final-version pairing and exact-ref
   publication. Avoid equivalent preceding acceptance/pairing runs. Immediate publishing
   reuses the invocation's stages; later publishing verifies afresh without re-versioning.
4. Report checks, review/native evidence, accepted/final SHAs, final pair versions,
   version/no-version outcome and remotely confirmed refs. Use `verification-workflow`
   for deferred gates, which block completion.

## Recover by failure

- **Held lock:** stop; neither wait on nor remove it. Busy master, divergence, dirty
  inputs or moved tips need owner resolution.
- **Final-pair/build failure:** inspect prepared files, staged diff, refs and logs.
  No release commit/tag is created. Restore only this attempt's changes when authorized,
  fix the cause and verify the new tip. Keep version/tag creation with semantic-release
  and preserve the release exception's scope.
- **Publishing failure:** inspect remote refs; retain the valid local release and retry
  `release-publish` with its expected SHA/tag and separate push authorization.
- **Model assets:** preserve their independent process and unrelated workloads/files.
  Read Development procedures (Model-weight releases) only for explicitly requested assets.
