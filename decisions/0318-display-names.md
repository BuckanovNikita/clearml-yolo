# ADR-0318 · Resolve readable project-local task and model names

A requested experiment name is meaningful to a reader, but another task or model in the same project can already use it.

**Decision.** Start with the requested name, query for collisions and try readable adjective–noun suffixes when needed. Recheck after writing, coordinate the suffix with the owned model name, and record requested and effective names in `run.display_names`. [File routing](0310-run-routing.md) uses the frozen task identity.

**Consequences.** The display name may acquire a suffix without renaming existing outputs. Resolution has a bounded number of attempts. Readers can use the recorded task and model identities to disambiguate runs independently of display text.

[Collision queries and recheck](../src/clearml_yolo/adapters/clearml/naming.py) · [Collision and retry cases](../tests/test_clearml_naming.py) · [Task naming](../docs/configuration/clearml.md)

The original decision rationale is undocumented in the cited sources.
