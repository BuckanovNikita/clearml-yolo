# Bug Assessment: Queue cleanup fails completed jobs

- **Slug**: queue-job-finalization (generated from the report)
- **Created**: 2026-10-15
- **Source**: pasted task failure and subsequent user clarification
- **Verdict**: valid
- **Severity**: high

## Report and symptom

Task `ebef6b89839549949e4be4d96c423cc5` produced its artifacts but failed in
`native_descendant_scope` with `UnverifiableProcessTreeError`: access to three
processes under `/proc` was denied. The supplied stack reaches `execute_owned`
and ClearML invocation finalization. The user confirmed `cy-queue` launch and
requires queue supervision outside jobs: train on all allocated GPUs, then release
all queue reservations except the first inference GPU so other jobs can use them.
No production process access or task-state changes are authorized or assumed.

## Evidence and reproduction

`execute_owned` nests native descendant cleanup inside the ClearML owner. The
native tree scans all same-UID processes and probes their environments; unrelated
access denial becomes an invocation failure after the workload returns. The queue
already has a separate guardian with subreaper ownership and GPU leases, duplicating
cleanup inside the job. The guardian itself uses the same global marker scan.
Existing cancellation tests deliberately demonstrate global denial for recovery.
The exact remote PIDs and their ownership are unavailable. Reproduce locally with
an inherited supervisor channel, completed workload and an injected inaccessible
unrelated process; verify task completion and independent guardian cleanup.

## Proposed remediation

1. Add a small runtime lifecycle channel with an inherited socket owned by the
   original pipeline PID. It conveys only a training-finished acknowledgement;
   the ordinary job imports no queue, allocation, telemetry or GPU locking code.
2. A supervised command leaves descendant cleanup to its guardian; direct commands
   retain native scope cancellation. Required computation/publication failures
   still fail tasks. Training cleanup precedes the lifecycle notification.
3. Live guardians discover only their own child topology across every thread,
   recorded births and subreaper adoption. Unrelated `/proc` permissions/churn
   cannot poison live supervision. Recovery retains conservative global discovery.
4. On acknowledged training completion, the guardian durably shrinks the claim to
   the first allocated GPU, releases other locks, and updates queue devices. The
   handoff is bounded and idempotent; corrupted/lost evidence cannot free capacity.
5. Add process, protocol, lease-failure and phase-order regressions; run native CPU
   distributed regressions, full routine suite, static/import and documentation gates.

## Architecture and task contract

See [architecture.json](architecture.json). Python remains >=3.12.13,<3.14 with
existing uv, uv_build, Ruff, strict mypy, Vulture and pytest tooling. No dependency
source or revision changes. Existing import contracts and negative injected-edge
tests enforce SDK ownership, runtime effects, and direct/queue isolation.

Parallel work after the architecture plan validates: runtime process-tree owner
implements scoped guardian discovery; lease/guardian owner implements shrink and
parent-side protocol; primary owns runtime channel, command/composition integration,
ledger and docs. Integrate before parent checks, then fresh independent review.

Planned source scope: runtime process_tree.py and execution_lifecycle.py; queue
locks.py, guardian.py and exec_child.py; hydra/common.py and composition.py.
Tests cover these responsibilities with existing suites and new scoped tests.

Documentation: update docs/queue.md, docs/runtime-isolation.md, contract summary,
README and current queue specification; inspect/update portable usage/evaluation
references in corp-skills as required. Preserve prior dated workflow history.
Commit/release through native Git-tag-only workflow after acceptance; no deployment.

## Risks and acceptance

Retain safe identity checks, cancellation cleanup, ambiguous ownership quarantine,
helper preservation and direct command semantics. A stage signal must come only
from the original pipeline PID and survive the launch exec chain without leaking
to model children. Partial durable shrink must remain conservative and recoverable.
Remote production reproduction and physical multi-GPU timing are not established
by local synthetic processes or mocked GPU claims and must be reported separately.

## Tasks

- [x] Inspect source, existing changes, workflow and affected contracts.
- [ ] Validate architecture plan before source edits.
- [ ] Reproduce failing cleanup and write behavioral regressions before fixes.
- [ ] Implement scoped guardian discovery, durable shrink and lifecycle handoff.
- [ ] Integrate, verify original failure and routine/native CPU regression suites.
- [ ] Update and validate affected documentation and portable guidance.
- [ ] Obtain fresh review; reconcile diff and validate architecture acceptance.
- [ ] Commit, evaluate release, push authorized branch/tag and verify refs.

Pre-existing exclusions: local pyproject.toml dependency source overrides and
untracked docs/cls-cls-pw-grid-search.md.
