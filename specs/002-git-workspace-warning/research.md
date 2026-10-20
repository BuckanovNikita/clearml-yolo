# Design decisions

- Use Git rev-parse working-tree detection rather than walking for a .git directory:
  this recognizes linked worktrees, submodules and unborn repositories correctly.
- Check launch cwd before Hydra instead of CY_HOME or package source. These are
  independent locations in current bootstrap, queue replay and ClearML metadata.
- Add a runtime adapter instead of importing ClearML's private Git helper, avoiding
  prohibited peer dependencies and source-identity-specific warnings.
- Reuse observability diagnostics and console capture; do not add logging setup,
  a dependency, a setting or a persistent warning-suppression cache.
- Keep nonzero status/invalid output wording epistemically accurate: Git control
  could not be verified, rather than claiming absence on permissions or trust errors.
