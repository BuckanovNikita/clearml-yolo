# Ticket 94: preserve selected YOLO training batches on OOM

Date: 2026-11-15. Repository comparison base:
`56fbf8bbcf05d92662bd747031a407433f286dc5`.
The worktree also contains ticket 03's independently owned fixed-recipe trainer
changes; this correction adds only the OOM gate in `run_callbacks` and preserves
those changes. It follows the routine-bug route against the existing
[no-retry contract](../../../docs/batch-estimation.md#select-a-table-entry-during-training)
and [baseline scientific workflow](../spec.md).

## Failure and correction

Installed Ultralytics 8.4.184 catches first-epoch single-process forward/backward
memory errors and retries at a halved batch unless its retry counter has reached
three. CY's owned trainer now sets that instance counter to the exhausted value
at `on_train_batch_start`, after initial configuration and AutoBatch selection.
The existing native handler therefore re-raises the original exception before
changing either batch field, rebuilding loaders, or repeating training.
Successful native epoch completion resets the counter normally.

This deliberately uses the installed native retry gate rather than duplicating
its training loop. The actual-loop regressions protect the integration when an
upstream version changes that gate. No dependency source, pin, device, precision,
resolution, or training duration was changed. Explicit and table-selected batch
resolution is unchanged; native initial AutoBatch retains its prior behavior.

Upstream `ultralytics/engine/trainer.py` SHA-256:
`7d060019b31e85ec429c16b7e728e9d7c5a9083b497fc2b362a76a543808dc60`.
Verified integrated `native_trainer.py` SHA-256:
`4cf0caf2ec6938157422251e2d714396aa20d8c3204b1f791adf7fd0133a803c`.
Verified `tests/test_yolo_oom.py` SHA-256:
`a3b48605bc58669bdc32dfbbe091057ea329961cd52cbd31b5f5b99713589f56`.

## Test seam and evidence limits

The approved seam is `OwnedDetectionTrainer.train()`, running the installed native
training loop, dataset loading, model computation, and optimizer on CPU. Each
disposable dataset contains two training and two validation images at 64 by 64;
a local tiny detection-model YAML avoids downloads. Model forward hooks and
parameter-gradient hooks inject bounded memory failures. Font retrieval and
optional external publisher registration are replaced at their SDK boundaries;
the training loop and retry handler are not replaced.

This is injected-error evidence, not physical GPU memory exhaustion. It does not
establish GPU capacity, multi-GPU training, remote publication, model quality, or
the campaign's separate native GPU acceptance. Initial AutoBatch exercises its
existing CPU selection path, not physical GPU capacity measurement.

## Verification ledger

- **Passed: red/green reproduction.** Before the correction, the actual loop
  invoked the failing model at batches `[2, 1, 1, 1]` and emitted three retry
  warnings. The assertion requiring one attempt failed. After the correction,
  the same test passed with the original exception object, batch 2, CPU device,
  and one teardown callback.
- **Passed: dedicated regression file.** Eleven scenarios passed: runtime OOM;
  each installed backend-memory error spelling; unrelated runtime errors;
  forward/backward `torch.OutOfMemoryError`; initial AutoBatch requests `-1` and
  `0.5`; a cloudpickle-restored fixed-recipe trainer; and successful two-epoch
  training that updates real parameters and writes a nonempty best checkpoint.
- **Passed: focused integration and compatibility regressions.**
  `uv run --locked pytest tests/test_yolo_oom.py tests/test_batch_resolution.py tests/test_native_runtime.py tests/test_native_training_outcomes.py tests/test_yolo_augmentation.py tests/test_train.py -q --disable-warnings --basetemp=.tmp/ticket94-focused`:
  73 passed in 7.70 seconds. These include table/explicit batch behavior,
  fresh-worker callback ownership, serialization, and training/publication
  failure separation. The successful native test observes epochs `[0, 1]`, four
  batch-one updates, changed parameters, and a best checkpoint.
- **Passed: focused type checking.**
  `uv run --locked mypy src/clearml_yolo/adapters/integrations/native_trainer.py tests/test_yolo_oom.py`.
- **Passed: focused Ruff lint and formatting.** `ruff check` and
  `ruff format --check` on those two files.
- **Passed: applicable mutation review; generated coverage excluded.** The native mutation selector excludes
  methods decorated with `@override`, including this changed `run_callbacks`.
  Ticket 03 also changes eligible undecorated functions in this same file; those
  are a separate scope and were not rerun here. The parent accepted this native
  selection exclusion after the actual-loop red/green reproduction; independent
  review will assess the private retry-gate compatibility. No generated mutation
  coverage is claimed for ticket 94.
- **Pending: independent review and integrated final verification.** The parent
  campaign session owns review, final checks, commit, and GPU acceptance.

The focused scope is appropriate to this native trainer behavior correction;
the campaign's final full suite is not duplicated. No global coverage floor is
claimed and no check has been waived.

## Resource ownership

All regression datasets, native checkpoints, caches, and output directories are
owned by this ticket beneath `.tmp/ticket94-*`. Training uses CPU and no loader
workers; test-local Torch thread configuration limits its native CPU work to two
threads and restores prior settings. No live service was created. All test
processes have exited and the four owned temporary output directories were
removed after preserving this evidence; no fixture or checkpoint is needed by
another campaign consumer.
