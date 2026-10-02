# Verification: current-only contracts

**Date**: 2026-10-02

**Scope**: [specification](spec.md), [plan](plan.md), [tasks](tasks.md).

## Repository gates

All commands used the existing locked environment with `uv run --locked --no-sync`.

| Check | Observed result |
|---|---|
| Full `pytest -q`, after the final source change | 745 passed, 9 skipped; 4 upstream hydra-zen/Pydantic deprecation warnings |
| `ruff check .` | Passed |
| `mypy .` | Passed; 94 source files |
| `lint-imports` | 9 contracts kept, 0 broken |
| `git diff --check` | Passed |
| Global environment helper tests | 30 passed; fake infrastructure only |

Rejection tests were observed failing before implementation, then passing. These cover missing
CSV input, required prepared result paths, historical-only recovery, unknown native settings,
canonical cache selection and the comparison evaluation schema. A final regression first failed
on native-dataset-specific path injection in resolved configurations, then passed after removing
that branch. Current CSV preparation, replay, both formats and native publication remain covered.

No dependency pins, submodule checkouts, lockfile or protected workflow files changed apart from
the explicitly authorized constitution amendment. Existing local dependency-source overrides
were preserved. No commit or release hooks ran; release hooks would mutate unrelated files.

## Real native execution and recovery

The fixture had disjoint train/validation/test images, one class and valid background rows.
Six actual ClearML invocations completed:

| Invocation | Acceptance evidence |
|---|---|
| CPU baseline pipeline | CSV-backed NDJSON training; absent automatic baseline skipped comparison |
| Single-GPU candidate pipeline | Reused the CSV cache, compared the current test split, produced reports |
| Standalone CPU training | Flat dataset format and current native Output Model publication |
| Standalone validation | Current task-backed weights, validation calibration and evaluation |
| Standalone comparison | Current task references and `evaluation.iou_threshold=0.3`, `evaluation.matching_strategy=greedy` |
| Standalone report | Consumed the paired comparison output and produced both reports |

All existing artifacts of these tasks were force-downloaded and verified as files. Each of the
three training tasks had one best-role Output Model; downloaded checkpoints loaded with the
expected class names. Current readers recovered the exact validation thresholds before and
after comparison; both baseline and candidate maps remained `{"box": 0.0123361004516482}`.
Repeated NDJSON training preserved cached image/NDJSON/YAML file sizes and modification times;
source image SHA-256 values were unchanged.

Nine evaluation workbooks had exactly `summary`, `per_class`, `confusion_matrix` and all four
named CSV sidecars. Both paired comparison workbooks had only `Сравнение` with excluded-class
and methodology sidecars; their manifests referenced existing paired files on `test`. The
skipped-baseline candidate workbook had `Classes` and `Summary` with its sidecars.
All nine command helps succeeded. An actual standalone training command supplied native data
without ground truth and failed with `MissingMandatoryValue` before a ClearML task was created.

Two initial acceptance-harness lookups used an incorrect comparison directory/task-name shape.
The application commands had completed; the harness was corrected and reused those completed
tasks. They were not counted as repeated execution. Machine-specific scripts, logs, receipts,
generated examples and cleanup evidence are archived in the global environment skill.

Tag-scoped cleanup removed the test project and its six tasks; the helper then reported zero
matching projects/tasks and removed the owned workspace. Four exact global cache downloads were
identified from these tasks' publication URLs and removed. Pre-existing data/services were preserved.

## Documentation and limits

README, maintained contracts, active specifications/quickstarts, constitution and project/global
integration guidance were synchronized. Three migration guides were removed, and incoming local
links were repaired; dated history uses supersession notes or archived version links.
Changed Markdown parses, fences/whitespace and relative file targets were checked. Generated
examples were exercised by the native invocations and configuration composition tests.
The final documentation scan passed for 48 changed Markdown files, 163 relative file links
and both referenced Markdown heading anchors. Both changed global guidance files also parse.

The nine skipped tests require optional live FiftyOne persistence. Physical multi-GPU/DDP,
fresh wheel/source-distribution installation, live service outages and live injected upload/flush/
interruption failures were not exercised. Existing mocked failure-path tests passed; they do not
establish those live outcomes. `mdformat --check` flags 13 touched documents which also fail at
the baseline revision; Markdown syntax and relative file-link checks passed. Remote archived
links were not fetched. Token/cost telemetry is unavailable for parent and delegated calls.

## Acceptance

Parent inspected the combined change set and mapped FR-001–FR-009 to implementation and evidence.
Spec Kit convergence found no remaining implementation work across nine requirements, four success
criteria, seven acceptance scenarios, six design decisions and the five core constitution principles
plus applicable operational constraints. No convergence tasks were appended; the existing review
gate was completed separately.

The fresh read-only `final_review` agent returned **ship**, with no findings, after inspecting
the complete diff, feature artifacts, current contracts and recorded native evidence. Its targeted
critical suite passed with 223 tests and the same upstream warnings; `git diff --check` also passed.
Requested model/effort was `gpt-5.6-sol` / `high`; runtime model/effort were unobservable.

## Commit-readiness pass

The user subsequently authorized a full Spec Kit completion pass, commit and push. Existing
specification, clarification decisions, plan, tasks, implementation and dated native evidence
were reused. Analysis confirmed coverage of all nine requirements and four success criteria;
convergence and an independent audit checked the implementation and constitution again.

The all-file `pre-commit run --all-files --verbose` gate passed after correcting the parent
runner environment: 745 tests passed, 9 optional tests were skipped and the same four upstream
warnings remained. Large-file, merge-conflict, TOML, YAML, newline, whitespace, changelog, Ruff,
mypy and import-linter hooks all passed. The initial runner exported `UV_LOCKED=1`, which prevented
release fixtures from creating their own lockfiles; removing that inherited setting reproduced
the resolution in an isolated probe and the original fixture before the full successful retry.
No application or test source change was required.

The entire local dependency-source block was removed for hooks, omitted from the staged
`pyproject.toml`, then restored exactly and unstaged. Lockfile, dependency revisions and protected
workflow state remain unchanged. At this verification checkpoint, no commit or push had occurred.

The hidden-inclusive documentation audit found one additional broken link in the historical
`.specify/bugs/excel-match-export/test.md` report to the deleted evaluation migration guide.
T011 tracks its one-line archived-link repair. The user's subsequent instruction to finish
authorizes the proposed exception; the link now targets the same guide at the immutable baseline
commit. The report's historical findings are preserved. Fresh documentation validation passed
for 49 changed Markdown files and 171 relative file links. The fresh `commit_acceptance` reviewer
returned **ship** with no findings, closing T011. Its first dispatch failed at model capacity;
the retry completed. Requested model/effort was `gpt-5.6-sol` / `high`, runtime settings and
token/cost telemetry were unobservable. The real commit hooks and push follow this checkpoint.
