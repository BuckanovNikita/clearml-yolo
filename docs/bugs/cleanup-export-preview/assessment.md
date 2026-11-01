# Export preview omits required input checks

**Date**: 2026-11-01
**Verdict**: Valid; medium severity, bounded remediation
**Source**: Local cleanup audit and approved specification; no supplied URL or external fetch.

## Symptom and reproduction

Preview accepted resolved missing-input configurations for onnx, build and verify while runtime correctly raised its existing ValueError messages.

The prior read-only audit reproduced this observation. The implementation agent
must record a focused automated failing regression against the isolated current
source before applying the fix. This report does not claim that later check ran.

## Root cause

The preview validates ExportSettings shape but omits the existing operation-specific validate_input_presence policy invoked by export execution.

## Proposed remediation

Share the existing pure predicate in core/export_requests.py; retain the method and exact order/messages/is-not-None semantics. Preview defers unresolved presence without external resolution and still rejects independently known absence.

## Files likely to change

src/clearml_yolo/core/export_requests.py; src/clearml_yolo/entrypoints/documentation/validation.py; tests/test_docs_validation.py

## Tests and acceptance

Missing operation inputs must fail before and pass after remediation; valid and unresolved cases, runtime errors, no effects and full configuration compatibility remain checked.

## Architecture and risks

Use the cleanup [architecture record](../../../specs/010-cleanup/architecture.json)
and [ledger](../../../specs/010-cleanup/tasks.md). No SDK/IO effects are added to
core or previews; test projects remain isolated. Public metadata, validation order
and exact absence semantics remain compatibility constraints. A new failure outside
this diagnosis requires reassessment, not weakened assertions. Record actual changes
and checks in adjacent fix.md and test.md after execution. Project-owned bug records
use the established docs/bugs location without changing installed workflow files.
