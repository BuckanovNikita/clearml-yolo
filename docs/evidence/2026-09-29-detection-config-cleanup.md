# Detection configuration cleanup verification — 2026-09-29

Scope: [feature 007](../../specs/007-detection-config-cleanup/spec.md), building on the
committed FiftyOne implementation without dependency changes. Initial acceptance left the
work uncommitted; the user subsequently authorized a release commit and push.

## Repository verification

- Baseline `uv run --locked pytest -q`: 485 passed, 8 opt-in database tests skipped.
- Final `uv run --locked pytest -q`: 515 passed, 8 opt-in database tests skipped;
  four existing Hydra/Pydantic deprecation warnings.
- `uv run --locked ruff check .` and `uv run --locked mypy .` passed.
- `uv run --locked lint-imports`: all nine contracts passed.
- Real opt-in `tests/test_fiftyone_publisher.py`: 8 passed against isolated MongoDB;
  upstream FiftyOne/MongoEngine deprecation warnings remain.
- Changed/new-file pre-commit checks for file sizes, conflict markers, final newlines
  and trailing whitespace passed. TOML/YAML hooks had no changed applicable files.
  Generated YAML composition is covered by pytest and a fresh cy-init-config invocation.
- Local links and whitespace in changed/new Markdown were validated; `git diff --check`
  passed. Dependency manifests, lockfile and both Git submodule revisions are unchanged.

Regression tests first reproduced independent-device/default-split and example-layout
failures, missing task-identity helpers, and omitted required plots. Exact payload tests
resolve stable source indices rather than assuming split-local positions. Zero-prediction
fixtures retain all 13 artifacts for each split; missing/empty inputs fail clearly.
A rejected evaluation upload fails the owner and preserves the local payload/dashboard.

Spec Kit specification, clarification, design, tasks and read-only consistency analysis
covered all ten functional requirements and four success criteria, with no unresolved
material ambiguity or constitution conflict. Implementation preserves complete Hydra
composition and runtime records while changing only example presentation.

The independent read-only review found a project-name collision with the runs/latest
shortcut and requested confirmation of renamed-task training paths. Both were reproduced
with regression tests and fixed: latest is encoded as a reserved component, and implicit
native training names use active task identity. The final suite above includes both fixes.

## Real CPU execution and artifact downloads

The isolated workflow used eight synthetic images across train/val/test, including one
background image per split, and one native CPU training epoch. Commands selected CPU
explicitly for both independent devices. Outputs used implicit task-derived roots.

| Invocation | Outcome | Downloaded artifacts | Split inventory | Publication |
| --- | --- | ---: | --- | --- |
| Initial pipeline, no baseline | Completed | 104 | 13 each: train/val/test | One receipt, new dataset |
| Second pipeline, automatic prod baseline | Completed | 113 | 13 each: train/val/test | One receipt, reused dataset |
| Standalone metrics | Completed | 46 | 13 each: train/val/test | One receipt, reused dataset |
| Explicit test-only metrics | Completed | 20 | 13 for test | One receipt, reused dataset |
| Metrics, publication disabled | Completed | 45 | 13 each: train/val/test | None |
| Standalone validation | Completed | 60 | 13 each: train/val/test | None |
| Standalone prediction | Completed | 15 | Outside metric parity | One receipt, reused dataset |
| Injected evaluation upload rejection | Failed as expected | Not a success gate | Local outputs retained | None |
| Injected evaluation interruption | Failed as expected | Not a success gate | Local outputs retained | None |

Every successful task's required-artifact manifest was checked and all its artifacts were
force-downloaded. Split artifact kinds/counts matched after suffix removal; thresholds
were identical across train/val/test. Evaluation JSON retained schema version 1 and exact
matching references, labels and confidence. Saved FiftyOne detections were checked against
payload statuses and full matching records, including indices and IoUs, for every split.

Each command had one task. Pipeline publication produced one receipt under its root and
no nested receipts. Every receipt payload path existed. Standalone metrics receipts lived
under the task root's metrics directory; prediction receipts lived under its owner root.
Dataset identity was reused across distinct roots and task namespaces. cy-val produced all
39 split artifacts without publication.

The comparison used the same two current test images. Candidate and baseline thresholds
matched their exact stored maps; developer/business reports remained test-only. Effective
training/prediction YAML retained actual data, project, name, mode, checkpoint and source
manifest values, and the source/checkpoint paths existed.

## Scope and limitations

Initial feature verification used CPU. The release follow-up below adds single-GPU
training and evaluation evidence. Automatic GPU selection, compilation and physical
multi-GPU execution were not exercised. The real database required an explicit task-owned MongoDB URI;
this run does not verify the bundled database executable on every installation.

Full command logs, task identifiers, artifact receipts and reproducible live-run scripts
are archived with the global environment skill, outside the repository. Task-owned ClearML,
FiftyOne, temporary database and synthetic run resources were cleaned up after inspection;
pre-existing shared services and data remain intact.

## Release follow-up

On the user's subsequent release request, one native single-GPU training epoch and
post-training train/val/test inference/evaluation completed with explicit device 0 and
compilation disabled. All 79 artifacts were force-downloaded; the 39 split artifacts
were present and thresholds matched across all splits. This isolated check disabled
FiftyOne publication; real publication evidence remains the earlier CPU/database runs.
The tagged project/tasks and synthetic GPU run outputs were removed after verification.

Release checks and final-version wheel/source installation evidence are archived in the
global environment skill's dated release record. The release workflow changes only the
root project version in pyproject.toml and uv.lock; dependency pins remain unchanged.
