# Bug Fix: Current dependency minimums

- **Slug**: current-dependency-minimums
- **Fixed**: 2026-10-05
- **Assessment**: [assessment](assessment.md)
- **Status**: applied

## Changes

Raised digital-metrics from >=0.5.3 to >=0.6.0 in pyproject.toml.
report-generator already matches its current version, >=0.1.0.
No dependency source, locked dependency version or submodule revision changed.

## Verification and documentation

uv lock --check --offline and uv sync --locked --offline --dev passed with the
existing local source overrides. Full checks appear in [verification](test.md).
No new implementation-mirroring test is needed for a metadata-only edit.
README.md, docs/development.md and docs/current-contracts.md need no changes:
installation syntax and runtime contracts are unchanged, and dependency minimums
belong in package metadata. The release workflow generates CHANGELOG.md.

## Deviations

Artifacts use bugs/ because project instructions preserve installed .specify/
files. The release uses an isolated master checkout to preserve local changes.

## Corrected implementation after user clarification

On master, fast-forwarded to the published clearml-yolo 0.14.0 baseline.
Set digital-metrics >=0.6.1 and report-generator >=0.1.1 and updated their gitlinks
to upstream release tags v0.6.1 and v0.1.1. No dependency source code was edited.
uv lock --offline updates those two versions and the upstream torchmetrics optional
extra minimum from >=1.0 to >=1.3.1; no other resolved package versions change.
uv sync --locked --offline --dev installs both requested dependency releases.
The main workspace is on master with its exact local source overrides preserved.
The next release is 0.14.1; the isolated old-baseline checkout is no longer used.
