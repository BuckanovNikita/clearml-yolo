# Scoped campaign verification — 2026-11-05

- Slug: `campaign-scoped-improvements`.
- Assessment: [assessment.md](assessment.md).
- Fix: [fix.md](fix.md).
- Result: partial; focused source behavior verified, integrated acceptance pending.

## Baseline reproduction

After validating the architecture plan and copying the existing diagnostic
regressions, before runtime edits:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MPLBACKEND=Agg \
  uv run --frozen --no-sync python -m pytest -q tests/test_campaign_numerics.py
```

Exit 1: four tests failed because scalar errors lacked `title`/series/iteration
context and the training-loss error lacked `batch=0` and image/component context.
The observed training assertion was:

```text
assert 'batch=0' in 'Torchvision training produced a nonfinite loss'
4 failed in 2.21s
```

These failures reproduce missing diagnostics, not the original campaign's
native numerical cause. The existing finite guards already raised errors.

## Post-fix focused checks

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MPLBACKEND=Agg \
  uv run --frozen --no-sync python -m pytest -q \
  tests/test_campaign_numerics.py tests/test_result_export.py \
  tests/test_native_backend_ddp_harness.py::test_cpu_observer_tracks_real_updates_hashes_and_original_samples \
  tests/test_architecture.py
```

Exit 0: **251 passed**, 19 upstream Hydra/Pydantic deprecation warnings.
The four diagnostic tests now pass. Nonfinite scalars leave the journal empty;
nonfinite Torch loss raises before gradients or parameter updates. Export tests
retain extension metadata, exact source occurrences, geometry exclusions,
threshold flags and sparse background numeric/CSV boxing. The CPU observer
uses real optimizer/EMA/hash/serialization operations while accelerator
discovery is explicitly absent. Architecture tests exercise the actual graph,
existing forbidden-edge negatives, pure effect rules and inert import checks.

The shared architecture planning validator exited 0 before runtime edits.
`git apply --check` and application passed; exact preserved file bytes were
confirmed. Scoped Ruff passed after integration. No source/dependency revisions
or selected mutation source/test inputs changed; the three configured mutation
subjects and their selected tests are outside this scoped diff.

## Pending final gates and limits

- Parent-owned retained 50,000-row exact parity and scoped timing measurement.
- Final integrated canonical verification, including CPU-DDP, after force integration.
- Documentation/link validation and companion portable usage reconciliation.
- Latest/prospective CY and queue normal resolution, matching installed/source
  metadata, integration/static/import/help verification.
- Fresh independent final integrated review and architecture acceptance.
- Authorized final Git-only delivery after required native gates.

The earlier DINO-only canonical result is not accepted as verification of this
new runtime diff. No GPU, native campaign replay, ClearML publication, original
AMP numerical recovery, SIGILL correction or physical multi-GPU behavior was
run or established by this bounded task. Historical performance figures remain
historical; no fresh speedup or end-to-end improvement is claimed here.

## Scoped documentation check

`python scripts/check_docs.py --all` with the three new scoped bug reports
explicitly included exited 0: 244 Markdown documents, zero issues. This is
local documentation evidence; the parent still runs the documented final
`verify.py --docs` stage after all integrated documentation changes.

## Parent-run retained-row parity and profile

The parent ran a task-owned adaptation of the retained 50,000-row driver using
trusted, hash-verified fixture inputs. The original reference function was
byte-identical to master `66279a6`. Exact DataFrame comparison passed against
the saved reference, original/current input frames remained unchanged, and
serialized CSV bytes were identical. On this scoped CPU sample with pandas
3.0.5, the original helper took 5.491169 seconds and the port took 1.227708
seconds. These are dated sample measurements, not an end-to-end speed or
model-accuracy claim.

The measured row-helper SHA-256 was
`40faa30d986b4920cca1b06d46018764b81cd456f84556e19d0a06e7e313f21b`.
Raw parent evidence retains `check-campaign-rows.py`, `campaign-rows.log` and
`campaign-rows-verification.json` outside the source tree. The parent is still
checking the additional relationship-edge comparison before closing the
aggregate parity check.

## Parent relationship-edge confirmation

The task-owned adaptation of retained `check_parity.py` exited 0 on the
current ported source. It compared the original implementation with current
`build_result_rows` using duplicate ground truth, background images, invalid
geometry, pre/post-threshold wrong-class relationships, threshold boundaries
and exclusions. Exact full DataFrame equality and byte-exact CSV equality passed.
Only the adapted output path was written; original drivers and data remain intact.
Together with the 50,000-row exact input/frame/CSV comparison recorded above,
this closes scoped export parity. It does not establish original campaign
numerical recovery, SIGILL resolution or end-to-end performance.

Baseline and focused test logs have been copied into the parent task-owned
evidence alongside `campaign-rows-verification.json` and
`campaign-relationship-parity.txt`. Final integrated canonical, prospective-version
pairing, native checks and fresh review remain pending after the force port.

## Final integrated verification checkpoint

The complete final-source canonical command exited 0 with a successful
unchanged-input receipt: Ruff, strict mypy, Vulture, import contracts and
4,844 ordinary tests passed; 30 tests were skipped and 81 opt-ins deselected.
The frozen proposed CY 0.46.0 / queue 0.1.9 pair passed normal resolution,
matching source/installed metadata, all 583 queue tests (7 hardware opt-ins
deselected), static/import/help and documentation checks.

All six DINOv3 default/JSON/mosaic L/X native cases also passed on that
proposed-version final source: 160 optimizer updates each, changed parameters,
80 evaluated images and downloaded/reloaded checkpoints. The remote audit
verified all six pinned derivations, derived hashes and canonical null selectors.
The command exited 0 with verified descendant exit and reservation release.
Raw case trees were retained as `final-native-archive`, and tag-scoped stand
cleanup verified zero remaining owned projects/tasks. These results remain
separate from the still-pending forced selected L/X and full64 estimator gates.

Fresh reviewer `review_integrated_source` found no blocking source or architecture
issues in the complete integrated CY and queue compatibility diffs. This is
source clearance, not final release acceptance. Final native catalogue audits,
architecture acceptance, actual delivered-version metadata and fresh final
review remain required before any commit/tag/push delivery.
