# Paired CY and queue compatibility — 2026-10-26

The original sections below retain the historical current-version check. The
[proposed-version check](#proposed-version-check) at the end records the later
CY 0.41.0/queue 0.1.2 snapshot verification and prepared requirement change. The
[frozen-runtime refresh](#frozen-runtime-refresh) records the latest complete pair check.

## Scope and source identity

This verification implements T010/T023 from the [task ledger](../tasks.md), following
the [paired source check](../../../docs/development.md#paired-cy-and-queue-release-check).
The parent had fetched both repositories before delegation. Inspection confirmed
that each checked-out base matched its current remote default-branch ref:

| Source | Base commit | Source and isolated installed version |
| --- | --- | --- |
| CY feature working tree | `9fd2294ab219c534fcce87b59eea7b56e9d01173` (`origin/master`) | `0.40.0` |
| cy-queue working tree | `9a6fccd86b8958a77809e4d2e7e2cc178d0a73ee` (`origin/main`) | `0.1.1` |

CY included the uncommitted feature implementation. Queue initially had a clean
working tree; the only task-owned queue change is
`tests/test_batch_estimate_submission.py`. The queue requirement remains
`clearml-yolo>=0.38,<0.41`. The latest inspected CY tag was `v0.40.0`; queue had no
version tags. No versions, dependencies, source revisions, runtime code, operational
environments, commits or remote refs were changed by this verification.

The existing approved editable dependency checkouts were retained:
`digital-metrics` at `6e801be1564dce458294eb23592cc1aa0939c4d9` (`0.7.0`) and
`report-generator` at `d10aa395d08f738e92e04e076cee93b3a993bf8f` (`0.1.2`).

## Installation and commands

An isolated Python 3.12.13 environment was created under
`.tmp/queue-pair.DsKl3O/venv`, using uv 0.11.32. A frozen export supplied the existing
lockfile's dependency versions and approved editable external sources. Both current
source trees were installed together with normal dependency resolution:

```bash
uv export --frozen --no-hashes --no-emit-project --format requirements-txt \
  --output-file .tmp/queue-pair.DsKl3O/requirements.txt
uv venv --python .venv/bin/python .tmp/queue-pair.DsKl3O/venv
uv pip install --python .tmp/queue-pair.DsKl3O/venv/bin/python \
  -r .tmp/queue-pair.DsKl3O/requirements.txt -e . -e ../cy-queue
uv pip check --python .tmp/queue-pair.DsKl3O/venv/bin/python
```

No `--no-deps`, dependency overrides or source metadata edits were used. Resolution
and installation succeeded for 282 packages; `uv pip check` reported all installed
packages compatible. Editable package metadata and imports pointed to the inspected
source trees with matching versions. Source metadata compatibility and imports from
outside either checkout are also exercised by the queue installation regressions.

The following checks use the isolated environment's executables, running from the
queue checkout so its own configuration applies:

| Check | Command | Result |
| --- | --- | --- |
| Focused null-batch coverage | `python -m pytest -q tests/test_batch_estimate_submission.py --tb=short` | 11 passed |
| Queue lint | `ruff check .` | Passed |
| Queue formatting | `ruff format --check .` | 80 files already formatted |
| Queue strict typing | `mypy .` | 68 source files passed |
| Queue import contracts | `lint-imports` | 2 kept, 0 broken |
| Queue ordinary integration suite | `python -m pytest -q` | 512 passed, 7 deselected, 4 warnings in 143.67 s |
| Installed queue CLI | `cy-queue --help` | Passed, including invocation outside checkout |

Command output is retained in the ignored task-owned directory
`.tmp/queue-pair.DsKl3O/` (`install.log`, `pytest.log`, `help.log`). The isolated
environment does not replace or modify the running/deployed environment.
The seven opt-in physical GPU cases were deliberately deselected. The four warnings
were the existing hydra-zen/Pydantic `__fields__` deprecation; no Hydra automatic
schema-matching warning occurred. Task-owned test processes finished, and the
isolated virtual environment was removed after checks; logs and exported requirements
remain as local evidence.

## Null-batch and allocation evidence

The new queue regression exercises both `pipeline` and `train`, across YOLO,
DEIMv2, RF-DETR, Faster R-CNN and FCOS. It composes actual Hydra submissions,
serializes and reloads immutable snapshots, enters the real snapshot runner and
checks the execution YAML and CY entrypoint selected at the final `execv` boundary.
GPU discovery and batch lookup fail the test if called during submission or worker
configuration. The requested null survives; training devices become allocation-relative
`[0, 1]`, prediction uses `[0]`, and physical GPU visibility keeps its assigned order.

A second regression writes independently validated fixture estimate records for
one and two GPUs through the real atomic cache adapter. After the real queue
execution configuration binds two GPUs, CY's native resolver selects the two-GPU
global batch of 8, rather than the one-GPU fixture batch of 32. The requested model
and immutable snapshot retain null; provenance records global batch 8 and per-GPU
batch 4. GPU inventory and the profile-construction boundary are controlled fixtures;
cache storage, dataset workload checks and compatibility selection execute normally.
These tests establish queue/configuration/cache integration, not physical GPU capacity.

## Architecture and acceptance limits

The [feature architecture record](../architecture.json) owns the paired check.
This work adds test coverage only; it changes no queue or CY runtime imports,
interfaces, process ownership, storage protocol or effect placement. Existing
queue import contracts and the full suite's architectural negative cases provide
the corresponding executable boundary checks. No new runtime module is introduced.

The feature's parent owns canonical CY verification, documentation reconciliation,
fresh independent review, actual multi-GPU execution and final architecture
acceptance. No physical GPU or ClearML execution was performed here. A successful
pair check at CY `0.40.0`/queue `0.1.1` does not establish compatibility for a future
version outside the queue's bounded requirement. Release remains blocked by the
feature's missing real multi-GPU acceptance evidence; no commit or push was attempted.

## Proposed-version check

The feature's concrete release proposal is CY **0.41.0**. Queue's package-fix policy
requires its next patch version, **0.1.2**. Before modifying the real queue bound,
normal resolver dry-run against the proposed source snapshots reproduced the old
`clearml-yolo>=0.38,<0.41` incompatibility (exit 1). After the successful checks below,
the real queue requirement was prepared as `clearml-yolo>=0.38,<0.42`.

Real source versions remain CY **0.40.0** and queue **0.1.1**. Only isolated snapshots
received proposed versions; no operational installation or release action occurred.
Queue has no lockfile. CY's snapshot project and lock root versions were updated
together; all other lock entries, declared dependencies and approved external source
revisions were preserved. The complete local `[tool.uv.sources]` section remained intact.

Snapshot capture included tracked and untracked nonignored source, preserving the
actual feature working tree, packaged YAML and the queue null-batch tests. Hashes
before and after copy rejected racing source changes. The captured base commits
remain those in the historical table; manifest identities were:

| Snapshot | Files | Original source-manifest SHA-256 |
| --- | --- | --- |
| CY | 685 | `a4169d36a838ed62fd1946a99db46e612e2504575b7ee3bf6246fe7037ba2dff` |
| Queue | 89 | `7558f5db7f7044fdd8155dc8a07fd4fab7e8da8ded9b3304f832e1048a651dd7` |

Per-file and parsed-TOML audits allowed exactly CY project/root-lock version changes,
queue project version and the approved queue upper bound. External dependency
snapshot bytes were unchanged. This used complete source snapshots, not stale HEAD
checkouts or the operational editable installation.
The final execution-source comparison found no CY drift and only the approved
real upper-bound change in queue; source, tests and check configurations still
matched the tested snapshot contents.

All commands ran with `CUDA_VISIBLE_DEVICES=''`. In the task-owned directory
`.tmp/queue-proposed.sTabGJ/`, Python 3.12.13 and uv 0.11.32 exported the frozen
dependency requirements, created an isolated environment and installed both editable
source snapshots together with normal resolution and no `--no-deps`.

| Proposed-pair gate | Result |
| --- | --- |
| Normal dependency resolution and installation | Passed: 282 packages |
| `uv pip check` | Passed |
| Source/installed metadata | CY 0.41.0 / queue 0.1.2 exactly, importing isolated snapshots |
| Installed queue requirement | Admits 0.41.0; rejects untested 0.42.0 |
| Complete queue suite, including null-batch and metadata tests | 512 passed, 7 physical GPU cases deselected, 4 warnings in 125.81 s |
| Ruff / formatting | Passed; 81 files already formatted |
| Strict mypy | Passed; 68 source files |
| Import contracts | 2 kept, 0 broken |
| Installed CLI outside checkout | Passed |
| Queue task documentation | 2 Markdown files, 0 issues |

The four warnings were the existing hydra-zen/Pydantic deprecation. The ordinary
suite covered the eleven null-batch cases, package/source metadata, ownership,
handoff and architecture negative cases. Physical GPU or ClearML acceptance was
not performed by this check.

Queue's task-native plan, architecture record and detailed evidence live under
`docs/bugs/cy-041-compatibility/` in its source tree. Its task-owned diff is the
single upper-bound change, that documentation, and the earlier new null-batch test.
The parent owns fresh independent review, final architecture acceptance and eventual
real-version changes. If versions or integration-relevant source change again,
refresh this check before release. The proposed-version requirement check is now
complete; physical feature acceptance and release remain separate gates.

Task-owned test processes completed. Disposable snapshots and the isolated virtual
environment were removed after verification; manifests, normalization and metadata
reports, exported requirements and command logs remain in the ignored evidence
directory. Neither package was committed, tagged, pushed or operationally installed.

## Frozen-runtime refresh

After CY corrected the lazy worker-ownership observer and GPU telemetry versus
birth-validated scan ordering, the proposed CY **0.41.0** / queue **0.1.2** check was
repeated against new current-source snapshots. Both remotes were fetched first:
SSH timed out, then per-command HTTPS overrides succeeded without changing remote
configuration. Local/default-branch commits remained CY
`9fd2294ab219c534fcce87b59eea7b56e9d01173` and queue
`9a6fccd86b8958a77809e4d2e7e2cc178d0a73ee`; latest CY tag was `v0.40.0` and queue
had no tags. The settled final CY physical harness files were included.

| Snapshot | Files | Original source-manifest SHA-256 |
| --- | --- | --- |
| CY | 690 | `5377905e27a3a244f65ecc8ad8f2c43d883f1e15b9a1fc73422817f5bccc1c4f` |
| Queue | 90 | `74133b0a30f6034139517b78ccd59feb4e60c699469666e66ee55119a239e398` |

Only snapshot project versions and CY's lock root version were normalized. The
prepared real queue bound `<0.42`, full local source overrides and approved external
dependency bytes/revisions were preserved. Post-check comparison found **zero drift**
in CY, queue and both external sources, including tests and check configuration;
no harness-only exception was needed. Real source versions remain 0.40.0 / 0.1.1.

All commands ran with `CUDA_VISIBLE_DEVICES=''`, Python 3.12.13 and uv 0.11.32.
Frozen requirements export, isolated environment creation, normal joint source
installation and `uv pip check` passed for 282 packages. Metadata/import assertions
confirmed exact proposed versions from the isolated snapshots; the installed queue
bound admits 0.41.0 and rejects 0.42.0.

| Refreshed queue check | Result |
| --- | --- |
| Full suite, including eleven null-batch cases | 512 passed, 7 physical GPU tests deselected, 4 warnings in 122.05 s |
| Ruff / formatting | Passed; 82 files already formatted |
| Strict mypy | Passed; 68 source files |
| Import contracts | 2 kept, 0 broken |
| CLI outside both checkouts | Passed |

All commands exited 0. The four warnings remain existing hydra-zen/Pydantic
deprecations. Physical GPU and external services were not exercised. Detailed
commands and results are recorded in queue's
`docs/bugs/cy-041-compatibility/verification.md`; manifests, normalized differences,
remote identities, metadata, final source audit and logs remain under ignored
`.tmp/queue-proposed-refresh.q6ai4kn5/`. Disposable snapshots/environment were removed
and all owned test processes completed. This refresh changed evidence/ledger only;
parent-owned independent review, architecture acceptance and hardware/release gates
remain separate.

The parent subsequently reconciled fresh independent reviewer `review_pair`'s
accepted verdict. Its own eleven focused tests, task-document checks and inspection
of refreshed logs found no blocking issue. Queue's architecture acceptance validator
then exited 0, and both task Markdown files passed with no issues. This closes
compatibility preparation; CY's physical gate and real-version release remain open.

After that capture, independent CY review corrected only
`tests/native_backend_ddp_harness.py` and
`tests/test_native_backend_ddp_harness.py`: RF-DETR's physical fixture now meets
its native minimum unique population, and offline tests cover that constraint.
No installed application code, package data, metadata, dependency, public integration
interface, queue source or queue test changed. The paired result remains applicable
to those unchanged execution inputs; the capture itself retains the earlier test
bytes. Final CY canonical verification covers the corrected harness separately.
