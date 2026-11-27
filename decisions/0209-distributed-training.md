# ADR-0209 · Keep distributed training under one invocation owner

For a non-YOLO detector with several selected logical GPUs, CY starts supervised rank processes and divides the global training batch evenly among them. DEIMv2 uses distributed training with NCCL, RF-DETR integrates with Lightning DDP, and Torchvision detectors use distributed data sampling. Rank failure or deadline expires the group. Prediction runs on one device.

Ranks report back to the owner, which retains responsibility for publication and cleanup. For Ultralytics-native DDP a rank-zero journal carries callbacks and artifacts to the owner for replay. CPU or simulated rank tests can check coordination. A native multi-GPU claim needs a matching hardware run.

[Training device selection](../docs/commands/cy-train.md) · [Supervised rank group](../src/clearml_yolo/adapters/integrations/distributed_training.py) · [Native callback relay](../src/clearml_yolo/adapters/integrations/native_ddp.py) · [Distributed configuration](../tests/test_distributed_configuration.py) · [CPU callback relay cases](../tests/test_native_ddp_cpu.py)

See [native DDP event relay](0219-native-ddp-relay.md).
