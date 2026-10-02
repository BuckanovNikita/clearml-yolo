# Bug Verification: Workspace cache boundary

- **Slug**: workspace-cache-boundary
- **Tested**: 2026-10-01
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

> **Follow-up review (2026-10-02):** A subsequent pre-push review found two remaining active
> XDG-default statements in the CLI contract and feature 008 FR-004. They were corrected
> before publication; the documentation-completion claim above is supported only after
> this reconciliation. Fresh checks and the checkout-isolation safeguards are recorded in
> [the dated review evidence](../../../docs/evidence/2026-10-02-workspace-cache-review.md).

## Summary

The original fresh-process startup and XDG dataset-routing failures no longer reproduce.
General dependency/process settings remain unchanged; approved project data locations and
explicit overrides are preserved. Final independent acceptance is recorded below.

## Checks Performed

All uv commands below used `--locked --no-sync`, preserving dependencies and the lockfile.

| Check | Command / Action | Result | Notes |
|---|---|---|---|
| Pre-fix reproduction | pytest -q tests/test_filesystem.py -k 'startup_preserves_general or dataset_default_ignores' | expected failure | 3 failed on environment/tempfile mutation and XDG selection |
| Affected regression suite | pytest -q tests/test_filesystem.py tests/test_dataset_cache.py tests/test_train.py tests/test_pipeline.py | pass | 68 passed; 4 Hydra/Pydantic warnings |
| Filesystem/export examples | pytest -q tests/test_filesystem.py tests/test_config_tree.py | pass | 52 passed; 4 warnings |
| Final direct storage/reproduction checks | pytest -q tests/test_filesystem.py -k 'data_storage or existing_fiftyone or preserves_general or dataset_default' | pass | 7 passed; 13 deselected; includes actual native/publication imports and settings path |
| Final regression suite | pytest -q | pass | 721 passed; 8 skipped; 4 Hydra/Pydantic warnings |
| Ruff | ruff check . | pass | All checks passed |
| mypy | mypy . | pass | No issues in 96 source files |
| Import contracts | lint-imports | pass | 9 kept, 0 broken |

## Documentation Stage

README, the maintained filesystem policy, feature 011 current intent/design/contract/quickstart
and appended task history, affected feature 008/009 guidance, exported configuration comments,
and the project E2E skill/prerequisites were reconciled. Prior dated evidence remains unchanged.
Markdown parsing, shell-example syntax and local-link/anchor validation are recorded below.
The current contract index continues to point to the same maintained filesystem policy.

Final validation parsed 17 changed/new Markdown files, checked 36 local links and heading
anchors, and passed `bash -n` for 18 shell examples. `git diff --check` also passed.
Configuration-export tests exercised generated examples and overwrite protection. Feature 011
tasks T032–T035 are complete and link to this evidence. Unrelated pre-existing edits in agent
instructions, workflow/development guidance, the contract index and local dependency overrides
were preserved.

## Residual Risks

- Eight real FiftyOne publication integration tests remain opt-in and skipped; native startup
  imports and directory selections were exercised without creating a remote ClearML task.
- GPU/native training and remote ClearML uploads were not rerun; this evidence does not assert
  those outcomes. Multi-process behavior retains existing native runtime/DDP regression coverage.
- Existing broad cache directories are neither migrated nor deleted. Inherited explicit cache
  environment values remain authoritative; fresh launches receive the corrected defaults.
- Four Hydra/hydra-zen warnings concern deprecated Pydantic field access in a dependency.
- No commit/release hooks ran because this task does not authorize a commit or release.

## Recommendation

The bounded storage-policy fix is verified by the original reproduction and regression suite.
The independent review returned ship with no findings; the documentation gate is complete.

## Independent Acceptance

Fresh read-only reviewer /root/cache_review returned **ship**, with no findings. It inspected the
scoped source, tests, current contracts and supplied verification evidence. It retained the
stated limits on GPU training, remote ClearML uploads, opt-in publication integrations and old
cache contents. Requested model/effort: gpt-5.6-sol / high; runtime model/effort and token usage
were not exposed by the native tool metadata. The parent inspected the combined diff and owns
the final verification and acceptance.
