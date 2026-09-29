# Implementation Plan: Explicit Detection Configuration

**Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Centralize project defaults and detection applicability in native_config. Render complete
stage examples with explicit shared references, resolve them through Hydra, then pass only
resolved stage values to execution. Remove helper and comparison defaults and persist both
requested arguments and native effective arguments/normalized target size.

## Technical Context

Python 3.12 CLI; existing uv, Hydra/hydra-zen, Pydantic, PyYAML and locked Ultralytics runtime.
Local YAML/JSON and existing ClearML configuration/artifact storage. Pytest, Ruff, strict
mypy and import-linter are required gates. No new dependencies or performance claims.
Scope: five native model commands and cy-init-config; detection only.

## Constitution Check

Pre/post-design gates pass: preserve layering, required tracking, command ownership,
comment-preserving YAML, explicit nulls, frozen thresholds and paired current-test comparison.
The accepted explicit-reference design retains inheritance through configuration, removes
hidden runtime merges and refines stage relevance. No governance amendment is needed.
External dependency pins remain unchanged. No commit/push; preserve pre-existing files.

## Project Structure

- src/clearml_yolo/native_config.py: applicability, canonical defaults, completeness validation,
  resolved prediction selection, comment-preserving rendering without synthetic entries.
- configs.py and config_tree.py: compose/export the same complete settings, with references.
- inference.py and tasks/: eliminate helper fallbacks, enforce stage ownership and report
  requested versus effective values; comparison models require their native fields.
- tests/: regression cases for generator, composition, invocation and normalization.
- README.md: Russian migration and ownership documentation.

## Design Decisions

Training defaults come from the locked native template plus explicit project overrides.
Prediction shares supported common settings via visible references, except stage-owned
model=null, mode=predict, project=null, name=null, conf=0.001, batch=1, rect=true, save=false.
Prediction-only values are native literals. Generated inactive settings remain comments.
Validate required template keys at execution boundaries, not in the generic projector or
renderer. No sparse execution settings are silently completed. Unknown keys and non-null
cfg fail. Preserve accepted native aliases only when the runtime supports their meaning;
reject aliases that would silently conflict with canonical quantize/end2end semantics.

Keep weights/checkpoint resolution, CSV dataset policy and output routing as explicit
command-owned derivations. A null model in prediction requires weights (or explicit
ultralytics_predict.model), never falls back to the training architecture. Training model
is explicit yolo11n.pt; a null training model fails. Native numeric settings are never
rewritten by wrapper helpers. Native argument/shape normalization remains observable.

## Workflow and Validation

Specify and clarify (accepted conversation) → plan/research/contracts → requirements
checklist review → tasks → read-only analysis → implementation → repository and real-run
verification → convergence → independent review. Extension hooks are empty.

Use failing behavior tests before changes. Run the full repository gates after integration.
Use running-end-to-end-tests and clearml-yolo-environment for real execution and downloaded
ClearML records. Preserve native compilation fallback reporting rather than claiming GPU
compilation from a configured flag alone. Dated evidence distinguishes mocked/native checks.

## Parallel Ownership

Parameter audit is read-only. A configuration implementer may own native_config.py,
config_tree.py, configs.py and their corresponding tests after contracts settle. Parent owns
runtime consumers, integration tests, documentation and feature artifacts. Review is read-only.
