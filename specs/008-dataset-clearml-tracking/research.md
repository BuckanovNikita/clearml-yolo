# Research

## Dataset lifecycle

Decision: Use cached prepared data.yaml directly, retaining NDJSON locally. Existing export
already writes a complete YOLO layout, so rerunning convert_ndjson_to_yolo duplicates
work. Preserve NDJSON basename/casing; keep flat numbered lowercase names. Reject repeated
label stems per split. CSV bytes are the only input content identity; no image hashes/mtimes.

Decision: Hold one filelock per entry across publication and the native training consumer.
Installed native verification may repair JPEGs and native caches can write .cache/.npy files.
Serializing consumers for the same entry is conservative but preserves native settings and
source-image immutability without monkeypatching the upstream dataset. Different cache entries
remain independent. Atomic staging and completion metadata prevent consumption of interrupted entries. Run cleanup has no ownership over this cache.

Alternatives rejected: Reconvert NDJSON each run (violates reuse); hardlink originals (native
repair can alter user images); image-content hashing (explicitly excluded); unguarded shared
native writes (race); disable native options silently (violates forwarding contract).

## Native ClearML

Installed Ultralytics 8.4.165 exposes five callbacks and registers trainer.best through
Task.update_output_model. Pretrain reuses Task.current_task(), connects General, and swallows
exceptions, requiring wrapper postconditions. Existing framework autocapture is already off.
Callbacks are copied into trainer instances; install before construction, keep through training.

Decision: Enrich the same registered native model; require registration and a fresh remote
checkpoint verification before task completion. Use public SDK model setters and metadata
methods, leaving IDs, timestamps and unavailable lineage alone. Never auto-publish production.
Exact installed API inspection is recorded in the model contract before implementation.

## Readable inventory

Decision: Canonical CSVs and workbooks only. The existing stage upload loops publish raw
metrics, manifests, YAML duplicates, native plots and checkpoints. Keep local diagnostics and
internal completion receipts; use one sanitized run configuration and native General.
Deduplicate tables by content, with internal alias satisfaction of required-publication checks.

## Comparison

Decision: Read exact validation CSV thresholds for new tasks and historical payloads for old
ones. Prefer explicitly identifiable best native model, never arbitrary last model. Preserve
latest completed prod task exclusion and paired selected-split inference (test in the pipeline).
Source task/model links replace copied configurations. Architecture and labels are checkpoint-owned.

## DDP native callback compatibility

Installed Ultralytics suppresses integration callbacks in the launching DDP parent.
`native_ddp.py` captures exact callback inputs and event-time preview/plot snapshots
in rank zero, using the upstream callback serialization path. After training the
invocation owner replays all installed native ClearML callbacks and applies the
worker's effective training arguments before enriching the same output model.
Workers never initialize ClearML or publish. Incomplete event output fails the
invocation. Snapshots survive until model/artifact waits and flush complete.
Single-process training bypasses replay. Physical multi-GPU execution remains an
environment-dependent integration check; CPU worker relay evidence is separate.
