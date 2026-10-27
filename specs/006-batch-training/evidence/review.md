# Independent review: feature 006

Date: 2026-10-26. Scope: the complete uncommitted feature relative to
`9fd2294ab219c534fcce87b59eea7b56e9d01173`, including added source/tests and
configuration data. Reviewers used fresh contexts, read actual implementation and
native library source, and had no write ownership or GPU permission.

## FCOS and shared Torchvision

Reviewer `review_fcos` found a preservation regression: the new distributed route
rejected native `-1`, `"-1"` and `[-1]` automatic device selectors. The parent
restored those single-device selectors and added workflow coverage. The reviewer
independently verified all three forms and rejection of invalid mixed selections.
No unresolved code findings remained in this scope.

The reviewer also executed native CPU/Gloo experiments for FCOS ResNet-50,
FCOS DINOv3-Small and Faster R-CNN DINOv2-Small: two ranks, two epochs, global
batch two, accumulation three, seven validation images including empty images,
resolution 128, random initialization. Full EMA state hashes and metrics matched
across ranks; all state tensors were finite; four EMA updates occurred and saved
checkpoints had no DDP prefix. All workers joined before temporary directories
were removed. This is CPU evidence, not pretrained CUDA or publication evidence.

## Cache and configuration

Reviewer `review_cache_config` reproduced a standard YOLO cache miss: CSV policy
sets `cls_remap=false`, whereas estimator defaults used the upstream true value.
The parent excluded this dataset-owned mapping control from the recipe hash.
The regression now composes native defaults, applies execution and dataset policy,
and selects a saved estimate against the assigned ordered devices. Independent
CPU reproduction confirmed identical estimation/execution profiles.

The reviewer also identified possible loss of final scalar/log lines when the
supervisor observes process completion before its next poll. The parent's final
event drain handles remaining log chunks and complete scalar records exactly
once. Its regression covers a log larger than one polling chunk.

Atomic probe receipts now fence completed GPU measurement from CUDA-context
teardown telemetry. Exit status and typed receipt validation still reject failed
workers. No unresolved findings remained in search, catalogue, storage, lookup,
replay, Hydra export/legacy precedence, CLI and the reviewed guidance.

## Distributed and probe review

Reviewer `review_distributed` identified two YOLO probe gaps, subsequently fixed
and independently re-reviewed:

- AMP must follow native rank-zero decision and broadcast, rather than separate
  per-rank decisions on heterogeneous devices.
- Bounded validation must execute native loss and metric processing as well as
  inference/postprocessing. A CPU reproduction showed that a deliberately failing
  validation loss was never called.

The integrated probe now runs the native AMP check on rank zero, restores its
callback registry and broadcasts the precision decision. Validation calls the
native detection validator with bounded synthetic data, including assignment
loss, matching, aggregate metrics and distributed gathers. New regressions
exercise real CPU detection loss/metrics, nonfinite rejection and the distributed
AMP decision. The parent ran 73 probe/profile tests, then 88 combined
probe/profile/worker/telemetry/event tests; both runs passed. Focused Ruff and
strict typing passed. The reviewer accepted both corrections with no remaining
code findings in the reviewed scope.

Catalogue profile construction now shares one GPU metadata snapshot, while every
actual trial independently checks visible identities, hardware and idleness.
The reviewer confirmed this preserves the trial safety boundary. Its regression
is included in the parent checks above.

The reviewer found no additional concrete issues in DEIM/RF-DETR rank setup,
unique validation, buffer/EMA synchronization, supervised cleanup, receipt
identity, global batch translation or owner publication. RF-DETR's synthetic
validation uses the larger effective training shape, a conservative envelope.

## Acceptance status

All three fresh reviewers accepted their original reviewed code scopes after the
fixes and parent verification. A subsequent focused memory review reproduced an
additional undercount: allocator peak 850, sampled device peak 700 and baseline
100 yielded usable 850 against a 900 budget, although the combined peak was 950.
The integrated correction records allocator and synchronized non-allocator
observations separately, refreshes the idle baseline for each optimizer path,
and takes the maximum of observed whole-device usage and their conservative sum.
RF-DETR samples before Lightning teardown. Parent checks passed 65 focused tests;
the implementer also passed 272 architecture checks and all 50 import contracts.

The full suite exposed a separate zombie-reaping omission when pre-existing
helpers were present. A deterministic regression reproduced it. The supervisor
now reaps recorded birth-matching adopted children after consuming direct worker
statuses; an unrelated helper remains alive. Parent verification passed 56
worker/tree/lifecycle/capability tests and scoped Ruff/mypy. An omitted YOLO batch
also now preserves its numeric default path instead of invoking explicit-null
lookup; 28 resolution/trace tests passed.

Independent re-review accepted these final corrections with no remaining concrete
findings. The reviewer passed 78 focused CPU tests and independently checked PID
replacement filtering, preservation of worker exit code 23 and preservation of an
unrelated helper's exit code 19. It confirmed that phase sampling remains an
observed memory envelope, not a guarantee of every transient non-allocator peak.

A subsequent real-process reproduction exposed a telemetry ownership race: an
owned compiler child can appear after the supervisor takes its PID snapshot but
before the GPU query completes. The monitor now receives a callable and refreshes
birth-validated ownership after collecting telemetry. It does not accumulate old
PIDs or waive unknown activity. Independent re-review reproduced the old failure
and accepted the correction; 71 focused tests passed, including PID replacement,
disappeared/foreign owners and active utilization without attributable PIDs.

The new four-family physical DDP harness received parent inspection and 40 passing
offline tests. Fresh reviewer `review_native_harness` then reproduced an incorrect
RF-DETR fixture assumption using the installed native data loader and distributed
sampler: at two ranks the intended 16 images repeat to 40, producing ten
microbatches/five updates rather than the hardcoded four/two. The corrected fixture
provides twenty unique images per rank, and validation derives expected counts
from population, global batch and accumulation. Real-loader regressions for two,
three and four ranks prove no repeated sample identities. The parent subsequently
passed 46 focused tests; scoped Ruff/format/mypy/Vulture also passed. Independent
re-review accepted the correction with no remaining blocking findings and passed
seven selected evidence/native-loader tests. The reviewer inspected the real backend
lifecycle hooks, supervision, publication, download/reload and fault cleanup.
Physical execution remains unavailable; these harness checks are separate from the
already reviewed runtime and do not close T022.

Code-review acceptance is separate from feature acceptance. Real multi-GPU
acceptance, the full native matrix and final canonical checks remain separate
gates. Missing native evidence continues to block commit and release under this
feature's acceptance plan.
