# Release fixture leaks unrelated TOML tables

**Date**: 2026-11-01
**Verdict**: Valid; medium severity, bounded remediation
**Source**: Local cleanup audit and approved specification; no supplied URL or external fetch.

## Symptom and reproduction

The protected-lock release test failed when local tool.uv.sources followed semantic-release settings in the source pyproject.

The prior read-only audit reproduced this observation. The implementation agent
must record a focused automated failing regression against the isolated current
source before applying the fix. This report does not claim that later check ran.

## Root cause

release_repo slices all text after the semantic_release header, copying unrelated later TOML tables into its supposedly isolated project.

## Proposed remediation

Extract only semantic-release table sections and children with standard-library parsing checks. Preserve unrelated source tables untouched and retain real hooks and protected-lock assertions.

## Files likely to change

tests/test_local_release.py

## Tests and acceptance

Exercise source layouts with and without local sources and similarly named unrelated tables; verify exact protected-lock bytes and real hook/recovery behavior.

## Architecture and risks

Use the cleanup [architecture record](../../../specs/010-cleanup/architecture.json)
and [ledger](../../../specs/010-cleanup/tasks.md). No SDK/IO effects are added to
core or previews; test projects remain isolated. Public metadata, validation order
and exact absence semantics remain compatibility constraints. A new failure outside
this diagnosis requires reassessment, not weakened assertions. Record actual changes
and checks in adjacent fix.md and test.md after execution. Project-owned bug records
use the established docs/bugs location without changing installed workflow files.
