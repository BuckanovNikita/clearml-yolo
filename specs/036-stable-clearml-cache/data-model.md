# Data model

- PreparedDataset adds optional cache_identity, supplied by validated dataset cache
  reads. Non-cache preparation remains supported with None.
- Canonical run retains full native input mappings and adds prepared_dataset identity
  plus generated root as provenance. This record is not an executable command argument.
- General is a scientific projection of native training settings.
- Controller hashing consumes detached script/hyper_params/configs data. Its normalized
  representation is ephemeral and versioned; it is never used as execution input.
