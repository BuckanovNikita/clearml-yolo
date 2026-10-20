# Design decisions

- Existing ground_truth inputs are paths; Hydra MISSING fields already compose mappings.
  Queue strict type validation must be expanded explicitly.
- ClearML Dataset.get resolves ID or project/name/version and finalized datasets.
  Its default selection uses highest semantic version, then most recently updated.
  get_local_copy(files=["dataset.csv"]) requests the selected CSV; SDK archive
  transport remains SDK-owned. Source datasets are CSV-only as requested.
- Preserve CSV location when reading relative image references; no copying to run_dir.
- A resolved source record makes nested-stage ownership explicit and prevents warnings
  for internally derived files. Requested selectors remain canonical replay inputs.
- Project extras currently group queue UI, detectors and exports. Upstream feature
  extras remain necessary; development packages must remain out of wheel requirements.
- Minimum dependency values are experimental outputs, not presumed lock versions.
  Approved external dependencies remain fixed throughout resolution and tests.

References: [ClearML Dataset](https://clear.ml/docs/latest/docs/references/sdk/dataset/),
[uv resolution](https://docs.astral.sh/uv/concepts/resolution/#resolution-strategy).
