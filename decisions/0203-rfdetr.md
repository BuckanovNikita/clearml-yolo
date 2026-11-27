# ADR-0203 · Use the RF-DETR preset's full detector checkpoint

CY selects the native RF-DETR class by preset and delegates training to its Lightning-based implementation. Pretrained initialization uses a full detector checkpoint. A separate backbone checkpoint is unsupported. The training dataset supplies the class vocabulary and the requested square resolution must be divisible by 32.

CY consumes `checkpoint_best_total.pth` as the training result. Prediction returns detections for the stored classes after the confidence and detection-count limits. The adapter rejects half precision and nondefault NMS IoU settings.

[Model configuration](../docs/configuration/model.md) · [RF-DETR training and prediction](../src/clearml_yolo/adapters/rfdetr/backend.py) · [Registry asset mapping](../src/clearml_yolo/adapters/rfdetr/assets.py) · [RF-DETR contract cases](../tests/test_rfdetr_backend.py) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443)
