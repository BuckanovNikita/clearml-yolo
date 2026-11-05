# Verification: preserve training outcomes

Date: 2026-11-05. Result: implementation accepted; Git-only release follows these checks.

## Focused and independent checks

Focused pipeline regressions passed (38), count/report regressions passed (20), architecture
and publication regressions passed (285), and native callback/DDP regressions passed (32).
These cover unavailable counts, all-unknown reports, real workbook roundtrips, dependency
skips, resource handoff, interruptions, native completion callbacks and actual relay cleanup.
Independent review accepted the final code with no unresolved findings; see [review](review.md).
Current and proposed CY/queue source checks passed; see [paired evidence](paired.md).

The first complete current-source suite reported 4 failed, 4785 passed, 30 skipped and
81 deselected. Three failures were an unset optional status-message field newly recorded by
the exact-signature fake; the fourth was an event-order fixture without prepared ground truth.
The fake now omits an unset optional message and the fixture supplies a real training row.
All four original paths plus finalization regressions passed (13 tests). Runtime code was
unchanged. The complete canonical suite was restarted and passed.

Initial broad and interrupted canonical attempts were not accepted. Their failures drove
fixture and explicit workbook SDK ownership corrections. Native attempts also exposed nested
finalization deadlines and unsupported ClearML completion arguments, which were corrected.

## Native reproduction

The final current-source run used the isolated CY 0.45.0 task environment, real YOLO CPU
training (one epoch, six synthetic images), real prediction and an isolated ClearML project.
It injected a metrics ValueError after successful training and prediction. Optional model
catalogue prefetch was disabled in the test harness; training, prediction and publication
were real. This establishes the failure lifecycle, not model quality or GPU behavior.

Exit code was zero. A nonempty best.pt survived. The local outcome reported training and
prediction succeeded, metrics failed, comparison/report skipped and completed_with_warnings.
Required combined prediction publication truthfully remained incomplete, without manufactured
upload receipts. ClearML task 8471c7de72b64b90b9dbb2e0ce613cf8 was read back as completed,
with a completed_with_warnings pipeline_outcome artifact and status_message:
`completed_with_warnings: Training succeeded; publication incomplete; see local outcome`.

The owned ClearML project/tasks and run directory were deleted after evidence capture;
cleanup confirmed zero remaining matching tasks/projects. Existing shared workloads and caches
were preserved. The earlier successful task 2918f4f8b7584f7c9b2af4f73e868ce9 was also cleaned.

## Scope limits

Training counts without exact checkpoint provenance remain unavailable. Historical remote
count recovery is not implemented. Fault-injection regressions cover malformed standalone
reports and strict training/interruption behavior. The configured mutation targets were
inspected: no selected training-box, evaluation-policy or export-quality module changed, so
that mutation suite is not applicable. CPU/DDP suite evidence does not establish GPU/NCCL.

## Final acceptance

Canonical verification passed with exit zero: Ruff, strict mypy, Vulture, import contracts
and 4789 pytest cases passed; 30 skipped and 81 opt-in cases deselected. The suite includes
real CPU/Gloo DDP and the original failure paths. Documentation validation passed: 241
Markdown files, zero issues. Independent architecture review is accepted, and its structured
record is validated at acceptance before commit. Portable usage discovery, behavioral
review and full collection Markdown validation passed; installed host exports were not changed.

Current-source and proposed-release paired checks passed as recorded in [paired](paired.md).
Release will use Git commits and an annotated tag only. Final release-version identity and
remote-ref evidence are recorded in the portable collection's dated pipeline-outcome evidence.
No local tool.uv.sources section was present to remove or restore for these commits.
