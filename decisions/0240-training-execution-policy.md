# ADR-0240 · Keep the requested training run intact on failure

A training run describes a specific scientific experiment. CY refuses training resume and uses an explicit starting model. An initial checkpoint supplies weights for a fresh optimization run. CY does not restore its optimizer or scheduler state. Native out-of-memory handling must propagate the failure without reducing the requested batch. CY does not retry with another precision, compiler setting or checkpoint.

For example, the Ultralytics trainer disables its native smaller-batch recovery, and the Torchvision trainer reports non-finite loss as an error. Choosing a smaller batch for a new experiment is a user decision. The bounded search in the batch estimator is a separate operation.

[Training command](../docs/commands/cy-train.md) · [Ultralytics recovery policy](../src/clearml_yolo/adapters/integrations/native_trainer.py) · [Torchvision loss validation](../src/clearml_yolo/adapters/torchvision/training.py) · [OOM and configured batch cases](../tests/test_yolo_oom.py) · [Explicit model validation](../tests/test_train.py)

See [training initialization](0206-training-initialization.md) and [batch estimation](0220-batch-estimation.md).
