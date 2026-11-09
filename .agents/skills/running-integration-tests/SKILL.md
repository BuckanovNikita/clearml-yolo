---
name: running-integration-tests
description: Run clearml-yolo live tests (tests/integration) through Task with bounded preflight, explicit deferral, one run tag and exact-tag cleanup on the shared ClearML stand. Use for integration or acceptance runs, the CPU stand smoke test, GPU or FiftyOne live suites, blocked setup, assertion failures, credential or TLS errors, an active .run-tag, or cleanup leftovers.
---

# Run clearml-yolo live tests

Live tests use the shared ClearML stand owned by the `k8s-infra` skill; read its
`references/run-contract.md` before touching the stand. Credentials come from the
k8s-infra project helpers, never from a file. `clearml-yolo-environment` explains this
machine's endpoints, 401 and TLS failures; this skill never deploys, restarts or stops
the stand.

Live tests are ordinary pytest tests under `tests/integration`. Development verification
and affected-test runs exclude that directory. `tests/conftest.py` marks them
`integration` and puts them in the `live` xdist group, so one worker runs them serially
while unit tests stay parallel; keep `--dist loadgroup`. Stand tests request the session
fixture `live_run` (`tests/integration/conftest.py`) explicitly: it prepares the run tag
through `tests/integration/lifecycle.py`, exports the stand environment, and stops the
run after the last test, failing the session when cleanup is incomplete. The FiftyOne
native-database tests in `tests/integration/fiftyone` run outside that fixture.
HOME-dependent locations (k8s-infra skill, weights cache, fonts) come from the real
environment saved in `CY_REAL_ENV`, because tests run under an isolated HOME.

```bash
uv run --frozen --no-sync task --exit-code infra-check         # read-only preflight
uv run --frozen --no-sync task --exit-code integration         # non-GPU live tests, CPU smoke
uv run --frozen --no-sync task --exit-code acceptance          # change acceptance
uv run --frozen --no-sync task --exit-code release-acceptance  # + GPU, FiftyOne, paired check
```

`L` abbreviates `uv run --frozen --no-sync python -m tests.integration.lifecycle` for
manual operations:

```bash
L check           # bounded availability check; creates no tag or resources
L up              # mint or adopt the run tag and record it in tests/integration/.run-tag
eval "$(L env)"   # export the run's stand variables for manual tools
L stop            # exact-tag cleanup, then release the tag (also the crash cleanup)
```

The k8s-infra helpers are not on `PATH`. The lifecycle resolves them from
`K8S_INFRA_SKILL_DIR`, else the installed k8s-infra skill under `~/.agents/skills` or
`~/.claude/skills`.

## Preflight and deferral

`infra-check` checks the stand's availability and capacity (`infra.py room`) and the
project's ClearML access, bounded by `CY_INFRA_CHECK_TIMEOUT` (60 seconds by default).

| Result | Exit | Action |
| --- | --- | --- |
| AVAILABLE | 0 | Live verification may start. |
| UNAVAILABLE | 3 | Outage, timeout or capacity wait: defer live verification. |
| ERROR | 1 | Diagnose credentials, TLS trust, configuration or an unexpected failure. |
| interrupted | 130 | Not a result; rerun. |

An availability result is not a test result. Losing availability during setup is blocked
setup; assertion failures after setup are test failures. For errors, keep TLS
verification and HTTPS as they are and diagnose with `clearml-yolo-environment`.

When unavailable, report the reason and the deferred checks, continue independent work
and retry at a meaningful milestone or after restored availability, without polling. A
GPU busy with the user's workload (reported by pcboard where available) defers the GPU
suites the same way. Multi-GPU DDP on a single-GPU host is waived and never blocks.
Deferred verification blocks acceptance, integration and release; when only blocked
checks remain, stop and ask for the user's decision.

For a focused selector, run `infra-check` first, then pytest on the selected
`tests/integration` path with `--dist loadgroup`; an ad hoc run is not acceptance.

## Rules

- **One run, one tag.** The lifecycle uses `INFRA_RUN_TAG` when exported, else the tag in
  `tests/integration/.run-tag`, else mints one with
  `infra.py newtag --project clearml-yolo --slug integration`. Every created ClearML
  project and task carries that tag in its name and tags. Outside Claude Code, export
  `INFRA_HARNESS=codex|ci|human` before minting.
- **An active `.run-tag` blocks a fresh run** in this worktree. After a crash, run
  `L stop`, or adopt the tag with `INFRA_RUN_TAG`. Never act on another run's tag.
- **Exact-tag cleanup.** `L stop` runs `clearml.py cleanup --prefix <tag>` and proves it
  with an empty `clearml.py ls --prefix <tag>`; only then is the tag released. Never
  broaden the selector, and run `cleanup --stale` only with `--dry-run`.
- **Concurrency.** Different tags never share objects. Respect the stand capacity that
  `room` reports; serialize runs from several worktrees beyond it.
- GPU suites take their `--run-*` options from `CY_DDP_ARGS` and `CY_SEVERSTAL_ARGS`;
  `release-acceptance` passes them through and runs the FiftyOne tests with
  `CY_TEST_FIFTYONE=1`. Supply the GPU options from [the DDP procedure](../../../docs/ddp-testing.md)
  and `pytest --help` ("native Severstal acceptance").
- The real-run gate (CPU and a single GPU) belongs to `running-end-to-end-tests`; these
  tests do not replace it.

## Completion evidence

Report the run tag, the selector, the pytest result and the cleanup proof. Distinguish
passed tests, failures, deferred, waived and error outcomes and incomplete cleanup. After
a failed or interrupted setup, clean owned resources with the exact tag and report what
may remain plus the same-tag `L stop` retry. Keep `.run-tag` while cleanup is incomplete.
A successful preflight without executed live tests is not acceptance.
