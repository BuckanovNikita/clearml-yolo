# Supplemental native-case readback preparation

The coordinator-owned ignored script
`.tmp/verification-gap-closure/readback_native_case.py` supplies supplemental
ticket03/05 observations without training, GPU execution, task creation or remote
mutation. It adopts only the live recorded environment whose identifier agrees
with `runs/verification-gap-closure/service-owner.json` and the case tags.
Credentials are obtained through `tests.integration.lifecycle.recorded_environment`
inside the process and are never written into a receipt or shell export file.

## Invocation

From the repository root, after the representative scenario has passed and the
coordinator admits the CPU validation workload:

```bash
uv run --locked python .tmp/verification-gap-closure/readback_native_case.py CASE
```

`--owner PATH` selects a different explicit ownership receipt. `--cpu-timeout N`
bounds the CPU validation child (default 600 seconds). `--local-only` verifies local
admission without remote calls or native validation and cannot establish acceptance.
`--help` requires neither the SDK nor credentials. An incomplete case is refused
before creating a readback directory or looking up the environment.

Every full invocation creates a fresh `CASE/readback/TIMESTAMP-ID/` with its script
snapshot, isolated ClearML cache, forced artifact/model downloads, sanitized remote
configuration/parameters/scalars/model metadata, native epoch telemetry, CPU
validation log/results, and `receipt.json`. Existing case evidence is never replaced.
A failure retains partial observations with `status=failed`; successful remote checks
alone cannot mark the receipt passed when native CPU validation fails or times out.

## Checks and interpretation

- Verify retained request/resolved-input/estimate/canonical hashes, manifest, CSVs and
  image bytes; require the original scenario's passed status and optimizer evidence.
- Independently fetch the completed task by ID, verify ownership and canonical
  recipe, and download the enabled publication inventory, including `pipeline_outcome`.
  Refuse failed/warning stages or unexpected skips. Compare artifact hashes with the
  original harness observations.
- Download the single associated best Output Model into a new cache. Check checkpoint
  bytes, training-task/project association, architecture selector, vocabulary and exact
  typed calibration metadata against the threshold CSV.
- Compare native two-epoch results and native arguments with canonical configuration;
  compare the stable scientific General subset with native arguments using the product
  parameter projection. Native routing/name normalization is not treated as a recipe
  mismatch. This is a scoped General check, not equality of every SDK parameter.
- Check published GT/held-out image membership and split assignments, decoded-pixel
  split separation, background contexts, prediction checkpoint identity, threshold
  validity and finite available workbook numbers. Unavailable metrics remain unavailable;
  this does not independently recompute dashboard scientific results.
- Reload the downloaded checkpoint for native CPU validation on the frozen 40-image
  validation population, using copied source images and derived YOLO labels inside the
  readback directory. The parser-required `train` dataset entry points at the same
  validation directory, but the script never invokes training. CUDA visibility is empty,
  validation workers are zero and the child has no exported ClearML credentials.

After success, the coordinator reviews `receipt.json` and retains the `handoff` fields,
`best.pt`, thresholds, downloaded evidence, script snapshot and native validation result.
The coordinator may remove the invocation's cache and CPU dataset copies after preserving
these outputs. No shared cache or original fixture is eligible for that cleanup.

The original launch receipts still own peak-memory/reserve monitoring, process-cleanup,
source/environment identity and timing evidence. This script neither reconstructs missing
telemetry nor certifies unobserved reserve minima. Native CPU validation is a loading and
execution check, not accuracy, export, multi-GPU or new GPU-capacity evidence.

## Preparation evidence

- **Passed**: CLI `--help`; no service/SDK initialization was needed.
- **Passed**: Ruff format and focused syntax/undefined-name/import checks (`E,F,I`).
  A first unrestricted Ruff run reported scratch-script style issues; formatting and
  import corrections were applied. No project-wide lint compliance is claimed.
- **Passed**: `--local-only` against retained failed case
  `ultralytics-default-4794e3a821` exited 1 with “Case has not passed; remote readback
  is forbidden.” No readback directory or remote request was created by that check.
- **Not executed**: successful-case admission, remote readback, model download and
  CPU validation. The complete readback remains pending a passed representative case.

No product/harness files, remote services, model assets or existing case files were
modified during preparation. No GPU or training work was launched. All preparation
commands exited; only the requested script and this usage/evidence record were created.
