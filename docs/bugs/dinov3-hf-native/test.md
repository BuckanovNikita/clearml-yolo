# Bug verification: official HF DINOv3 initialization

- Slug: `dinov3-hf-native`.
- Tested: 2026-11-04.
- Assessment: [assessment.md](assessment.md).
- Fix: [fix.md](fix.md).
- Result: partial — source implementation and CPU acceptance verified; parent gates pending.

## Original failure and source audit

The previous original-Meta validator rejected both valid converted representations
with `Asset sha256 checksum mismatch`. Fresh authorized downloads confirmed that
the two frozen Facebook repositories contain Transformers safetensors rather than
the original Meta `.pth` representation. Four released archives and all 61 declared
weight/config members matched their pinned checksums. The released timm DINOv3 Small
bytes and configuration matched a fresh upstream download; all 162 timm tensors
matched the corresponding official-HF-derived native tensors exactly. This is a
source-representation gap, with no observed published-asset corruption.

## Executed checks

Focused tests cover exact Q/K/V ordering, both MLP layouts, native buffer restoration,
missing/extra/nonfinite/shape/dtype failures, original-cache precedence, explicit
and unrequested initialization bypass, unauthorized access, source integrity and
revision checks, derived receipt/checkpoint corruption, tampered tensors with an
updated file hash, concurrent atomic publication and canonical-config preservation.
The CPU-only RNG regression reproduced the CUDA-seeding issue before correction.

Real `prepare_model_assets` resolved both selected DEIM L/X models without backbone
overrides. Their 188/212 native state entries exactly matched the independently
verified converter, with strict loading and preserved CPU RNG. Four fixed real-image
cases per preset passed consumed-feature parity at the pre-established
`atol=rtol=1e-3`; exact source-tensor round-trip and repeated native/HF evaluation
passed. The stricter `1e-4` diagnostic did not pass and is not claimed as acceptance.
Complete native Hub and derived caches were reused without rewriting while the
Hub SDK network entrypoint was blocked.

Ruff passed for all task-owned Python files; strict mypy passed all five checked
source/test files. The combined focused suite passed **452 tests** (21 upstream
warnings) in 15.87 seconds:

```text
python -m pytest tests/test_dinov3_hf_weights.py tests/test_deim_assets.py \
  tests/test_model_assets_loading.py tests/test_deim_backend.py \
  tests/test_architecture.py tests/test_model_assets.py tests/test_native_assets.py \
  tests/test_hub_assets.py tests/test_weight_preparation.py -q
```

The original failing observation, fresh-download/hash checks and real CPU parity
were run by dated task-owned audit drivers. Parent evidence retains
`current-contract-reproduction.json`, `verification.json`, `tensor-comparison.json`,
`production-native-preparation.json`, both `production-native-*-parity.json`,
`offline-reuse.json`, the drivers and their logs. The CPU driver command is
`CUDA_VISIBLE_DEVICES='' python native-cpu.py` with the isolated source view and
explicit task-owned cache root. It calls actual selected-model preparation,
compares all tensors to the independently verified reference and runs the fixed
real-image feature checks. No GPU is visible to that process.

`python scripts/verify.py --docs` passed Markdown/local-link validation after the final evidence append. Architecture planning validation passed;
acceptance remains pending parent canonical/native checks and review.

## Acceptance still required

Parent integration must run the canonical application checks on the final combined
diff, execute native GPU fallback training/estimator acceptance, obtain fresh
independent review and validate architecture acceptance. Companion portable usage
documentation is being reconciled separately. No local test result here establishes
GPU/DDP execution, ClearML publication, the full estimator matrix or a release.

## Integrated acceptance update — 2026-11-04

The final combined source passed the canonical verifier: **4,790 passed,
30 skipped, 81 deselected** in 1,068.42 seconds, including architecture negative
cases and CPU-DDP; Ruff, mypy, Vulture and import contracts passed. The unchanged-input
receipt is `application-106ddd8c9333425a8182c6d398a2d77b`. Documentation validation
also passed. These results supersede the pending parent canonical check above.

All **six native DEIM L/X cases** (default, JSON and mosaic) passed through the
production HF fallback without model/backbone overrides: 160 actual updates per
case, zero skipped updates, finite losses, changed parameters, 80 prediction images
and downloaded-checkpoint reload. Initialization identities match within each
preset. The six-case run took 741.92 seconds with 57 unrelated cases deselected.
Fresh server readback verified the pinned HF source, conversion/native revisions
and derived SHA-256 in every published `model_assets` record; canonical weight
selectors remain null. Exact derived bytes and downloaded artifacts are retained
with a full hash manifest. Owned processes exited, GPU ownership was released,
and tag-scoped cleanup confirmed no remaining owned projects or tasks.

Normal editable resolution of proposed CY **0.46.0** with cy-queue **0.1.9** passed
the queue suite: **583 passed, seven physical cases deselected**, together with
metadata/dependency, static, import and help checks. Before/after source inventories
were identical. These candidate versions have not been released.

Fresh independent reviews `hf_conversion_review` and `integrated_source_review`
returned SHIP for source and architecture within the verified scope; see
[review.md](review.md). The companion portable skill update and its independent
review/evaluation passed at source level; publication remains separate.

The complete 64-model estimator matrix is still pending. Single-GPU native
training does not establish physical multi-GPU execution or close that gate.

## Isolated current-master verification status — 2026-11-05

The preceding results describe the earlier combined source, not this isolated
DINOv3 port on master `66279a6`. Current focused/canonical/native/paired checks and
fresh review have not run. See the appended [integration ledger](fix.md#current-integration-ledger)
for remaining acceptance work. The architecture record intentionally resets those
results to `not-run`; historical passing counts are not transferred to this source.

Architecture planning validation passed before source integration (exit 0). The
scoped patch passed `git apply --check` and was then applied without conflicts.
These structural checks do not establish runtime acceptance.

## Current-master sequential integration — 2026-11-05

Base: `66279a6` (CY 0.45.1), isolated `work/sequential-integration-20261105`.
The preserved combined-source results above remain historical. Current task-owned
raw logs and driver copies are retained outside the repository under
`cy-sequential-20261105-evidence`; evidence commands use the new checkout's
independently provisioned environment. No dependency pins changed.

- Focused regressions: `CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MPLBACKEND=Agg
  uv run --frozen --no-sync python -m pytest tests/test_dinov3_hf_weights.py
  tests/test_model_assets_loading.py tests/test_deim_backend.py -q` passed,
  105 tests.
- Fresh CPU driver: `CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CY_HOME=<owned-cpu-home>
  .venv/bin/python <owned-native-cpu.py>` exited 0. Both presets preserved
  CPU RNG and matched every tensor from the independent reference conversion.
  Four feature cases per preset passed the predeclared `atol=rtol=1e-3`
  criteria. Worst absolute differences were approximately `4.06e-5` (Small)
  and `1.17e-4` (Small+). The stricter diagnostic criteria did not pass;
  these results do not establish exact numerical feature identity.
- `uv run --frozen --no-sync python scripts/verify.py --docs` exited 0.
- Canonical Ruff, strict mypy, Vulture and import contracts passed; the complete
  ordinary suite is still running.
- The first native launch inherited a shared Ultralytics cache path. It was
  cancelled before acceptance, descendants were verified exited, and the owned
  reservation was released. Its tagged ClearML project was deleted and the
  tag-scoped listing was empty. Logs are retained as an aborted attempt.
  A fresh launch uses a task-owned `YOLO_CONFIG_DIR` and weights destination.

Native training, published provenance/readback, ordinary selected estimator,
final canonical receipt, paired proposed versions and fresh review remain pending.
The full forced 64-model matrix belongs to the subsequent force stage.

### Verification execution corrections

The first canonical suite was interrupted to normalize the temporary local
`pyproject.toml` section removal; it supplies no successful canonical receipt.
The final run started with the normalized exact source view and unchanged
installed environment. Ruff, strict mypy, Vulture and import contracts passed
again; the complete suite remains in progress. `git diff --check` passed.

A second native attempt was cancelled while optional full-catalogue mirror
preparation was downloading unrelated assets. Its descendants exited and owned
reservation was released. Cache preparation now uses the supported
`CY_WEIGHTS_DOWNLOAD_TIMEOUT=5` to bound optional mirror requests, with
read-only reuse/copies of existing cached assets and normal production validation.
This changes neither selected DINOv3 source pins nor weight/backbone selectors,
and supplies no claim that full-catalogue restoration succeeded. The six-case
training attempt will use the same bounded optional mirror budget.

Latest queue source `694c12f9c2a1a0064284a69d010e846108d43875` (0.1.8) was
normally installed with this CY source (currently 0.45.1) in a separate copied
environment. Dependency check, matching source/installed metadata, Ruff lint/format,
strict mypy, both import contracts and CLI help passed. The queue suite passed
583 tests with 7 hardware cases deselected. Proposed 0.45.2 and final-version
metadata verification remain required before delivery.

Portable guidance was updated in an isolated companion corp-skills checkout
from `0a3ed5e16d06ff478b9e067f57b601a3a9823e2b` (0.7.4). Package metadata,
links, Markdown and four-skill list-only discovery passed. A fresh independent
source review and both explanation-only evaluations passed. Native acceptance
and final release wording remain pending; no skill was installed.

### Final canonical result

`CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MPLBACKEND=Agg
uv run --frozen --no-sync python scripts/verify.py` completed with exit 0,
including Ruff, strict mypy, Vulture and import-linter. The complete ordinary
suite passed 4,828 tests, with 30 skipped and 81 deselected. The verifier wrote
a successful unchanged-input application receipt. This includes the architecture
negative cases and CPU-DDP coverage; the skipped/deselected opt-in hardware
cases are not claimed as passed. No scoped mutation target, selected mutation
fixture/test or dependency revision changed in this DINOv3 port.

The proposed CY 0.45.2 / queue 0.1.8 pair was separately normally resolved and
installed from a hash-bound candidate copy differing only in root release versions.
Matching source/installed metadata, dependency check, all 583 queue tests
(7 hardware cases deselected), static/import checks and help passed. Original
source and the canonical CY environment remained unchanged. Final actual-source
version/metadata recheck is still required after hooks and before push.

Both DEIM L/X default native cases have passed; the remaining JSON/mosaic cases
and complete remote provenance audit are still pending. Task-owned YOLO cache
seeding copied existing primary-checkout files with SHA-256 equality checks,
leaving originals intact and retaining production validation.

### Native completion and ordinary-admission blocker

The six current-source DEIM L/X default, JSON and JSON-mosaic cases all passed.
Each completed 160 optimizer steps with changed parameters, downloaded/reloaded
its checkpoint and evaluated 80 images. Every non-default case matched its
corresponding default initialization. The owned native command exited 0; all
descendants exited and the GPU reservation was verified released.

The remote provenance audit exited 0 for all six tasks: pinned official source
URL/revision/SHA-256, converter and native revisions, actual derived-file hash,
and unchanged canonical null detector/backbone selectors were verified. Raw
case trees were moved into the task-owned `native-archive`; the published
provenance readback documents remain in `default-hf-provenance`. Tag-scoped
cleanup removed the owned project; the resulting listing had zero projects
and zero tasks. FiftyOne was explicitly disabled by the existing harness.

The ordinary selected-estimator command used the documented 960-pixel,
150-class/300-object workload, one GPU, 90% memory budget, ceiling 1024 and
300-second trials, without `--force` or weight overrides. It exited 1 before
any trial for both models: `No idle selected GPU ... busy or its telemetry is
unavailable`. A separate read-only observation found 2% GPU utilization,
2,989 MiB used and no compute PID. The current conservative idle rule rejects
activity without a PID; VRAM usage alone is not the blocker. No workload was
stopped and the ordinary rule was not relaxed. Ownership/process cleanup
remains independently verified by the launcher receipt.

**Current result: partial; release held.** The original HF format/conversion
failure is resolved on the six actual native paths, but successful ordinary
trials and fresh winner confirmation remain an unmet acceptance gate. The
source/architecture review can proceed; release cannot proceed until this gate
is completed. No forced estimate, historical result or failed admission is
reported as ordinary-estimator success.

### User-directed continuation and scoped independent review

After the idle-admission result, the user instructed “Ignore this is idle.”
The earlier ordinary-estimator hold is preserved as the observed failed attempt;
it is not the remaining execution route. Selected L/X estimator acceptance is
now deferred to the planned explicit force mode on the frozen final integrated
source, with successful native optimizer receipts and fresh winner confirmation.
The complete 64-model gate remains owned by force. No intermediate release will
precede those results, final source/version pair checks and integrated review.

Fresh independent reviewer `dinov3_final_source_review` inspected the DINO-only
source, architecture/import contracts and raw canonical/CPU/native/provenance/
cleanup/proposed-pair evidence. Verdict: SHIP for this scoped source and
architectural design; no blocking source findings. This is not release acceptance.
The reviewer requested this explicit ordinary-versus-forced-gate reconciliation;
the failed ordinary record is retained unchanged. Physical multi-GPU remains
unverified. The later campaign/force integration requires final integrated checks
and a fresh independent review before delivery.

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

## Estimator criterion reconciliation — 2026-11-06

The selected L/X audit previously required a usable batch for both models. This
was stricter than the existing aligned-eight contract: the search starts at eight
per GPU, and a native OOM or measured memory-budget failure at that minimum is a
legitimate `no_capacity` outcome. The prospective selected audit now accepts either
an independently confirmed usable winner or a raw-receipt-proven minimum-eight
`no_capacity`, with matching current profiles and verified owned-process cleanup.
This changes no workload, search grid, optimizer, memory budget or model settings.
Earlier failed attempts remain failures. Host ENOMEM, generic exceptions and
cleanup failures cannot establish GPU capacity. Fresh independent source reviewer
`review_oom_boundary` accepted this interpretation of the existing contract.

The old-source selected X run exposed a typed `torch.AcceleratorError` carrying
integer CUDA error code 2; the worker incorrectly recorded generic `error`. The
scoped [OOM receipt correction](../accelerator-oom-receipts/assessment.md) has CPU
regression coverage; native replay on refreshed source remains required. L failed
separately while launching `nvidia-smi` with host ENOMEM and then bounded worker
cleanup. Diagnostic outer-cgroup cleanup and reservation release were verified,
but that failed measurement is not a valid estimator result. Investigation remains
open. No release has been delivered.

### OOM-corrected integrated verification

The canonical command on the combined source including the scoped AcceleratorError
receipt correction completed with exit 0 and unchanged-input receipt
`application-d76129d35b89403aa15cf9216f8acfb2`. All static/import checks passed,
and the ordinary suite passed 4,856 tests (30 skipped, 81 deselected), including
CPU-DDP and architecture negative cases. Native selected/catalogue acceptance,
final paired source-version checks and final review remain open.

### Selected L diagnostic outcomes — 2026-11-06

Three bounded runs on the retained pre-correction candidate produced distinct
telemetry failures: helper execution ENOMEM, helper exit 255, and a 15-second
whole-device query timeout. Full exception leaves also retain internal worker
cleanup timeouts. Each diagnostic outer guard eventually verified descendant exit
and released its reservation; the diagnostic command's exit 0 means evidence was
written, while every measured case remained failed.

The final instrumented failure snapshot showed ample available host memory, payload
usage below its configured cap and zero memory/OOM/task-limit events in its cgroup
and visible ancestors. It does not support memory-cap exhaustion or CUDA capacity
classification. Nearby driver errors do not establish causality. A bounded idle
telemetry check subsequently succeeded; that does not establish telemetry reliability
under the original workload. Raw snapshots, stdout/stderr capture and ownership
receipts are retained externally as diagnostic evidence. No production telemetry
fallback, timeout relaxation, workload reduction or global machine change was made.
The unresolved native telemetry/runtime failure continues to block selected L
acceptance and the dependent full catalogue gate.
