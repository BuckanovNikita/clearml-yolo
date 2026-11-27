# ADR-0219 · Replay Ultralytics DDP callbacks in the owning process

The native trainer can execute epoch and validation callbacks inside ranks that do not own the ClearML task. CY records supported rank-zero events and their required local files in a run-owned journal. The owner replays those events through the native callback integration before training publication completes.

This lets owner-side publication use captured epoch values and plots. A worker cannot create a second task or independently publish an epoch. The CPU relay cases establish local event transport. Remote delivery and native multi-GPU behavior require their respective live evidence.

[Training command](../docs/commands/cy-train.md) · [Native callback relay](../src/clearml_yolo/adapters/integrations/native_ddp.py) · [Owner replay integration](../src/clearml_yolo/adapters/integrations/training.py) · [Native relay cases](../tests/test_native_ddp.py) · [CPU rank relay](../tests/test_native_ddp_cpu.py)

See [distributed training](0209-distributed-training.md).
