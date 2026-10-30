# Independent review: numerical-search recovery

Date: 2026-10-30. Verdict: **ship**. Findings: none.

A fresh native agent, `numerical_final_review`, reviewed the integrated final CY
and portable-skill diffs after parent verification. Requested controls were
`gpt-6.1-sol`, high effort, no inherited conversation, no write ownership and no
further delegation. Host runtime settings beyond the requested controls were not
independently observable.

The reviewer confirmed one fresh full repeat, preservation of memory bounds and
numerical cause, failed-confirmation rejection, replay/legacy-schema safety,
read-only preservation and status propagation. The four affected runtime modules
retain responsibilities, inward dependencies and explicit effect ownership; existing
import contracts and negative tests cover them. Architecture acceptance is supported.

The reviewer independently ran all **26** new recovery tests and `git diff --check`.
They inspected the successful canonical receipt/logs and reviewed proposed CY/queue
pairing and portable documentation checks. They did not rerun those broader suites.

Both appended portable explanation-only evaluations passed in the fresh context:

- Older failed data cannot supply null-batch training; a bounded older-version
  rerun still requires independent confirmation and remains ceiling-limited.
  Updated recovery preserves the failed numerical trial and diagnostics, all
  native checks, limited-status precedence, schema compatibility and implementation
  fingerprint requirements. It claims neither a memory maximum nor native GPU success.
- Every failed confirmation, including OOM, remains unusable without another fallback.
  Initial numerical failure also fails. Failed/null pending snapshots may be active
  or interrupted; command state must be checked and provisional data remains unusable.

No commands from the explanation-only prompts were executed. This is native review
agent evaluation, not an OpenCode or live target-model benchmark.

Residual limits: exact A40 numerical reproduction and successful supervised GPU
recovery integration remain unavailable. The telemetry guard was preserved. Final
post-hook pairing and Git release delivery remain parent-owned release checks.

The parent inspected the full task-owned diff: four existing runtime modules,
three test files, five maintained CY guidance/specification documents and the new
bug artifacts. Release tooling may additionally generate CHANGELOG.md and root
package versions in pyproject.toml/uv.lock. No dependency, import contract, SDK
numerical behavior, original installed environment or unrelated pending change is
included. The companion portable collection owns its guidance, evaluation cases,
version/changelog and dated no-impact evidence.
