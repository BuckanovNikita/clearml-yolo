# Bug Verification: Informative error diagnostics

- Slug: informative-error-diagnostics
- Tested: 2026-10-06
- Assessment: [assessment.md](assessment.md)
- Fix: [fix.md](fix.md)
- Result: verified (diagnostic-loss bug)

## Checks performed

| Check | Command or action | Result |
| --- | --- | --- |
| Original diagnostic loss | Strengthened publication tests: seven failures before fix, then all 23 publication tests pass | Pass |
| Safe formatter | 33 formatter regression cases, including malformed userinfo and nested secret values | Pass |
| Regression suite | `uv run --frozen pytest -q` | 1192 passed, 29 skipped |
| Lint | `uv run --frozen ruff check .` | Pass |
| Typing | `uv run --frozen mypy .` | Pass |
| Import layers | `uv run --frozen lint-imports` | Nine contracts kept |
| Native runtime and remote optional failure | [Live verification](../../../docs/evidence/2026-10-06-error-diagnostics-live.md) | CPU/GPU retry/paired standalone commands passed; 36 native FiftyOne tests passed |
| Initial distribution installation | Wheel and source distribution in separate fresh environments | Nine helps and eight generated configurations per environment; artifact parity and dependency checks pass |

## Review and documentation

The first independent review found two redaction gaps: malformed URI userinfo with quotes/angle delimiters and composite secret assignment values. Both were reproduced with failing tests and corrected; parent reran formatter/publication tests (53 passed), Ruff and mypy. A final URI suffix regression was also reproduced and fixed. Fresh independent read-only review returned ship and independently passed all 33 formatter cases; parent formatter/publication checks passed all 56 cases.

Seven changed Markdown files and 18 local links passed structural/link/whitespace checks. User-facing README remains Russian. A final CLI boundary regression suite passed with existing deprecation warnings.

## Residual risks

The user's original backend failure remains unidentified. A first GPU invocation encountered an intermittent SDK model readback failure; no SDK/service changes were made and the fresh retry completed. Physical multi-GPU and interactive App/browser behavior were not exercised. Default pytest skips opt-in integration tests; the native FiftyOne subset was separately run against the test database. Early distribution checks used version 0.17.1 artifacts; final release packaging must be refreshed after the checked version commit.

## Recommendation

The loss of useful diagnostic messages is resolved. Release publication still requires final independent review, documentation validation, normal commit/release hooks and final-version packaging/readback verification.
