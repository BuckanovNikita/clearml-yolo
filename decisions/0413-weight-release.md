# ADR-0413 · Package verified weights and licence notices as a separately versioned release

A model asset release has its own identity and redistribution constraints. The packaging tool partitions the prepared catalogue into size-bounded archives, separates the restricted DEIM weights, and emits the manifest and checksums. Publishing is an explicit operation under a new weights tag. The subsequent code change points consumers to those pinned bytes.

A change to timm-backed weights must keep the producing version and the consumer manifest compatible. Operators need upstream notices and the applicable weight licences when distributing the archives. [Release procedure](../DOCS.md#release) · [Archive packager](../scripts/package_weights.py) · [Bundle cases](../tests/test_weight_bundles.py) · [Version decision](https://linear.app/sip-ds-team/issue/SIP-327) · [Bulk restoration](0213-bulk-weights.md)
