# Acceptance scenarios

Use the isolated environment procedure in the [end-to-end skill](../../.agents/skills/running-end-to-end-tests/SKILL.md).
For newly tagged direct and queued runs, configure non-default weight decay via YAML and CLI,
inspect run/run_overrides/General before preparation, then observe gt_csv before training and
completed results before later work. Download artifacts and compare to local complete files.
Exercise DDP owner-only callbacks separately; record backend/hardware availability honestly.
Use fresh outputs and explicit ClearML project/tags. Never rewrite historical tasks.
