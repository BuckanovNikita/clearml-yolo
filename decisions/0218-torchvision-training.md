# ADR-0218 · Share the training recipe across Torchvision detectors

Faster R-CNN and FCOS share a trainer for COCO-prepared data. It constructs the selected head and backbone, loads explicit detector weights strictly, uses AdamW and accumulates gradients according to configuration. With EMA enabled it evaluates the averaged model after each epoch.

The trainer records loss and validation metrics and selects the best checkpoint by validation mAP50–95. Non-finite loss fails training. The common recipe leaves class offsets, head geometry and output decoding to the detector adapter.

[Model configuration](../docs/configuration/model.md) · [Optimizer, EMA and checkpoint selection](../src/clearml_yolo/adapters/torchvision/training.py) · [Evaluation](../src/clearml_yolo/adapters/torchvision/evaluation.py) · [Faster R-CNN behavior](../tests/test_fasterrcnn_backend.py) · [FCOS behavior](../tests/test_fcos_backend.py)

See [Faster R-CNN](0204-faster-rcnn.md) and [FCOS](0205-fcos.md).
