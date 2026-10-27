# Bug Verification: Explicit Hydra schemas and complete configuration exports

- **Slug**: hydra-schema-export
- **Tested**: 2026-10-26
- **Assessment**: [hydra-assessment.md](hydra-assessment.md)
- **Fix**: [hydra-fix.md](hydra-fix.md)
- **Result**: verified for the bounded configuration repair

## Summary

The original missing local command base and three automatic-schema warnings no longer
reproduce. Fresh exports compose with packaged application defaults disabled. Legacy
trees, lazy interpolation, native overrides, multirun preflight, invalid-setting
rejection, collision protection, publication defaults and replay remain covered.

## Checks Performed

Run from the repository root with the existing frozen environment:

```bash
uv run --frozen --no-sync pytest -q \
  tests/test_config_self_containment.py tests/test_config_tree.py \
  tests/test_model_configs.py tests/test_hydra_transforms.py \
  tests/test_configs.py tests/test_hydra_sweep_configuration.py \
  tests/test_configuration_publication.py tests/test_model_replay.py --tb=short
```

Exit 0: **317 passed**. The 114 command/model matrix entries include both augmentation
profiles for training, all six FCOS backbones and the existing Faster R-CNN-only export
scope. Automatic-schema warnings are errors in the focused regression matrix.
Four pre-existing `hydra_zen` Pydantic deprecation warnings remain outside that category.

```bash
uv run --frozen --no-sync ruff check \
  src/clearml_yolo/entrypoints/hydra/configs.py \
  src/clearml_yolo/entrypoints/hydra/common.py \
  src/clearml_yolo/entrypoints/hydra/config_tree.py \
  src/clearml_yolo/entrypoints/hydra/validation.py \
  tests/test_config_self_containment.py tests/test_config_tree.py tests/test_model_configs.py
uv run --frozen --no-sync mypy \
  src/clearml_yolo/entrypoints/hydra/configs.py \
  src/clearml_yolo/entrypoints/hydra/common.py \
  src/clearml_yolo/entrypoints/hydra/config_tree.py \
  src/clearml_yolo/entrypoints/hydra/validation.py \
  tests/test_config_self_containment.py tests/test_config_tree.py tests/test_model_configs.py
```

Both exited 0. Ruff reported all checks passed; mypy reported no issues in seven files.
Scoped `git diff --check` also exited 0.

## Reproduction Evidence

Before implementation, the first five regression cases failed for the missing
`pipeline.yaml` and automatic schema matching. After implementation, those cases pass
within the combined suite. The subprocess precedence regression failed with
`LOCAL_EPOCHS=100` before the launcher correction and passes with `LOCAL_EPOCHS=23`.

## Residual Risks and Recommendation

This evidence establishes configuration behavior, not training, GPU or publication
outcomes. Private schemas still come from the installed CY package; the exported
application YAML dependency closure is local. Broader feature acceptance remains with
the parent, including canonical architecture checks, paired queue integration and fresh
independent review. No commits or release actions were performed by this bounded task.
