# Implementation plan: cleanup and baseline reset

## Technical context and constitution check

Retain Python >=3.12.13,<3.14, uv/uv_build, current lint/type/test configuration,
approved external dependencies, CLI and persisted/publication contracts. The user's
explicit approved history reset supersedes ordinary preservation-in-checkout rules;
original documents remain immutable in Git. No workflow tooling is modified.

## Architecture

[Architecture record](architecture.json) covers pure core policy/names, runtime process/GPU
adapters, queue lock ownership, test consumers and byte-identical fixture moves. Existing
`.importlinter` and architecture positive/negative tests enforce inward imports, SDK/effect
ownership, dynamic targets and inert initialization. No interfaces or owners are added.
Existing feature 036 and configuration-split records continue owning their prior changes.

## Implementation and dependencies

1. Capture pre-existing work, create native specification/plan/tasks, validate architecture.
2. Resume feature036 live acceptance through an exclusive bounded agent; parent preserves its source.
3. Remove proven orphan helpers and move historical fixtures without regenerating expectations.
4. In parallel author cleanup-code in its maintained personal repository; no shared source writes.
5. Draft stage-zero current requirements and historical mapping before any deletion.
6. Parent integrates, runs affected/full checks, records documentation and obtains fresh review.
7. Commit all retiring history and accepted source as checkpoint H, following native hooks.
8. Cut over documentation to 000-baseline and immutable H references; remove archived history,
   clear local feature selection, verify 001 discovery and final docs/fixture behavior.
9. Validate documentation-only cutover through a no-impact stdin record. Commit/push authorized
   changes and Git version tags; release/install only the new personal skill.

## Documentation stage

Affected: baseline; current-contract index; project/technical/development/import/static/queue/DDP/
backend/export guidance; README (Russian); constitution navigation only; project end-to-end skill;
portable corp-skills clearml-yolo references. Retain current topic guides as authority where already
established. Preserve pending, waived and unavailable verification states. Old contracts are
reconciled by current topic, not concatenated. Final cutoff results live in the baseline.

## Acceptance and stopping conditions

Use frozen/no-sync tools in the prepared environment. Run Ruff, mypy, Vulture, import contracts,
affected and full pytest, documentation checks, native acceptance and required hooks. Verify
fixture hashes, archived bytes/SHA paths, intact tooling and next feature 001. Independent review
follows integration and checks. Missing required live checks block source acceptance/release and
history removal; useful independent skill/document preparation continues. No new packages,
GitHub Releases, deployment, unrelated cleanup or dependency refresh.

## Published-work reconciliation

Delivery preflight discovered origin/master ahead at
`41a4036666b2225a4e3029e1695499cf914a5f59`, including released feature 036 and
037-early-accurate-publication (v0.35.0). Preserve the reviewed local work on an
isolated branch with ordinary checks, merge the published ancestry, reconcile
conflicts and the baseline against that implementation, then run affected/full
checks and fresh review before final H and cutover. Do not overwrite published
work or reuse its version tag. The interrupted initial commit created no commit.
