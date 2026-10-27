# Integrated verification — 2026-10-26

Source: uncommitted feature 006 relative to
`9fd2294ab219c534fcce87b59eea7b56e9d01173`, version `0.40.0`.
The existing local `tool.uv.sources` section and approved dependency revisions
remain unchanged. No commit, version, tag, push or installation is claimed.

## Focused integration

Parent checks covered search/cache/CLI, null lookup and replay, queue allocation,
worker lifecycle, native profile construction, DEIM/RF-DETR probes, shared
Torchvision/FCOS and warning-free/self-contained Hydra composition. Later focused
runs supersede earlier counts only for their own scopes; counts are not summed.

- Search, cache, CLI and lookup integration: 117 tests passed.
- DEIM, FCOS, Faster R-CNN, shared Torchvision and batch resolution: 102 passed.
- Runtime worker ownership and GPU telemetry: 14 passed.
- RF-DETR probe/AMP update accounting and final event draining: 39 passed.
- Updated YOLO native validation/AMP and profiles: 73 passed; the combined
  probe/profile/worker/telemetry/event scope subsequently passed 88 tests.
- Ruff and strict typing passed for the integrated source before the final
  canonical run; canonical checks remain the acceptance authority.

See [review](review.md), [paired queue evidence](queue-compatibility.md),
[live FCOS publication](fcos-live.md), [documentation](documentation.md) and
[mutation applicability](mutation.md) for their commands and limits.

## Canonical attempts

Command: `uv run --frozen --no-sync python scripts/verify.py`.
The verifier retains per-command logs and input fingerprints under
`.git/verification/`. It rejects a success receipt when governed inputs change
during verification.

1. Run `98bd2d61778449e8938b38cdcc0a8c40` passed Ruff, strict typing,
   Vulture and import contracts. Pytest terminated with signal 4 after 779.12 s,
   at approximately 72%, with no preceding assertion failure. Its main thread
   was in `test_standard_basic_auth_and_local_read_timeout`; a request-handling
   thread was collecting garbage while parsing HTTP headers in `email/feedparser`.
   Core dumps were disabled for this process. This is an unexplained native
   interpreter crash, not a passing suite or a diagnosed application defect.
2. The bounded original failure module, `tests/test_model_assets.py`, passed
   11 tests in 4.74 s in a fresh process. Similar unresolved crashes were already
   recorded in [feature 003](../../003-portable-training/evidence/2026-10-23-interpreter-crash.md)
   and [feature 005](../../005-reduce-verification/evidence/verification.md).
   A clean module run does not establish a fix for the full-suite crash.
3. Run `cca4b631f07e428ebf8c73dc6efe13fa` passed Ruff and strict typing
   for 398 files, then Vulture rejected an unused `augment` argument in the new
   validation test double. The test now asserts the expected native false value;
   no production behavior changed. Pytest did not run in this attempt.
4. Run `26ece632599c492ba04779a681729e70` started with
   `CUDA_VISIBLE_DEVICES=''` and a process-local 4 GiB core-dump limit. Ruff,
   strict typing, Vulture and all 50 import contracts passed. Full pytest finished
   with 3,812 passed, 7 failed, 30 skipped and 47 deselected in 1085.06 s.
   CUDA hiding prevents the ordinary CPU suite
   from creating a competing context during serialized GPU acceptance; it is not
   a workaround claimed to fix the interpreter crash.

The seven failures were inspected individually. Export's expected inventory lacked
the newly required local `export.yaml`; the optional Severstal harness omitted
the six FCOS presets and dispatched them through Faster R-CNN. Its inventory,
backbone handling and reload routing were corrected, with 146 focused CPU tests
passing and 63 physical scenarios collected without execution. Three Torchvision
probe failures came from a process that had imported the old receipt schema before
the concurrent memory-accounting edit; fresh-process probe checks passed afterward.

The trace failure reproduced a real compatibility bug: absent `batch` was treated
as explicit null. The guard now requires the key to be present; explicit CPU/MPS
null requests fail before GPU discovery. The parent passed 28 resolution/trace
tests. The cleanup failure reproduced with a pre-existing helper: a killed detached
child became an adopted zombie whose identity was not shared with the outer scope.
The supervisor now reaps only its recorded, birth-matching adopted children after
consuming direct worker statuses. A deterministic regression preserves the earlier
helper; 56 worker/tree/lifecycle/capability tests and scoped Ruff/mypy passed.

The separate memory review reproduced a false usable capacity at allocator peak
850, idle baseline 100 and budget 900. Separate synchronized non-allocator samples
now produce the conservative whole-device envelope 950. RF-DETR captures it before
native teardown. Parent verification passed 65 memory/probe/RF/telemetry tests;
the implementer also passed 272 architecture checks and all 50 import contracts.
Old measurements are invalidated by the changed implementation fingerprint.

Run `e41e5cfc4eb24862a9278a93107e01f9` subsequently passed Ruff, strict
typing, Vulture, all 50 import contracts and the complete collected suite:
**3,886 passed, 30 skipped, 65 deselected**, 157 warnings, 951.89 s. The verifier
then correctly rejected the receipt because governed files changed during the
new physical-harness work. This is successful execution of that collected suite,
not a final canonical acceptance receipt. The suite must run again after integration.

The final four-family DDP harness passed 40 focused offline tests in the parent
process. An initial explicit selection also included the physical test file without
its required flags; all 18 physical cases correctly failed at the opt-in fixture
before GPU or service execution. The corrected offline-only command passed. This
selection error is not physical acceptance evidence.

Run `8b4b456fbcca4a6d9d0ed95000dc6fcc` passed Ruff, strict typing,
Vulture and import contracts. The parent intentionally interrupted its pytest
process through the verifier's cleanup path after fresh review identified an
incorrect RF-DETR fixture population in the new physical harness. That run has no
success receipt. The harness correction and focused checks precede the next full run.

Run `54697fe0a60e4151abb390ac1b3011e5` then passed Ruff, strict typing
(404 source files), Vulture, all 50 import contracts and the full ordinary suite:
**3,940 passed, 30 skipped, 81 deselected**, 163 warnings, 901.36 s. Its final
receipt was rejected because the parent updated the sibling queue's evidence
document during the run. The verifier inventories every file in editable dependency
trees, including documentation. Inspection of every governed input's modification
and change timestamps found exactly one changed path:
`cy-queue/docs/bugs/cy-041-compatibility/verification.md`. Application code and tests
remained unchanged. This is a passing suite but a failed canonical receipt; both
trees are frozen for the next run. The private drift inventory is retained.

## Remaining acceptance

The physical multi-GPU gate is unavailable on the currently selected single-GPU
host. Existing host-side video activity also prevents the final idle estimator
matrix and a search reaching an actual capacity boundary. No unrelated workload
was stopped. The latest proposed CY 0.41.0/queue 0.1.2 snapshots passed normal
resolution, exact source/installed metadata and 512 queue tests; actual versions
remain unchanged. Fresh independent code reviews are accepted after their fixes.
Final canonical verification passed with unchanged governed inputs; architecture
acceptance must continue to reject the missing physical gate. No commit or release
proceeds while it remains open.

## Final scope reconciliation

The parent inventoried all 204 changed/added CY paths, including untracked source,
packaged YAML, tests and feature evidence. Every path falls within the architecture
record; there are no deletions or out-of-scope files. The pre-existing entire local
`[tool.uv.sources]` section is excluded from task ownership and remains intact.
`uv.lock` and both approved external dependency checkouts are unchanged. Sibling
queue metadata/tests/documentation and canonical portable usage-source edits have
separate evidence; pre-existing usage-skill changes were preserved. No operational
environment, version, commit, tag or remote branch was changed.

## Final canonical result

Run `98ac228d6f9d468dbd654f85ea5b4756` used
`CUDA_VISIBLE_DEVICES='' uv run --frozen --no-sync python scripts/verify.py` with
both CY and editable dependency trees frozen. It exited **0** and wrote a valid
`.git/verification/application.json` receipt after the second fingerprint matched.
Ruff, strict mypy (404 files), Vulture and all 50 import contracts passed. The full
ordinary suite completed with **3,940 passed, 30 skipped, 81 deselected**,
163 warnings, in 975.91 s. Physical opt-in cases were not run. The successful
receipt establishes this source/environment check; it does not establish GPU
capacity or multi-GPU behavior. The earlier native interpreter crash did not recur
in this run; no causal fix for that historical crash is claimed.

A fresh idle preflight during this final run again exited 2 because the selected
GPU was busy. No native workers were launched by that preflight and no unrelated
workload was changed. The only unfinished acceptance work is the current full
estimator matrix, a search reaching an actual capacity boundary, and real
multi-GPU/native publication and recovery execution. The hardware-dependent
architecture acceptance gate and release remain open accordingly.

The final architecture acceptance validator exited **1** with
`checks[1].result.status: acceptance requires passed`. That entry is the native
physical gate. Canonical, paired and documentation results are passing and fresh
code review is accepted; the validator correctly refuses overall acceptance while
the native result remains unavailable. Plan validation and final whitespace checks
passed. No gate was waived or rewritten as successful.
