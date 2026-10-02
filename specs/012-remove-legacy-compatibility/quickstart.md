# Validate the current-only contract

Generate editable examples with `uv run cy-init-config DIRECTORY`, then compose all commands
using their current required inputs. Standalone training needs `ground_truth=truth.csv`.
Comparison overrides use `evaluation.iou_threshold` and `evaluation.matching_strategy`.

Run the documented development gates through uv. Verify missing training input, historical-only
publications and unsupported configuration fail with strict current-contract errors.

For native acceptance, follow the [end-to-end guidance](../../.agents/skills/running-end-to-end-tests/SKILL.md)
and its environment prerequisites. Use an isolated tagged ClearML project, explicit project/tags,
task-owned workspace, small disjoint train/val/test data and explicit devices. Train CSV-backed
baseline and candidate runs, download the model/validation threshold table and compare their
current test images. Repeat CSV training against the same cache and check source bytes.
Record real CPU/GPU outcomes, required publication verification and cleanup in dated evidence.
