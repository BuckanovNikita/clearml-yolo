# Bug Verification: Queue job finalization and inference handoff

Date: 2026-10-15. Baseline: `932614ba698dede3ec6405476846ecbbc95f0976`.
Scope and implementation: [assessment](assessment.md), [fix](fix.md),
[architecture record](architecture.json). Independent review passed; release delivery remains pending.

## Failure and correction

The supplied remote incident is a queued task whose work and artifacts completed,
then native scope exit raised `UnverifiableProcessTreeError` for inaccessible
processes. The regression reproduced that exception at the command boundary before
the correction. With a genuine inherited supervisor channel, the successful task
now completes without entering the direct-command native scope. Unsupervised
commands keep their existing cleanup behavior.

Live guardian tests exclude unrelated processes, preserve birth identity across
PID reuse, inspect children of every native thread, track double-fork/session
escape and adoption, and retain ownership when a zombie leader still has threads.
Relevant unreadable topology continues to block unsafe release. Historical owner
recovery retains its existing conservative global marker scan.

Handoff tests use real local locks for synthetic GPU identities. They prove the
first reservation stays owned while another lease acquires extras, with publisher
processes still alive. Training memory cleanup precedes the notification; inference
waits for acknowledgement. Precommit claim failure, durable contraction followed
by failure, lost acknowledgement, repeat notification and cancellation are covered.
These tests establish reservation behavior, not physical multi-GPU execution.

## Executed application checks

- Full routine suite: **2545 passed, 30 skipped, 7 deselected**, 617.33 seconds.
  Includes native CPU/Gloo DDP regressions. Optional skips/deselections are not
  claimed as hardware or publication coverage.
- Focused lifecycle/direct checks: 45 passed; lifecycle checks with the added
  bounded-timeout case: 7 passed. Guardian/handoff cases: 15 passed; combined
  guardian/grace/process checks: 33 passed. Live subreaper cases: 13 passed;
  combined process/direct/recovery checks: 64 passed. Selections overlap.
- The final test-only safety guard prevents synthetic recycled PIDs from ever
  opening an actual pidfd even if the ownership regression recurs. Together with
  the lifecycle tests, its final selection passed 8 tests.
- Ruff, strict mypy (322 source files), and Vulture passed.
- `lint-imports`: all 43 contracts passed. Separate architecture suite: 104 passed.
- Wheel and sdist build passed. Each was installed into a fresh environment outside
  the checkout, with import origin verified in its new site-packages. All 12 CLI
  helps and Linux runtime capability/new-module probes passed for each artifact.
  These application installs reused the prepared locked dependency environment;
  they do not establish independent dependency resolution. Candidate metadata was
  still 0.30.1 before the release workflow.

Raw local logs are retained under the ignored `.tmp/queue-job-finalization/`.
No dependency source or approved revision was modified.

## Native execution and publication

Direct CPU acceptance passed with ClearML task
`fb49b2a0a558454d8d6151eaeefbef7f` and output model
`218c752aafc44571a9f237ba8ba05c9e`. A force-downloaded checkpoint was reloaded and
used for prediction. Downloaded ground truth contains six rows, two per disjoint
split, including three empty-image markers. Predictions preserve all six source
identities and contain six ground-truth plus 30 prediction rows.

The scoped fixture uses random local YOLOv8n initialization, one epoch and six
synthetic images. Metrics, report and comparison are disabled; no scientific
accuracy or full report-publication claim follows from this acceptance.

Real queued single-GPU acceptance passed through submission, frozen snapshot,
persistent worker and external guardian. Queue job
`18be07ff-1998-4016-9f18-20f5e1b404a8` completed at revision 8; ClearML task
`a95acc6f25da4f209a0f701ab0fa8934` completed and published one output model,
`c3fbef6b58fc4868a2e176e90b6f98b5` (6,189,034 bytes). Force download, reload and
prediction passed; artifact contents matched the CPU structural checks. Live
readback observed console output and native epoch scalars before completion.

The worker used explicit `--max-used-memory-gib 3` for this scoped check after
the default admission correctly remained pending against NVML telemetry. No
shared workload was stopped. Two earlier pending attempts were cancelled; a
temporary harness JSON-shape error was corrected before GPU admission. Neither
was an application execution failure.

Postflight claim and token were null, all five recorded guardian/descendant birth
identities were absent, owned workers exited 0, and tagged cleanup proved zero
remaining test tasks/projects after evidence and downloads were archived. The
integrated source identity was
`bcf1803d06f625de0bef7f44f33c7c9c4bfc8200f1e70e03128a0d5d99cc6c0e`.

Physical multi-GPU/NCCL training is unavailable on this one-GPU test host; synthetic
reservation tests are not a replacement for that hardware check. The original
remote task was not rerun or modified.

## Documentation and portable guidance

Maintained queue/runtime contracts, README, the current queue specification and
project-owned end-to-end skill/prerequisites were updated. Ten changed application
Markdown files, including the bug evidence, passed markdownlint with line-length
checking disabled to match existing prose. The combined local-link check passed
72 file/heading targets; skill metadata passed.

The companion corp-skills usage and evaluation references describe the same
ownership, stage ordering and failure semantics. Package discovery, strict YAML
metadata, local links, Markdown and no-impact architecture validation passed.
Two fresh-context native Codex evaluations correctly explained three-GPU contraction
and the distinction between a completed task and uncertain guardian cleanup.
They also identified the release-pending label. These are behavioral reading
checks, not automatic skill routing or OpenCode/DeepSeek runtime evidence.

Fresh [independent review](review.md) returned **ship**, with no blocking findings,
and independently passed all 35 new tests. Parent reconciled the complete task-owned
diff and architecture acceptance. Git-tag-only release delivery remains pending.
