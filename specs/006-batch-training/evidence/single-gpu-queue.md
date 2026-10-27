# Single-GPU amendment: paired queue verification

Date: 2026-10-27. Scope: T031 in the [feature ledger](../tasks.md), following
the [paired source gate](../../../docs/development.md#paired-cy-and-queue-release-check).
This is fresh evidence for the single-GPU lookup and extrapolation implementation;
the earlier [pair results](queue-compatibility.md) remain historical.

## Sources and isolation

Both repositories were fetched successfully over their existing SSH remotes before
capture. Local bases still matched their remote default branches:

| Repository | Local and remote default-branch SHA | Current version | Proposed version |
| --- | --- | --- | --- |
| CY | `9fd2294ab219c534fcce87b59eea7b56e9d01173` | 0.40.0 | 0.41.0 |
| cy-queue | `9a6fccd86b8958a77809e4d2e7e2cc178d0a73ee` | 0.1.1 | 0.1.2 |

The latest CY tag was `v0.40.0`; queue had no tags. Capture followed the parent's
application-source freeze and included tracked and nonignored untracked files,
packaged YAML and existing feature changes. Before/after manifests rejected racing
edits during copying. Snapshot manifest identities were:

| Source | Files | SHA-256 of original file manifest |
| --- | --- | --- |
| CY | 690 | `96c169540f9a67a452e907b55a4a4a6ab57cf775986748beefa28a42715b298c` |
| Queue | 90 | `9ce5abcf4fa630333de67581a2aef832c8026f979b2b0b49a2e0626d193e2357` |

The approved external sources were copied unchanged: `digital-metrics` at
`6e801be1564dce458294eb23592cc1aa0939c4d9` and `report-generator` at
`d10aa395d08f738e92e04e076cee93b3a993bf8f`. The complete local uv source section
and all dependency versions/revisions were preserved. The queue's already prepared
`clearml-yolo>=0.38,<0.42` requirement was retained.

An isolated Python 3.12.13 environment first installed and checked the current
versions, then reinstalled and checked the proposed versions. Only disposable
snapshot metadata changed: CY project and root lock versions, and queue project
version. Parsed TOML comparisons proved no other metadata or lock change.
Real versions, operational installations and working-tree dependencies did not change.

## Executed checks

All commands used `CUDA_VISIBLE_DEVICES=''` and uv 0.11.32. From the CY snapshot:

```bash
uv export --frozen --no-hashes --no-emit-project --format requirements-txt \
  --output-file ../../requirements.txt
uv venv --python /path/to/prepared/python ../../venv
uv pip install --python ../../venv/bin/python -r ../../requirements.txt \
  -e . -e ../cy-queue
uv pip check --python ../../venv/bin/python
```

Normal joint dependency resolution succeeded for both pairs, without `--no-deps`
or dependency overrides. Each `pip check` reported all 282 packages compatible.
Explicit assertions confirmed exact source/installed version agreement and imports
from the isolated snapshots. The installed queue bound admits 0.41.0 and rejects
0.42.0. Queue checks ran from its snapshot with the isolated executables:

| Check | Current 0.40.0 / 0.1.1 | Proposed 0.41.0 / 0.1.2 |
| --- | --- | --- |
| `ruff check .` | Passed | Passed |
| `ruff format --check .` | 82 files formatted | 82 files formatted |
| `mypy .` | 68 files passed | 68 files passed |
| `lint-imports` | 2 kept, 0 broken | 2 kept, 0 broken |
| `python -m pytest -q` | 512 passed in 126.27 s | 512 passed in 121.02 s |
| `cy-queue --help` outside both checkouts | Passed | Passed |

Both suites deselected seven opt-in physical GPU cases and emitted four existing
hydra-zen/Pydantic deprecation warnings. The complete ordinary suite includes the
eleven null-batch submission/allocation cases, source/installed metadata, immutable
queue snapshots, handoff, process ownership and negative architecture checks.
Exact-allocation legacy measurements continue to take precedence in the existing
queue regression. CY's amendment tests separately cover extrapolated lookup against
worker-assigned allocations. No physical GPU or ClearML outcome is claimed here.

## Reconciliation and cleanup

The final audit found no change in application source, package metadata, dependency
inputs, queue source/tests or either external source after capture. The sole changed
execution-related file was CY's `tests/test_batch_estimate_cli.py`, which the queue
suite does not execute; its later coverage belongs to the parent's canonical run.
This does not expand the scope of these paired results to that changed CY test.

Commands and exit codes, raw logs, original manifests, source-drift audit, normalized
metadata and installed metadata are retained in the ignored task-owned directory
`.tmp/queue-single-gpu-7msk3f5a/`. All owned test processes completed; disposable
snapshots and the isolated environment were removed after preserving evidence.
No runtime/source/requirement changes, commits, tags, pushes or deployment were made
by this verification. Parent canonical checks, physical acceptance, fresh review
and release gates remain separate.
