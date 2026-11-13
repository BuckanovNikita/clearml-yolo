---
name: running-end-to-end-tests
description: Select real-run evidence for native CPU/single-GPU execution, cy-queue, ClearML publication, FiftyOne or detector/export changes, including release acceptance.
---

# Verify native outcomes

Use [development acceptance](../../../docs/development.md#acceptance-tiers) to select
automated stages. This skill covers evidence those stages do not establish. Read
[prerequisites](references/pipeline-prerequisites.md) before preparing inputs and
[clearml-yolo-environment](../clearml-yolo-environment/SKILL.md) before a live run.
Respect active host mode and existing authorization; verification grants no publishing
or deployment authority.

## Select claims and evidence

Use the maintained contract as the assertion inventory. The checks below are concrete
starting points, not replacements for the affected contract. Mocked tests establish
only their simulated behavior; retain the live/manual observation for a native claim.

| Claim and authoritative contract | Concrete verification |
| --- | --- |
| Direct CPU and single-GPU execution; [runtime isolation](../../../docs/runtime-isolation.md) | Task `acceptance` CPU smoke and `release-acceptance` single-GPU Severstal suite; inspect current task/checkpoint and downloaded outputs |
| CPU distributed behavior; [distributed regressions](../../../docs/development.md#native-cpu-distributed-regression-tests) | `tests/test_native_ddp_cpu.py`, `tests/test_distributed_training.py`, `tests/test_torchvision_distributed.py`; distinguish real CPU processes from simulated GPU cases |
| Queue ownership/admission/recovery; [queue contract](../../../docs/queue.md) | Task `paired-check` runs the sibling queue suite; additionally compare one task-owned single-GPU direct run with a queued run using the same settings, inspect allocation and terminal cleanup |
| Input identity and dataset reuse; [input provenance](../../../docs/input-provenance.md), [filesystem policy](../../../docs/filesystem-policy.md) | `tests/test_ground_truth_sources.py`, `tests/test_dataset_cache.py`, `tests/test_identity_flows.py`; repeat a live CSV run and read back exact CSV bytes/source identity and retained workspace |
| Configuration and replay; [configuration contract](../../../docs/experiment-records.md#configuration-resolution-and-replay) | `tests/test_config_tree.py`, `tests/test_configuration_compatibility.py`, `tests/test_model_replay.py`; inspect generated command/model YAML and replay a task-owned saved configuration |
| Thresholds, comparison and reports; [evaluation contract](../../../docs/experiment-records.md#evaluation-comparison-and-historical-model-recovery) | `tests/test_comparison_scoring.py`, `tests/test_comparison_recovery.py`, `tests/test_population_count_workbooks.py`; run baseline-free and baseline/candidate evaluation, then standalone `cy-val`, `cy-compare`, `cy-report`, including nondefault options |
| Publication, models and completion; [publication inventory and lifecycle](../../../docs/experiment-records.md#required-publication-and-task-lifecycle) | `tests/test_native_tracking_contract.py`, `tests/test_training_success_finalization.py`, live CPU/Severstal suites; independently force-download required artifacts and the best Output Model, load it and compare hashes/metadata with actual checkpoint and thresholds |
| Readable interactive charts; [plot contract](../../../docs/experiment-records.md#reports-and-readable-visualization) | `tests/test_interactive_evaluation.py`, `tests/test_pr_curves.py`; inspect standalone rendered chart HTML and compare ClearML API chart payload/readback |
| Telemetry and failure containment; [diagnostics](../../../docs/diagnostics.md), [runtime isolation](../../../docs/runtime-isolation.md) | `tests/test_console_capture.py`, `tests/test_console_deadline.py`, `tests/test_execution_lifecycle.py`; independently read active console/scalars, observe failures and preserve local outcome diagnostics |
| FiftyOne publication; [native evaluation contract](../../../docs/runtime-isolation.md#fiftyone-evaluation-publication) | Task `release-acceptance` runs `tests/integration/fiftyone`; inspect fresh-process reload, native evaluation/panel data and optional failure/cancellation behavior; `tests/test_bounded_fiftyone.py` covers containment |
| Package compatibility; [paired release contract](../../../docs/development.md#paired-cy-and-queue-release-check) | Task `paired-check` with final source versions, installed metadata, normal resolver and queue suite |

## Manual observations

1. Use disjoint validation/test inputs including empty images; pass explicit project
   names, tags, workspace and device choices. Keep source data and existing SDK settings
   intact. Match direct/queued settings; scheduling does not establish a compiler fix.
2. Observe task-owned cancellation and failure paths with their logs and cleanup proof.
   Use simulated regressions for multi-device allocation, lost acknowledgements,
   guardian failure and ownership fencing. Physical multi-GPU, external multi-user and
   two-host NFS scenarios are outside the maintained acceptance gate; their product
   capabilities remain unchanged, and simulations do not prove those deployments.
3. Read publication through the API independently of command completion. Apply the
   linked lifecycle contract to trained-checkpoint warning completion versus failed
   standalone/skip-training commands. Missing uploads remain unverified even when
   training succeeds. Include checkpoint-owned training counts, unknown/zero handling,
   baseline skip reasons and exact validation thresholds in downloaded reports.
4. Render standalone confusion-matrix and PR HTML in a browser. Exercise every matrix
   normalization and class legend, empty/unknown cases, hover, captions and slot identity
   against the plot contract. The test environment has no ClearML web UI; API payload
   readback and standalone rendering establish those two layers separately. Embedded
   ClearML-UI presentation is not a mandatory acceptance scenario or an inferred pass.
5. For FiftyOne App claims, inspect native evaluation/report views against the linked
   contract after explicitly installing its plugin in the backend environment. Automated
   database/panel tests and worker containment are still required. Temporary database,
   GPU or other supported-resource unavailability defers verification.
6. Record source versions, commands, selectors, task/model IDs, observations and
   limitations in dated evidence before cleaning only owned resources. Preserve evidence
   needed for diagnosis and prove no owned live processes or environments remain.

CPU and single-GPU native runs remain release requirements. Packaging archives are
built only for a concrete packaging investigation, never as routine release gates or
deliverables. When detector/export integration changes, additionally apply
[multi-model acceptance](references/multi-model-acceptance.md).
