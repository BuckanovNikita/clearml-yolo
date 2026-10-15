# Correctness and documentation cleanup — 2026-10-15

## Task contract

Implement the supplied correctness/architecture/documentation plan on Python
`>=3.12.13,<3.14`, retaining uv/uv_build, the current scientific algorithms and
approved dependency sources. Preserve local uv sources and the untracked grid-search
draft. Delivery includes verified task-scoped commits and Git tags/pushes only.

## Routes and ownership

| Work | Native artifacts | Owner and dependencies |
| --- | --- | --- |
| Four shared input defects | [Bug assessment](../../../.specify/bugs/input-evaluation-correctness/assessment.md) | Input implementer; storage/core/application contract first |
| Static architecture blindspots | [Bug assessment](../../../.specify/bugs/architecture-check-blindspots/assessment.md) | Architecture implementer; independent test files |
| Read-only documentation checker | [Feature](../../../specs/033-documentation-checks/spec.md) | Checker implementer; isolated script/tests/dependency hunk |
| Governance, contracts and compression | This record and [architecture](architecture.json) | Parent; final input wording follows implementation |
| Native acceptance and release | Dated verification appended here | Parent after integration, then fresh independent review |

## Tasks

- [x] Inspect instructions, existing changes, workflow and governing contracts.
- [x] Inventory tracked project prose; preserve pre-edit snapshots outside tracked content.
- [x] Reconcile constitution, queue, architecture and input contracts as meaning changes.
- [x] Add linked module, queue and provenance diagrams with rendered review.
- [x] Make the contract index a topic-to-authority-to-check map.
- [x] Compress current prose, then bounded historical batches; retain per-file counts and removal/movement evidence.
- [x] Validate navigation against representative maintenance tasks.
- [x] Update authoritative portable usage skill and its examples/evaluations.
- [x] Run targeted and routine suites, Ruff, mypy, Vulture, import contracts, docs, installed distributions/configuration.
- [x] Run affected native CPU/GPU/ClearML acceptance and download canonical rows.
- [x] Reconcile final diff, records and actual checks; obtain fresh independent review.
- [ ] Commit, evaluate native release, push intended branch/tag and verify refs.

## Acceptance boundaries

No new acceptance claim for five physical GPUs, multi-user/multi-host NFS or CUDA
11.8 targets. Native runs cannot be inferred from mocks. Markdown parsing does not
validate Mermaid grammar; rendered review is separate. Compression preserves IDs,
commands, tables, dates, numerical results, caveats and evidence identities; uncertain
wording remains. Installed workflow assets, generated changelog and symlinks are excluded.
