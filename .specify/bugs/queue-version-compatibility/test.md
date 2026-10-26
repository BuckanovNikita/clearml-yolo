# Bug Verification: latest CY and queue compatibility

- **Slug**: queue-version-compatibility
- **Tested**: 2026-10-26
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Checks performed

| Check | Result |
| --- | --- |
| Original resolver reproduction after fix | Passed normal joint editable installation without dependency bypasses |
| `uv pip check --python .venv/bin/python` | Passed: all 283 installed packages compatible |
| Source/installed metadata | CY 0.40.0 and queue 0.1.1 agree; queue range `>=0.38,<0.41` |
| New compatibility regressions | Both failed before correction, passed after; also independently rerun by reviewer |
| Complete ordinary queue suite | 501 passed, 7 opt-in GPU cases deselected, 4 upstream warnings |
| Queue Ruff, format, strict mypy and import-linter | Passed; both inward/pure-policy contracts kept |
| Outside-checkout CLI checks | `cy`, `cy-train`, `cy-queue --help` all passed |
| Current augmentation composition | Pipeline and train snapshots composed/froze/validated with a real serialized pipeline |
| Documentation and local links | Both repositories passed, including task evidence |
| Independent final diff review | Accepted by fresh native read-only `final_review`; no blocking findings |
| Architecture acceptance | Queue module-impact and CY documentation-only records passed |
| CY canonical verification | Ruff, strict mypy, Vulture, import-linter and complete ordinary pytest passed |

The queue fix commit is `89938c2367c6ed143ae2eab96ae6513ab70bb392`, followed by
documentation delivery commit `9a6fccd86b8958a77809e4d2e7e2cc178d0a73ee`. Both are
pushed to the new public [queue repository](https://github.com/BuckanovNikita/cy-queue).
GitHub reports PUBLIC/default `main`; local HEAD and fetched `origin/main` agree.
Full queue evidence and independent review are in that repository's
`docs/bugs/queue-version-compatibility/` directory.

## CY acceptance and reconciliation

CY's task-owned changes are AGENTS, README, queue/development guidance and these
native bug artifacts. No CY runtime, dependencies, lockfile or release machinery
changed. The existing local uv source section is preserved exactly outside the
commit view. Approved external dependency copies and historical feature evidence
remain unchanged. The portable usage skill was inspected; its compatible source
installation and unchanged CLI/config examples require no update.

An early canonical CY verification was interrupted after static checks passed:
the editable queue's documentation/evidence changed during the run, invalidating
its dependency input snapshot. Only the task-owned verifier/process group was stopped;
no successful acceptance was claimed for that run.
Canonical verification was restarted after finalizing and delivering the queue
checkout. The final input-stability check passed and the canonical tool recorded
success. Its complete pytest result was **3,393 passed, 30 skipped, 47 deselected,
167 warnings in 802.55 seconds**. The private command log is
`.git/verification/application-b07e40a6e982466283d6be65ecd9519e-4.log`; the receipt is
`.git/verification/application.json`. All four configured static checks passed too.
These inputs remain fixed through the CY documentation commit and native hooks.
Anonymous HTTPS access to the public queue remote also returned the exact delivered
`main` commit. CY remains version 0.40.0; documentation-only history is evaluated by
its normal release hook without forcing a version bump or new tag.

## Limits

Fresh integration evidence covers the latest pair on the prepared Python environment;
it does not re-establish every older CY/Python combination, GPU training, ClearML
uploads or multi-host/NFS outcomes. The existing lower compatibility bound is retained
and untested future CY minors remain excluded. Both repositories now require latest
source-pair verification before every release, including proposed versions and
post-hook installed-version refresh when needed.

## Commit hook verification

The first commit attempt stopped for the normal generated-changelog review; its
exact-source verification hook passed. The three generated lines describe an
already committed documentation change. They were inspected, added to the no-impact
scope and staged for a normal retry. Local uv source overrides were restored on the
failed attempt and are preserved through the retry procedure.
