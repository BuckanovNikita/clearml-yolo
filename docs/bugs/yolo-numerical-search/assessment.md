# Bug assessment: numerical failure discards usable search candidates

- Slug: `yolo-numerical-search` (generated).
- Assessed: 2026-10-30.
- Verdict: valid recovery/usability defect; native numerical cause unconfirmed.
- Severity: medium; a late numerical failure discards all capacity recommendations.

## Observation and evidence

The user reports `FloatingPointError: YOLO probe produced nonfinite validation loss`
and then no compatible validated single-GPU estimate. Their catalogue records CY
0.44.2, Ultralytics 8.4.189, Torch 2.14.0, compiled AMP YOLOv3u, 960 square images,
100 classes and 300 objects/image. Batches 1, 2, 4, 8, 16 and 24 passed both optimizer
paths. Batch 32 completed but exceeded the 90% memory budget; batch 28 failed
numerically. The saved failed case correctly has no independently confirmed winner.
The other active case displays an interruption diagnostic while its command is running.

Current `BatchSearch.observe` intentionally aborts every noncapacity failure.
This is a proven recovery limitation, not evidence of A40 incompatibility. Target
hardware reproduction is unavailable. Real cached YOLOv3u probes passed locally at
128/batch 1/AdamW and 640/batch 28/MuSGD, including compiled and eager execution.
Relevant detection numerical code is unchanged between Ultralytics 8.4.184 and
8.4.189. Native training warmup differs from the probe but has not been established
as this failure's cause. Do not change AMP, optimizer steps, synthetic workload,
finite guards or model state to suppress an unproven numerical defect.

## Remediation and compatibility

On a numerical failure during discovery only, if a previous candidate passed all
checks and the memory budget, request one fresh confirmation of that candidate.
Successful confirmation yields a usable `numerically_limited` result, explicitly
not a measured maximum. Preserve the original failed trial and diagnostic. Any
failed confirmation, first-candidate numerical failure or other failure still leaves
no recommendation. Never use numerical failure as a memory upper bound. Keep every
native optimizer path, update count, validation and memory check intact.

Propagate limited status and diagnostic through saved evidence, exact lookup,
extrapolated recommendations and CLI output. Read existing schema-1 catalogues;
write schema 2 for the new status and refuse that status under schema 1. Reading
alone must not rewrite historical data. Correct the provisional snapshot diagnostic
to say independent confirmation is pending and the search may still be running.
No public option changes. Old readers must be upgraded before reading new catalogues.
Implementation fingerprints invalidate prior recipes as usual.

The user's requested fix authorizes implementation. A preference question offered
this recovery versus strict failure; after allowing time for a reply the recommended
recovery is the stated default. Any later answer steers the work.

## Architecture and tasks

See [architecture.json](architecture.json). Core owns pure search, validation and
schema policy. The application retains progress through injected ports; the CLI
owns presentation. SDK/GPU behavior, worker and storage effect ownership are unchanged.
Existing import contracts and negative tests cover all changed modules; no new edges.
Python compatibility remains >=3.12.13,<3.14, uv/Ruff/strict mypy/pytest toolchain and
approved external dependencies unchanged. Isolated latest-source checkout protects
unrelated pending work. Root owns integration; bounded read-only investigation and
isolated environment setup precede verification, then fresh independent review.

1. Add failing regressions replaying the reported 1..32,24,28 sequence, confirmation
   rejection, persistence migration, lookup/extrapolation and active snapshots.
2. Implement recovery and presentation without numerical or memory-policy weakening.
3. Update batch guide, README, affected feature contracts and portable usage guidance.
4. Verify focused behavior, real native probes, canonical application/architecture and
   documentation checks; verify latest paired CY/cy-queue, including release metadata.
5. Reconcile task-owned diff, obtain fresh independent review, accept architecture,
   then complete the authorized Git-only release and preserve historical evidence.

No physical A40 result, corrected underlying numerical computation, measured memory
maximum for a limited result, or real multi-GPU capacity is claimed.
