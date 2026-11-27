# ADR-0225 · Admit batch probes only on observable CUDA devices

Batch capacity measurements can reflect another process's workload. The estimator combines visible CUDA device identity with whole-GPU memory, utilization and compute-process telemetry. It checks availability before launching a case and checks for contamination during the measurement. A busy selected GPU can be replaced by an eligible selected GPU with the same hardware profile.

The explicit `--force` option permits background activity with no attributable competing compute process. A known foreign compute PID still prevents measurement. Forced results carry a background-sensitive marker through the table and recommendations. Missing whole-GPU telemetry, including unsupported MIG layouts, prevents measurement.

[Estimator command](../docs/commands/cy-batch-estimate.md) · [GPU telemetry and admission](../src/clearml_yolo/adapters/runtime/gpu_inventory.py) · [Case selection](../src/clearml_yolo/entrypoints/batch_estimate.py) · [Telemetry and process cases](../tests/test_gpu_inventory.py) · [Admission and forced reporting](../tests/test_batch_estimate_cli.py) · [Forced-measurement decision](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768)
