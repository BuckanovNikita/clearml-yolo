# Verification evidence — 2026-09-28

## Initial documentation and SpecKit review

- Resolved active specification/constitution templates through `resolve-template.sh`.
- `setup-plan.sh --json`, `setup-tasks.sh --json`, and
  `check-prerequisites.sh --json --require-tasks --include-tasks` completed successfully.
- Extension hook configuration contains no registered hooks.
- Specification clarification used the approved plan and subsequent heavy-test restriction;
  no new questions were necessary. Requirements quality checklist passed all eight items.
- At that checkpoint, cross-artifact analysis mapped all 12 functional requirements to tasks;
  all five success criteria had corresponding lightweight or explicitly deferred real-run
  verification. No critical, high, ambiguity, duplication or constitution-conflict findings
  remained in that review.
- `git diff --check` passed after documentation edits.
- Local relative Markdown link and code-fence check passed for 14 changed/current Markdown
  files. This check did not verify remote URLs.

## Initial restricted implementation verification

The final combined focused command was:

```bash
uv run pytest tests/test_configs.py tests/test_config_tree.py tests/test_release_config.py \
  tests/test_ultralytics_params.py tests/test_native_config.py tests/test_clearml_session.py \
  tests/test_train.py tests/test_predict.py tests/test_pipeline.py tests/test_inference.py \
  tests/test_comparison_reinfer.py tests/test_comparison_assemble.py -q -k 'not ddp'
```

Result: **198 passed, 1 deselected**, with three existing hydra-zen/Pydantic deprecation
warnings. These checks use mocked model execution and ClearML; they do not train models,
exercise a GPU, or connect to live ClearML. The deselected test imports native runtime in a
DDP subprocess. Native parser checks are retained separately in
`tests/test_native_yaml_compatibility.py` and were not run during this restricted session.

Additional checks passed:

- `uv run ruff check .`
- `uv run mypy .` (62 source files, including the deferred native-parser test module)
- `uv run lint-imports` (all seven contracts)
- `uv run pre-commit run check-toml --all-files`
- `uv run pre-commit run check-yaml --all-files`
- `uv run pre-commit run check-merge-conflict --all-files`
- `git diff --check`
- Final relative-link/code-fence validation: 16 changed/new Markdown files, zero errors.
- A fresh-process generator probe created ten files inside a temporary directory and asserted
  that Torch, Ultralytics and ClearML were absent from `sys.modules`; cleanup completed.
- The lockfile diff adds only ruamel YAML and its C extension; external dependency references
  and submodule gitlinks are unchanged.

The aggregate pre-commit command and full pytest suite were not run because they include
native-runtime tests. This is not evidence of those checks passing.

## Review and convergence

Independent static review found three gaps: silent comparison-owned overrides, shared replay
manifests across distinct caches, and four prediction-only keys active in training YAML.
T022–T024 record the fixes. Each regression was observed failing before correction and passes
in the final focused command. Re-review returned **ship** with no remaining static blockers.
An additional mocked regression prevents provisional training YAML from creating the native
run directory and accidentally triggering run-name incrementation.

At this checkpoint T021 remained unchecked pending real-run authorization. No commits, pushes or release were performed.

## Initial authorization restriction

The user instructed: “not run work heavy tests until i say”. No heavy tests were run by the
documentation workflow. Native training, GPU inference, live ClearML artifact downloads,
full heavy integration and direct native replay were unverified at that checkpoint.


## Authorized full verification

The user subsequently instructed “you can run heavy tests” on 2026-09-28.

- `uv run pytest` passed: **335 passed**, with three existing deprecation warnings,
  before the fresh-process regression below was added.
- Real execution exposed missing Hydra registration in fresh CLI processes. Importing the
  central configuration module at the application boundary fixes it. All eight generated
  command subprocess regressions failed before the correction and passed afterward.
- `uv run pre-commit run --all-files` passed after that correction, including the full pytest,
  Ruff, mypy, import-linter and configured file checks. Independent review found no blockers.

The project end-to-end workflow then passed using a task-owned synthetic detection dataset,
one training epoch, image size 96, and explicit project/tags:

| Invocation | Outcome | Downloaded artifacts |
| --- | --- | ---: |
| Ground-truth ingest | Completed | 6 |
| CPU pipeline without an automatic baseline | Completed; comparison skipped appropriately | 84 |
| GPU pipeline with the completed CPU task as baseline | Completed; paired comparison and reports | 109 |
| Standalone validation | Completed; nondefault IoU threshold | 42 |
| Standalone comparison | Completed; continuous AP method | 48 |
| Standalone report | Completed | 9 |

All required-upload manifests were checked and every artifact was force-downloaded, with
file size and SHA-256 recorded. Downloaded native YAML and ClearML configuration objects
retained upstream comments and stage filtering. Retained prediction manifests were present.
Direct native Ultralytics training and prediction replay using the downloaded YAML both
passed. Each application invocation owned exactly one task; replay created no extra tasks.

Validation-calibrated thresholds stayed frozen for test. Baseline and candidate used identical
current-test image manifests and inference settings apart from owned model/output paths.
Baseline thresholds matched the original CPU validation artifact. No duplicate native model
uploads were registered.

Failure injection also passed: rejected artifact upload exited 1; SIGTERM exited 143. Both
real tasks ended failed and retained local diagnostics. Cleanup deleted the tagged project
and task-owned local directory, and confirmed zero remaining tagged projects/tasks. Detailed
machine-specific logs, task identities, artifact hashes and cleanup receipt are archived in
the environment skill's dated evidence, outside the repository.

T021 and T025 are complete. These runs verify CPU and a single GPU with a small synthetic
dataset; they do not establish model quality, performance at scale, or physical multi-GPU DDP.
At the completion of these verification runs, no commit, push or release was performed.
