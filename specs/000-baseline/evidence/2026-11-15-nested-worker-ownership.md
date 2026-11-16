# Nested training worker ownership — 2026-11-15

Ticket: [95: Preserve ownership across nested training supervisors](../../../.scratch/verification-gap-closure/issues/95-preserve-nested-worker-ownership.md).
This routine bug fix preserves the existing process-ownership contract; no new configuration or operational
policy is introduced. Coordinator acceptance, full coverage, final gate and commit remain separate.

## Reproduction and correction

The outer `run_workers` starts a child that calls `run_workers` again. The inner worker starts a detached
leaf; both ignore SIGTERM. An unrelated sibling exists before outer supervision begins. Both supervisors
previously assigned the same `CY_TRAINING_WORKER_OWNER` variable, so the inner assignment erased the outer
ownership marker. Cancellation stopped the direct worker but could leave detached descendants whose ownership
the outer scope could no longer prove safely. The conservative scope raised `UnverifiableProcessTreeError`.

The [original discovery](../../014-estimated-batch-acceptance/evidence/2026-11-15-nested-workers-initial.txt)
and [saved reproducer](../../014-estimated-batch-acceptance/evidence/2026-11-15-nested-workers-reproducer.py.txt)
remain available. The new product regression independently reproduced the failure before implementation:
one exception-cancellation case failed in 10.52 seconds. Its own token-restricted pidfd cleanup removed and
reaped the test descendants, and only the test's finalizer terminated its unrelated sibling.

`run_workers` now creates one fresh owner environment key per invocation. Each rank gets its own existing
token as that key's value. Nested supervisors inherit the ancestor keys rather than overwriting them, so
the outer `ScopedProcessTree` retains positive ownership after detachment/reparenting. The legacy variable
is still assigned exactly as before. Parent environment, signatures and result schemas are unchanged.
Birth checks, pidfd signalling, scoped discovery and conservative cleanup errors are unchanged; no new
numeric-ancestry adoption or broad signalling was added.

The regression's readiness barrier waits until the detached leaf has installed its stubborn signal handler
before triggering timeout or cancellation. It checks disappearance of the outer, inner and detached PIDs,
and survival of the unrelated sibling, for ordinary exceptions, KeyboardInterrupt and timeout.

## Selected verification

Base for the isolated mutation snapshot: `5dda250c56a074f1dd174783e4d71025f673083a`.
Original workers source SHA-256: `12a2811f2aafe5b5e873405a026880c67af5e8b4e45cfb47f49c9263cb6df101`.
Reviewed workers source SHA-256: `739f865e2fc6a7d289602348000b71ff226f42d8574af9ca88d8e2b3dae98609`.
New regression SHA-256: `c814fc0a06b31cb91de683afc2c54033164abe5ffa3d87133774b1b86a6b80b3`.

| Check | Outcome | Evidence |
| --- | --- | --- |
| New exception-cancellation regression against original source | failed as expected | Real ownership error reproduced; no GPU launched |
| New exception, interrupt and timeout regressions after correction | passed | 3 cases, 6.96 seconds |
| New regressions plus existing training workers, independent pool and harness nesting | passed | 28 cases, 27.76 seconds |
| Ruff lint and formatting check for owned source/test files | passed | No automatic edits required |
| Focused mypy for owned source/test files | passed | No issues in two files |
| Task-owned diff whitespace check | passed | No errors |
| Fresh independent review after focused verification | passed | Coordinator relayed no blockers and recommendation to accept after remaining gates |
| Bounded native mutation report | passed (report), limitations below | One changed function, one child, 120-second budget; 88 mutants, 47 killed, 41 survived, zero unreached/unrun |

The focused command was `uv run --locked pytest -o addopts='' -n 0 tests/test_nested_training_workers.py
tests/test_training_workers.py tests/test_worker_pool.py tests/test_nested_worker_cleanup.py`. It establishes
real CPU process cleanup, normal/failing worker behavior and pool composition, without GPU or service claims.
The existing legacy-marker observation also remained covered. No global coverage floor is inferred from it.

The coordinator authorized a unique `GIT_INDEX_FILE` containing the captured HEAD plus only this worker source
and new regression. The shared index is untouched. The native mutation driver exports that snapshot into its
own disposable workspace. Default mutation selection excludes `process_capabilities`, including these new
real-process cases; the live regression evidence above is therefore separate. The original red reproduction
also observes the exact behavior of replacing the new per-invocation key with the fixed legacy key; another
equivalent expensive red run is unnecessary.

## Mutation review and resource disposition

The native command was `uv run --locked task --exit-code mutation -- --base
5dda250c56a074f1dd174783e4d71025f673083a --max-functions 1 --max-children 1
--budget-seconds 120`. It exited zero in 93.36 seconds. Its clean baseline and forced-failure
check passed. Testmon selected five entries: `test_batch_probe.py`, the excluded new nested
regression module, `test_training_workers.py::test_failure_kills_peer_and_next_trial_succeeds`,
`test_worker_pool.py`, and `test_worker_targets.py`. Thus the report did not run every existing
worker test. Only `run_workers` was selected; generated mutants in other functions were outside
this report, not additional survivors. No mutation configuration or exclusion was changed.

All 41 survivor diffs were regenerated from the frozen source using the installed mutmut generator,
without executing tests or editing product code. Numbers below refer to `x_run_workers__mutmut_N`.

| Survivor IDs | Disposition |
| --- | --- |
| 6–9, 14–17, 81–83 | Diagnostic text changes; exact presentation is not the ownership contract. No production change justified. |
| 1, 4, 10 | Unchanged input-validation branches; the selected successful-command test does not establish invalid-input rejection. Selection gap, not equivalence. |
| 22, 24, 26, 28, 36–38, 42–44 | Unchanged directory creation and log/stdin routing; selected test does not establish nested-directory creation or complete IO routing. Selection gaps. |
| 35, 41 | Remove the child environment, including ownership markers and command environment. Behavior-changing; real nested process tests are excluded from this mutation run. Not declared equivalent or killed. |
| 39, 45, 50, 53, 54, 56, 60 | Remove session isolation or corrupt process/tree ownership arguments. Behavior-changing, with process-capability coverage excluded. The original fixed-key red proof specifically establishes why ownership composition matters; it is not a claim that these distinct generated mutants were executed. |
| 63, 65 | Remove ownership information or the monitor callback from the await call. Selected no-monitor failure test misses this behavior; separate real cancellation regressions exercise monitor-driven cancellation. Not declared killed. |
| 71, 76–80 | Unchanged simultaneous primary/cleanup-error preservation branch; selected test does not reach that combination. Selection gap, not equivalence. |

The generated f-string key has no direct mutmut replacement in this report. The pre-fix real-process
failure and post-fix three-case pass are the direct observation for fixed-key versus per-invocation-key
ownership. Survivor counts are advisory evidence with these explicit limits, not a claim of full mutation
coverage. No further tests were started after machine tool calls stalled; the coordinator requested
preserving the existing bounded report and red proof instead of adding jobs during that interruption.

Logs and the isolation manifest are retained in `.tmp/ticket95/`: `red.log`, `green.log`, `focused.log`,
`types.log`, `mutation.log`, `mutation-selection.json`, and `survivor-diffs.txt`. The native driver removed
its exported workspace, and the launcher removed its unique temporary index and lock in `finally`.
Real-process fixtures ran token-restricted fallback cleanup, and no task-owned GPU or service was started.
These small retained logs are evidence, not disposable model/cache data. Final coordinator checks and
commit remain pending; the source and new test are frozen at the hashes recorded above.

On 2026-11-16 the coordinator identified a WSL restart. Completed mutation and focused checks above
preceded the interruption and remain retained evidence. Subsequent read-only shell calls were interrupted;
they establish no additional verification. Coordinator full coverage was interrupted with exit 143 and
remains pending. No supplemental mutation test was started. The resumed coordinator owns the final gate.

No product changes outside `adapters/runtime/workers.py` belong to this ticket. The neighboring acceptance
harness and its independent-pool cleanup test are owned by ticket 03. No GPU, service, dependency, user cache,
release or push action was performed.

Coordinator acceptance on 2026-11-16: the full unit baseline passed (4,766 passed,
one skipped; 84.67% coverage), and the canonical automatic gate passed on integrated
content `7c8f694`. The reviewed worker implementation was unchanged. Commit `e1fe64e`
was fast-forwarded to local `master` after byte-identity checks, preserving unrelated
pending work. Ticket 95 is accepted; no push or release occurred.
