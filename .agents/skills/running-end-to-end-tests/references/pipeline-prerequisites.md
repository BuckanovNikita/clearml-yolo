# Select native-run inputs

Paths start at the repository root. Read contracts affected by the intended claim;
versions, options and defaults belong to configuration and command help.

| Decision before execution | Authoritative guidance |
| --- | --- |
| Prepare CY, optional queue and backend dependencies | `docs/development.md` (External dependencies; Paired CY and queue release check) |
| Choose an invocation workspace and preserve SDK/user state | `docs/filesystem-policy.md` |
| Select local CSV or finalized CSV-only ClearML dataset; resolve media and literal IDs | `docs/input-provenance.md` (ground truth sources) |
| Generate editable YAML for the selected command/model and choose explicit native devices | `docs/experiment-records.md` (configuration resolution and replay), `cy-init-config --help` |
| Select native backend, pretrained assets or export runtime | `docs/multi-model-backends.md`, `docs/model-assets.md`, `docs/tensorrt-deployment.md` |
| Choose direct or queued execution, isolated metadata and recovery ownership | `docs/queue.md`, `cy-queue --help` |
| Prepare baseline/candidate inputs, exact validation thresholds and identity sidecars | `docs/experiment-records.md` (evaluation comparison and historical model recovery), `docs/input-provenance.md` |
| Enable FiftyOne with a shared lock directory for publishers using the same owned database | `docs/runtime-isolation.md` (fiftyone evaluation publication), `clearml-yolo-environment` |

Before live work, establish available hardware and preserve unrelated compute. Use the
owned environment's endpoints and explicit tagged project overrides; never adapt an
archived invocation without checking its current contract. A finalized remote dataset
must have accessible image references; compare its downloaded CSV bytes with the local
source before claiming transport parity.

For native family comparisons, use the same current images and frozen thresholds.
Checkpoint descriptors and provenance serve different purposes: preserve both when
copying inputs and validate hashes. Use explicit labels for legacy inputs without
inventing training identity. Retain workspace arenas and diagnostics until deliberate
cleanup confirms idle descendants.
