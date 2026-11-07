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

## W6 workflow review — 2026-11-07

- Scope: the committed branch `bug/estimate-diagnostics-20261107` at `f390fe0`
  (fix commit `bf5c5f6` and evidence commit `f390fe0`) against `origin/master`
  `fe7332b`, covering both bug folders and `docs/batch-estimation.md`.
- Lenses and votes: this was the remaining-work orchestration's step 4 review. Its
  findings were checked by verification voting before they were passed on. The
  per-lens names and vote tallies were not passed to the agent that wrote this
  record, so they are not given here. Only the findings that survived verification
  were passed on.
- Verdict: **ship after fixing three low-severity findings**. No source, test,
  interface or architecture defect survived; all three findings are in evidence
  records.

| ID | Severity | File | Finding | Disposition |
| --- | --- | --- | --- | --- |
| F1 | low | [architecture.json](architecture.json) | The `static` check recorded `prek run --all-files` as passed, but [test.md](test.md) never records that run. | Fixed. The check now names the commands that actually ran (`ruff check .`, `mypy .`, `vulture`), matching the Checks table, and says the commit hooks ran on the staged files. `prek run --all-files` was not run, so it is no longer claimed. |
| F2 | low | [test.md](test.md) | In the fail-first itemization, the per-file counts summed to 11, but the result was `13 failed`. | Fixed: `test_batch_estimate_workflow.py` contributes six test cases (four functions, the formatter test parametrized three times), so 6 + 4 + 3 = 13. |
| F3 | low | [isolation test.md](../scripts-import-isolation/test.md) | The link for post-rebase results pointed at `#checks`, which holds only pre-commit results. | Fixed. Pre-commit results now link to `#checks`, and post-rebase results link to `#commit-and-post-rebase-verification-2026-11-07`. |

These fixes change documentation only; no source or test file changed. Their checks
are the documentation check, the architecture validator and the commit hooks.
