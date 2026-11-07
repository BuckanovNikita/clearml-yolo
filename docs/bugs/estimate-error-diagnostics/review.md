# Independent review: estimate error diagnostics and scripts import isolation

- Date: 2026-11-07
- Reviewer: a fresh `feature-dev:code-reviewer` subagent with no inherited
  conversation, no write ownership and no further delegation. It received the
  intent and constraints, but not the parent's conclusions.
- Scope: the complete uncommitted worktree diff for both
  [estimate-error-diagnostics](assessment.md) and
  [scripts-import-isolation](../scripts-import-isolation/assessment.md), plus
  `docs/batch-estimation.md`.
- Verdict: **ship with nits**; no blocking finding.

## Findings

- `error_diagnostic` keeps the plain `Type: message` format and does not lose any
  group leaf or note. Core stays pure, and the application/adapter call sites follow
  the inward layering.
- The `NativeBatchProbe.run` branch order is correct. The `RuntimeError` rule is
  unchanged and pinned. A `BaseExceptionGroup` that carries cancellation still
  propagates. The probe now records grouped and subprocess failures that previously
  escaped as `error` trials. The use case already turned them into a failed case, so
  the end state is equivalent, and nothing harmful is newly swallowed.
- `_query` notes keep the exception type and `str()`. Bytes, `None` and blank
  streams are handled.
- The scripts import fix matches the repository pattern. The fresh-collection
  regression with `-P` would fail on the old module.

## Nits and disposition

- `discover_gpus` has the same missing-stderr blind spot: recorded as a follow-up in
  [fix.md](fix.md).
- The diagnostic reads `status 12. (nvidia-smi stdout: ...)`: cosmetic, pinned, kept.
- The reviewer could not run commands, so it judged red/green by reading. The parent
  ran each new regression before and after the fix ([test.md](test.md)). That
  includes `test_failing_nvidia_smi_output_reaches_the_trial_diagnostic`, which the
  reviewer asked to confirm: the `_Workers` fake invokes the real monitor.

Reviewer approval does not establish the parent's suite, hook, documentation or
paired-queue results; those are recorded in [test.md](test.md).
