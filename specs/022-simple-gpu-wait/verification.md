# Verification: Simple GPU waiting

Date: 2026-10-10. Scope: queue removal and direct invocation, feature 022.

## Implementation and review

Removed queue persistence, reservations, worker supervision and the project Hydra launcher.
Stateless availability polling selects inherited CUDA logical indices before invocation
ownership begins. CPU/MPS bypass inventory; sequential jobs ignore only their own retained
CUDA context. The requested/effective device records and native cleanup remain.

The parent inspected the combined implementation, packaging and documentation diff.
A fresh independent read-only review returned ship after checking logical device mapping,
task ownership, replay, primary-error preservation and the corrected CPU test fixtures.

## Automated checks

- The initial launcher/device regression checks failed against the old implementation.
  The inventory/wait implementation also has recorded failing-before/passing-after tests.
- Affected execution, architecture, resource and regression modules: 216 passed.
- The first full suite reported 1,366 passed, 30 skipped and nine failures in fake-task
  routing/replay tests. Direct execution exposed their implicit GPU demand; those
  configuration-only fixtures now explicitly request CPU. Their complete module then
  passed all 13 tests. Full commit/release hooks remain the final suite gate.
- Ruff and strict mypy passed; import-linter kept all 27 contracts.
- Both wheel and source archive installed in fresh environments with the frozen runtime
  dependencies. All ten installed command helps passed from outside the source checkout.
  Both generated ten YAML files and refused overwrite without changing their hashes.
  CPU, one-GPU and two-GPU example configurations composed successfully.
- Built archives and installed targets include GPU waiting/probing, native DDP and FiftyOne
  integration, with no removed queue, reservation runtime, worker or launcher plugin.
- Maintained Markdown, local links, anchors, fences and whitespace were validated;
  generated configuration composition checks cover changed examples.

## Native checks

- Native one-epoch training completed and the commands exited zero on CPU and one GPU.
  Best-checkpoint publication/readback and required training ground truth upload succeeded.
- A CPU pipeline with training skipped completed prediction, evaluation and the expected
  missing-baseline comparison path, then exited zero.
- A standard two-job GPU prediction sweep completed sequentially in the invoking process.
  The jobs created separate completed ClearML tasks, including reuse after the first
  job's CUDA context. The sweep exited zero.
- The pipeline and both sweep tasks were read back as completed. Every published artifact
  from those three tasks was force-downloaded successfully.
- Initial prediction verification commands mistakenly included the unsupported
  `ultralytics_predict.workers` key and failed before task creation. Removing that test
  override produced the successful checks above; application configuration was unchanged.
- Task-owned projects, tasks and run directories were cleaned; scoped listings were empty.
  Machine-specific commands, logs and task identifiers are retained with environment guidance.

## Limits

Physical multi-GPU/DDP execution and MPS were not available in these native checks;
device mapping, ownership and demand paths have structural/unit coverage. This change
provides no exclusive GPU allocation guarantee between concurrent commands.
Native busy-to-free verification was inconclusive: telemetry did not expose the owned
CUDA test process, even after polling for an update. Both attempts cleaned their process.
Busy-to-free behavior is established by injected inventory tests, not by that native probe.

The original other-machine hang after `report_business`, with FiftyOne enabled, was not
reproduced. Its queue cleanup exception alone does not identify the underlying wait.
FiftyOne publication and ClearML shutdown remain separate hypotheses, deferred by request.
An earlier full training-plus-evaluation probe on the original implementation failed at
ClearML model association readback; that path is not claimed fixed by queue removal.

## Release

Release remains gated by the repository's commit and release hooks. Only a Git version
tag is to be published; no package assets or registry publication are part of this task.
