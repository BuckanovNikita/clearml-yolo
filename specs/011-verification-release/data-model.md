# Data Model: Verification and Release Workflow

| Entity | Fields | Rules / transitions |
|---|---|---|
| Verification stage | name, inputs, outcome ∈ {passed, failed, deferred, waived, error} | Outcome comes from the executed command's exit status; never from cached freshness. `deferred` blocks acceptance/integration/release; `waived` never blocks. |
| Preflight result | status ∈ {AVAILABLE=0, UNAVAILABLE=3, ERROR=1} | Bounded by `CY_INFRA_CHECK_TIMEOUT`; creates nothing. |
| Run tag | value, owner worktree, file `tests/integration/.run-tag` | none → active (`up`) → stopped (`stop`, exact-tag cleanup, empty listing proves cleanup). An active tag blocks a new run. |
| Release lock | `<git-common-dir>/clearml-yolo-release.lock` (flock) | Held from fast-forward through tag/push; held lock is a reported blocker. |
| Version commit | subject `chore(release): X.Y.Z`; paths ⊆ {pyproject.toml, uv.lock, CHANGELOG.md} | Only root `clearml-yolo` lock entry's version may differ from HEAD. |
| Coverage floor | `[tool.coverage.report] fail_under` | Set from measured value at adoption; only raised later. |
| Paired evidence | CY SHA+version, queue SHA+version, queue location | Missing checkout or metadata mismatch → error. |
