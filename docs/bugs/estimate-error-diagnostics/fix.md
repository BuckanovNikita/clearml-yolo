# Bug fix: batch-estimate error diagnostics drop telemetry evidence

- Date: 2026-11-07
- Status: applied
- Assessment: [assessment.md](assessment.md)

## Changes

| File | Change |
| --- | --- |
| `src/clearml_yolo/core/batch_estimation.py` | Added pure `error_diagnostic(error)`. It renders `Type: message` (unchanged for a plain exception without notes), appends `__notes__`, and recursively lists group leaves, using the group's `message` instead of the counted `str()`. |
| `src/clearml_yolo/application/use_cases/batch_estimate.py` | Failed-preparation and failed-trial case diagnostics use `error_diagnostic`. |
| `src/clearml_yolo/adapters/integrations/batch_probe.py` | `NativeBatchProbe.run` has a new branch after the unchanged `FileNotFoundError` and `RuntimeError` branches. It turns `ExceptionGroup` and `subprocess.SubprocessError` into an `error` trial with the formatted diagnostic. A `BaseExceptionGroup` carrying `KeyboardInterrupt` still propagates. |
| `src/clearml_yolo/adapters/runtime/gpu_inventory.py` | `_query` attaches non-empty nvidia-smi stdout and stderr to `CalledProcessError` and `TimeoutExpired` as notes (decoding bytes), then re-raises the same object. |
| `tests/test_batch_estimate_workflow.py` | Exact case diagnostic for a nested telemetry/cleanup group; preparation-failure group; formatter keeps the plain format, recurses and renders notes. |
| `tests/test_batch_probe.py` | Grouped, lone `CalledProcessError` and lone `TimeoutExpired` failures become `error` trials that the search observes as `failed` with one retained trial. Leaf, note and command text containing "GPU" do not change the status. `RuntimeError` text classification is pinned (two `contaminated` cases, one `error` case). A `KeyboardInterrupt` group propagates. A failing fake `nvidia-smi` reaches the trial diagnostic through the real monitor. |
| `tests/test_gpu_inventory.py` | A fake `nvidia-smi` exiting 12 keeps the `CalledProcessError` type and text, with NVML stdout/stderr in notes. A timeout carrying bytes or text output gets a note. A failure with empty streams gets no notes. |
| `docs/batch-estimation.md` | Search and evidence: telemetry, timeout and cleanup failures are saved as `error` trials with leaf and nvidia-smi output diagnostics; GPU-named direct rejections remain `contaminated`. |

## Deviations from assessment

The [source assessment](../selected-l-telemetry-loss/assessment.md#secondary-diagnosability-defects-confirmed-not-root-cause)
named only the exception group for defect 2. A lone `CalledProcessError` or
`TimeoutExpired` from the monitor escapes in the same way when cleanup succeeds,
leaving `trials: []`. The probe branch therefore also catches
`subprocess.SubprocessError` as `error`. Both previously escaped and were not
classified; no existing classified outcome changes. `contaminated` and `error` both
end a search as `failed`, so search outcomes are the same; only the trial is retained.
`TimeoutExpired` output is noted as well, because the 15-second query timeout was one
of the observed symptoms.

## Documentation update

Updated `docs/batch-estimation.md` (Search and evidence). Inspected the portable usage
source `corp-skills/skills/clearml-yolo/SKILL.md` and `references/evaluation.md` at
`11b686662c748adbf7876840af4c5dfdb965c01b`. No portable-source change is needed: the
CLI, configuration, outputs and recovery steps are unchanged, and the skill does not
describe trial status classes or telemetry diagnostics.

## Follow-ups

- `src/clearml_yolo/adapters/runtime/worker_pool.py:151` joins independent case
  failures with `f"{type(error).__name__}: {error}"` and can drop grouped leaves in
  the same way. It could reuse `error_diagnostic`; not changed here.
- `gpu_inventory.discover_gpus` runs its torch metadata subprocess with `check=True`.
  If it fails, the probe now records an `error` trial, but torch's stderr is not
  attached. Reusing `_attach_output` there is a cheap follow-up (review nit).
- The selected-L measurement remains blocked on the environmental decision in the
  source assessment. This fix improves evidence only.
