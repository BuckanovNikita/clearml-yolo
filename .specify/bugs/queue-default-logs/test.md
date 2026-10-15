# Bug Verification: Default queue worker diagnostics

- **Slug**: queue-default-logs (from assessment/fix context)
- **Tested**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified — original failure path, required checks and Git-tag delivery completed.

## Original failure path

A real empty-queue worker registered and exited on SIGTERM with no stderr before
implementation; the new default-output regression failed on that empty string.
After implementation the same subprocess path emits startup/root, immediate idle
heartbeat and orderly shutdown, exits zero, clears its registration and leaves
stdout empty. DEBUG exposes polling; WARNING suppresses routine output.

## Executed checks

Commands used the existing prepared Python 3.12.13 environment with uv no-sync and
this checkout's source import path. No dependency resolution or upstream changes.

| Check | Result |
| --- | --- |
| Initial focused queue commands/service/logging | 48 passed; four existing Hydra/Pydantic deprecation warnings. |
| Final `pytest tests/test_queue_logging.py -q` | 7 passed; real CLI, waiting through storage, deduplication/heartbeat, redaction, historical completion and failed-worker cleanup. |
| `uv run --frozen --no-sync lint-imports` | 43 contracts kept, zero broken. |
| `uv run --frozen --no-sync pytest tests/test_architecture.py` | 104 passed; includes injected forbidden logging/adapter edges and dynamic/initializer checks. |
| Ruff / Vulture | Passed. |
| Mypy | Passed, 318 checked files; first test-only re-export error corrected and rerun. |
| `uv build --no-sources` | Source distribution and wheel built successfully with uv_build; unpublished. |
| Actual `cy-queue worker --help` | Correct INFO default and DEBUG/INFO/WARNING/ERROR choices. |
| Markdownlint 0.41.1 | Five changed/new Markdown documents passed with MD013 disabled for existing prose/table style. |
| Local Markdown links/anchors | Five files: 33 valid local targets/anchors. |
| `git diff --check` | Passed. |
| `uv run pre-commit run --all-files` | Full pytest hook passed, along with Ruff, imports, Vulture and file hygiene. The wrapper initially exited 1 for expected generated changelog changes and the test typing issue; the latter passed on rerun, and changelog output was reviewed for staging. |

## Documentation and review

Companion corp-skills source started at `e5c6512`, version 0.2.2; its documentation
release v0.2.3 was published as `a94cd2d0303117c3df2844f1a8c0fa73799bcb21`.
Remote main and the annotated tag (object `4df86c609b14734297f84c69bc93d9d1c028bcf0`)
were independently verified at that commit. Its usage/evaluation references document the actual CLI and child log
location. Metadata, discovery, Markdown and packaged links were checked. Fresh
baseline evaluation exposed the previous gaps. Fresh independent reviewer `/root/final_review` returned **ship** after inspecting
the complete application and companion diffs, module contracts, source behavior
and recorded passing checks. The updated explanation-only usage prompt passed:
INFO/idle/waiting/DEBUG and the exact child log path were retrieved without
starting workloads. The reviewer identified one record reconciliation detail:
`core.redaction` is now included in the CLI allowed dependencies. The parent subsequently observed the full pytest hook pass and completed the
native commit and release gates. Requested reviewer settings were GPT-6.1 Sol,
high effort; actual runtime model settings are not exposed.

The queue application remains free of Loguru and concrete infrastructure. Its
optional callback receives public QueueView values; the CLI owns rendering and
log policy. Storage/process effects, GPU policy, persisted records, TUI and stdout
formats remain unchanged. Final reconciliation covers the two production modules, new logging tests, README,
queue guide, bug artifacts and native generated changelog. No dependency or
composition-target changes were introduced. The record explicitly includes the
redaction dependency identified during review. All planned implementation, check
and documentation tasks are complete; Git delivery remains separate.

## Scope and limitations

This is logging acceptance, not GPU training or remote ClearML acceptance. The
real idle worker and local queue/process tests do not establish new GPU or upload
outcomes. Existing upstream deprecation warnings are retained. No services or
pre-existing jobs were stopped. Only task-owned subprocesses were terminated.

## Delivery

The initial source commit `87cbe27bc461a0f31b4e7df3ac19db3c7c64b107` passed all native
hooks: 2,511 tests passed, 30 skipped, no failures/errors (630.652 seconds). The
concurrent compatibility task published v0.30.0 while these checks ran. The fix
was rebased onto that checked release as
`d817adda23cad20a1a62df732042314efeab8dc2`. Only generated CHANGELOG content conflicted;
retaining the newer release's generated history resolved it. Production modules
and regression tests are byte-identical to the independently reviewed source.

The integrated baseline supports Python `>=3.12.13,<3.14` and uses `uv_build`.
These compatibility changes belong to v0.30.0, not this patch. One rebase-triggered
post-commit invocation selected an empty default environment and failed to import
Loguru. The contributor commit remained valid. The documented manual release retry
used the prepared environment without dependency resolution and completed normally.

Native release commit `e4a7a735fd51cf038347e760bffd949f35f02908` passed all required
hooks, including 2,511 tests passed, 30 skipped and zero failures/errors (617.221
seconds). It changes only the application version token in pyproject.toml/uv.lock,
plus the generated changelog. No dependency revisions changed relative to v0.30.0.
The annotated `v0.30.1` tag object is `067ce7403c4f2501c72988fadadc959f9450aba3`.

Both distribution formats built. A separate temporary environment installed the
0.30.1 wheel without dependencies and reused the prepared dependency packages.
Outside the checkout, with its source import override removed, the installed
command reported the new help and ran a real empty-queue worker: INFO startup,
immediate idle heartbeat, SIGTERM shutdown, zero stdout, exit zero and registration
cleanup. This tests the installed application artifact, not a fresh dependency
resolution. The temporary environment was task-owned; user installations were not
upgraded.

A documentation-only merge `8a4932304caed060e5e0c4cc63eacb77c8220fca` retained the
concurrent compatibility delivery record (`eda01e3`) without changing the tested
application, tests, pyproject or lockfile. Its native hooks completed; application
hooks correctly had no matching files. Eight affected Markdown documents passed
lint. An atomic push published master and v0.30.1, and remote master, annotated tag
and peeled commit matched the local refs above. This final evidence commit follows
the documentation-only native workflow; its tip is reported in the handoff.

The original main checkout's unrelated work and local dependency configuration
remain preserved. No registry publishing, GitHub Release, asset upload or skill
installation was performed.
