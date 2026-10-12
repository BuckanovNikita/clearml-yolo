# Bug Assessment: Hydra device lists fail YAML serialization

- **Slug**: yaml-device-list (generated)
- **Created**: 2026-10-12
- **Source**: pasted user error; CLI clarification
- **Verdict**: valid, reproduced locally
- **Severity**: high — list-valued device requests can prevent training or prediction
- **Baseline**: `25d709b` (`v0.24.1`)

## Report

The user reports `yaml.representer.RepresenterError: ('cannot represent an object',
[-1, -1, -1, -1, -1])`. They identified the command as `vy` and cannot provide more
context; investigation assumes the project's `cy` command. The exact original launch
and full traceback remain unavailable. The user suggested OmegaConf container conversion.

## Reproduction and root cause

An in-memory `OmegaConf.create` configuration with `ultralytics.device=[-1]*5`, passed
through `_device_values`, `requested_devices`, `requested_settings` and
`render_native_yaml`, raises the exact reported exception. No hardware or server is needed.

`entrypoints/hydra/common.py::_device_values` retains `ListConfig` values. Restoring
requested device intent then reintroduces the container into otherwise plain workflow
settings. PyYAML rejects it when writing training/prediction requested-settings snapshots.
ClearML provenance also stringifies it instead of retaining a JSON list. Confidence: high
for this reproduced failure path; the user's complete launch has not been replayed.

## Proposed remediation

Convert configuration-valued device entries to resolved plain containers in
`_device_values`, retaining scalar shape and detaching lists from their Hydra parents.
Keep conversion at the Hydra boundary; do not register global YAML representers or change
SDK code. Preserve requested devices separately from selected execution ordinals.

Files: `src/clearml_yolo/entrypoints/hydra/common.py`, `tests/test_gpu_execution.py`.
Tests must write and read real requested/effective YAML through `_execute_assigned`, cover
direct and remapped execution, and preserve JSON provenance as lists. Include interpolation
resolution, scalar forms, and snapshot independence from later configuration mutation.

## Dependencies, verification and documentation

The parent owns implementation, regression tests and bug records. A bounded read-only
agent independently traced the failure while the parent reproduced it; no dependency
changes are needed. Focused tests and static checks precede fresh independent review;
required full commit/release hooks follow. Preserve exact local uv source overrides.

Review README, runtime/GPU execution and configuration-publication guidance. This restores
the documented list-device and requested/effective snapshot contracts; record a concrete
no-change reason if no user-facing semantics change. Validate bug Markdown and local links.

## Risks and limits

Resolve device interpolation while it still has its Hydra parent. Do not turn list values
into strings or replace requested identities with effective ordinals. Local serialization
checks do not establish five-GPU execution or the user's unavailable full command.
