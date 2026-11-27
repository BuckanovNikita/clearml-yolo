# ADR-0230 · Run each detector export operation as its own task

Deployment requires distinct artifacts from graph export, engine build and quality verification. For a Faster R-CNN model, `cy-export` accepts one operation per invocation, checks its required inputs and owns one ClearML task. The source weights or artifact connect successive invocations.

CY uploads the operation's artifacts and records `export_result` provenance. It does not register an additional Output Model. A quality-gate failure fails the task after the available report is published. A partial run may leave local evidence before a report is ready to upload.

[Export command](../docs/commands/cy-export.md) · [Export workflow](../src/clearml_yolo/application/use_cases/export.py) · [Operation admission](../src/clearml_yolo/core/export_requests.py) · [Inputs and publication ordering](../tests/test_export_workflow.py) · [Early artifact publication](../tests/test_early_export_publication.py)

See [ONNX export](0231-onnx-export.md), [engine build](0232-tensorrt-build.md), [quality verification](0233-export-verification.md), and [export metadata](0235-export-metadata.md).
