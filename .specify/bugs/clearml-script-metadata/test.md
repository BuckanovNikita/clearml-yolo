# Bug Verification: ClearML script metadata

- **Slug**: clearml-script-metadata
- **Tested**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: implementation accepted; final source hooks passed. Native release delivery remains pending.

## Checks performed

| Check | Result | Evidence |
| --- | --- | --- |
| Pre-fix live reproduction | Confirmed | Completed task `52567e01e7f84e508ac24c6455eba9e6` has empty repository/entrypoint and absent branch/commit/working directory. |
| Failing regression | Expected failure | Source metadata assertion observed zero writes before implementation. |
| Focused behavior and architecture | Pass | `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_clearml_script.py tests/test_clearml_session.py -q`: 261 passed after integration, URL/fresh-read correction and Git-environment isolation; five existing Hydra/Pydantic warnings. |
| Import contracts | Pass | `uv run --frozen --no-sync lint-imports`: 43 kept, zero broken; architecture suite includes forbidden-edge mutation cases. |
| Ruff | Pass | `uv run --frozen --no-sync ruff check .`. |
| Strict mypy | Pass | `uv run --frozen --no-sync mypy .`: 332 files after integration. |
| Vulture | Pass | `uv run --frozen --no-sync vulture`. |
| Packaging | Pass | `uv build`; built wheel contains `clearml_yolo/adapters/clearml/script.py`. No distributions published. |
| Original live execution path | Pass | Real three-image `cy-ground-truth`, exit zero, exactly one completed task; fresh API readback below. |

The initial full run on the older base had 21 failures: 19 missing optional
detector dependencies, one queue protocol mismatch with concurrent host state,
and one watchdog SDK double lacking script publication. Existing locked extras
resolved all 19 detector failures (45 checks passed). The queue case passed after
integrating the latest committed queue implementation. The corrected watchdog
fixture passed all 20 subprocess tracing checks. No shared queue records were deleted.

Five URL regressions reproduced the independent review finding before the SSH/IPv6
correction; the final focused run includes all nine origin URL cases.

The broad pre-review suite passed 2590 tests, with 30 skipped and seven
explicit physical-GPU cases deselected. The all-files hook command exited one
because it regenerated the changelog and the review corrections were applied
while its test hook was running. This is not a complete successful hook run;
the source commit must rerun the final checks without concurrent edits.

The first source-commit attempt was intentionally terminated after detecting
Git-fixture environment leakage; it did not produce a commit. Git settings and the
isolated index were restored. The corrected fixture and production Git reads are
covered by a failing-then-passing inherited-environment regression and a 21-case
canary run that leaves Git config, HEAD and index unchanged.

## Live readback

The initial corrected task `de2b8dcf2b0a4b6fa9d2e314eca95389` verified the five
fields before review. After both review corrections, a second real CPU task
`1a24a8775a6c4c8e80fed631ce2c7b30` completed, exited zero and was the only task in
its isolated project. Independent API readback at 2026-10-15T14:22:52Z confirmed:

| Field | Recorded value |
| --- | --- |
| repository | `git@github.com:BuckanovNikita/clearml-yolo.git` |
| entry_point | `-m clearml_yolo.entrypoints.ground_truth` |
| branch | `fix/clearml-script-publication` |
| version_num | `dcbbc4903cec07c67ce50cd9b116ea3f6dab8216` |
| working_dir | `.` |
| diff | Empty |

[Open the final verification task](http://clearml.k8s.localhost/projects/cab8b5e956054d3fab2c2306d4edd47d/experiments/1a24a8775a6c4c8e80fed631ce2c7b30/execution).

The isolated task and its synthetic workspace are intentionally retained for user
inspection. No training, GPU workload or shared-service change was required.

## Documentation review

The tracking publication contract documents all five fields and their limits.
The existing contract index already points to it. README and portable usage skill
commands, examples and configuration remain correct; the inspected companion source
commit and no-change reason are in the assessment. Machine setup stays in global
skills. Markdown/link checks and fresh review are recorded before acceptance.

## Residual limits

Source-less wheels cannot invent Git identity. Missing Git or origin is warned;
detached HEAD records its exact commit and HEAD selector. Git diff and raw argv are
not uploaded. Existing tasks are unchanged. Remote-agent metadata is preserved.

## Final source acceptance

Source commit `2170b7912e7835e27dc72e20e14a954c0c3c8a5c` completed with exit zero. Its unmodified pre-commit
hooks passed the changelog check, Ruff, strict mypy, all 43 import contracts,
Vulture and the complete pytest suite. No hooks were bypassed. The post-commit
release hook correctly skipped versioning on the isolated feature branch.
The worktree was clean afterward; Git repository mode, origin and author identity
remained intact.

The final focused suite passed 261 cases with five existing warnings. The 21-case
Git-hook canary test left its config, HEAD and index unchanged. Fresh independent
review found no remaining actionable issue; see [review.md](review.md).
Markdown, local links and the reconciled architecture acceptance record are
validated before the acceptance-documentation commit. No source revisions,
dependency locks or public CLI/configuration contracts changed.

Native integration and release await the separate queue release work in the
shared checkout. Existing unrelated changes remain untouched.
