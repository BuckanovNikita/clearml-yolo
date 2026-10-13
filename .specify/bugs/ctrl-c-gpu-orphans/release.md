# Ctrl+C cancellation release verification

Date: 2026-10-13. Scope: the cancellation fix and its bug/contract documentation.
This continuation supersedes the earlier release deferral in [test.md](test.md);
the original workspace remains untouched while checks run in an isolated checkout.

## Scope and sequence

The seven paths in [architecture.json](architecture.json), plus adjacent bug records,
are selected. Existing static-analysis hooks, configuration, documentation, tests,
local dependency overrides and the unrelated gpu_queue edit are excluded. The source
and release commits use the established hooks, with local uv source overrides absent.
Only generated changelog and root project/lock version updates are release metadata.
No dependency resolution or upstream dependency changes are authorized or performed.

Scope/integration investigation ran independently while the parent prepared the
checkout and native acceptance. Source verification, checked semantic version creation,
fresh distribution checks, independent release review and explicit branch/tag pushes
are sequential dependencies. The original workspace will be fast-forwarded only after
its retained edits pass a byte-level preservation check.

## Native execution and publication

Both CPU and single-GPU one-epoch train-to-predict runs completed through queued
supervision, with automatic admission enabled and force disabled. A six-image
synthetic dataset used disjoint train/validation/test splits with one background image
per split. Random weights establish execution only, not model quality. Training used
batch 2, 64-pixel inputs, zero loader workers, AMP false and compile false.

Fresh server readback confirmed one completed task and one loadable native best Output
Model per run. Required gt_csv and predicts_csv artifacts were force-downloaded:
6 source rows and 108 prediction/background rows each, original source identity
preserved, confidence bounds checked, standalone prediction marked not evaluated.
The GPU run recorded one reserved UUID; its final registry contained no requests.
The supervising process retained its original CUDA_VISIBLE_DEVICES value.

The initial readback harness expected GPU selection metadata on CPU; this field is
correctly absent without selected GPUs, so the harness was corrected. The first GPU
attempt waited without creating a task because existing use exceeded the default
2 GiB limit. Interrupting that owned waiter exited 130. A scoped rerun used a 4 GiB
admission limit and completed. Existing GPU processes and shared services were preserved.
Tagged test projects/tasks and owned invocation directories were cleaned after each
attempt, with zero matching resources confirmed by the environment helper.

An isolated SDK configuration used supported report_use_subprocess=false, as in the
previous release, to avoid the known external reporting subprocess issue. No SDK
source or runtime monkeypatch was used. Evaluation/comparison/report and FiftyOne
publication were excluded because their contracts and implementations are unchanged.

## Limits

The user's other multi-GPU host was not accessed. Real CPU Torch ranks establish
separate-session cancellation; the GPU smoke establishes single-device execution,
publication and ordinary lease cleanup. Physical multi-GPU CUDA/NCCL cancellation
remains unverified. Linux pidfd/process-visibility requirements and conservative failure
on a newer opaque same-user process remain documented compatibility constraints.

## Completion evidence

Commit hooks, final distribution verification, independent release review and remote
readback will be appended after their results are available.

## Process-exit race found by the release gate

The first completed isolated full-suite run failed two Hydra launcher checks
(2269 passed, 30 skipped): environment inspection reported access denied for
short-lived processes. A fresh read-only investigation identified a stat/environment
race: the process can exit after its live stat snapshot, leaving a stale unreadable
flag. Those logs are consistent with this race but do not establish the exact states
of the already-disappeared PIDs at the time of denial.

A deterministic five-case regression reproduced false cleanup failures for disappeared
and zombie processes before the amendment (2 failed, 3 passed). The runtime adapter
now refreshes process state after environment access denial; only confirmed exit clears
the uncertainty. Live processes, reused live PIDs and denied state refreshes remain
fail-closed. The actual non-dumpable process regression remains unchanged. This adds
no module, public interface or dependency and stays within the existing ownership
adapter/test scope. Final verification and review cover the amended candidate.

After the exit-race amendment, the combined cancellation/supervision/queue/launcher/
architecture run passed 180 tests. Touched-source Ruff and mypy passed. Native CPU
and queued single-GPU train-to-predict runs, force-downloaded artifact/model checks
and empty-registry cleanup verification were repeated successfully on this candidate.

## Ownership correction from independent review

The fresh reviewer reproduced a second race without sending OS signals: root PID
reuse after the initial process table could make numeric ancestry/session expansion
adopt an unmarked child of the replacement. Two deterministic regressions failed
before correction, one for each association. For production supervised jobs, new
ownership now requires the inherited marker, while retained PID/start identities are
refreshed. Numeric ancestry/session expansion remains only for private callers without
a token, preserving the earlier compatibility path and its explicitly limited guarantee.
The sole production attachment path always supplies a fresh token. Runtime and GPU
contract documentation now states this distinction. Module boundaries and dependencies
are unchanged; the amended ownership behavior is covered by the same architecture scope.

## Stable discovery correction from follow-up review

A second independent review reproduced a late-fork omission: a parent can exit during
inspection after creating a child absent from the original directory enumeration.
Three deterministic regressions failed before correction, including a two-generation
case that exercises actual table construction when an enumerated child disappears
before stat. Cleanup now requires two empty scans with identical candidate PID/start
and live-versus-zombie identities. Disappearing enumerated processes and state changes
during inspection invalidate a scan and trigger another iteration within the existing
shutdown deadline. Ordinary running/sleeping transitions do not change the cohort.
This preserves fail-closed visibility handling and bounded cleanup while preventing
single-snapshot emptiness from releasing a live descendant's capacity.

The corrected candidate passed 185 focused cancellation/supervision/queue/launcher
and architecture checks. A final cancellation-only run passed all 18 cases after
lint formatting. Full Ruff and mypy checks passed (285 source files). Final native
CPU and single-GPU queued train-to-predict runs repeated the publication/readback
checks above; the GPU registry was empty after cleanup and tagged resources were
removed. These are local execution results, not remote multi-GPU verification.

Fresh independent read-only review accepted the corrected implementation with no
remaining blockers. It checked ownership, PID reuse, late-fork discovery, fail-closed
visibility, bounded shutdown, signal deferral and the matching tests/contracts.
Release hooks and installed-distribution verification remain separate pending gates.


## Local 0.26.1 candidate acceptance — 2026-10-13

The source commit is `77146e737a5f6a4c7fb981c9c4fc64ce33ab50fb` and the checked version commit/annotated
Git tag is `0184f32b0f30a8ec0071d76f7a1d743800517490` / `v0.26.1`. The final source bytes match the
independently reviewed candidate. Release metadata changes only the root version in
pyproject.toml and uv.lock, plus the generated changelog; parsed dependency metadata
and approved dependency sources are unchanged. Local source overrides are absent
from both commits and remain preserved in the original checkout.

| Final gate | Result |
| --- | --- |
| Source commit hooks | Passed: full suite 2281 passed, 30 skipped; lint, types and 40 import contracts passed. |
| Version commit hooks | Passed: full suite 2281 passed, 30 skipped; normal metadata/lint/type/import checks passed. |
| Recovery tag validation | Passed: required all-files checks and full suite 2281 passed, 30 skipped. |
| Focused regression and architecture | 185 passed, including 94 architecture checks; final cancellation file 18 passed. |
| Native CPU and single-GPU execution | Queued train-to-predict, native model/artifact readback and empty GPU registry passed; tagged resources cleaned. |
| Fresh wheel installation | 790 checks passed, including all 11 CLI help commands, configuration contracts and 157 source-file byte comparisons. |
| Fresh source-distribution installation | 790 checks passed in a separate environment, including the same CLI/configuration/source checks. |
| Dependency compatibility | Both fresh installed environments passed uv pip check. |
| Independent review | Corrected code approved with no blocking findings; scope/integration preservation review passed. |

The 30 suite skips are 29 isolated FiftyOne/database cases and one unsupported native
filesystem reflink operation. They are not passes. Earlier Vulture results belong to
the initial workspace verification; the released hook configuration uses Ruff, mypy
and import-linter, and the unrelated static-analysis change is excluded.

The first version-commit attempt and initial source-distribution install exhausted
the temporary filesystem while copying dependencies. The source commit was retained;
no tag was created by that failed attempt. Completed/partial task-owned environments
were removed, installation and test temporary files moved to the data filesystem,
and the documented checked recovery completed. A retry harness also corrected its
working directory for existing relative dependency paths. No product source, lock
resolution, dependency version or hook was changed or bypassed to recover.

After capacity recovery, the tag revalidation process terminated with SIGILL during
the native DDP reader thread entering tracing while garbage collection was active.
The traceback does not establish its cause. No SIGILL is sent by the cancellation
implementation, and no task-owned process remained after the abort. All 22 native-DDP
tests passed in the targeted rerun. The unchanged candidate then passed the complete
normal recovery gate before tag creation. This isolated interpreter crash is recorded
as an unresolved intermittent validation observation, not a corrected product defect.

Distribution SHA-256 values (local verification artifacts; no package upload):

- `clearml_yolo-0.26.1-py3-none-any.whl`: `1b5b9804c537db53d9ee5b9101e4633cf457e3ea3bb3e8f2e5f85c6e934b1ad1`
- `clearml_yolo-0.26.1.tar.gz`: `e14f1874736fd26e32d1dea698bd6b4b9cae4c5351c17e7fbaac58f34318e07a`

Architecture acceptance reconciles the seven owned implementation/test/contract paths,
six bug records and generated release metadata. The separate workspace preservation
check was refreshed after another actor removed unrelated static-analysis edits;
all owned source files were unchanged, and the remaining local source overrides are
preserved. No unrelated change is included in this release.

- [x] Reproduce and correct the original cancellation defects and release-discovered races.
- [x] Complete regression, native execution, installed-distribution and documentation checks.
- [x] Obtain independent review and reconcile module architecture acceptance.
- [x] Create checked source/version commits and the annotated Git version tag.

This record captures local acceptance before the explicit branch/tag push. Publication
and original-checkout fast-forward are verified separately by remote ref readback and
byte-preservation receipts. No GitHub Release object or package asset is authorized.
Remote physical multi-GPU CUDA/NCCL cancellation remains unverified as stated above.

## Concurrent upstream release and 0.26.2 continuation

The atomic publication attempt was rejected without changing either remote ref:
master had advanced to `95f07e17f413c369dad6af7b801a540ac12fa756`, and the
remote `v0.26.1` already identified the separate static-analysis release. The local
0.26.1 candidate and its checks above were not published. Its history is retained
as evidence; the cancellation release now targets 0.26.2 on the newer committed base.

None of the seven cancellation-owned paths overlaps the intervening upstream diff.
Their tested bytes were carried intact into a new isolated checkout. The static-analysis
changes are now committed baseline behavior and are preserved; no dependency change
is authored by this cancellation release. Its current Ruff and Vulture checks passed
without amendments. The module boundaries, public interfaces and effect ownership
remain unchanged. Updated full hooks, native CPU/GPU checks and fresh distributions
will establish acceptance on this integrated base before publication.

On the refreshed base, Ruff, Vulture and mypy passed (286 source files). Native CPU
and single-GPU queued train-to-predict runs repeated successfully; downloaded model
and CSV readback checks passed, the GPU registry was empty, and tagged resources were
removed. Documentation parsing/local links and structural architecture acceptance
passed. Full commit hooks and 0.26.2 distribution checks remain pending at this point.

## Final 0.26.2 acceptance — 2026-10-13

The cancellation release is based on committed upstream `95f07e1`. Source commit
`6e7b7a730326f829337e259673cd1d830bdd54c4` and version commit `04fc8e95171fd2b2198430ddcc4b191a371a97b5`
passed their normal hooks; the annotated tag is `v0.26.2`. This supersedes the
unpublished local 0.26.1 candidate for publication, without rewriting its evidence.

| Current gate | Result |
| --- | --- |
| Source commit full suite | 2296 passed, 30 skipped; normal hooks passed. |
| Version commit full suite | 2296 passed, 30 skipped; normal hooks passed. |
| Fresh wheel installation | 790 checks, all 11 CLI help commands and 157 source-file byte comparisons passed; uv pip check passed. |
| Fresh sdist installation | 790 checks, all 11 CLI help commands and 157 source-file byte comparisons passed; uv pip check passed. |
| Static and architecture | Ruff, mypy (286 files), Vulture and 40 import contracts passed without weakening the newer policy; architecture checks passed within the full suite. |
| Native CPU and single-GPU | Queued train-to-predict, downloaded model/artifact checks and empty GPU registry passed; tagged projects/tasks removed. |
| Independent integration review | Fresh review of the final integrated candidate approved publication subject to completed release gates. |

The source and tests retain the previously reviewed cancellation bytes. The current
baseline already contains the separate static-analysis release; the task-owned diff
adds only the seven cancellation paths, six bug records and generated release metadata.
Parsed project/lock metadata changes only the root version from the new base. Approved
dependency sources and upstream work are preserved, including the current Vulture gate.
The local uv overrides remain outside release commits.

The 30 skipped checks are the isolated FiftyOne/database cases and an unsupported
filesystem reflink operation; they are not counted as passes. Physical multi-GPU
CUDA/NCCL cancellation on the user's remote host remains unverified. The earlier
capacity failure and isolated interpreter abort remain historical failed attempts;
no hook, code path or dependency was altered to hide either failure.

Local distribution SHA-256 values:

- `clearml_yolo-0.26.2-py3-none-any.whl`: `59483d280563d24a4a9da4b1c85c6dfd4f2b36c7d87912dcc0dd81184bf28c03`
- `clearml_yolo-0.26.2.tar.gz`: `7000c8bb4280ca97f19a6b04be141fede03d349b9321cea93ec95b9449207bf5`

Documentation parsing/local-link checks and architecture acceptance are rerun after
this evidence update. Explicit branch/tag publication and original-workspace preservation
are checked by remote readback and byte-level receipts after this acceptance commit.
No GitHub Release object, registry publication or package upload is performed.
