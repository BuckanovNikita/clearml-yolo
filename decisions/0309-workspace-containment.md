# ADR-0309 · Resolve project writes beneath the selected workspace

Hydra, native training and helper processes can resolve relative paths at different times. A symlink can turn a path that looks local into an external write.

**Decision.** At startup CY freezes `CY_HOME` to an absolute root, defaulting to the launch directory. Project write destinations must physically resolve beneath that root, including native output overrides and an explicit scratch root. Library-owned caches, configuration and external read-only inputs keep their own locations.

**Consequences.** An output directed through a symlink outside the workspace raises a containment error. Changing `CY_HOME` selects another project workspace. The separate [scratch](0311-runtime-scratch.md) and [result routing](0310-run-routing.md) contracts define the contained destinations. Library selectors such as `HOME`, XDG and temporary-directory variables retain the user's values.

[Workspace bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py) · [Composed destination validation](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Native route containment](../tests/test_native_output_containment.py) · [Workspace guide](../docs/workspace.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/28b74f72054889c4b0706fecb8983c0ed6196235)
