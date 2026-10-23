# Implementation Plan: Portable training and extracted queue

**Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved plan as three independent streams after the shared contract gate: queue extraction, model assets, and Agent replay. Parent owns integration, cross-repository checks, documentation, review and release.

## Technical Context

Python >=3.12.13,<3.14; existing uv/uv_build, strict mypy, Ruff, pytest and import-linter. Linux process supervision remains required. CY currently contains queue policy/application/adapters/entrypoints; native replay happens after required-input validation and runtime choice. Existing local tool.uv.sources changes are unrelated and must survive exactly. No dependency revision updates, package publication or distribution builds are routine acceptance steps.

## Constitution Check

Preserve inward dependencies and explicit effect ownership, deferred SDK imports, inert initializers, single invocation-owned task, strict settings and direct-command isolation. Queue extraction is authorized; portable native/Agent claims require real execution. No installed workflow or constitution edits. No gate waiver is inferred from tool availability.

## Project Structure and Architecture

The CY record is [architecture.json](architecture.json). The sibling queue has its own docs/architecture.json because record paths must stay within each repository.

- CY core asset records contain immutable source/identity/checksum descriptions with no effects.
- CY adapters/assets own bounded HTTP, cache, locks, archive extraction and integrity checks; detector adapters own asset selection and native loading. Integration prepares an execution-only model copy and provenance; parent invokes it after canonical publication.
- CY ClearML adapter fetches a detached remote snapshot before runtime construction; entrypoint applies/validates replay, constructs the selected runtime and joins the original task through existing invocation. No queue calls.
- cy_queue core/application retain scheduling rules and ports; outer adapters retain filesystem, GPU and guardian effects. CY integration owns Hydra composition and child command selection.
- Queue may import CY process_tree, supervision, execution_lifecycle, bootstrap, filesystem, diagnostics, presentation, models and Hydra config/validation/sweep helpers. Queue integration may import CY entrypoint/application contracts. CY must never import cy_queue or queue-only Textual/NVML.
- Existing lock/config/storage namespaces and wire records remain unchanged. Snapshot installation identity adds both distributions. Shared acknowledged lifecycle protocol is unchanged.

## Ownership and dependencies

Queue worker owns new sibling repository and removal of CY queue-only modules/tests; it records mixed-file followups for parent. Asset worker owns core/assets.py, adapters/assets, DEIM/RF-DETR/Faster R-CNN adapters and new asset tests. Parent owns common.py, ClearML replay, pyproject/lock, architecture checks, mixed tests, documentation and Spec Kit artifacts. Workers do not delegate. Fresh independent review follows integrated parent verification.

## Verification and documentation

Use uv run --frozen --no-sync for the prepared CY environment. Run complete applicable pytest, Ruff, mypy, Vulture, lint-imports and documentation checks; sibling uses an explicit CY source installation and its own configuration. Exercise HTTP failures/concurrency/offline placement and archive integrity, bare remote entrypoints, package identity and queue train command. Follow end-to-end/environment skills for real training, queue/Agent execution and downloaded publication checks. Live Artifactory remains unavailable.

Update README.md (Russian), docs/queue.md, multi-model-backends.md, filesystem-policy.md, runtime-isolation.md, current-contracts.md, module/import guidance, baseline affected contracts and corp-skills/skills/clearml-yolo/{SKILL.md,references/usage.md,references/evaluation.md}. Reconcile final diff/checks/review and validate both architecture records before release.

## Resumed execution decision, 2026-10-23

The user confirmed that GPU use on this PC is authorized by default unless explicitly
restricted. Background memory therefore does not prevent an authorized small native
verification workload. Production queue admission remains strictly below 2 GiB.

The live queue acceptance harness first observes the unchanged production rule,
then configures the existing real GPU inventory adapter with a bounded higher memory
ceiling only inside its task-owned worker/guardian processes. It preserves actual
telemetry, physical identity, shared coordination, holds/reservations and native
execution. No production source or public queue setting changes. Evidence must name
the test ceiling and distinguish live GPU/guardian/publication outcomes from default
busy-GPU admission. This completes the real execution check without claiming that the
normal production queue admits an occupied GPU under its 2 GiB rule.
