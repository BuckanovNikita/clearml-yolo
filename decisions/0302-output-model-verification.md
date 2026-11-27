# ADR-0302 · Bind a ClearML Output Model to the best checkpoint

Downstream experiments can select a checkpoint by ClearML identity, so the published model must be traceable to the bytes used locally.

**Decision.** YOLO enriches the best model registered by the native callback. For the other detector families CY publishes the checkpoint with its [descriptor](0207-checkpoint-descriptor.md). CY checks the owner task, model identity, remote weights URL, tags, model metadata and downloaded checkpoint digest. An invocation-owned verifier runs at the completion barrier.

**Consequences.** A registration conflict, changed bytes or missing metadata raises a publication error. A model verified in this invocation can later receive [calibration metadata](0303-threshold-metadata.md). SDK tests exercise the protocol. Establishing an actual storage round trip requires a live backend.

[YOLO verification](../src/clearml_yolo/adapters/clearml/native.py) · [Detector publication](../src/clearml_yolo/adapters/clearml/detectors.py) · [YOLO boundary tests](../tests/test_clearml_native.py) · [Detector boundary tests](../tests/test_detector_publication.py) · [Model contract](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b)
