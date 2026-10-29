# Data model

`AssetSpec` retains canonical identity and adds an optional native cache root or
`HubAsset` (repository, requested revision, native filename and effective cache root).
Managed source and weights retain existing identity/path behavior when neither is set.
`ResolvedAsset` records actual bytes/source/commit rather than a mirror credential URL.

`PreparationFailure` records selection and sanitized diagnostic. `PreparationResult`
contains catalogue/destination fingerprint, effective locations, successful assets,
failures and whether a completed automatic attempt was skipped. Completed receipts
persist only after the entire pass; interruption never creates a completed receipt.
