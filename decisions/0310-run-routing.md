# ADR-0310 · Route result directories by task identity or explicit destination

Several experiments can share a workspace and the same requested display name. Users also need to feed an existing run directory into a later pipeline stage.

**Decision.** The default result root encodes the ClearML project, task name and task ID as safe path components. Pipeline `run_dir` takes precedence over `run_id`; explicit destinations still satisfy [write containment](0309-workspace-containment.md). Reusing a directory preserves its contents. Pipeline runs and default-routed training update `runs/latest`.

**Consequences.** The task ID disambiguates independent runs. The latest-run link is replaced atomically; a pre-existing ordinary file or directory at that name is moved aside with its contents. A link update error produces a warning. Stage destinations and Hydra composition logs have separate layouts.

[Run identities and latest link](../src/clearml_yolo/adapters/storage/run_identity.py) · [Routing and displacement cases](../tests/test_run_identity.py) · [Stage directory layout](../docs/workspace.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/7ef1c10ab4d633d4b9535aef24167bdb5c5247da)
