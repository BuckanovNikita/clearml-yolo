# ADR-0104 · Share prepared datasets under a locked content key

## Context

Repeated training jobs need reusable preparation while concurrent jobs can request the same entry. Hashing every image on a cache hit would require reopening the source media.

## Decision

Key the prepared dataset by CSV bytes, ordered resolved image references, preparation format and preparation version. Use a native per-key file lock, build under staging and require a complete, valid layout before reuse.

## Consequences

A hit can avoid reading the source image bytes. Replacing media in place while preserving its path leaves the key unchanged. A different preparation version creates a different entry. Consumers can select `dataset_cache_dir` and CY retains completed entries.

## Evidence

- [Cache key, completion validation and publication](../src/clearml_yolo/adapters/storage/dataset_cache.py)
- [Reuse and locking tests](../tests/test_dataset_cache.py)
- [Recorded decision about unchanged media paths](https://linear.app/sip-ds-team/issue/SIP-219)
- [Prepared dataset cache](../docs/formats/datasets.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#dataset-cache)
