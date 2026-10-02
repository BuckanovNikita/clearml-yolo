# Implementation Plan: FiftyOne Integration

**Branch**: `master` (no branch created) | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Eligible commands publish neutral exact evaluation payloads through a typed publisher. One FiftyOne adapter owns all FiftyOne imports, persistent identity, locks, run-scoped mutation, and receipts.

## Technical Context

Python 3.12; existing Pydantic/pandas/ClearML/digital-metrics plus FiftyOne in main dependencies. Storage is a local persistent FiftyOne DB and task output directories. Validate with pytest, static gates, real FiftyOne smoke, and real pipeline evidence. No UI/media copy; only `cy`, `cy-predict`, `cy-metrics`; pipeline publishes once.

## Constitution Check

PASS: typed Pydantic models, strict import boundary, one ClearML owner, preserved raw artifacts/scoring, and explicit evidence gates satisfy Principles I–IV. Update import-linter rules only as needed for the new package boundary.

## Design

- `clearml_yolo.comparison.evaluation_payload` owns `EvaluationPayload(schema_version=1)` and box/match Pydantic records.
- `clearml_yolo.publishing` owns models, protocol, factory, no-op, and sole FiftyOne adapter. Tasks only use neutral types.
- Reuse key is prefix/schema/effective-GT SHA256. Stored identity additionally records resolved paths, which must validate before reuse; original GT hash is provenance.
- Dataset completion and task-run completion are separate. A per-dataset local lock protects mutation; retries replace only their task-ID namespace.
- Metrics emits exact fixed-threshold digital-metrics status/index/label/confidence/IoU payloads. Raw predictions remain separate; publication never rematches or evaluates.
- Preflight precedes costly work. Pipeline suppresses nested publication and produces one local
  receipt plus a meaningful run-configuration link on success. Visualization setup and
  publication errors warn and continue computation, per the 2026-10-02 clarification;
  setup failure disables visualization for that invocation. Earlier fail-owner intent is superseded.

## Artifacts

- [research.md](research.md), [data-model.md](data-model.md), [publisher contract](contracts/publisher.md), [quickstart.md](quickstart.md)

## Post-Design Constitution Check

PASS. FiftyOne remains observational, no-op stays dependency-free, and real external behavior has dedicated verification tasks.
