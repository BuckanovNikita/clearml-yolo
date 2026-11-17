# SIP-63 release PR verification — 2026-11-17

## Scope and selection

Base: `99d45b48ef8fdb7f8f9d4fcc60bd8ce677421022` (fetched `origin/master`).
Branch: `feat/sip-63-release-pr`. Linear: https://linear.app/sip-ds-team/issue/SIP-63.
The change replaces local release integration with a release PR and separately
authorized tag-only publication. No product runtime, dependency revision or model asset
changes are included. Existing product behavior is unchanged; native/GPU, mutation and
live CY/queue pairing were not selected. This implementation request does not authorize
publishing a real code release. Human merge remains required.

## Executed checks

- Passed: full automatic `prek run --all-files` with SKIP, PREK_SKIP, CY_VERIFY_SCOPE
  and PRE_COMMIT_ALLOW_NO_CONFIG cleared after the final code changes. Includes lock,
  Ruff, format, architecture, mypy, Vulture and dependency checks; static route selected.
- Passed: focused Ruff, formatting, mypy and whitespace checks.
- Passed: temporary manual scenarios executing the actual release wrapper, installed
  semantic-release, actual release lock guard and real Git against a local bare origin.
  A transport helper routed a GitHub SSH URL locally without mocking effective URL reads.
- Passed: no-version leaves source/refs unchanged and creates no PR/push; preparation
  creates one version commit and PR without a tag or master push; retry reuses both.
- Passed: merged-source publication creates an annotated tag at the merged SHA, pushes
  only that tag, and preserves the identical tag object on retry.
- Passed: dirty trees, stale expected tips, unmerged PRs, version/lock mismatches,
  held locks, moved checkout/master and conflicting remote tags are rejected.
- Passed: explicit GitHub repository binding, inline evidence in the PR, caller-relative
  evidence paths from a subdirectory, staged version guard, and refusal of extra staged paths.
- Passed: `push.followTags=true` with a reachable unpublished annotation did not publish
  that annotation during either preparation or publication. Differing/multiple push URLs
  were rejected before source/ref mutation; GitHub-to-GitHub URL rewriting selected the
  effective repository, and rewriting to a local destination was rejected.

GitHub PR list/view/create responses were simulated. The fixture used a minimal lock
refresh in place of the production build hook and simulated the staging Task boundary;
the actual version guard ran. Production static gate components passed separately.
Live GitHub merge/tag publication and live pairing are not established by these checks.
Temporary harnesses, repositories and transport helpers were removed; no child processes
remain and no real release refs were changed.

## Independent review and source identity

Fresh independent review found automatic tag-following and ambiguous push-destination
risks. Both were fixed, including effective URL rewrite handling. Follow-up review found
no outstanding issues, and adversarial scenarios above passed on the final sources.
An earlier automatic invocation was invalidated by concurrent editing; the unchanged
final source subsequently passed. No required failure is hidden by a hook skip.

Validated SHA-256:

- `scripts/release.py`: `930bcac834ce656e5e6802e9fb5c02433bcd4ddb409d4ab3b635115dd28663d5`
- `scripts/release_lock_guard.py`: `eb79fc0dee407eaa4eb1f1941e989dc2b254334d4d727a3dbc9fd8d670b2bfd2`

Commit identity, final committed-tip gate and PR delivery are recorded in SIP-63 and
the PR after execution. Reuse these manual results only while these inputs and the
stated boundaries remain applicable. This evidence does not claim a published release.
