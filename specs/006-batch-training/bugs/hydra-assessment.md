# Bug assessment: generated Hydra schema collisions

Date: 2026-10-26. Source: supplied user plan. Verdict: valid. Severity: medium.

Exporting Faster R-CNN ResNet-50 pipeline configuration and composing it produced
three automatic-schema warnings for model, transforms/default and transform_overrides.
The wrapper references pipeline but no pipeline.yaml is exported; ConfigStore currently
supplies it. Cause: public YAML names collide with registered structured configurations.

Remediation uses distinct schema names and explicit YAML schema defaults, ordinary
packaged public defaults, and a complete selected export dependency closure. Preserve
legacy files, precedence, interpolation, validation and force/collision protections.
Affected files: entrypoints/hydra/{configs,common,validation,config_tree}.py and config
tests. Architecture and acceptance are shared with [the feature plan](../plan.md).

Reproduction and original-path checks are tracked in T018/T019. This linked assessment
is kept under feature documentation to preserve installed .specify workflow tooling.
