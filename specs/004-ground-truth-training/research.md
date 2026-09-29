# Research Decisions: Ground-Truth Training

**Date**: 2026-09-29

## Native Local NDJSON Compatibility

Decision: use Ultralytics >=8.4.165 and its native local NDJSON converter. The header
contains `path: "."`; each image record names a file under `images/<split>/`.
The training task explicitly calls `convert_ndjson_to_yolo` with an output directory
inside the run-owned preparation directory, then passes the resulting YAML to training.
Declare aiohttp directly because the native converter imports it even for local files.

Evidence: the released 8.4.165 converter resolves these paths locally and copies images
([upstream converter](https://github.com/ultralytics/ultralytics/blob/v8.4.165/ultralytics/data/converter.py)).
The original lock (8.4.126) lacked this support. An offline regression blocks HTTP image
requests and exercises the actual converter. No HTTP server or custom NDJSON parser is
needed. Native conversion may rename its image copies; the retained preparation manifest
and cleaned CSV preserve original image identity for downstream evaluation.

Alternatives rejected: implicit conversion (global output routing); temporary HTTP server
(unnecessary); custom conversion (duplicates supported upstream behavior).

## Input and Identity

Decision: strict structural validation, recoverable invalid box filtering, sorted original
class names, absolute original paths in cleaned CSV, and collision-free numbered exported
filenames. Preserve raw numeric-looking labels as strings. Read/verify image dimensions once.
Copy images into owned outputs so upstream repair/caching cannot mutate source images.

Rationale: original evaluation identity must survive export renaming, while background
images and dropped-box counts remain reproducible in both formats.

## Configuration and Tracking

Decision: training prepares only when CSV input exists; pipeline always supplies its CSV.
Return explicit `cleaned_ground_truth` and `dataset_reference` fields. Enforce data, detection
task, classes, class remapping, fraction, single-class, and validation split ownership.
Reject resume in CSV mode. Disable prediction class filtering for the CSV-driven pipeline.
Retain requested/effective override records. Preserve ordinary native controls.

Generated YAML is connected with remote overrides disabled. NDJSON and explicit non-image
manifests/label archives are artifacts, not files passed through the YAML configuration adapter.
Preparation uses sibling `.datasets/<name>` storage and the existing invocation task.

## Parallel Review and Clarification

The runtime and integration investigations ran independently. The integration reviewer
approved all eight custom requirements-quality items. The accepted user corrections
resolve format naming and invalid-box behavior; no additional material questions remain.
No Spec Kit hooks are registered. Post-design constitution check passes: no new SDK access
in domain modules, no model imports for configuration, and no external submodule changes.
