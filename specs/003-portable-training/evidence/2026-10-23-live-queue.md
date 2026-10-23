# Real extracted queue acceptance, 2026-10-23

The extracted queue completed real standalone `train` and `pipeline` GPU execution,
ClearML publication, forced artifact/model downloads and native checkpoint reload.
The acceptance harness used a task-owned **test-only 16 GiB admission
ceiling** because background GPU memory exceeded the production limit. Real NVML
telemetry, CUDA visibility, host coordination, holds, reservations, launch gates,
guardians and lifecycle communication remained active. This establishes the real
queue execution path under that isolated test condition. It does **not** establish
successful admission under the unchanged production rule of used memory below 2 GiB.

## Method and ownership

The existing end-to-end and machine environment skills supplied capacity preflight,
project credentials, a minted run tag and exact-prefix cleanup. The harness created
only its own queue configuration, metadata, fixtures, processes and ClearML project.
It used the existing host coordination namespace; no hold or reservation was bypassed,
and no other workload, dependency, service or production source was changed.

An ignored, task-owned `sitecustomize.py` selected the existing `GPUInventory`
constructor's memory ceiling in the acceptance worker and its descendants. The
constructor still used the real NVML provider and physical UUIDs. Both the worker's
inventory and guardian's fresh admission check received the same test ceiling.
Separate observational wrappers recorded the real `retain_first` return and
successful socket acknowledgement without replacing either operation. This is
verification instrumentation, not a new queue configuration option. The normal
worker startup message still describes the production default; the instrumentation
records establish the effective ceiling in the isolated test processes.

The production worker first processed the submitted train job without injection.
It left the job pending with `Waiting for GPU capacity: 1 requested, 0 available`
and no allocation. That worker was stopped through its normal signal handler.
The test worker then admitted the same immutable snapshot. Observed memory before
this run was 9,717,768,192 used bytes out of 34,190,917,632, with 24,473,149,440 bytes
free. The harness required at least 16 GiB free before starting its tiny training.
After execution, an uninjected inventory again reported the production default
of 2 GiB and `busy=true`, with 9,717,047,296 used bytes.

Both submitted command shapes were:

```bash
python -m cy_queue.entrypoints.queue submit --command train --gpus 1 --json -- \
  ground_truth=FIXTURE.csv ultralytics.model=yolov8n.yaml \
  ultralytics.epochs=1 ultralytics.imgsz=64 ultralytics.batch=2 \
  ultralytics.workers=0 ultralytics.pretrained=false ultralytics.amp=false \
  ultralytics.plots=false ultralytics.compile=false \
  clearml.project_name="RUN_TAG clearml-yolo" clearml.tags=[RUN_TAG]
```

The pipeline used `--command pipeline`, enabled prediction and disabled metrics,
reports, comparison and FiftyOne publication. Native GPU selectors were omitted:
`--gpus 1` owned allocation and logical-device remapping. The fixture contained six
96×64 RGB images with disjoint train/validation/test membership, one object image
and one empty image per split. Each command trained for one epoch on CUDA device 0
using the queue-selected physical GPU. Predictions used that allocation. Downloaded
checkpoints were subsequently reloaded for a CPU prediction so verification required
no GPU use outside the queue's lease.

The final successful run occurred from 15:49:19 to 15:50:47 UTC. Machine-specific
scripts, exact commands, real UUIDs, logs, records, checkpoints, downloaded files and
JSON evidence remain under the ignored `.tmp/portable-queue/` workspace. Its successful
archive is `archive-clearml-yolo-codex-20261023-portable-queue-8i1m`.

## Verified results

| Command | Queue/task outcome | Forced downloads | Native reload |
| --- | --- | --- | --- |
| `train` | Completed, one CUDA epoch and native scalar telemetry | `gt_csv`, one best Output Model | Downloaded checkpoint predicts one image |
| `pipeline` | Completed, one CUDA epoch and prediction | `gt_csv`, `predicts_csv`, one best Output Model | Downloaded checkpoint predicts one image |

Both downloaded ground-truth files preserved every original CSV field, six rows,
three empty images and six unique source-row/object IDs. Numeric coordinates were
compared after numeric normalization. The pipeline prediction artifact contained
36 rows. Each downloaded checkpoint hash matched its native selected `best.pt`.

| Command | Task ID | Output Model ID | Downloaded checkpoint SHA-256 |
| --- | --- | --- | --- |
| `train` | `e44e938e0a684ce8938606001bac4a21` | `f02e9b1f5a29401da12715dc1100736a` | `11b82334e75d2cbbb6224d61660f3c06a401e699d05ed90fe590e7dfa53bcad7` |
| `pipeline` | `ec2d14a5b4c446e4970d59416d9b802c` | `b1c13539936f47df90c36b49e560f9cf` | `8810b257e943f2a8204a7e320e95cc747956c76e0728706bf9497a0d29dfae27` |

The downloaded `gt_csv` SHA-256 for both commands was
`f965f0d748532e085c3219a0c80da968d91458e9a720b2b88b13e1d1678a0faa`;
the pipeline `predicts_csv` SHA-256 was
`e45727cebf4aa47a213c2d68e341387a35061f447c23fe7bc770cc490238573a`.

Snapshot bytes and hashes remained unchanged through execution, and both snapshots
retained the same combined package identity. Both validated against the installation
used by the worker. Canonical replay retained the requested YOLO YAML and
`pretrained=false`; queued source/model-weight selectors retained their null values.
YOLO's canonical `model` object intentionally contains only backend and preset.

The standalone train command held its allocation through completion and has no
pipeline stage handoff. The pipeline performed the real training-finished handshake:
`retain_first` returned, the guardian persisted its claim and acknowledged the socket
message, and the owner continued inference. Seventeen subsequent samples observed
the first GPU still claimed while the pipeline was running. Terminal cleanup removed
both jobs' claims. With one physical GPU this verifies first-device retention and
acknowledgement, not release/reassignment of additional physical GPUs.

## Corrections, cleanup and limits

An initial harness submission supplied native GPU selectors and was correctly
rejected before job creation. Subsequent harness corrections used exact ClearML IDs
from durable queue records instead of the unsuffixed task name, and removed an
inapplicable non-YOLO configuration assertion. Earlier native runs completed, but
those attempts did not finish publication verification and are not counted as the
successful acceptance run. Their tagged resources were cleaned too. No production
change was required. The final live harness and its separate archive audit exited 0.

All observed owned child/guardian process birth identities were gone at the final
read-only audit. No owned worker, GPU claim or hold remained. Exact-prefix cleanup
removed the successful run's project and two tasks; subsequent listing returned zero
projects and tasks. Fresh exact-ID SDK reads also confirmed both task IDs no longer
exist. The invocation directory was removed after retaining the private archive. Durable host coordination files were preserved for normal future operation.

The active prepared environment still reported stale CY distribution metadata
0.34.0 and queue 0.1.0 while importing the current source checkouts. This run therefore
proves execution and stable identity in that environment, not satisfaction of the
queue's declared CY >=0.38,<0.39 dependency. The separate candidate source-install
check owns compatible package metadata verification.

No production module or interface changed in this follow-up; its effects were confined
to the authorized ignored harness and dated evidence. Physical multi-GPU handoff,
multiuser/multihost operation, normal 2 GiB admission with an idle GPU, performance,
model quality and actual Artifactory connectivity remain outside this evidence.
