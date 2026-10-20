# Ground-truth source contract

All current ground-truth consumers accept local CSV paths or these mappings:

```yaml
ground_truth: {dataset_id: DATASET_ID}
# Alternative:
# ground_truth: {project_name: annotations, name: truth, version: "1.2.0"}
```

Version may be omitted for native ClearML latest selection. ID cannot be combined
with project/name/version. Unknown/empty fields fail before remote effects.
The finalized dataset inventory must contain only root `dataset.csv`; extra files
or links, missing CSV or incomplete datasets fail before materialization.
ClearML owns archive transfer/caching, including whole historical chunks.
Source bytes and image references remain unchanged. Local inputs warn at execution,
continue normally and require no dataset SDK calls. Nested stages receive resolved
records and do not warn again. Export still permits absent ground truth.
Queue submission validates and persists selectors without downloading. Execution and
remote replay resolve the requested selector once, storing actual identity/version and
CSV digest separately without replacing the executable selector with a cache path.
