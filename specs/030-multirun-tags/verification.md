# Multirun tag verification — 2026-10-14

## Planning and scope

Spec Kit specification, plan, task generation and consistency analysis cover FR-001
through FR-006 and all three success criteria. T004–T008 implement/test all six
requirements; T009–T011 cover documentation and architecture acceptance. No uncovered
requirement or unresolved design clarification was found. Architecture planning
validation exited 0 before implementation and after refining interpolation timing.
The installed workflow files and `.specify/` remain unchanged; feature paths were
resolved with `check-prerequisites.sh --json --paths-only` and an explicit feature directory.

Parent owns all repository writes. `inspect_multirun` independently reviewed launch
paths with no writes, confirming closure lifetime, queue snapshot persistence and the
existing remote replay boundary. Native delegation requested GPT-6.1 Sol/medium in a
fresh context; runtime model/effort settings are not exposed by the tool.

## Regression evidence

- Initial `pytest tests/test_multirun_tags.py -q --maxfail=2` failed twice because
  direct jobs had only user tags. After implementation, the focused multirun/sweep/
  session suite passed 160 tests.
- A saved `job-${hydra:job.num}` tag exposed premature queue interpolation. The
  dedicated regression failed at `tag_multirun_job` with an unset Hydra context.
  Applying tags inside `_resolved`, after installing that job's context, fixed it.
  Final multirun/sweep checks passed 30 tests, including that case.
- The initial full suite exposed uninitialized-Hydra access in the existing composed
  configuration tests. A focused reproduction failed in
  `test_file_resolver_sees_remote_inputs_and_derived_output`; the launch callback now
  checks context initialization before reading MULTIRUN mode. Final targeted results
  passed 177 tests across multirun tags, Hydra sweep configuration, ClearML sessions,
  configuration upload commands and publication commands. Full commit-hook outcomes
  are recorded below when available.
- Ruff passed. Strict mypy passed for 307 source files. Vulture passed.
- Import-linter passed all 43 contracts. Architecture tests passed 104 cases,
  including injected forbidden dependencies, direct-to-queue edges, SDK ownership,
  cycles and generated configuration targets. No import exceptions were added.
- Markdown structure, whitespace, balanced fences and 171 local links across the
  initial 12 changed Markdown files passed; `git diff --check` passed.

## Live ClearML task readback

The bounded `live_tag_check` agent ran a real `cy-ground-truth -m` with `seed=1,2`,
six synthetic YOLO images with empty-image examples, explicit project/user tags,
and a separate invocation workspace. Parent inspected the server-readback JSON and
cleanup output. Both tasks completed and published `gt_csv`:

| Task ID | Shared generated tag |
| --- | --- |
| `3b6843936f6a44618baab5951da4b9b0` | `multirun-049901318a0e44508104f07234e9f3de` |
| `6e717a3f40a74301a27ec50339b769ff` | `multirun-049901318a0e44508104f07234e9f3de` |

Fresh server reads found exactly one generated UUID4 tag on each task, with the
explicit harness and `user-multirun-verification` tags preserved. All owned projects,
tasks and invocation directories from three attempts were cleaned up; the final
tag-scoped listing was empty. Machine-specific commands/logs remain outside this
repository in the environment evidence.

Earlier attempts intermittently failed in the existing ClearML naming query:
`Task._query_tasks` received `res.response.tasks is None`. No unrelated SDK/naming
repair was made; the successful final attempt does not establish that issue is fixed.
This verifies task tagging and lightweight publication, not GPU training, remote
retagging, the complete detector acceptance matrix or real queue-worker execution.
Queued grouping is covered by actual snapshot composition/serialization and execution
configuration readback. Remote replay retains existing task metadata.

## Documentation review

Updated the Russian README, direct/queue guide, project contract summary and current
contract index. The feature contract and quickstart describe shared identity, ordinary
RUN preservation, fresh launches and frozen queued tags. Existing generated defaults,
publication inventory, environment recipes and native-training guidance need no change:
no configuration fields, artifact names, runtime dependencies or execution policy changed.

The generated changelog was refreshed with the repository release helper and inspected.
The local `pyproject.toml` source overrides and concurrently appearing untracked
`docs/cls-cls-pw-grid-search.md` are excluded from this task.
