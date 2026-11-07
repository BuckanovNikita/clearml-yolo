# Feature 036 live acceptance resumed: 2026-10-20

The primary plain run passed native CPU publication and actual server-backed
controller cache miss/hit/scientific-miss. A separate direct single-GPU run
passed. No runtime, dependency, SDK or shared-service changes were made.

## Reproduction

Run from the application checkout after reading the installed environment and
shared-stand contracts. `run.sh` sources `agent_env.sh`, obeys capacity WAIT,
mints a tag, authenticates from the project's Secret, and always invokes the
tagged cleanup helper. Credentials are consumed directly and never persisted.

```bash
CY_ACCEPT_EVIDENCE=/path/to/new-evidence bash run.sh
CY_ACCEPT_MODE=direct-gpu CY_ACCEPT_EVIDENCE=/path/to/gpu-evidence bash run.sh
```

`live_acceptance.py` records exact commands and results in each `summary.json`.
It uses one native CPU seed and real `ClearmlJob` construction with the
normalization callback, then launches uncached jobs with the same four remote
environment selectors used by SDK `LocalClearmlJob`. It uses normal
`python -m clearml_yolo.entrypoints.train` invocation without SDK substitution.
`LocalClearmlJob` itself is not used because its launcher treats the whole
module entrypoint as a filesystem filename. This verifies the actual SDK job
hash/clone/cache path; it is not a full `PipelineController` DAG deployment.

The optional `CY_ACCEPT_TRACE=1` uses `trace_remote.py` to observe exceptions in
the installed SDK's model constructor through `sys.settrace`. It changes no
application/SDK source or return values. This diagnostic mode was not used for
the primary acceptance repeat.

## Runs and outcomes

| Evidence | Minted tag suffix | Outcome |
| --- | --- | --- |
| `attempt-1/` | `s96y` | Native CPU completed; harness queried the wrong unsuffixed task name. |
| Root logs/summary | `xfxc` | CPU seed passed; first remote clone failed the native model identity guard after upload. |
| `gpu/` | `rdch` | Direct native CUDA training/validation, publication and forced-download/reload checks passed. |
| `diagnostic/` | `nvdp` | Full miss/hit/scientific-miss passed with constructor exception observation; none was observed. |
| `plain-repeat/` | `n1op` | Full miss/hit/scientific-miss passed through ordinary uninstrumented subprocesses. |

All tags have prefix `clearml-yolo-codex-20261020-cache-cleanup-`.
Each run's cleanup log proves zero remaining tagged projects/tasks and deletion
of the exact tag-named local workspace. `acceptance-checks.json` verifies
successful terminal results, stable dataset identity, scientific override
readback, cleanup proofs and absence of owned processes. `gpu-before.log` in
`gpu/` and the top-level `gpu-after.log` preserve GPU observations. No pre-existing
service or GPU consumer was stopped.

Primary CPU task IDs are
`3e0cdf99da4b43fc889c5ffe59b917f0` (seed),
`7b0f51d864744d3489647dff4a88ab6b` (initial miss and routing hit),
and `3b27e57594de4abe9359ed3cddb1966a` (scientific miss).
The GPU task is `1446398496124c718a35368615af6402`.
These remote tasks were intentionally deleted by tagged cleanup after their
evidence was downloaded.

The dataset contains eight non-square synthetic images: four train, two val and
two test, with one empty image in each evaluation split. One-epoch random-weight
YOLO11n runs at image size 64 establish native execution only; zero mAP is not an
accuracy claim. Direct GPU uses `compile=false`, so this does not establish
compiled or physical multi-GPU behavior.

Each successful task has full canonical native settings, no execution/output
keys in General, the expected dataset identity, native scalars, `gt_csv`, and one
downloaded native best model whose bytes match the local checkpoint and whose
class mapping reloads correctly. `plain-repeat/independent-readback.json`
independently verifies the seed and initial-miss CSV rows/names/backgrounds,
project/tag identity, and repeated forced model downloads.

## Preserved failure and limits

The first remote clone, `5bca853a9b0041f78b92cba7ad4ea811`, failed with
`NativeModelError: ClearML did not reopen the native output model for enrichment`.
The failure was after successful training/upload and was not counted as a pass.
The underlying installed SDK constructor catches exceptions at
`clearml/model.py:2217–2241`; the initial run did not observe the swallowed
exception. Its task/model before/after snapshots were not captured before
cleanup. Subsequent diagnostic and plain runs captured snapshots and did not
reproduce it. Do not infer a root cause or a repair from these successful
repeats. The original intermittent failure remains unexplained.

`source-hashes-before-fix.json` and `acceptance-checks.json` confirm the observed
projection/cache/session/native/replay sources stayed unchanged; despite the
historical filename, no source fix was applied. All product acceptance details
are summarized portably in the feature 036 verification record. Parent-owned
integration, fresh review, architecture acceptance and release remain separate.
