# ADR-0233 · Compare the exported engine against its source checkpoint

To verify a specific engine, CY requires matching checkpoint and engine metadata, the selected precision, and labeled ground truth. It freezes a corpus from the requested split, including image hashes, and evaluates native and exported detections on the same cases. The report checks preprocessing agreement, valid and invalid input shapes, and COCO accuracy at the supported precisions.

A usable reference needs observed detections and positive mAP. The permitted mAP50–95 loss is 0.001 in FP32 or 0.005 in FP16. Detection matching diagnostics accompany the verdict. The corpus can be uploaded before verification completes, and the local report retains partial evidence on error. Only an actual engine run can establish quality for that artifact and hardware.

[Export command](../docs/commands/cy-export.md) · [Corpus and profile verification](../src/clearml_yolo/adapters/export/verification.py) · [Evaluator](../src/clearml_yolo/adapters/export/quality.py) · [Quality gate](../src/clearml_yolo/core/export_quality.py) · [Quality boundary cases](../tests/test_export_quality.py) · [Corpus and publication cases](../tests/test_export_workflow.py)

See [standalone inference](0234-tensorrt-runner.md).
