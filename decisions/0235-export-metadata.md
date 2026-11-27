# ADR-0235 · Bind graph, engine and inference policy with a sidecar

An exported graph or engine does not by itself identify the source classes, preprocessing or inference thresholds. The export metadata JSON sidecar records the checkpoint descriptor, graph digest, inference policy and optimization profiles. Engine build extends the metadata with the engine digest, precision, plugins and runtime versions. Consumers validate the relevant identities before use.

The technical reference says export sidecars are never rewritten. The writer uses fixed output names and replaces the sidecar contents when another successful graph export or engine build writes to the same output directory. Downstream operations still validate their input sidecars. [Export contract](../DOCS.md#export) · [Open discrepancy](https://linear.app/sip-ds-team/issue/SIP-353)

[Export command](../docs/commands/cy-export.md) · [Metadata schema](../src/clearml_yolo/core/export.py) · [Sidecar writer](../src/clearml_yolo/adapters/export/metadata.py) · [Operation output paths](../src/clearml_yolo/adapters/integrations/export_operations.py) · [Metadata integrity cases](../tests/test_detector_export.py) · [Changed graph rejection](../tests/test_export_workflow.py)
