# Implementation Plan: Local dependency copies

Use the existing uv editable paths and lockfile. Remove submodule registration and
move local .git pointer files into parent Git metadata for recovery, retaining all
source files and upstream object databases. Ignore only the two dependency paths.
No application behavior, new data model, dependency update or runtime API changes.

## Constitution Check

Preserve dependency contents and resolved versions; use normal hooks and the
existing master release workflow. No installed workflow files change. Extension
configuration has no hooks. Use explicit feature paths rather than modifying
.specify/feature.json. The user has authorized implementation, commit and release.

## Documentation Scope

Update docs/development.md, the current contract index, active dependency spec and
setup quickstarts. Preserve dated history and README's established usage-only scope.
Validate Markdown, local links and setup/import behavior. Record dated verification.

## Verification

Snapshot dependency contents before conversion and compare afterward. Check Git
index modes, ignored paths, TOML, editable imports, locked sync, full repository
hooks and the final branch/tag refs. Parent owns edits and verification; bounded
agents own read-only investigation and a fresh final review.
