# Bug Fix: Informative error diagnostics

- Slug: informative-error-diagnostics
- Fixed: 2026-10-06
- Assessment: [assessment.md](assessment.md)
- Status: applied

## Changes

Added the independent diagnostics module at the lowest import-contract layer. It summarizes exception chains and redacts credential-bearing URLs, authentication headers and labeled secret values; DEBUG stacks contain frame locations only. Empty messages, failing string conversion and cyclic causes remain safe. Existing Loguru DEBUG defaults and caller-owned sinks are preserved.

Publication warnings now distinguish factory, preflight, request preparation, backend publish, receipt write and run configuration recording, retaining relevant task/path context. Optional failures still warn and continue. Missing receipts remain failures without invented success.

Updated error boundaries in ClearML finalization/cleanup, configuration parsing/resolution, optional FiftyOne configuration, model/threshold recovery, dataset cache/image EXIF handling, prediction cache, CUDA probe and latest-run symlink handling. Configuration payloads remain suppressed while error categories, JSON locations and available field paths are exposed. Expected missing cache files remain quiet. ClearML failure status fields are unchanged.

## Tests and verification

Publication red tests reproduced seven missing-message/operation cases before the fix. Formatter tests cover secret shapes, malformed/spaced credential URLs, INFO/DEBUG behavior, no attached exception object, explicit/suppressed/cyclic causes and broken exception string formatting. Handler regressions cover source/reason context, suppressed opaque values, primary-error preservation and quiet cache misses.

Parent full pytest: 1192 passed, 29 skipped; Ruff, mypy and all nine import contracts passed. Native release verification and optional publication failure with actual Console readback are recorded in [live evidence](../../../docs/evidence/2026-10-06-error-diagnostics-live.md).

## Documentation

Updated Russian README troubleshooting, project contract summary and publisher contract. Documentation/link validation and final review are recorded in test.md after completion.

## Deviations

Work moved into an isolated checkout after another feature began changing the shared checkout. One live GPU attempt hit an intermittent ClearML SDK readback error; a fresh retry passed. The original user's unidentified backend OSError was not reproduced; the exact diagnostic-loss boundary was reproduced using a deliberately failing publisher.
