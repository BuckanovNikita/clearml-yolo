# GPU control simplification verification — 2026-10-15

## Scope and baseline

Implementation starts at `9355693` and reuses feature 031's GC-01–05 amendment.
The exact local dependency-source overrides and unrelated grid-search draft remain
outside the delivered diff. No dependency revision or installed workflow tool changes.

Baseline parser inspection rejected minimal disable/release commands and had no
free command. Public records exposed UUIDs. The first startup regression run failed
four cases because high/missing memory did not stop the child and the shared public
identity helper did not yet exist. Memory-only telemetry initially failed the
MIG-independent regression. These failures preceded the implementation fixes.

## Behavioral and static checks

- Parent integrated queue controls, generation locks, startup, subprocess lifecycle,
  handoff, output, inventory and architecture selection: 314 passed.
- Strict boundary scenarios use actual task-owned guardian/workload subprocesses
  with file-backed fake NVML: exactly 2 GiB, above, unavailable, below by one byte,
  freeing during the final memory read, preserving a running job/sibling reservation,
  and a subsequent fresh check after manual freeing. No production test bypass exists.
- Real host-local locks exercise cross-root, concurrent, live/stale and interrupted
  operations, generation fencing, recovery and handoff. Simulated protected foreign
  records cover ownership-independent freeing; no real cross-UID execution is claimed.
- Initial full suite: 2562 passed, 3 failed, 30 skipped, 7 deselected. Failures were
  the newly added presentation module missing explicit architecture classification
  and two cancellation tests missing the subprocess NVML fixture. The classification
  and negative import cases were added; architecture selection passed 106 tests.
  The cancellation suite passed all three cases after explicit fixture selection.
- Review exposed an interrupted-handoff generation collision. Its new regression
  failed before the fix. Reused lock paths now advance generations even without
  claim metadata; live and stale successor regressions pass.
- Review exposed uncaught opaque driver errors during physical identity discovery.
  Three new tests failed before adapter-boundary translation. The corrected CLI
  errors sanitize GPU IDs and cold worker admission keeps jobs pending. Parent
  output/service/inventory regression selection: 135 passed.
- A separate cleanup investigation reproduced one failure among four combinations
  of retained/released GPU and live/recovered completion. The fix deletes only this
  process owner's historical sibling record before reducing its recovery allocation.
- Ruff, strict mypy (330 source files), Vulture and all 43 import contracts passed
  before final review fixes. Final integrated checks are recorded below when complete.

## Documentation and review

Updated queue, diagnostics, isolation, current contracts, Russian README, technical
reference and project end-to-end guidance. Canonical companion usage/evaluation
sources are updated separately; installed skill copies remain untouched.

Nine application Markdown documents and 36 companion files passed Markdown lint;
application checks disable the existing long-line rule. Local links/anchors, eight
minimal CLI examples, four removed-option rejection cases, strict skill metadata,
skill validation and discovery passed. The fresh documentation reviewer returned
ship with no blockers and passed four reasoning scenarios. These are reasoning
checks, not live target-model performance. See the [review record](review.md).

## Native evidence and limits

Read-only live NVML on this machine reported GPU 0 using 2288119808 bytes, above
the fixed 2 GiB limit. The fresh startup availability function returned false.
No live controls, existing GPU workloads or shared services were changed. Real
GPU execution was unavailable under the new admission rule; subprocess/lock tests
with fake NVML do not establish CUDA, multi-GPU/NCCL, multi-user/NFS or ClearML
publication outcomes. Feature 031's pre-existing external physical acceptance gap
remains open and is not converted into passing evidence by this amendment.

## Final checks and delivery

The full rerun completed with 2572 passed, 30 skipped, 7 deselected and 93 warnings
in 651.48 seconds. Five regressions added during review are covered separately by
the final focused selections: 59 control/generation/startup/handoff/grace tests and
135 output/service/inventory tests passed. The first source commit attempt also passed the full pytest hook on the final
combined tree, including those five tests, plus all static/import hooks. That commit
stopped because the changelog hook added the previous release-verification entry;
the generated change was reviewed before the normal checked retry.

Final Ruff, mypy (330 source files), Vulture and whitespace checks passed. All 43
import contracts passed; executable architecture coverage includes both newly
injected forbidden presentation-module dependencies. Fifteen changed application
Markdown files passed lint and 252 local file/heading links resolved. Wheel and
source-distribution builds succeeded as a preliminary packaging check; immutable
release version/package and remote-ref verification remain delivery work.

Independent follow-up review returned ship with no remaining code blockers. The
architecture record reconciles every task-owned changed/new path, including test
helpers, import configuration, technical reference and project skill guidance.
The local source section and unrelated draft are excluded; no removed module or
untracked implementation file is omitted. Local amendment acceptance is complete;
this does not close the earlier external physical acceptance gap. Git-tag release
results will be recorded in release.md after the native workflow finishes.
