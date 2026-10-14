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
  are recorded below.
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

## Release acceptance

The source commit `e248cc266f61b0d5898ce5f0a01e09fbe5417f44` and automatic version
commit `05aa05ca61d615540a7fb17cbf63abba21c5e8f4` passed their applicable hooks,
including full pytest, Ruff, mypy, import-linter and Vulture. The initial full suite
had 10 failures in composed configuration/publication tests before the initialized
Hydra guard; those paths passed in the final focused suite and checked commits.
Hook output reports success without a test count, so no final full-suite count is inferred.
The [independent review](independent-review.md) accepted the final implementation.

The first commit attempt could not resolve the private dependency after temporary
removal of local source overrides. The successful retry used `UV_NO_SYNC=true` to
run every normal hook against the existing verified dependency environment without
resolving or updating dependencies. No hooks were bypassed. The entire original local
source section was preserved and restored unstaged after both attempts, including
the nested version commit. Committed project and lockfile metadata changed only the
root version from 0.27.0 to 0.28.0; dependency sources and revisions are unchanged.

Annotated tag `v0.28.0` points to the version commit above. Its tree
`58cb5f50a63d4e2bc1fc4a469853ca869a8b3cca` exactly matches the immutable tree used
for packaging verification. The parent compared the three runtime module hashes
and regression-test hash against the independently reviewed files; all matched.
The branch and tag were pushed explicitly. Remote readback confirmed the version
commit on `master` and as the peeled tag, with annotated tag object
`438a4ae5bffdc54ccf22ecca9634b23510ac18f3`. No GitHub Release, package publication
or asset upload was performed.

## Installed distributions

The bounded packaging agent built a wheel and source distribution from that immutable
tree outside the working checkout, installed each into a separate environment and
confirmed version 0.28.0 and exact content of all 174 package files. Each installation
passed 101 command checks, including all 12 command help entries, 42 configuration
cases, export inventories, overwrite/preservation behavior and invalid-family rejection.
Each also passed all 14 multirun regression tests copied unchanged from the tree,
with the repository fixtures. The parent checked every expected command exit, both
test-log summaries and both artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| `clearml_yolo-0.28.0-py3-none-any.whl` | `b3c246a39e6b2c9fde2798ee124181aaf1ce028cd5eee07cde801db5f5f763cb` |
| `clearml_yolo-0.28.0.tar.gz` | `38417f939f04e0b3c80c88c91a9a38b64eedd2bfbb02e721711ab1bb8f0b2183` |

The fresh package environments explicitly reused the verified development environment's
dependency site-packages. This establishes package installation/content and installed
entrypoint behavior, not fresh dependency resolution. Initial harness destination and
fixture mistakes were corrected before the passing checks. No package-check process
remains running; review artifacts and logs were retained outside the repository.

Final acceptance reconciled the architecture record with the actual release diff.
The subsequent status/evidence updates affect documentation only, with no import,
interface, dependency or effect changes. Final Markdown structure, whitespace, balanced
fences and 172 local link targets passed across 15 task-owned Markdown files. The
architecture acceptance validator and `git diff --check` passed. These checks cover
the evidence updates; unrelated application tests need no further rerun.
