# Integrated verification — 2026-10-24

Baseline: `9c3f296f370971436afd8cc300c31034d52dd4dc`. The exact local
`[tool.uv.sources]` section was preserved in private Git storage and removed before
final checking. Dependency resolution was not repeated while it was absent.

## Parent integration observations

Ruff, strict mypy, Vulture and import-linter passed on the first integrated attempt.
The parent interrupted pytest after discovering that nested `uv run` adds a recursion
counter and a duplicate environment bin directory. The interrupted run reached 1,031
passed and 47 deselected in 106.21 seconds; it produced no success receipt and does not
count as completed suite verification. Its log is `.tmp/cy005-final-verify.log`.

The real temporary-Git lifecycle test was strengthened to use `uv run` for verification
and the automatic release hook. It reproduced two suite executions before correction
(`.tmp/cy005-nested-uv-red.log`, one failure). Normalizing the counter and duplicate PATH
entries in both the actual checking environment and its identity retained lookup order.
The receipt tests and strengthened lifecycle test then passed: **32 passed in 9.99s**
(`.tmp/cy005-nested-uv-green.log`). Scoped Ruff and strict mypy also passed.

The lifecycle test retains actual Git, installed pre-commit and semantic-release
operations, parent/version/path/changelog validation, failed-tag recovery and post-recovery
reuse. Only its check command and dependency inventory are bounded fixture substitutes.
Its assertions require exactly one fixture pytest run across the entire sequence.

A second parent inspection found tracked deletion staging changed the inventory from
a missing-file marker to no entry. The focused deletion regression reproduced an
unnecessary third check after staging (`.tmp/cy005-staged-delete-red.log`). Repository
content now omits absent files consistently while effective-index validation still
rejects a missing committed file. The parent stopped the second incomplete full run
before applying this correction; it did not produce reusable success.
The second interrupted run recorded **1 failed, 1,294 passed and 47 deselected** in
324.43 seconds. Its failure was an existing publication-order test attempting a DEIM
source download in an isolated empty cache. Baseline inspection confirmed that the
test and Hydra asset preparation path already had this missing isolation. A focused
probe replacing downloads with an immediate test failure reproduced the network call
(`.tmp/cy005-publication-red.log`). The ordering test now supplies prepared model inputs
at the asset boundary, consistent with its existing native-execution stubs. Dedicated
asset-resolution/execution tests remain separate and unchanged.
The ordering and asset-execution files then passed **25 tests in 6.16s**, with Ruff
and strict mypy passing (`.tmp/cy005-publication-green.log`).

A bounded follow-up found that retargeting a dangling symlink previously reused stale
success because only its missing target was fingerprinted. The regression failed
before correction. Fingerprints now preserve link identity and text even when the
target is absent, and the staged view accepts Git's legitimate dangling links. The
receipt suite passed **33 tests in 8.06s**, plus scoped Ruff and strict mypy. Valid and
dangling link changes both invalidate success; staging the verified link reuses it.

## Pre-review canonical gate

Command: `uv run --frozen --no-sync python scripts/verify.py --force`.
Pre-review log: `.tmp/cy005-final-verify-v3.log`. Exit **0**; final before/after input
fingerprints matched and `.git/verification/application.json` was written atomically.

| Check | Result | Command elapsed seconds |
| --- | --- | ---: |
| Ruff | Passed | 0.04 |
| Strict mypy | Passed, 347 source files | 59.68 |
| Vulture | Passed | 1.84 |
| import-linter | 46 contracts kept, zero broken | 0.26 |
| Complete ordinary pytest | 3,375 passed, 30 skipped, 47 deselected, 168 warnings | 1,256.11 |

Pytest's internal duration was 1,248.66 seconds. Overall canonical wall time, including
fingerprinting and subprocess overhead, was **1,347.48 seconds (22m 27s)**, measured
with `/usr/bin/time -p` (`.tmp/cy005-canonical-time.txt`). This is slower than the supplied
historical approximate baseline, which was not a controlled comparison. Reuse removes
repeated complete checks for the same inputs; it does not promise a faster first suite.

This was the completed full-suite run before independent review. The two earlier interrupted
attempts and their findings are recorded above. Ordinary selection includes native CPU
DDP; the 47 opt-in GPU/native acceptance cases were deselected. Twenty-nine FiftyOne
checks require the isolated integration opt-in, and one reflink case skipped because
the filesystem lacks that capability. Skips/deselections are not passing evidence.

The Git-private receipt records each exact command, elapsed time, exit zero, log name
and log SHA-256. Its run identifier is `bc4357aa702749398c450f28abe362cd`.

The default ordinary suite includes architecture negatives and native CPU/Gloo DDP.
Physical GPU/NCCL and live ClearML publication are outside this refactor's verification;
no such outcome is inferred from unit or CPU tests. Active queue caller checks are
recorded in [cancellation coverage](cancellation-coverage.md). Mutation is separate:
see the [baseline and dispositions](mutation.md).

## Pre-review documentation and reduction

Canonical `--docs` passed with all new feature Markdown supplied automatically.
It will be repeated after the final evidence edits. `git diff --check` passed.

The supplied historical approximately 12-minute suite is not a fresh before measurement.
Line totals use physical lines in distinct maintained `.py` files under `src`, `tests`
and `scripts`, including new untracked files and excluding deleted files/generated trees.
| Maintained Python | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Application source | 29,670 | 29,202 | -468 |
| Tests and helpers | 47,948 | 47,880 | -68 |
| Scripts | 1,231 | 1,757 | +526 |
| Total | 78,849 | 78,839 | **-10** |

The net reduction includes the new verification entrypoint, receipt tests and mutation
assertions. Reduction comes from unused implementation removal and shared graph,
cancellation and test-fixture setup. Check timings are recorded with the completed gate.

## Review follow-up

[Independent review](review.md) identified dependency-inventory gaps and one false
mutation equivalence. The actual no-force probe also invalidated on the host's per-tool
call ID. These findings were corrected and require a fresh complete gate. The probe
was stopped after Ruff and during mypy, before pytest; it removed stale evidence as
designed. Separate normalized-environment probes now match across tool calls.

The pre-review success above does not accept subsequent code edits.

## Final integrated gate and actual reuse

After the review corrections and the empty-side mutation regression, the same canonical
`--force` command completed with exit **0**. Its before/after input snapshots matched,
and success was written atomically. Run identifier:
`dfe4e64c650f4a8ea8e2a415e9cbc173`; log: `.tmp/cy005-final-verify-v5.log`.
The private receipt was copied to `.tmp/cy005-final-receipt.json` before testing reuse.

| Check | Result | Command elapsed seconds |
| --- | --- | ---: |
| Ruff | Passed | 0.04 |
| Strict mypy | Passed | 56.28 |
| Vulture | Passed | 1.99 |
| import-linter | 46 contracts kept, zero broken | 0.27 |
| Complete ordinary pytest | 3,381 passed, 30 skipped, 47 deselected, 168 warnings | 1,141.08 |

Pytest's internal duration was **1,134.87 seconds (18m 54s)**. Total canonical wall time
was **1,229.85 seconds (20m 30s)**, including input inventory/hash checks
(`.tmp/cy005-final-v5-time.txt`). The skip/deselection limitations above still apply.

A separate host tool call then ran the default command without `--force`. It exited
zero in **13.88 seconds**, reported `Reused successful application checks`, and invoked
none of the five check commands. Logs: `.tmp/cy005-final-reuse.log` and
`.tmp/cy005-final-reuse-time.txt`. This establishes actual reuse across host invocations;
the temporary Git lifecycle test covers contributor/version commits and tag recovery.
Actual release-hook results are recorded separately in delivery evidence.

| Final maintained Python | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Application source | 29,670 | 29,202 | -468 |
| Tests and helpers | 47,948 | 47,866 | -82 |
| Scripts | 1,231 | 1,780 | +549 |
| Total | 78,849 | 78,848 | **-1** |

The final total includes every new maintained Python file. Architecture test consolidation
retained all 64 lexical source/expectation pairs and actual configured-contract negative
cases. Cancellation helpers preserve the independent raw `/proc` observation and timeout
values. New receipt and mutation regressions account for the added tooling/test surface.
Six generic pre-commit checks also passed on the complete task file set before this run.
The temporary mutmut package-inspection download was removed; private logs and ignored
mutation output remain as evidence and an incremental cache.

## Corrected inventory acceptance run

The fifth run above preceded the nested-input exclusion finding described in
[review](review.md). After correction, the canonical `--force` command ran again and
exited **0**, with unchanged before/after input snapshots and an atomic success receipt.
Run identifier: `6d4d17eb4e744782ad88fd65cdcdca7d`; log:
`.tmp/cy005-final-verify-v6.log`. The receipt was copied to `.tmp/cy005-v6-receipt.json`.

| Check | Result | Command elapsed seconds |
| --- | --- | ---: |
| Ruff | Passed | 0.05 |
| Strict mypy | Passed, 347 source files | 44.33 |
| Vulture | Passed | 1.55 |
| import-linter | 46 contracts kept, zero broken | 0.24 |
| Complete ordinary pytest | 3,388 passed, 30 skipped, 47 deselected, 168 warnings | 1,063.08 |

Pytest's internal duration was **1,057.64 seconds (17m 37s)**. Total canonical wall time
was **1,138.34 seconds (18m 58s)** (`.tmp/cy005-final-v6-time.txt`). The skips and
deselections have the same stated limitations. A separate host invocation without
`--force` reused the receipt in **14.02 seconds**, executing none of the five checks
(`.tmp/cy005-v6-reuse.log`, `.tmp/cy005-v6-reuse-time.txt`).

Final corrected totals: application **29,202** lines (-468), tests **47,861** (-87),
scripts **1,784** (+553), total **78,847** versus baseline **78,849**, a net reduction
of **two maintained Python lines**. The additional regressions share the existing
input-case matrix. Runtime, architecture and selected mutation inputs are unchanged
from their accepted independent review. The canonical documentation check validated
**104 Markdown files with zero issues** before the final review record update.

## Interpreter crash and bounded reproduction attempts

The eighth canonical run used the unified governed-directory inventory and passed
Ruff, mypy, Vulture and all 46 import contracts. Pytest exited with signal **SIGILL**
(return code **-4**) after **817.91 seconds**, during
`test_standard_basic_auth_and_local_read_timeout`. The crashing thread was garbage
collecting while parsing an HTTP header; the main thread was in the expected local
HTTP read-timeout path. This is an interpreter/native crash, not an assertion failure.
Its cause is not established by the Python traceback. Log:
`.git/verification/application-22c16e117b784ab8b608baca40576bcd-4.log`.
The verifier failed closed and retained no success receipt. No root core dump appeared.

Without source, dependency or environment changes, the asset HTTP/loading files passed
**40 tests in 16.77 seconds** (`.tmp/cy005-asset-crash-reproduction.log`). Selecting the
asset cases after full test collection then passed **41 tests, 3,429 deselected in
28.38 seconds** (`.tmp/cy005-asset-crash-full-collection.log`). These attempts did not
reproduce SIGILL and do not establish its root cause or substitute for full acceptance.
The same complete canonical command is retried with the failed attempt preserved here;
no test retry, skip or behavior workaround has been introduced.

## Final complete retry of unchanged inputs

The ninth canonical `--force` invocation exited **0**. The full suite passed the
original HTTP timeout path and all remaining tests. Final input snapshots matched,
and the verifier wrote success atomically. This establishes a completed gate for
the current implementation; it does not identify the cause of the earlier SIGILL.
Run identifier: `5b23da30ad9440248b62f0fc37efbcd2`; main log:
`.tmp/cy005-final-verify-v9.log`; immutable receipt copy: `.tmp/cy005-v9-receipt.json`.

| Check | Result | Command elapsed seconds |
| --- | --- | ---: |
| Ruff | Passed | 0.04 |
| Strict mypy | Passed, 347 source files | 49.92 |
| Vulture | Passed | 1.60 |
| import-linter | 46 contracts kept, zero broken | 0.23 |
| Complete ordinary pytest | 3,393 passed, 30 skipped, 47 deselected, 168 warnings | 936.02 |

Pytest's internal duration was **931.32 seconds (15m 31s)**. Total canonical wall time
was **1,028.34 seconds (17m 08s)** (`.tmp/cy005-final-v9-time.txt`). Skips/deselections
retain the limitations above; this includes actual CPU/Gloo DDP, not physical GPU/NCCL
or live ClearML publication. The supplied historical approximately 12-minute baseline
is not a controlled first-suite performance comparison.

Final maintained Python: **29,202 source lines (-468)**, **47,854 test/helper lines
(-94)** and **1,791 script lines (+560)**; total **78,847**, a **net reduction of two**
from 78,849. These totals include every new maintained Python file. Consolidation
retains both partial/path-limited index rejection cases and strengthens retry checks
for both index views and interruption.

The subsequent default verification command, launched in a separate host tool call,
reused this receipt in **14.50 seconds** and executed no check commands. Logs:
`.tmp/cy005-v9-reuse.log` and `.tmp/cy005-v9-reuse-time.txt`. Documentation validation
and `git diff --check` also passed after the final evidence update.
