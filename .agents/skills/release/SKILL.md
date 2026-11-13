---
name: release
description: Select local integration or publishing, check review and native evidence, and recover failed clearml-yolo release attempts. Use for releases, held locks, moved refs or prepared version changes.
---

# Release clearml-yolo

[Local releases](../../../docs/development.md#local-releases) own policy;
[Task operations](../../../Taskfile.ops.yml) and
[semantic-release configuration](../../../pyproject.toml) own commands and versions.

1. Establish authorization for the intended operation. `release-local` permits local
   fast-forward integration and version/tag creation; publishing requires separate
   authorization, either `--publish` on that invocation or `release-publish` later.
   An implementation request alone does not authorize a real release.
2. Inspect the clean proposed tip and current CY/cy-queue sources. Resolve missing
   prerequisites through [setup](../../../docs/development.md#external-dependencies).
   Confirm fresh independent review and the CPU/single-GPU, direct/queued and
   publication observations selected by
   [end-to-end acceptance](../running-end-to-end-tests/SKILL.md). Automated stages do
   not establish manual observations. Check host capacity before GPU execution.
3. Invoke the selected Task entrypoint with the full immutable `--expected-tip` SHA.
   Let it own automated stages, locking, fast-forward integration, semantic-release,
   final-version pairing and exact-ref publication. Do not precede it with equivalent
   acceptance or paired stages. The invocation reuses its stages; later publication
   deliberately checks the existing version afresh without re-versioning.
4. Report actual check outcomes, review/native evidence, accepted and final SHAs,
   final pair versions, version/no-version outcome and any remotely confirmed refs.
   A deferred supported gate blocks completion; follow
   [verification workflow](../verification-workflow/SKILL.md).

## Diagnosis and recovery

- A held lock is a blocker: do not wait on or remove it. A busy master worktree,
  divergent history, dirty inputs or moved expected tip needs owner resolution.
- Final-pair or build failure leaves prepared files for inspection and creates no
  release commit/tag. Inspect the staged diff, actual refs and logs before recovery;
  restore only this attempt's changes when authorized, fix the cause and verify the
  new tip. Never hand-edit versions/tags or widen the release exception.
- Publishing failure does not erase a valid local release. Inspect remote refs first;
  retry through `release-publish` with the existing expected SHA/tag, retaining the
  separate push authorization. Do not run version creation again.
- Keep unrelated files, workloads and the independent model-weight release process
  intact. Use [weight releases](../../../docs/development.md#model-weight-releases)
  only for explicitly requested model assets.
