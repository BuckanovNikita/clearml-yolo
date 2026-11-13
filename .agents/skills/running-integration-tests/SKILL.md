---
name: running-integration-tests
description: Use when running live tests or manual native checks, managing an owned test environment, or investigating its failures.
---

# Verify live outcomes

Paths start at the repository root. Read `docs/development.md` (Acceptance tiers)
and `specs/012-own-test-infra/contracts/test-environment.md` before live work.
For this machine, read `.agents/skills/running-integration-tests/references/machine-workflow.md`.
Use `docs/current-contracts.md` to select assertions for the affected claim.

## Execute selected checks

1. Check host capacity and the recorded environment's ownership. Select Task
   `integration` for its automated lifecycle, or explicit comprehensive `acceptance`
   / `release-acceptance`. Focused runs establish only their selected checks.
2. For manual work, use Task `infra-up`, then capture `infra-env` output and check its
   success before evaluating it. Keep credential exports out of logs. Use
   `INTEGRATION_RUN_TAG` explicitly in project names/tags and choose a local workspace.
   The creator later runs `infra-down`; adopters leave deletion to their owner.
3. Preserve failure evidence before teardown. Require infrastructure deletion proof;
   local run outputs remain until deliberately cleaned. Diagnose through lifecycle
   errors and the owned record. Use `verification-workflow` for blocked checks.

## Observe claims automation does not prove

Select only affected observations, comparing actual results with their topic contracts:

- Native execution: CPU/GPU runs with disjoint validation/test inputs and empty images;
  compare direct/queued runs with identical settings when queue integration is affected.
- Publication: independent API readback, forced artifact/model downloads, checkpoint
  loading and identity/threshold comparison; command completion alone proves no upload.
- Charts: render standalone HTML and exercise every affected normalization, legend,
  empty/unknown case, hover, caption and slot identity. API payloads and browser rendering
  establish different layers; embedded ClearML UI is outside the maintained gate.
- FiftyOne App: install its plugin explicitly and inspect affected native views alongside
  database/panel and containment checks.
- Detector/export: select affected matrices in `docs/multi-model-backends.md` and
  `docs/tensorrt-deployment.md`; real export execution and target compatibility remain
  separate from numerical quality or random-weight smoke.

Record source identities, commands, task/model IDs, observations, limitations and cleanup
in native evidence. Simulations do not establish physical multi-GPU, multi-user or NFS
execution. Retain source data and user SDK settings throughout.
