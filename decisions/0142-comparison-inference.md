# ADR-0142 · Reuse comparison predictions only for compatible inputs

## Context

Comparing two stored dashboards could mix image populations, resolutions or native settings. Repeating inference for unchanged inputs can be expensive.

## Decision

Re-infer both models on the current split with the same requested settings. The cache key includes checkpoint location and content hash, settled inference options, backend assertions and split image names and resolved paths. Validate available cached provenance before reuse and record requested and effective inference evidence.

## Consequences

Disabling `reuse_existing` forces inference. Refreshed checkpoint timestamps alone do not invalidate results. The image membership fingerprint assumes immutable media at each location. Cached predictions are sought in the selected output directory. Each role also produces a [native output archive](0014-native-output-archive.md).

## Evidence

- [Cache key and split fingerprint](../src/clearml_yolo/application/use_cases/compare.py)
- [Native inference reuse](../src/clearml_yolo/adapters/yolo/reinfer.py)
- [Cache identity cases](../tests/test_comparison_identity_cache.py)
- [Comparison settings](../docs/commands/cy-compare.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#re-inference-and-prediction-cache)
