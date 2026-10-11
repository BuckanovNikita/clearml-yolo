# Verification — 2026-10-11

Implementation, native acceptance and fresh independent final review are complete.
Release checks remain pending. No dependency pins changed.

## Completed evidence

- Queue/FIFO/supervision/exact-selection/Hydra tests: 54 passed.
- Command-specific export tests: 54 passed, including fresh-process runtime-import
  blockers, all eight selections, exact output inventories and overwrite protection.
- Runtime bootstrap/filesystem tests: 69 passed, including real SIGTERM, orphaned
  parent/live-child ownership, recovery, outside-project configuration rejection and
  environment rollback on initialization failure.
- Bounded FiftyOne process tests cover phase hangs, failures, cancellation, redaction,
  receipt identity and unsafe cleanup retention. Final integrated count pending.
- Native CPU/Gloo distributed regression: all five scenarios passed (two/four ranks,
  both rank failure cases and owner callback failure).
- Final parent pre-commit verification: the full pytest suite, Ruff, strict mypy and
  all import contracts passed. The changelog hook first regenerated committed
  history; that change was inspected and the hook rerun passed. Canonical replay
  and execution-control integration: 17 passed.
- Built wheel and sdist; installed each into separate fresh environments reusing the
  existing dependency installation without the project's editable source path. All
  ten command helps and all eight exported Hydra configurations passed. Confirmed
  packaged queue namespace/plugin/worker and native extension imports. Rebuilt and
  repeated both installation checks after the final isolation correction; archived
  bootstrap/compatibility source matched the final checkout. This did not test a
  fresh dependency resolution.
- Documentation agent checked 26 changed/new Markdown files, 212 local links/anchors,
  44 fenced examples, YAML, shell/Python syntax and all eight real export/composition
  examples. Additional dedup/programmatic-runtime amendments received scoped checks.
- Actual bounded FiftyOne preflight succeeded against an isolated test database.
- Post-fix ClearML configuration/session/TRACE regressions: 98 passed.
- Final architecture/execution/native-runtime integration: 80 passed. A reproduced
  FiftyOne internal-state path override was corrected: unrelated ambient environment
  names no longer select internal SDK files; 39 bounded-publication/compatibility
  tests and focused Ruff/mypy checks passed afterward.
- Live acceptance completed ten ClearML tasks, force-downloaded 82 artifacts and read
  back four native Output Models. FIFO inspection collected 468 queue observations,
  including 131 with one active job and two waiters. Healthy FiftyOne publication
  retained 12 samples and three native evaluations; unreachable publication warned
  after 3.046 seconds while full computation completed.
- Paired comparison used the same four images and settings for both models. Standalone
  validation with nondefault IoU 0.6, greedy matching and continuous AP, followed by
  comparison/report generation, passed.
- File-access auditing of four post-fix native commands recorded 26,569 events, no
  known forbidden home configuration/session opens and 24 project session-cache opens.
  Invocation scratch was removed. Exact-tag cleanup left zero owned projects/tasks,
  removed the owned FiftyOne set, and confirmed all 14 traced PIDs had exited.
- Native evidence is retained externally; archive SHA-256:
  `33b8575a71a882f2d0e7e19878f82f5ab2b72bebcf9e34b715d4ee17b3fb0eea`.
- Final scoped documentation checks validated six Markdown files, 31 local links and
  anchors, 17 fenced examples, Python/shell syntax and whitespace/conflict-marker/fence
  checks. New path/binding/compatibility guidance was checked against bootstrap and the
  ClearML configuration adapter; existing CLI/Python examples were unchanged.

## Integration failures and corrections

The first full run had 65 failures, 1559 passes and 30 skips. Most failures were
cross-test environment contamination after persistent initialization; additional
fixtures still expected the removed queue or configured library paths outside their
project. Added test-state restoration, updated policy-specific fixtures and corrected
programmatic native runtime restoration. Preserved dedup's filesystem-only behavior.
The later full suite had one failure, 1,638 passes and 30 skips: an outdated fake SDK
fixture did not expose the configuration interface now checked by the adapter. The
fixture was corrected and the 98 affected tests passed again. Final full-suite
verification then passed through the repository pytest hook; neither earlier failed
full run is reported as passing.

## Pending acceptance

Release remains pending. Native
Windows, physical multi-GPU and the WSL busy-to-idle transition are unverified. The
original hang's root cause remains unconfirmed; bounded failure evidence does not
establish that cause.
Machine-specific commands/logs and service identity are retained outside this repository.

## Independent review corrections

The first independent reviews required fixes for three reproduced edge cases:

- A disappeared UUID left a pending queue head waiting indefinitely. Its own
  supervisor now reports the loss and cleans its ticket; healthy followers advance
  without removing another live owner's state. Queue/supervision/scheduling/launcher
  regression verification: 56 passed. A follower-first race was also reproduced and
  corrected: admission stops at every invalid pending visibility set, so another
  supervisor cannot silently admit its surviving subset.
- Hardcoded SDK directories could bypass validated custom XDG roots through symlinks.
  Session/model directories now follow those roots and validate physical project
  containment before creation. Real SDK configuration/session/TRACE verification:
  101 passed, including three red/green symlink cases.
- ETA's literal colon list parser corrupted Windows drive letters and POSIX directory
  names containing colons. Bootstrap now transfers absolute model paths as JSON and
  the worker uses ETA's public configuration API before FiftyOne imports. This keeps
  SDK source unchanged. Native Windows remains unverified; the portable regression
  exercises real ETA with a filesystem normalization seam.

Post-correction parent architecture/entrypoint/native/control checks: 89 passed.
Ruff, strict mypy (220 files) and all 29 import contracts passed. Parent ETA/bootstrap/
bounded-publication verification passed all 100 tests. A final real FiftyOne preflight
(6.223 seconds), publication (3.597 seconds) and fresh-process readback passed with
12 samples, three native evaluations and exact configured ETA model paths. All
follow-up scratch, owned datasets and tagged resources were removed.

A subsequent review reproduced an outward fontconfig cache symlink; the parent also
found equivalent FiftyOne internal-state symlink escapes. Both now validate physical
project containment before supplying SDK paths. Final combined bootstrap, publication,
ClearML state and queue regressions passed all 127 tests, with Ruff, strict mypy and
29 import contracts passing afterward. Fresh independent review approved the combined
changes, independently passing 40 queue, supervision, FiftyOne compatibility and
fontconfig tests plus a private-binary-path containment check. No blockers remain.

The final wheel and sdist each matched all 117 Python modules and included plugin
configuration. Fresh installations passed 20 installed-origin checks, 20 command
helps and four representative exports/compositions. The complete eight-command
matrix had already passed in both installation formats before these path guards.
