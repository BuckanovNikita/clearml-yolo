# Configurable GPU memory availability — 2026-10-12

The user requested GPUs below 2 GiB used memory to qualify as free and a project-level
override. The amendment implements `autogpu.max_used_memory_gib`, default 2.0.
Equality is busy. Total memory includes all processes and driver allocations.

## Evidence

- Before implementation, inventory/default/custom-setting regressions failed under
  process-based detection. A separate regression demonstrated a permissive follower
  incorrectly admitting another project's stricter pending head.
- After integration, the affected inventory, settings, queue, direct execution,
  supervision, launcher, model replay, scheduling and config-export selection passed
  332 tests. A subsequent targeted regression selected three visible devices using
  the supplied 1215/3/409 MiB values, with process queries forbidden by the fake.
- Ruff passed. Strict mypy reported no issues in 278 source files. Import-linter kept
  all 40 contracts. Changed Markdown parsed, 172 local link targets existed and
  `git diff --check` passed before this evidence file was added.
- `cy-init-config` exported `autogpu.max_used_memory_gib: 2.0`. Composition tests
  accepted a fractional override for every model command and export, while rejecting
  nonpositive/nonfinite/nonnumeric limits. Direct waiting, both queued modes, worker
  contraction and replay protection have regression coverage.
- A read-only real NVML probe classified the same occupied device as busy at the
  default and free under a higher configured limit. No GPU workload was started.
- Wheel and source distribution builds passed offline without source overrides;
  the wheel contains the new control and NVML memory probe. A custom 0.5 GiB value
  saved in exported project YAML composed successfully. Final documentation checking
  parsed the changed Markdown and verified 178 local link targets.
- Independent review reproduced two Hydra resolver gaps: fresh workers lacked
  Hydra context, and job environment overrides could change the policy after admission.
  Both received failing regressions. Preparation now resolves within the job environment
  and freezes validated policy values before worker transport. The 14-case wiring
  regression suite passed after these corrections. Parent verification also passed
  58 affected integration tests, full strict mypy and Ruff after the correction.

## Scope and limitations

The supplied eight-card snapshot was reproduced through telemetry fixtures; no
three-GPU training run or remote-host inspection was performed. Memory eligibility
does not bypass visibility, FIFO position or live reservations. Updated supervisors
admit only their own pending head, preserving registry v1 and avoiding cross-project
limit leakage. Older supervisors can still apply their historical admission policy
to foreign tickets; use updated supervisors together.

Documentation reconciles the maintained GPU execution and queue-state contracts,
README, project contract summary/index, quickstart and integration prerequisites.
Completed historical workflow records remain unchanged, with dated amendments appended.
## Final checks

The initial full suite passed 2148 tests with 30 skips. Subsequent review corrections
are covered by targeted checks and the final commit hooks. Routing-switch reads now
defer memory-policy resolution until the job environment exists, covering limits
provided only by `hydra.job.env_set`. A fresh independent review approved the integrated correction with a ship verdict.
The final source and version commits run the repository hooks before Git publication.

The final wiring selection passed 17 cases, including single-command and sweep routing
with a limit supplied only through the job environment. The first commit attempt
regenerated the changelog and attempted dependency resolution without local overrides;
it failed before code checks. Retry uses the established `UV_NO_SYNC=1` procedure
against the verified environment with all hooks enabled. Exact source overrides are
saved and restored around every attempt.
