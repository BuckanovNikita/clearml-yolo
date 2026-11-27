# ADR-0405 · Measure branch coverage on the full unit suite

An affected-test selection cannot establish the repository's coverage floor. The coverage task runs the full unit scope with branch measurement, writes worktree-local coverage data and enforces the configured threshold. It excludes the integration tree.

A passing coverage run supports a coverage claim for those sources and tests. The separate [acceptance workflow](0410-acceptance.md) adds live service evidence when needed. [Coverage invocation](../Taskfile.yml) · [Coverage settings](../pyproject.toml) · [Verification policy](../AGENTS.md#checks)
