# Capability: Consistent validation and maintainable acceptance

## Problem

Divergent validation paths, unsafe duplicated cache publication and expensive repeated
test setup make experiments harder to diagnose and maintain.

## Desired behavior

- Preserve CLI/API behavior, configuration precedence, JSON-schema metadata, serialized
  data, scientific results, compatibility and approved dependency pins.
- Execution and export previews share input-presence semantics and validation order.
  Known missing required inputs fail consistently; unresolved expressions remain
  deferred. Preview performs no external resolution or I/O and uses exact null checks.
- Hub publication has one effect owner and preserves safe paths, locks, validated atomic
  placement, copy fallback and original files. Worker-role ownership remains explicit.
- Release fixtures select only semantic-release configuration, tolerate local uv source
  overrides, and retain real-hook and protected-lock assertions.
- Architecture checks cover every import syntax form and SDK ownership boundary;
  configuration checks retain every distinct command/model/profile scenario.
- Configuration exports use schema 3; bulk weight preparation follows the current
  [model asset contract](../../docs/model-assets.md), distinct from standalone resolution.
- Performance work compares the same source/environment/workload and reports setup and
  execution time separately. Reusable fixture setup must preserve isolation.

## Acceptance

Exercise missing ONNX/build/verify inputs and valid/deferred previews; confirm identical
runtime diagnostics and no preview I/O. Validate safe Hub publication and fresh-cache
offline native loading. Verify release fixtures with local overrides, negative import
boundaries, public metadata and all unique configuration scenarios. Use current hook
semantics from [verification](../011-simplify-hooks/spec.md); complete required checks
and fresh independent review before authorized delivery.
