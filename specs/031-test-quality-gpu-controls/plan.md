# Implementation Plan: Test quality and GPU controls

Implement the approved [specification](spec.md) with Python 3.12, the existing uv
toolchain and native Spec Kit ledger. Do not modify installed workflow tooling.

## Architecture

[architecture.json](architecture.json) records module impact, dependencies and
acceptance. Core owns typed GPU records and pure allocation decisions; application
owns explicit control ports; adapters own identity probes, atomic records, locks,
audit and recovery; entrypoints compose CLI behavior. Test helpers never become
production dependencies. Reuse existing import contracts and negative tests.

`require_process_supervision() -> None` validates local supervision before native
scope entry. `check_interpreter_supervision(interpreter: str) -> None` runs a bounded
fresh interpreter probe before queue prepare_start. Queue/guardian integration is
owned by the queue workstream; the runtime helper is owned by the parent.

GPU controls accept physical integer selectors and full UUIDs. Identity enumeration
must not initialize CUDA or require healthy memory telemetry. Holds are per UID and
host-wide, live allocations are not preempted, and release covers all UUIDs in a
matching claim. An incompatible control fence in the existing claim scan blocks
old admission while existing leases retain their normal finish path. Force release
is audited metadata recovery, not implicit process termination or verified cleanup.

## Workstreams and dependencies

1. Parent owns artifacts, runtime supervision, pyproject/lock, architecture checks,
   integrated verification and documentation (including corp-skills source).
2. Queue agent owns core/application queue, queue adapters and CLI, physical inventory
   API and dedicated GPU-control tests. Uses the parent's supervision API; does not
   edit process_tree.py or project/dependency configuration.
3. DDP agent owns GPU harness/options, tests/conftest.py, test_native_ddp_gpu.py,
   harness tests and docs/ddp-testing.md. No live GPU/ClearML execution by the agent.
4. Quality agent owns new composed/property test modules. No configuration or
   production changes; parent installs approved development dependencies.
5. Parent integrates and verifies; a fresh independent read-only reviewer assesses
   the resulting change after verification. Subagents do not delegate further.

## Verification

Use `uv run --frozen --no-sync` for pytest, Ruff, mypy, Vulture and import-linter.
Exercise negative architecture/tooling tests, real local lock/process races and
deliberate semantic faults. Preserve native CPU DDP. New GPU tests require explicit
opt-in, physical device indexes, project and artifact directory; record missing
remote acceptance rather than fabricate it. Default scenario timeout is 1200s
with separately bounded cleanup. No retry-to-green policy.

## Documentation and existing work

Update development, queue, runtime isolation, current contracts, README and remote
DDP instructions. Reconcile the portable usage package in corp-skills (SKILL.md,
references/usage.md and references/evaluation.md), validate it and record source
identity. Preserve pyproject's local tool.uv.sources section and the unrelated
untracked docs/cls-cls-pw-grid-search.md. No .specify file changes or history rewrite.

## Constitution alignment

Existing inward boundaries, typed ports, sole task ownership, publication barriers,
project-contained outputs and explicit effects remain required. The approved
operator override is an explicit exception to automatic verified-only release:
audit it as unverified manual release, never as successful cleanup. Historical
specifications stay unchanged; new control contracts are additive.

## Local delivery amendment — 2026-10-15

The user requested: "finish all local work that started commit and push release".
Finish the local release and companion usage-skill delivery now, retaining T016
as pending external acceptance. This release authorization does not establish
physical GPU/NCCL or ClearML results. Preserve the earlier dated verification.

Incorporate the two upstream workflow-documentation commits through `e1b6346`
before committing. The integration preserves the feature code byte-for-byte.
Run ordinary source and generated-release commit hooks, inspect generated
metadata/changelog, validate distribution contents and push only the branch and
annotated Git tag. Restore local dependency overrides exactly after each commit
attempt. Keep the unrelated grid-search draft out of commits.

The parent owns tool Git operations and final evidence. A bounded companion
workstream prepares and validates the portable usage-skill patch; it depends on
verified tool release refs before describing the interface as released. Fresh
independent review covers the final release diff and evidence. No further module
or dependency changes are planned; the existing architecture record continues
to disclose the outstanding physical check.

## GPU control simplification — 2026-10-15

Implement the approved GC-01–05 amendment. The task-owned
[generation architecture record](gpu-control-simplification/architecture.json)
extends the original record without rewriting its historical acceptance gaps.

Core retains private UUID records and adds typed operator events/results and lease
generations. Queue adapters own an append-only per-device generation transition
under the host transaction, generation-specific lock/claim files, and generation
fencing on every guardian mutation. Historical process ownership remains available
for job supervision independently of current capacity. Explicit free is an
authoritative host-local event, not process cleanup or a job result. It does not
need the original NFS queue. Automatic reservation queries ignore stale unlocked
claims; explicit holds and live allocation locks remain exclusions.

Control API: disable(selector) -> GPUHold; enable(selector) -> None;
release(selector) -> GPUFreeResult; free is the CLI alias. GPUFreeResult contains
only the selected internal identity, actor, generation and event timestamp.
GPUControlStatus may retain private identity/claim details; public projections
must not serialize internal records directly. Full identities remain accepted as
internal/backward-compatible selectors, but help and public views use indexes or
short labels. Deprecated token/reason/force CLI arguments are removed.

Startup owns the fresh NVML memory check after reservation acquisition and before
opening the workload gate. Threshold is fixed at 2 GiB. Unknown/high readings
release the attempted reservation and return the job to pending. Allocation
generation must still match before launch. Direct commands remain unscheduled.

Work ownership: reservation agent owns core queue records, locks, operator controls
and dedicated control tests; presentation agent owns queue CLI/TUI, presentation
helpers and output tests; parent owns application ports, inventory, guardian/runtime,
workflow artifacts and integration tests. Documentation may run independently once
interfaces are stable. All delegates are bounded and do not delegate further.
Parent integrates, runs checks, and obtains fresh independent review afterward.

Reuse existing layer, SDK-owner and direct-command import contracts and their
negative tests. Validate the architecture plan before implementation and reconcile
it against the final diff and executed evidence before acceptance. Update queue,
current contracts, diagnostics, runtime isolation, Russian README and canonical
corp-skills usage/evaluation references. Preserve local dependency overrides and
the unrelated grid-search draft. No dependency revisions change.

Constitution inspection: historical scheduler constraints were already superseded
by feature 029. This explicit operator override is authorized by the user's plan;
it changes capacity bookkeeping without performing PID-based automatic cleanup.
Unknown memory still prevents automatic launch. Installed `.specify` files remain
unchanged, as required by project policy.
