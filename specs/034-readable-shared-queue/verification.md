# Integration verification — 2026-10-16

## Scope and preservation

Feature 034 is implemented in an isolated worktree because the original checkout
contains another task's finalization-deadline work and a user grid-search draft.
Neither those edits nor dependency sources/revisions were modified. Local editable
source overrides are excluded from delivery. No production queue configuration,
shared service lifecycle, existing users or GPU workloads were changed.

## Executed checks

- Initial full routine run: 2,862 passed, 30 skipped, 7 deselected; three failures
  and 22 fixture errors. The errors were a legacy transaction mock lacking the new
  root keyword. Failures were the old queue configuration recipe, the intentionally
  changed visible workbook source banners, and a subprocess SDK double missing the
  Logger interface. All were corrected without changing the immutable extraction
  fixture or machine provenance. Affected reruns passed: 59 GPU/Hydra/trace cases
  and nine workbook/readability cases.
- The next complete routine run passed: 2,891 tests, 30 skipped, seven deselected.
  It ran before the independent review's final output corrections. After queue review
  fixes, 78 queue/Hydra/TUI/readability/multirun tests passed; affected entrypoint Ruff
  and strict mypy checks passed. The commit gate will rerun the final integrated suite.
- Parent archive/presentation/readability rerun: 57 passed. Parent architecture
  graph and negative injected dependency tests: 227 passed.
- Parent Ruff, strict mypy (343 source files), Vulture and import-linter (43 contracts)
  passed. Final checks after review corrections are recorded below when complete.
- Agent report/console checks: 396 passed before live integration; after the SDK
  startup correction, 178 session/trace/capture/deadline cases passed.
- [Two-user acceptance](multiuser-evidence.md): real separate Unix identities,
  permissions, concurrent ordering, archive/recovery visibility, cross-root exclusion,
  owner workers/guardians and cleanup, including injected-failure cleanup.
- [Native acceptance](native-evidence.md): real CPU validation with separate-process
  active server readback, downloaded artifacts, exact hidden identity and capture
  receipts. The initial SDK startup leak was reproduced and corrected; fresh live
  readback then passed. Synthetic fixtures establish execution, not model quality.
- Built both wheel and source distribution. An isolated built-wheel environment
  imported the installed package outside the checkout, passed all 12 command helps
  and nine command configuration exports, and imported both new modules. Build/install
  verification will be repeated against the final source and source distribution.
- Documentation checker passed on 487 tracked/new Markdown files before final evidence
  additions. Fresh usage review accepted the corrected docs and companion skill;
  nine reasoned scenarios and actual read-only config/help checks passed. This is not
  a live OpenCode/DeepSeek or automatic-routing claim.
- Parent documentation validation after review annotations checked 489 Markdown files
  with zero issues. Companion Markdown validation checked 38 files with zero issues;
  its no-impact architecture record passed acceptance validation.
- Parent checks on the first frozen review correction passed: Ruff, mypy (343 source
  files), Vulture and all 43 import contracts; 293 architecture/report/workbook/identity
  compatibility cases and 103 publication/diagnostic cases passed. Independent rereview
  confirmed the original four output fixes but identified a further alias-collision
  issue for table/scalar labels; final acceptance awaits its correction and checks.
- Both wheel and source-distribution installations passed outside the checkout:
  all 12 command helps, all nine configuration selections, default selection, three
  alternate model families, Hydra composition, overwrite refusal/unrelated-file
  preservation and read-only shared queue settings. The first harness attempt assumed
  Hydra help contained argparse's word "usage"; that harness-only assumption was removed.
- Final collision correction: parent Ruff, strict mypy (343 files), Vulture and all
  43 import contracts passed; 439 affected publication/architecture tests passed.
  The implementer's 123 affected cases and four final regressions passed. A separate
  active live scalar/table readback confirmed distinct stable labels, exact raw journal
  records and receipt bytes, and complete tagged cleanup; see native evidence.
- The final independent output rereview accepted the corrections: 117 tests and
  24 alias arrival orders passed. Queue and portable usage reviews also accepted
  their scopes. All original review findings are resolved.
- Both distributions were rebuilt from the final frozen feature source and installed
  again into their separate environments. The complete installed verification above
  passed for each. This verifies the feature source before its release version bump.
- Final documentation validation covered 490 tracked/new Markdown files with zero
  issues, including review and native evidence; `git diff --check` passed.
- Complete final feature-source routine run passed: **2,927 passed, 30 skipped,
  seven deselected**, with 93 existing warnings, in 623.57 seconds. The skipped and
  deselected cases are not counted as physical acceptance. Commit and release hooks
  will execute their required gates separately.

## Limits and pending gates

Initial physical GPU inspection found an existing workload, which was left intact.
A later capacity check allowed a tiny direct single-GPU validation, which passed along
with fresh CPU publication, artifact downloads and original class-key recovery. The
queue's automatic admission threshold is distinct from direct inference capacity.
Physical multi-GPU and two-host NFS were not exercised.
The earlier feature 029/031 waiver remains scoped to its historical targets; no new
physical outcome is inferred. Browser interaction was not exercised; Textual pilot
and task-link boundary tests cover this change's UI behavior.

The final full suite, fresh runtime/architecture review and documentation validation
passed. The architecture acceptance record is reconciled with the complete task diff;
delivery remains pending. Companion source guidance is
prepared for 0.2.7 and must follow application delivery. No deployment or package
publication is authorized by this feature.
