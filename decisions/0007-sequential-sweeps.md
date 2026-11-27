# ADR-0007 · Run a direct Hydra sweep sequentially

A sweep expands one command into a set of experiments. `-m` or configured multirun mode enables Hydra's basic sweeper and launcher. CY checks write destinations for the members before the first job. Each member then has its own command preflight and experiment task. A later invalid value can therefore fail after an earlier job has executed.

CY appends one launch-specific tag to the explicit tags on every member so the tasks can be found together. Concurrent scheduling belongs to the [queue integration](0317-queue-boundary.md). [Configuration guide](../docs/configuration/README.md) · [Sweep expansion](../src/clearml_yolo/entrypoints/hydra/sweeps.py) · [Launch cases](../tests/test_hydra_sweep_configuration.py) · [Grouping tests](../tests/test_multirun_tags.py)
