# Implementation plan: automatic multirun tags

## Technical context and decisions

Use existing Python 3.12, Hydra/hydra-zen, OmegaConf and ClearML configuration.
No dependency or configuration-schema change. Scope is three Hydra entrypoint modules.
The only pre-existing change is the local source section in pyproject.toml; preserve it.

Reuse `sweeps.py` for `new_multirun_tag() -> str` and
`tag_multirun_job(config, tag) -> None`: create a UUID4 `multirun-<32 hex digits>`
only when needed, then append it to each concrete job's `clearml.tags` without
replacing user tags. Resolve explicit tags only within the job's Hydra context.
The direct `_launch` closure owns the tag across actual Hydra MULTIRUN callbacks.
Queue `compose_snapshots` owns it across the fully composed batch; `_resolved` applies
it after installing the job's Hydra context and before snapshot serialization.
Ordinary runs do not call the helper; queued execution uses its existing RUN snapshot.
No global variable, environment propagation, callback plugin, SDK change or new module.

## Architecture and constitution check

[architecture.json](architecture.json) maps scope to existing executable dependency
contracts. Entrypoints own configuration mutation and random identity creation; ClearML
adapters retain task/network effects. Direct launches must not import queue adapters.
Reuse current exhaustive graph, SDK ownership, cycle and injected-negative tests.
Typed inward boundaries and explicit invocation ownership remain intact. Historical
constitution queue-policy text is superseded by feature 029's maintained contract;
this task changes no allocation or scheduling policy.

## Workstreams and dependencies

The parent owns all writes and integration. A bounded read-only subagent investigates
launch paths while the parent prepares artifacts. Then regression tests precede code.
Documentation may be inspected alongside test execution. Final independent read-only
review follows parent integration and verification; release follows acceptance.

## Verification and documentation

Run real Hydra subprocess sweeps and queue snapshot regressions, ClearML session tests,
architecture tests, lint-imports, Ruff, mypy and Vulture. Commit hooks run the full suite.
Check README, project/current contracts and queue guidance with Markdown/local-link
validation. No GPU/training behavior changes; no live publication claim is made.
Record dated outcomes in verification.md and reconcile the final diff before acceptance.
