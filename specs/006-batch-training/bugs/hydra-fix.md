# Bug Fix: Explicit Hydra schemas and complete configuration exports

- **Slug**: hydra-schema-export
- **Fixed**: 2026-10-26
- **Assessment**: [hydra-assessment.md](hydra-assessment.md)
- **Status**: applied

## Summary

Public YAML names now extend private `_cy_schemas` registrations explicitly. Fresh
exports include their editable command base and selected application YAML dependencies.
Packaged public defaults support direct commands and existing generated trees without
rewriting user files. No warning filters were added to production code.

## Changes

| File | Change |
| --- | --- |
| `entrypoints/hydra/configs.py` | Register private schemas and a packaged fallback search path; expose detached command fields and export documents. |
| `entrypoints/hydra/defaults/` | Add ordinary public YAML for every command, selected model, profile and overlay, including all six FCOS presets. |
| `entrypoints/hydra/config_tree.py` | Export the command base, selected model and required native default groups; retain collision and force protections. |
| `entrypoints/hydra/common.py` | Read private built-in fields for publication; make the CLI configuration directory the primary source. |
| `entrypoints/hydra/validation.py` | Return the preflighted local source to the launcher without bypassing existing checks. |
| `tests/test_config_self_containment.py` | Cover warnings, disabled fallback, legacy trees, invalid settings, collisions and actual CLI precedence. |
| `tests/test_config_tree.py`, `tests/test_model_configs.py` | Reconcile expected exported files with the expanded dependency closure. |

All runtime paths above are under `src/clearml_yolo/`. The parent retains ownership
of registry, augmentation, architecture and broader feature integration changes.

## Tests Added or Updated

The new regression file initially failed all five missing-base/schema-warning cases
against the original implementation. Its matrix covers every supported command/model
combination and both training profiles with the packaged application fallback disabled.
Legacy tests remove precisely the newly exported files and preserve all remaining bytes.
Explicit invalid settings remain rejected by the existing pipeline validator.

A real CLI subprocess exposed a second precedence issue during implementation:
Hydra appends `--config-dir` after plugin search paths. Before correction, a locally
edited RF-DETR epoch count of 23 was replaced by the packaged value 100. The launcher
now uses the same local directory as its main source; the regression observes 23.

## Local Verification

See [verification](hydra-test.md) for commands and results. Focused configuration,
publication and replay tests, scoped Ruff and strict mypy all passed.

## Deviations from Assessment

The CLI precedence correction is necessary to preserve the assessed local-file
contract after introducing ordinary packaged defaults. It remains within the assessed
configuration modules. Bug artifacts use this feature-owned directory as directed;
installed Spec Kit files remain unchanged.

## Follow-ups

The parent owns user documentation, canonical verification, architecture acceptance,
paired queue verification, independent review and release gates for the whole feature.
