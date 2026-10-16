# External acceptance closure — 2026-10-16

## Decision and scope

**Disposition: closed by user waiver; physical outcomes remain unverified.**
The user asked to “close this as i can't provide more info” after the five-GPU and
multi-host NFS gaps were reported, then explicitly requested commit and push with
a release only if needed. This instruction closes the outstanding requests for
external results in features 029 and 031. No further user evidence is awaited.

The unavailable five-physical-GPU direct/queued eager/compiled matrix, associated
physical multi-GPU/NCCL failure/cancellation checks, and actual two-user/two-host NFS
acceptance are waived as completion/release gates for the delivered implementation.
The waiver covers these target-dependent checks only. Existing software checks,
ownership and fail-closed behavior, required documentation checks, and truthful
reporting of runtime evidence remain required. No supported interface or runtime
behavior changes, and no new hardware, NFS or deployment claim is established.

| Historical obligation | Current disposition |
| --- | --- |
| 029 T011: actual multi-user/NFS/host partition checks | Closed by waiver; unverified |
| 029 T015 and T028: outstanding physical matrix and external native acceptance | Closed by waiver; completed local portions and unresolved native evidence retained |
| 029 T019: remaining native prerequisite after completed software review | Closed by waiver; original architecture result retained |
| 029 T020: original release prerequisite | Superseded by T034/v0.27.0 delivery; remaining external prerequisite now waived |
| 031 T016: user-supplied physical multi-GPU results | Closed by waiver; no external result requested |
| 031 T015: remaining physical prerequisite after completed local reviews | Closed by waiver; original architecture result retained |

Original checkboxes and dated outcomes remain historical snapshots. This decision
and the linked current-status notices supersede their open-task disposition for
the listed obligations. The original architecture JSON files keep their `not-run`
results; evaluating their original full-matrix scope can still fail. Neither those
results nor this documentation-only architecture check are evidence of physical
acceptance. No validator, test marker, skip policy or test expectation is weakened.

Original cuBLAS, intermittent CPU-DDP SIGILL and ClearML missing-model-ID evidence
remains unresolved as recorded in feature 029; this waiver does not fix those
failures. Other target-specific acceptance, including CUDA 11.8/backend export
claims, is outside this decision. A future request to certify an affected target
requires a new scoped acceptance run and review using the retained procedures;
the current task has no pending external-data dependency.

## Documentation and architecture plan

Follow the repository's documentation-maintenance route. Update current queue/DDP
acceptance guidance, status/navigation and dated amendments in both feature
specifications, plans, ledgers and verification records. Preserve completed history
and the original architecture records. The adjacent [architecture record](architecture.json)
records inspected no-impact scope; validate it before edits and at acceptance.

README, command examples and the canonical portable usage source were inspected.
They describe unchanged interfaces and do not require these external results from
the user, so no usage-package or example changes are needed. No new runtime test,
live workload, infrastructure modification, dependency update or package build is
needed for this disposition change.

## Tasks and checks

- [x] Inspect current contracts, implementation boundaries, prior checks and user authorization.
- [x] Validate no-impact planning, then add scoped closure notices and amendments.
- [x] Validate project Markdown/links, preserved evidence and final architecture scope.
- [x] Obtain independent read-only review of waiver scope and evidence accuracy.
- [x] Prepare task-scoped delivery and verify the current remote branch ancestry.

## Verification and review

On 2026-10-16, `uv run --frozen --no-sync python scripts/check_docs.py --all`
plus the explicitly selected new decision checked 475 Markdown files with zero
issues. The no-impact architecture validator passed planning and acceptance;
`git diff --check` passed. Both original feature architecture files remain
byte-identical, including their `not-run` results. Current runtime, tests, examples,
dependencies, installed workflow assets and the portable usage package are unchanged.

Fresh read-only reviewer `acceptance_closure_review` returned **ship**, independently
repeating the 475-file documentation check, both record-validation phases and the
whitespace check. It confirmed bounded waiver scope, preserved historical results,
no pending external-input obligation for the listed tasks, and the explicit limits.
No physical workload or unrelated application suite was run for this prose change.

## Delivery

The user authorized commit and push, with a new release only if required. The task
uses a Conventional Commit, normal applicable hooks and native release evaluation,
then an explicit master push with remote-ref verification. The generated changelog
refresh records prior committed history. No version bump is forced for this
acceptance-disposition documentation. Exact local uv overrides and the untracked
grid-search draft are preserved; no shared resource is modified.
