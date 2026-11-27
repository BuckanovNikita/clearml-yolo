# ADR-0404 · Select affected unit tests with testmon

Repeated development runs can use historical dependencies to choose affected tests. The test task fingerprints the environment and uses a worktree-local testmon database. A full unit run executes the unit suite while refreshing that history. Both exclude the live integration tree.

Some distributed and process-capability scenarios have explicit marker invocations. Select them when validating those contracts. Changing the random seed or retrying until green would conceal the original failure. [Unit tasks](../Taskfile.yml) · [Environment fingerprint](../scripts/testmon_environment.py) · [Pytest configuration](../pyproject.toml) · [Operating instructions](../AGENTS.md#checks)
