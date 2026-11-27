# ADR-0204 · Preserve Faster R-CNN geometry on a padded canvas

A prepared image can be much shorter than the canvas on which Faster R-CNN builds its feature pyramid. CY scales the image to fit, pads on the right and bottom, and fixes region-of-interest pooling scales to the backbone strides. Inferring scales from only the valid image height could pool from the wrong feature locations.

The classifier reserves an internal background class. CY maps foreground detections back to the dataset vocabulary. The best checkpoint from validation mAP50–95 is `best.pth`. The predictor can use class-aware NMS and CUDA half precision. This family also supports the export workflow.

[Model configuration](../docs/configuration/model.md) · [Faster R-CNN model](../src/clearml_yolo/adapters/fasterrcnn/model.py) · [Canvas transform](../src/clearml_yolo/adapters/torchvision/transform.py) · [Faster R-CNN contract cases](../tests/test_fasterrcnn_backend.py) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443)

See [Torchvision training](0218-torchvision-training.md) and [export](0230-export.md).
