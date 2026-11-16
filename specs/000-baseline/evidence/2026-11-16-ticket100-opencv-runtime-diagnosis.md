# Ticket 100: loaded OpenCV mismatch in direct/queued comparison

Date: 2026-11-16. Status: CPU diagnosis reproduced; environment preparation is
proposed, not executed. Ticket 92 scientific parity remains blocked. This record
does not accept ticket 100 or reinterpret a failed/needs-review receipt as passed.

## Scope and identities

The read-only runtime investigation used local CY master
`5c0ece16a73ecc9ce279b564b7d69471c69007fa`, 32 commits ahead of recorded
`origin/master`; no remote references were fetched. The direct environment is
`.venv`; the queue v2 environment is the retained
`.tmp/verification-gap-closure/ticket92-plan-20261116/venv`. Existing v1/v2
environment, plans, public/private job records and durable coordination binding
remain unchanged. Only this dated evidence and ticket-owned diagnosis scratch were
written. No model, GPU computation, package installation or queue operation ran.

The affected direct case is `ultralytics-default-2e66fec4f0`; the queued case is
`queue-acceptance-v2/completed`, job
`6e5315ee-4953-42e8-aa8b-04e3657cea0b`. The fresh readback
`20261116T172130Z-d1d5d435` retains `needs_review`; earlier helper failures are
preserved. The two cases have identical initial optimizer parameter hashes but
different first-epoch losses and final scientific outputs. Matching arguments and
distribution versions did not establish equivalent loaded image-processing code.

## Reproduced mismatch

Both environments declare `opencv-python==5.0.0.93` and
`opencv-python-headless==4.14.0.94`. Both distributions own the same
`cv2/cv2.abi3.so` path. Their installed RECORD entries disagree, as expected for
different binaries sharing that namespace:

| Environment | Imported cv2 | Binary bytes | Binary SHA-256 | Matching RECORD |
| --- | --- | ---: | --- | --- |
| Direct | 5.0.0 | 74161369 | `f7746177b49e0368c73142ab92d3d5a4a9ce989aecce7178d7e05c58679349c9` | opencv-python |
| Queue v2 | 4.14.0 | 70500369 | `eaf864c6e211836c68ad35c5cfa1b042232a58f4e5f976c319f58e0e8a849b16` | opencv-python-headless |

The other distribution's binary RECORD fails in each environment. Full resolved
module/binary paths, runtime build information, declared versions, source-image
hashes and raw CPU outputs are retained in the companion JSON. This demonstrates
namespace collision; it does not reconstruct the precise historical installer
ordering from logs.

The direct cv2 directory contains84 non-bytecode files. Its execution subset is15
files:13 Python modules, the native extension and the Qt plugin. Fourteen execution
files match the cached opencv-python5 wheel; `gapi/__init__.py` is an extra retained
file from the overlapping layout. V3 must match this exact execution-file set and
hashes, not merely the native extension. All84 ancillary/runtime hashes are retained
separately. Matching this existing hybrid namespace does not solve the dependency
graph collision. The independent export preparation's15-file baseline agrees with
this diagnosis and is linked by hash in the companion JSON.

The retained standalone `pixel_probe.py` runs both existing interpreters with CUDA
hidden and one CPU thread, without importing a detector. It reads the same sorted
160 frozen training JPEGs. It hashes decoded pixels, linear resizing to width640
(height rounded up proportionally), a fixed float32 affine transform
`[[0.8, 0, 30], [0, 0.8, 240]]` to 640x640 with border114, and BGR-to-HSV pixels.
Decoding, resizing and HSV aggregate hashes match. Warp hashes differ:

- Direct: `ca5d51a6ab9bf9e0d0c6dbe358cc6c4c2f702a168b34a8b383349bbe9c550ffe`.
- Queue v2: `5258bfc7ed5fd4edde39bbd60ab15170dc99b8e9f73bff73e81c79e29218bca0`.

For `012d29df4.jpg` (source SHA-256
`5b59424943796cc869228db4e99f80ce656454ba7a3d14c53bb8cceff9bf1d3c`),
11,754 of 1,228,800 channels differ, maximum absolute difference1, mean absolute
difference0.0095654296875. This is a deterministic CPU differential probe, not a
replay of the historical training RNG draws. Native Ultralytics
`data/augment.py:1212`, `RandomPerspective.apply_image`, calls this same
`cv2.warpAffine` operation; its source hash is retained. Different loaded providers
therefore constitute an observed preprocessing confounder, not a proposed tolerance.

Reproduce from the CY repository root:

```bash
env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  nice -n 19 taskset -c 0 .venv/bin/python -B \
  .tmp/verification-gap-closure/ticket100-opencv-diagnosis-20261116/pixel_probe.py
```

All four subprocesses exited successfully; no temporary images or environment
files were written. Retained script/output hashes are in the companion JSON.

## Proposed isolated v3 preparation

Preserve both historical environments. Create a new task-owned v3 environment
under `.tmp/verification-gap-closure/ticket92-plan-v3-20261116/venv` only after the
coordinator freezes the intended CY and queue checkouts. Retain their Git/source,
lockfile, editable metadata, Python and package identities. Product dependencies,
source pins, scientific batch72/two epochs/seed0 recipe and zero tolerance remain
unchanged. The existing host coordination binding must be reused, never replaced.

Use native preparation's locked sync and editable-source installation in v3:

```bash
# cwd: frozen CY checkout; these are proposed commands, not execution receipts
v3_root=/mnt/wsl/data/nkt/clearml-yolo/.tmp/verification-gap-closure/ticket92-plan-v3-20261116
v3_venv="$v3_root/venv"
diagnosis_dir=/mnt/wsl/data/nkt/clearml-yolo/.tmp/verification-gap-closure/ticket100-opencv-diagnosis-20261116
queue_checkout=/mnt/wsl/data/nkt/cy-queue
test ! -e "$v3_venv"
test ! -e "$v3_root/uv-cache"
mkdir -p "$v3_root"
cp -a --reflink=auto /mnt/wsl/data/nkt/.cache/uv "$v3_root/uv-cache"
export UV_CACHE_DIR="$v3_root/uv-cache" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
UV_PROJECT_ENVIRONMENT="$v3_venv" uv sync --locked --dev --offline --link-mode copy
uv pip install --python "$v3_venv/bin/python" --offline \
  --link-mode copy --constraint "$diagnosis_dir/v2-distributions.txt" -e "$queue_checkout"
uv pip install --python "$v3_venv/bin/python" --offline --no-deps \
  --link-mode copy --require-hashes --reinstall-package opencv-python \
  -r "$diagnosis_dir/opencv-provider.txt"
uv pip check --python "$v3_venv/bin/python"
```

The retained constraints contain all284 v2 declared distribution versions; they
constrain queue installation without changing lockfiles. Compare the final
inventory exactly against the frozen expected inventory; any intentional source
version change needs explicit provenance rather than a silently loosened pin.
Missing cached dependencies or unavailable build requirements are preparation
errors, not permission to resolve newer versions.

Before copying, budget the private cache plus new environment and installation
transients against actual free disk space. All subsequent uv commands, including
the selected pairing route, inherit this task-owned `UV_CACHE_DIR` and copy link
mode. Reading the approved shared cache for the initial copy does not authorize
mutating it. Keep the private cache through evidence collection; its later cleanup
belongs to the v3 owner and must not follow symlinks into shared inputs.

`opencv-provider.txt` selects only the locked manylinux_2_28 x86_64 wheel for
opencv-python5.0.0.93 with SHA-256
`c8de2dec111122a02e8beb28e16c31904992dfd6186560b142a92c71403c1039`.
The existing uv cache has this provider's unpacked archive; its native binary
already hashes exactly like the direct environment. This investigation verified
the cached binary and recorded wheel metadata, but did not run an installer or
claim the offline hash-required installation succeeds. The installer must verify
the wheel hash or fail closed. Do not reconstruct/repack a wheel, remove headless
metadata, modify a shared cache, or write the root/v2 environments. Reinstalling
the existing provider last is an explicit local preparation choice while the
two locked distributions still overlap; it is not a product dependency fix.

Before any GPU run, require successful pip checks, native
`scripts/paired_metadata.py check`, exact expected package/source identities,
actual imported cv2 version/path and all15 execution-file hashes matching direct,
review of ancillary-file differences against the retained84-file inventory, and exact
160-image CPU preprocessing equality. Freeze all new observer/request/config and
snapshot identities. Later sync/install operations invalidate this provider check.

Run the retained probe's child mode explicitly with the v3 interpreter and a new
output path. Do not run its no-argument collector: that collector deliberately
targets historical direct/v2 interpreters and rewrites `pixel-probe.json`.

```bash
test ! -e "$v3_root/pixel-probe-v3.json"
env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  nice -n 19 taskset -c 0 "$v3_venv/bin/python" -I -B \
  "$diagnosis_dir/pixel_probe.py" --child > "$v3_root/pixel-probe-v3.json"
```

Compare the new JSON's image inventory and all four aggregate pixel hashes exactly
against `pixel-probe.json`'s frozen `runtimes.direct` entry. Require the expected
actual cv2 version/binary identity and all15 execution-file hashes separately as
above. Save the comparison receipt under v3, preserving the frozen diagnosis
script, original direct/v2 receipt and their hashes. A mismatch stops preparation.

Fresh paired CPU verification is selected because installation applicability
changed. Run the maintained paired-check route on the frozen source pair and
retain its receipt. Its ordinary Task creates/removes its own temporary environment;
that result alone does not attest the retained v3 binary. Also run the same native
paired metadata, queue Ruff/format/mypy/import-linter/unit-suite and CLI-help checks
using the prepared v3 interpreter, capturing source stability before/after. Do not
change Task or present this v3 supplemental execution as the untouched stock Task.
No separate documentation gate is introduced.

After CPU preparation and independent review, the coordinator may schedule the
already-authorized serial native comparison with existing ownership cleanup and
8GiB minimum reserve. Preserve all v2 failures. A fresh capacity confirmation and
unchanged scientific recipe remain necessary; CPU image equality alone cannot
establish GPU training parity or authorize accepting different outputs.

## Diagnosis verification status before v3 execution

- Passed: CPU mismatch reproduction, loaded-provider/RECORD identity checks and
  cached provider binary comparison. No mocks or live service claims.
- Deferred: v3 installation, its loaded-provider and CPU pixel parity, fresh paired
  checks, and subsequent exact native scientific comparison.
- Unverified: whether correcting OpenCV resolves all708 differing checkpoint
  tensors and the prediction/threshold/metric discrepancies. The full historical
  math/environment state was not captured. Source inspection found no parent-side
  TF32/matmul setting mutation by fresh-process batch probes; this is not proof of
  equality of every historical runtime flag.

An earlier visual impression of shifted training images was rejected by numerical
pixel alignment and is not a finding. No tolerance relaxation or product patch is
recommended from this bounded diagnosis.

## Actual v3 CPU preparation and remaining pairing gap

The reviewed proposal above is retained byte-for-byte in
`.tmp/verification-gap-closure/ticket92-plan-v3-20261116/reviewed-v3-proposal.md`
(SHA-256 `94c8daf16b509e82a356fd7a53460215ef08eb33dc0bd5c9c32e1c5d85cd0175`).
The following execution supersedes its earlier deferred installation status.
The linked `preparation-summary.json` binds commands, logs, process identities,
resource samples, exact source and final observations. No GPU/model execution ran.

The private cache copy, locked offline sync, constrained queue installation and
hash-required offline OpenCV provider selection passed. The retained v3 environment
has all 284 expected declared versions, package identity
`70cb1afb0777588e7f399ad40ea21ccdac47c3f2aaf4566d558111baebe12fce`,
and all 15 OpenCV execution-file hashes equal to direct. All 160 input hashes and
all four CPU operation aggregates now match direct exactly, including affine warp.
This reproduces the declared hybrid namespace; it does not resolve the overlapping
dependency declarations. Root and old-v2's retained 84-file cv2 inventories each
remain unchanged. All installer/cache mutations targeted owned v3 paths.

The first local identity checker failed because it normalized observed distribution
names but not expected names. Its failure and script remain retained; a separate
checker normalizing both passed. An optional fingerprint command was rejected by
a tool hook; no retry or bypass occurred, and approved existing manifests plus Git
source assertions supplied the intended source evidence. These are preparation-tool
failures, not product/dependency failures.

Pip consistency, native paired metadata, actual-v3 queue Ruff/format, mypy (70 files),
import contracts and CLI help passed. The selected native paired Task failed with
3 failed, 524 passed and 7 deselected in 181.56 seconds. Its temporary environment
was removed. The separate actual-v3 suite failed with 2 failed, 525 passed and
7 deselected in 179.74 seconds. Every failure is preserved, including both sets of
temporary test records; neither suite is reported as passed.

[Ticket102 diagnosis](2026-11-16-ticket102-queue-observation-diagnosis.md) identifies
intermediate lifecycle observations against unchanged queue revision d3627a0.
An independently implemented test-only correction and fresh selected verification
remain required. V3 native preparation and ticket92 acceptance are blocked; unrelated
native backend/export work is not. No inference of solved scientific parity follows
from CPU pixel equality. All historical v2 scientific failures retain their status.

All preparation phase children were reaped. The final four suite/supervisor PIDs
were absent, and a bounded process scan found no remaining command containing the
owned v3 path before environment handoff to ticket102. Owned environments, caches,
receipts and test directories remain intentionally retained for that work. No shared
queue coordination binding or external dataset was deleted. CPU affinity was 0–1,
priority nice19, CUDA hidden, and memory/disk guards stayed above their limits.

A separate readback helper validates each Dataset counts Training task ID against
its corresponding producer identity before comparing every other cell exactly.
Checks against all four actual direct/v2 workbooks passed and rejected wrong IDs
and changed annotation counts. It still reports other scientific differences and
was independently approved by the coordinator for future v3 readback after admission
and required gates; no tolerance or product code changed.
