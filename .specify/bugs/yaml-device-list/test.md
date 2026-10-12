# Bug Verification: Hydra device list serialization

- **Slug**: yaml-device-list
- **Tested**: 2026-10-12
- **Assessment**: [assessment](assessment.md)
- **Fix**: [fix](fix.md)
- **Result**: verified for the reproduced failure path

## Checks performed

| Check | Result |
| --- | --- |
| Before-fix regression run | Three failures reproduced `RepresenterError`; six scalar checks passed |
| Focused execution/configuration/replay/pipeline/train/detector tests | 197 passed, four existing dependency deprecation warnings |
| Ruff | Passed |
| mypy | Passed, 277 sources |
| Import-linter | Passed, 40 contracts |
| Markdown and local links | Passed, three bug records and four local references; no code examples |
| Fresh independent review | Ship, no actionable findings; 16 independently run device-execution tests passed |
| Required full commit/release checks | Both passed: 2,127 tests passed, 30 skipped, no failures |

The regression calls the production assigned-execution boundary with Hydra device lists,
writes real requested/effective training and prediction YAML, reads them back, and checks
JSON provenance. It covers direct and automatically remapped execution, list interpolation,
scalar values and detector snapshots independent of later source mutation.

## Residual risks

The exact user command and full traceback were unavailable. The identical exception was
reproduced locally and eliminated on that path. Tests use simulated assigned device IDs;
they do not establish physical five-GPU execution. No dependency upgrades or server changes
were required.

## Release delivery

Released and pushed `v0.24.2` at `33f110b98b491e88367434f4d9aa86033a8b0e42`; branch and
annotated tag object IDs were remotely verified. Both wheel and source distribution were
built from a clean archive of that commit. Each fresh installation passed the original
five-element device-list YAML reproduction and command-help checks. Packaged sources
matched the committed files byte for byte.

The exact local uv source overrides were restored unstaged and excluded from commits.
Every dependency-lock byte remains unchanged apart from the root package version bump.
The local editable package metadata was refreshed to the release version with no dependency
changes; all 267 installed packages passed compatibility checks and lock validation passed.
No GitHub Release object or package assets were published. The full-suite skips require
an isolated FiftyOne environment (29) or native reflink support (one); they are not
reported as passing checks. The focused reproduction and independent review passed.
