# Feature 007 verification — 2026-10-29

## Implementation and scope

Source base: `0037059dcf8a8ed16582f256b98036480cabd842` (CY 0.41.0).
The intended feature release is CY 0.42.0. Existing local uv source overrides
were preserved privately and removed for final checks and commit hooks; they
must be restored unstaged after those hooks finish. Approved external dependency
sources and installed dependency versions remain unchanged. Hugging Face Hub,
already locked at 2.2.0, is now declared directly because the adapter imports it.
The native Hub API imports and endpoint-argument contracts also passed with
Hugging Face Hub 2.2.0 in an isolated Python 3.13.14 environment. This supplements
the full Python 3.12.13 checks; it is not a second full application-suite run.

The task owns the native asset core records; asset resolver, storage, validation,
Hub and catalogue adapters; YOLO/RF-DETR/Torchvision native discovery; manual
command and pipeline invocation; exact import contracts and regression tests;
user/contract documentation; and this feature's Spec Kit artifacts. Existing
mocked pipeline tests explicitly isolate preparation, preserving the ordinary
suite's offline boundary. No custom model/configuration arguments are rewritten.

The companion queue change extends its tested CY bound through 0.42 and adds
six immutable-worker configuration tests. The authoritative portable usage skill
is updated in an isolated copy of its collection; unrelated changes in the
original collection checkout remain untouched. Those repositories have their
own task evidence and commits. No deployment, registry publication or release
archive is part of delivery.

## Focused regression evidence

- Native destination and legacy promotion tests were observed failing before
  implementation, then passed with the narrow asset storage boundary. Project
  output containment and escaping native leaf symlink rejection remain enforced.
- Catalogue tests cover filtering/deduplication, changed identity/location/model,
  partial failure, explicit retry, concurrent starts, interrupted retry, malformed
  receipts and failure isolation. Fresh command help rejects network/ClearML
  effects. Pipeline invocation preserves custom YAML, explicit paths, pretrained
  booleans/filenames and resume values.
- Hub tests cover actual source selection, safe/binary representation provenance,
  actual commits, native metadata, legacy promotion, corrupt blobs/configuration,
  mirror precedence, scoped authentication, lock failure and diagnostic redaction.
- Parent inspection reproduced a two-pass configuration failure: downloaded HF
  weights could previously hide a failed configuration download on retry. The
  fix requires configuration completion for native and promoted caches. The
  regression observes two failed attempts, successful config-only repair at the
  actual commit, and unchanged weight inode/mtime. All 20 focused Hub tests pass.
- Replay/publication fixture adaptation passed 57 focused cases. Existing asset,
  model and DEIM regression checks passed 41 cases before the final Hub repair;
  the canonical run below supersedes these partial checks for acceptance.

## Native and paired evidence

[Native verification](native-verification.md) records real downloads, recovery
provenance and fresh processes with network connections denied. All 44 YOLO
filenames and every included backend have native-loading evidence. Custom YAML
training, boolean/filename pretrained behavior, explicit paths, changed cwd,
relative caches, spawned workers and auxiliary AMP checkpoint lookup passed.
The completed manual pass prepared 56 assets with zero failures, then automatic
preparation reused its completed fingerprint. Initial upstream timeouts and exact
hash-validated cache/mirror recovery are retained as separate observations.

The isolated paired source check uses normal dependency resolution and proposed
CY 0.42.0 / cy-queue 0.1.3 metadata, including source/installed origin equality,
queue static/import checks, its complete ordinary suite and command help outside
both checkouts. The queue's dated compatibility report records captures and
results. Final committed metadata must be checked again before pushing.

The final stable proposed pair passed normal installation and `uv pip check`
(282 packages), exact metadata/import-origin checks, queue Ruff/format/mypy,
both queue import contracts, all 518 ordinary queue tests (7 physical GPU tests
deselected), and outside-checkout CLI help. Source capture audits found only
dated/documentation drift; implementation, tests, package/check configuration and
both approved external sources were unchanged during that final run.

Fresh independent portable-skill evaluation passed four scenarios: custom YAML
preparation, partial automatic failure/manual retry, read-only inspection/queue
planning, and missing HF configuration. It retained installed-version guards,
performed no downloads/submission, and distinguished preparation receipts from
offline loader evidence. This was native Codex evaluation, not live OpenCode
target-model execution. Installed `cy-download-weights --help` passed from outside
the checkout in the isolated paired environment.

## Mutation applicability

Inspected `[tool.mutmut]`: selected code is `core/datasets.py`,
`core/evaluation/policy.py` and `core/export_quality.py`; selected tests are
dataset records, input correctness, comparison scoring, export quality and
policy mutation. None of those code/test files or their fixtures changed.
No installed dependency identity changed: the added direct Hub requirement uses
the already locked version. Consequently this task has no affected selected
mutation target. No mutation run is claimed; new asset failures have direct
fault-injection and concurrency regression coverage.

## Acceptance status

The integrated canonical command executed Ruff, strict mypy, Vulture, all 51
import contracts and the full ordinary pytest suite successfully: 4,035 passed,
30 skipped, 81 deselected and 167 warnings, including native CPU-DDP checks.
The suite took 912.61 seconds. Its acceptance receipt was correctly withheld
because the installed editable queue dependency's dated verification file was
updated during execution. An input-mtime audit found that single changed input;
runtime code, tests and dependency metadata were stable. Private logs use
application run ID `437d2d5c0e9148a4a8d0291eafea95cd`.

## Isolated final acceptance

Concurrent feature 008 subsequently began changing the shared repository's
runtime files. The parent captured exactly the task-owned feature 007 changes
into an isolated clone of the same source base; the private manifest proves byte
identity at capture. No feature 008 files or later shared-checkout edits are part
of this release. The shared checkout and its local source configuration remain
preserved. A new isolated environment was installed using normal resolution,
the approved external source copies, frozen requirements and an immutable queue
source copy. `uv pip check` passed for all 282 packages.

[Review](review.md) records the reproduced HF logging and terminal-progress
findings, corrections and independent closure. Final focused checks passed 305
Hub/architecture cases and 45 preparation cases. The final reviewer independently
passed all 77 Hub/preparation cases and approved the scoped correction; earlier
fresh full-scope reviewers found no other functional or architecture blocker.

After the final diagnostic correction, the actual manual command was rerun with
network blocked using the isolated installation: **56 assets, zero failures,
exit zero**, followed by `skipped=True` for automatic preparation with unchanged
settings. Its private log is `.tmp/native-accepted.log` in the isolated checkout.
Native transfer callbacks were checked through actual HF HTTP APIs with in-memory
transports and native Xet progress-reporter construction/update/close; no new live
Xet transfer is claimed.

[Live acceptance](live-verification.md) records the completed CPU/single-GPU
custom-Hydra pipeline pair, native AMP, disjoint-content input checks, frozen
thresholds/current-test comparison, forced publication/model downloads and owned
stand cleanup. These functional results make no accuracy or numerical-parity
claim. Diagnostic-only corrections followed that live pair; the final offline
command and focused real SDK regressions cover their affected paths.

The final approved-code proposed CY 0.42.0 / queue 0.1.3 pair passed normal
resolution, all 282 dependency consistency checks, exact source/installed
metadata, queue Ruff/format/mypy/import contracts, 518 ordinary queue cases and
outside-checkout help. Seven physical GPU cases were deselected. Capture audit
found only CY evidence prose changes; runtime/test/package/check inputs and the
approved external sources were stable. Queue review and architecture acceptance
passed, and its task-scoped local commit is
`4205b9b` (`fix: support CY 0.42 native weight preparation`). Delivery waits for
the final committed CY/queue metadata check.

## Final canonical acceptance

The final isolated `uv run --frozen --no-sync python scripts/verify.py` exited
zero and recorded its accepted receipt. Ruff, strict mypy, Vulture and all 51
import contracts passed. The complete ordinary suite passed **4,049 tests**,
with 30 skips, 81 deselections and 167 warnings in 929.83 seconds, including
native CPU distributed-training scenarios. The skipped/deselected optional
targets are not counted as passing tests. The source/dependency input snapshot
was unchanged across the complete run.

Private application run ID is `6137ac971b25470094f976dc9206c8c8`; the accepted
receipt is `.git/verification/application.json` in the isolated checkout.
Documentation validation passed with zero Markdown/local-link issues, and the
reconciled architecture acceptance validator exited zero. Release metadata and
actual committed paired versions remain to be reconciled before pushing.
