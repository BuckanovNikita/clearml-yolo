# Saved estimate coverage listing

## Intent and approach

The user selected saved coverage over current-run compatibility or dual modes.
List missing models from existing evidence without CUDA or --imgsz; retain original
measurement behavior and saved schemas. Current-run readiness would require GPU and
recipe resolution and is outside scope. No browser/UI or native training is needed.

## Interfaces and failure behavior

A pure core function returns one frozen coverage record per selected model in
catalogue order, retaining unsuccessful cases only when no usable case exists.
Case diagnostics fall back to the latest unsuccessful trial diagnostic/status, then case status;
no records means No saved attempt. CLI prints MODEL / STATUS / REASON with saved
resolution, hardware and workload on failure rows, selected/covered/missing totals
and the path. It escapes control characters in stored text to preserve rows.
Only --list, --models and help apply to listing. Explicit measurement flags,
including values equal to their defaults and argparse abbreviations, must fail.
Errors use existing argparse exit 2; missing estimates exit 0.

## Architecture and acceptance

The core has no effects or outer imports. Entry point composes the existing store,
reads once and renders; shared options remain inert. No new module or storage port
is needed. Existing import/architecture negative tests plus targeted effect guards
cover boundaries. The [record](architecture.json) indexes checks. Verification
includes missing/failed/usable/mixed contexts, aliases/order, diagnostic fallback,
unchanged catalogue bytes, malformed files and no runtime/GPU/probe/write effects.
