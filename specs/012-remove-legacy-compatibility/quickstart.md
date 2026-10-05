# Validate the current-only contract

Generate editable examples with `uv run cy-init-config DIRECTORY`, then compose all commands
using their current required inputs. Standalone training needs `ground_truth=truth.csv`.
Comparison overrides use `evaluation.iou_threshold` and `evaluation.matching_strategy`.

Run the documented development gates through uv. Verify missing training input and unsupported
configuration fail with strict current-contract errors. Historical recovery now follows the
[approved recovery contract](contracts/task-recovery.md), superseding its former rejection check.

For native acceptance, follow the [end-to-end guidance](../../.agents/skills/running-end-to-end-tests/SKILL.md)
and its environment prerequisites. Use an isolated tagged ClearML project, explicit project/tags,
task-owned workspace, small disjoint train/val/test data and explicit devices. Train CSV-backed
baseline and candidate runs, download the model/validation threshold table and compare their
current test images. Repeat CSV training against the same cache and check source bytes.
Record real CPU/GPU outcomes, required publication verification and cleanup in dated evidence.

## Recovery compatibility validation (2026-10-05)

Use the existing `cy-compare` baseline/candidate task references and current ground truth;
no new CLI keys or source configuration imports are required. Exercise a historical task
as baseline, as candidate and in both positions. Verify a higher-priority malformed source
fails; explicit maps win; only the chosen checkpoint downloads; task/artifact provenance
has no model link. Compare the same current split images with frozen stored thresholds.
Dashboard recovery must warn for rounded values/unavailable calibration provenance.
Native loading must report incompatible architecture failures instead of silently selecting
another checkpoint. Record actual native checks and unavailable cases in dated evidence.
