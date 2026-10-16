# Physical multi-GPU DDP acceptance

The external-result obligation for the delivered implementation is
[closed by user waiver](evidence/2026-10-16-acceptance-closure/decision.md).
Physical multi-GPU outcomes remain unverified. This procedure is retained for a
future explicitly requested target certification; no result bundle is awaited.

These **new** `ddp_gpu` tests run the production direct and queued YOLO pipelines
with real CUDA/NCCL ranks and ClearML publication. Existing CPU/Gloo DDP tests
remain part of ordinary pytest. Ordinary pytest deselects the physical suite and
does not probe GPUs or contact ClearML through this harness.

Prepare the repository's [development environment](development.md), including its
approved external dependency revisions and CUDA-enabled detector dependencies.
Use Linux/WSL with working NVML, NCCL, at least two whole physical GPUs, supported
pidfd/subreaper supervision and Git. Configure ClearML using its usual SDK
configuration or environment. Required artifacts need an accessible storage
backend. Supply a dedicated test project, not a production project. Select idle
GPUs and run one harness invocation at a time; do not use pytest-xdist.

Physical indexes mean the indexes shown by `nvidia-smi`, not inherited CUDA logical
indexes. The harness resolves indexes through NVML identity enumeration, then sets
`CUDA_VISIBLE_DEVICES` to the ordered whole-GPU UUIDs before starting fresh children.
Queued submission uses logical indexes within that new UUID visibility, preserving
the production queue's selector semantics. MIG selections are unsupported.

Run exactly the new physical tests:

```bash
uv run --frozen --no-sync pytest -m ddp_gpu \
  --run-ddp-gpu \
  --ddp-devices=0,1 \
  --ddp-clearml-project=clearml-yolo-ddp-tests \
  --ddp-artifacts=.tmp/ddp-results \
  -ra -vv
```

Missing opt-in, required options, devices, capabilities, credentials or services
fail an explicitly selected test; they never become a skip or successful result.
A missing artifacts option retains selection-failure evidence in
`.tmp/ddp-results`. Each scenario otherwise creates a unique directory beneath the
requested artifacts directory before parsing selection or running preflight.

The serial matrix comprises direct eager, direct compiled, queued eager, queued
compiled, queued rank exit, repeated queued cancellation, and guardian death with
owner recovery. Every training configuration uses a local YOLOv8n architecture YAML,
random initialization, two epochs, disjoint generated train/validation/test images
and an empty image in each split. No pretrained model download is requested; this
establishes execution, not accuracy.

The success scenarios assert actual CUDA rank/device UUIDs, NCCL world size,
requested compile wrapping, changed trainable parameters and synchronized per-epoch
parameter hashes. The production pipeline trains and evaluates/predicts the current
validation/test images. Fresh-process observers record real task/artifact/model
calls and reject worker-side publication. Server readback requires one tagged task
and one native best Output Model, force-downloads the canonical CSVs, validation
thresholds and full/DTRK dashboards, checks image membership including empty images,
reads workbooks, and compares downloaded checkpoint bytes with the native best.
An independent downloaded-checkpoint inference reload uses CPU after queue completion;
the production pipeline's CUDA prediction reload occurs within its allocation.

Queued observations check the complete UUID allocation at launch, all-rank readiness,
and the post-training prediction gate. Rank exit terminates a real nonowner rank
with exit code 73 before its first native batch. Cancellation calls the production
cancel command twice. Guardian death uses a pidfd pinned to the recorded owned
guardian, requires `recovery_required` with the full claim retained, then invokes
production owner recovery. Terminal queue states and cleared whole-allocation claims
are required. Test gates and observers run only in acceptance-owned pipeline/rank
processes; they do not replace native training loops, NCCL, ClearML transports or
production cleanup. Worker, guardian and capability-probe startup stay uninstrumented.

The native execution deadline defaults to 1200 seconds per scenario. Set
`--ddp-timeout=2400` for a slower compiler/device combination when needed. Cleanup
has a separate default 150-second production budget (`--ddp-cleanup-timeout=180`); its minimum
is 120 seconds so it respects the production guardian's 90-second owner shutdown
grace. Production cancellation/recovery runs first. The final fallback has its own
15-second budget, so an exhausted production deadline or owner-stop error cannot
prevent its five-second TERM grace and subsequent KILL/verification. Fallback harness cleanup
signals only processes with the exact invocation ownership environment and verified
PID birth identity; finding survivors fails acceptance even when fallback termination
succeeds. Uncertain recovery leaves quarantine intact and records the failure.
Pre-existing processes, service instances and unowned queue claims are preserved.

Each directory retains `summary.json`, `junit.xml`, source/version and physical
inventory evidence, a source-file hash manifest including untracked source files,
generated data/configuration, command logs, rank/owner logs, task events, queue
transitions/allocation readbacks, downloaded artifacts, checkpoint hashes, and cleanup
receipts. Preflight failures retain the files available at the failure point rather
than inventing absent rank/publication evidence. Diagnostic configuration and logs
are redacted, and environment evidence uses a small explicit safe list; credentials
are never copied from SDK configuration. Remote tasks/models and local evidence
are retained for review under the unique test tag; cleanup does not delete them.

Archive the directory after pytest returns, including failed scenarios:

```bash
tar -czf ddp-results.tar.gz -C .tmp ddp-results
```

Share the archive together with the exact pytest command and its exit status. Review
all scenario summaries, failed receipts, task/model identities and queue transition
records. A passing offline harness test, CPU DDP run or single-GPU run does not
establish this physical multi-GPU acceptance. Until a target executes this command
and the results are reviewed, physical acceptance remains unverified.

The offline harness checks can be run separately:

```bash
uv run --frozen --no-sync pytest tests/test_ddp_gpu_harness.py -q
```

The maintained [queue contract](queue.md) and
[publication inventory](../specs/014-evaluation-publication/contracts/publication.md)
define the production behavior checked here.
