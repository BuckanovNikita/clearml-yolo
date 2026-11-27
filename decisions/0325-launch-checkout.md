# ADR-0325 · Warn when Git cannot identify the launch directory as a working tree

An experiment can use local configurations that are independent of the source checkout recorded on its ClearML task. Operators may want to version those experiment inputs.

**Decision.** The Hydra launch checks the original launch directory with a bounded, read-only Git command, stripping inherited Git environment overrides. It warns and continues when the directory cannot be verified, including when Git is absent.

**Consequences.** An unversioned launch can still run. The warning does not initialize a repository or include raw Git error output. [Script identity](0319-script-identity.md) separately records the checkout containing the installed CY code.

[Launch check](../src/clearml_yolo/adapters/runtime/git_workspace.py) · [Command integration](../src/clearml_yolo/entrypoints/hydra/common.py) · [Probe and warning cases](../tests/test_git_workspace.py) · [Launch contract](../DOCS.md#commands-and-configuration)

The original decision rationale is undocumented in the cited sources.
