# Bug Verification: Hydra device list serialization

- **Slug**: yaml-device-list
- **Tested**: 2026-10-12
- **Assessment**: [assessment](assessment.md)
- **Fix**: [fix](fix.md)
- **Result**: reproduced failure path verified; full commit/release gates pending

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
| Required full commit/release checks | Pending |

The regression calls the production assigned-execution boundary with Hydra device lists,
writes real requested/effective training and prediction YAML, reads them back, and checks
JSON provenance. It covers direct and automatically remapped execution, list interpolation,
scalar values and detector snapshots independent of later source mutation.

## Residual risks

The exact user command and full traceback were unavailable. The identical exception was
reproduced locally and eliminated on that path. Tests use simulated assigned device IDs;
they do not establish physical five-GPU execution. No dependency upgrades or server changes
were required.
