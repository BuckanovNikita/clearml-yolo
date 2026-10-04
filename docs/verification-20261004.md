# Parent acceptance evidence — 2026-10-04

This verifies the [14-finding remediation](review-fixes-20261004.md) against baseline
`4c0e627`, with the candidate digital-metrics and report-generator fixes evaluated separately.
No committed dependency references, lockfile entries or submodule revisions changed.
The original workspace and its local editable overrides were preserved.

## Regressions and package checks

- Pinned dependency environment: `uv run --no-sync pytest -q` — 917 passed, 9 skipped.
- Isolated candidate dependency environment: the same full suite — 917 passed, 9 skipped.
- After the final stale-plot correction: all 136 affected metrics, comparison-assembly and
  session tests passed. Both legacy and suffixed producers must create fresh confidence plots;
  absent fresh outputs fail, and unrelated destination files remain intact.
- Ruff passed; mypy checked 110 source files; all nine import contracts were kept.
- Wheel and sdist built. An installed wheel exercised all nine entrypoint help commands,
  configuration export, and rejection of repeated export without overwrite permission,
  with malformed optional FiftyOne configuration.
- Test-first probes preserved the original failing assertions. The first focused YOLO set
  produced 32 expected failures before remediation; the telemetry-stall test failed by timeout.
  Three stale-plot cases failed before the final correction.

## Real native and ClearML acceptance

A disposable, explicitly tagged project used synthetic, disjoint train/validation/test image
sets, including empty images. Every run used explicit ClearML project names and tags.
Training used a fresh YOLO architecture for one small epoch. No pre-existing task, model,
service, GPU job or stored dataset was modified.

| Dependency configuration | Execution | Result |
|---|---|---|
| Committed pins | Native CPU pipeline | Completed; 16 artifacts and one output model downloaded. |
| Committed pins | Native single-GPU pipeline with paired baseline comparison/reports | Completed; 19 artifacts and one output model downloaded. |
| Both proposed dependency fixes | Native CPU pipeline with paired comparison/reports | Completed; 19 artifacts and one output model downloaded. |
| Both proposed dependency fixes | Native single-GPU pipeline with paired comparison/reports | Completed; 19 artifacts and one output model downloaded. |
| Both proposed dependency fixes | Standalone validation, comparison and report entrypoints | Completed; respective 10, 5 and 2 artifacts downloaded. |

Downloads were forced from the service, then checked for readable evaluation/report contents,
expected workbook sheets and nonempty output models. Normal report outputs used fresh destinations.
The first combined CPU attempt exposed a plot-naming incompatibility; it was corrected and the
complete CPU run repeated successfully. That failed attempt is not counted as acceptance.

Live failure checks rejected required uploads and flushes, and delivered SIGTERM during an
owned invocation. In each case the original failure reached its caller, the remote task became
failed, and cleanup ran without SDK self-abort. An independent digital-metrics Tracker failure
also retained its original exception and reached remote failed status. SDK task closure precedes
a failure transition through a fresh task handle. If SDK closure itself fails, the original
exception is preserved; a terminal remote state cannot be guaranteed in that exceptional case.

A live baseline lookup with multiple required tags and a whole-name alternation pattern selected
the eligible older baseline rather than a newer task missing a required tag.

All test-owned ClearML tasks, models, artifacts and the disposable project were deleted after
verification. The final cleanup query found zero tasks/projects under the owned tag. Local run
outputs were removed; dated diagnostic logs remain outside the repository in environment evidence.

## Queue and boundary evidence

Queue regressions use event-blocked telemetry and concurrent registry operations to prove the
lock remains available while telemetry waits, with state reread, FIFO admission and atomic
reservations. Impossible partial reservations are rejected. These checks do not induce a real
NVML driver hang. EXIF tests use actual rotated non-square JPEGs and verify unchanged source
bytes. Replay tests exercise the actual adapter through a fake SDK round trip, including explicit
empty values; they do not claim a separate remote replay experiment.

## Remaining limits

Physical multi-GPU/DDP execution, Windows, induced hardware/driver hangs, enabled FiftyOne
persistence and measured GPU-memory improvements were not exercised. The nine opt-in integration
skips are disclosed rather than counted as passes. Neither backend matching/AP parity nor those
platform outcomes are claimed. Mandatory application, package and live checks for this change
were available and passed; these platform limits do not conceal a known failing regression.

## Documentation

The working assessment/fix/test records are self-contained and leave historical audits local.
Maintained CLI, training conversion, optional publisher, publication, tracking and GPU queue
contracts were updated. README usage and committed dependency installation instructions remain
accurate, so no README change was needed. Markdown parsing, local links and changed installed
examples were checked. No installed workflow tooling or constitution was changed.

## PCRE boundary followup

Independent review identified that MongoDB's PCRE permits a terminal newline before `\Z`,
unlike Python's regex engine. A PCRE whole-record oracle reproduced the remaining failure
(one failed, three passed). The expression now adds a portable strict-end negative lookahead,
rejecting terminal-newline names in both engines while preserving deliberate regex patterns.

## Final independent review

The final fresh Sol reviewer returned **ship** after inspecting the complete patch and running
227 affected tests, including the PCRE whole-record boundary. No actionable findings remained.
Physical platform and optional persistence limits above remain explicit.

Final full reruns after both review corrections passed **927 tests, 9 optional skips** in each
of the pinned and combined dependency environments. Four upstream deprecation warnings remain.
The commit hooks regenerated the committed-history changelog, which was reviewed and staged.
The first hook attempt had an incompatible `UV_FROZEN`/`--locked` environment setting; it was
removed and the required checks rerun without bypassing hooks. `UV_NO_SYNC` preserves the
already verified dependency environments while all configured checks execute normally.
