# Research decisions

- Decision: extract the existing scheduler rather than reimplement it. Inspection shows distinct core/queue.py, application/queue.py, adapters/queue, GPU inventory/probe and queue entrypoint modules. Preserve wire fields and fixed namespaces; include both distribution identities.
- Decision: fetch replay before runtime. common.execute_owned currently calls OmegaConf with throw_on_missing=True and selects runtime before invocation/replay, explaining bare Agent failures.
- Decision: retain a CY lifecycle/process interface. Direct commands already use execution_lifecycle and native_descendant_scope without scheduling; queue remains the caller.
- Decision: asset resolution is an outer adapter with execution-copy integration. Existing model presets and native backend adapters remain authoritative for transformations. Detailed upstream verification is delegated within the asset stream; no approved dependency source changes.
- Alternative rejected: automatic dependency installation, reverse queue imports, a new submission interface, changing YOLO downloads, or treating local HTTP fixtures as live Artifactory proof.
