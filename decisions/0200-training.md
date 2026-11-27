# ADR-0200 · Run standalone training from ground truth

A user can train a detector without running the downstream evaluation workflow. `cy-train` resolves ground truth under one training task, requires populated training and validation splits, prepares the backend's input dataset and trains the selected architecture. Dataset-derived settings own the labels, split and prepared paths used by the trainer.

The observable result is the family's best checkpoint in the training directory. Missing checkpoints, invalid training settings and publication failures fail the standalone command. A completed native training call alone does not establish successful remote delivery.

[Training command](../docs/commands/cy-train.md) · [Training workflow](../src/clearml_yolo/application/use_cases/train.py) · [CSV training boundary](../tests/test_train.py) · [Training finalization cases](../tests/test_training_success_finalization.py)

See [dataset preparation](0103-dataset-preparation.md), [model initialization](0206-training-initialization.md), [augmentation](0208-training-augmentation.md), [distributed training](0209-distributed-training.md), [batch lookup](0222-batch-lookup.md) and [training failure policy](0240-training-execution-policy.md).

Detector families have individual contracts for [YOLO](0201-yolo.md), [DEIMv2](0202-deimv2.md), [RF-DETR](0203-rfdetr.md), [Faster R-CNN](0204-faster-rcnn.md) and [FCOS](0205-fcos.md).
