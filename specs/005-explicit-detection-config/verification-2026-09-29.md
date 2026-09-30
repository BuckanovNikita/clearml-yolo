# Verification — 2026-09-29

## Scope and Baseline

Phase 005: detection-native parameter classification, complete configuration sections,
explicit references/defaults, runtime ownership and requested/native-normalized records.
Starting working tree was clean. Baseline: 434 tests passed with three existing
hydra-zen/Pydantic deprecation warnings. External dependency revisions were not changed.

## Regression Evidence

- New configuration tests failed on old defaults, task-irrelevant active keys, synthetic
  renderer defaults, accepted aliases and incomplete prediction sections before changes.
- New inference tests failed because missing native settings and checkpoint-derived image
  size were accepted, and requested/normalized records did not exist.
- Non-detection checkpoint regression failed for segment, pose, classify and OBB before
  guards were added. Training guard now also covers native-data training.
- Configuration owner: 66 focused tests passed. Integrated runtime suite: 121 passed.
- Full integrated suite: 455 passed, three existing warnings; subsequent training tests
  passed (7 total in that file). The final pre-commit run passed every configured hook, including the full suite
  with 457 collected tests.
- Ruff and strict mypy passed (72 files); all seven import-linter contracts passed.
- Local Markdown links and final newlines passed for all 14 reviewed documentation files.

## Independent Review

A read-only reviewer checked parameter ownership, classification, composition, actual
native consumers, comparison propagation, metadata and task guards. Two findings resolved:
non-detection checkpoint rejection and ambiguous naming of native image size. The retained
`normalized_imgsz` is the stride-normalized predictor target, not tensor-shape telemetry;
rectangular batches may use smaller tensors. Final reviewer verdict: no blocking findings;
123 focused tests passed. This review did not itself execute real models.

## Native Acceptance

The initial native sequence below used 906 before the user corrected the default to 960.
Those records remain evidence of explicit-value forwarding and native stride normalization.
The final default is 960 in configuration, generated examples and documentation. Two
regressions failed against 906 before the correction; the complete pre-commit checks passed again after it, including all 457 tests.

Real CPU execution passed for native training, a full baseline pipeline, a candidate
pipeline with paired current-test comparison, standalone prediction and standalone validation.
Standalone comparison also completed with 49 artifacts downloaded at 906. After the
correction it completed again at the default 960: all 49 artifacts were force-downloaded,
both roles' requested YAML contained imgsz=960, compile=true and nms=true, and both recorded
normalized targets were [960, 960]. Cleanup verified zero remaining tagged tasks/projects.
No training epoch followed the final default correction; training's
configuration path passed the full tests, and the earlier real training run used 906.
Each successful invocation owned exactly one completed ClearML task. All artifacts were
force-downloaded and inspected: 19 for training, 85 for the baseline, 95 for the candidate,
14 for prediction and 43 for validation. Required artifact manifests were checked.

- One-epoch native training produced a usable checkpoint. Native compilation completed and
  the training epoch executed with configured compile=true and nms=true.
- Requested imgsz=906 remained in requested YAML; native stride normalization produced 928.
  Predictor normalized target records are distinct from actual rectangular tensor shapes.
- The baseline correctly skipped automatic comparison when none existed. The candidate
  compared both models on exactly the same two current-test images with frozen thresholds.
- Standalone prediction preserved explicit compile=false, nms=false, imgsz=64 and batch=2
  in downloaded requested YAML. Standalone validation retained frozen calibration thresholds.
- Explicit null image size failed the command and its task without selecting a fallback.
- Controlled upload rejection, flush rejection and SIGTERM produced failed tasks and
  nonzero exits (1, 1 and 143), retaining local diagnostics before task-owned cleanup.
  These checks injected failures at SDK boundaries; they do not establish service-outage recovery.

The initial harness needed two corrections: nullable artifact local paths, and a full
training baseline rather than a skip-training task without an uploaded checkpoint.
These were harness assumptions, not application regressions. A separate standalone
comparison check also correctly rejected identical checkpoint paths; its harness now uses
separate copies to exercise both roles. Blank synthetic images then produced no comparable
detections, correctly failing comparison; the success check uses an installed sample image. Its person-only threshold mapping required
an explicit classes=[0] filter, because the sample also contains other detected classes.

Machine-specific commands, task identifiers, logs and downloaded-artifact inspection records
are retained with the global clearml-yolo environment skill. Tagged main-run cleanup verified
zero remaining tasks/projects and removed task-owned run directories. Pre-existing services
and external dependency revisions were preserved. GPU/multi-GPU execution, performance and
package-release readiness were not tested or claimed.

## Convergence

Converged: no missing, partial, contradictory or unrequested implementation findings.
The assessment checked eight functional requirements, three buildable success criteria,
seven user-story acceptance scenarios, edge cases, seven grouped plan decisions and all
five constitution principles against the present source, tests and real-run evidence.
No additional convergence task or empty phase was appended.

| Intent | Evidence |
| --- | --- |
| FR-001–FR-003; US1; SC-001 | Reviewed 113-key inventory; complete commented YAML exports; composition/default tests |
| FR-004–FR-005; US2/1–2 | Resolved prediction references; complete execution validation; missing/null/false regressions |
| FR-006; US2/3; SC-002 | Shared inference adapter; ownership checks; all five model command paths exercised |
| FR-007; US3; SC-003 | Downloaded requested/effective YAML; 906→928 normalization; paired membership and frozen thresholds |
| FR-008 | Russian README, migration guide, preserved interfaces and unchanged dependencies |
| Plan decisions | Canonical defaults, explicit references, completeness checks, alias rejection, owned inputs, normalization records and verification workflow |
| Constitution I–V | Typed/linted code, import contracts, one-task/output ownership, dated verification and task-owned cleanup |

Independent review completed before this convergence pass; the final 960 correction was
rechecked against FR-003, configuration tests, documentation and native comparison evidence; no additional implementation
pass is required for the accepted scope.
