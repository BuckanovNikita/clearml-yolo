# Implementation and acceptance status

Status is evidence-specific. User-waived obligations are closed while their physical
outcomes remain unverified; completed checkboxes do not establish a hardware result.

| Topic / amendment | Implementation and checks | Release evidence | Acceptance disposition / limits |
| --- | --- | --- | --- |
| Shared queue and acknowledged contraction (029) | [Specification](../specs/029-shared-cy-queue/spec.md), [verification](../specs/029-shared-cy-queue/verification.md), [native checks](../specs/029-shared-cy-queue/native-verification-2026-10-13.md) | [v0.27.0 delivery](../specs/029-shared-cy-queue/release-2026-10-13.md) | [Closed by user waiver](evidence/2026-10-16-acceptance-closure/decision.md); five-GPU and actual multi-user/multi-host NFS outcomes remain unverified, with native failure evidence preserved |
| Test quality and supervision preflight (031) | [Specification](../specs/031-test-quality-gpu-controls/spec.md), [verification](../specs/031-test-quality-gpu-controls/verification.md) | [Initial release](../specs/031-test-quality-gpu-controls/release.md) | [Closed by user waiver](evidence/2026-10-16-acceptance-closure/decision.md); physical multi-GPU/NCCL outcomes remain unverified |
| Per-device generation-fenced free (031 amendment) | [Current operator contract](queue.md#physical-gpu-operator-controls), [verification](../specs/031-test-quality-gpu-controls/gpu-control-simplification/verification.md) | [v0.31.0 delivery](../specs/031-test-quality-gpu-controls/gpu-control-simplification/release.md) | That release did not establish physical multi-GPU, real multi-user/NFS or new ClearML acceptance; the external GPU/NFS obligations are [closed by waiver](evidence/2026-10-16-acceptance-closure/decision.md) |
| Python compatibility (032) | [Contract](../specs/032-python-compatibility/contracts/python.md), [dated matrix](../specs/032-python-compatibility/verification.md) | Same dated matrix records v0.30.0 | Interpreter version alone does not prove Linux supervision capabilities |
| Input correctness, architecture checks and docs (2026-10-15) | [Task ledger](evidence/2026-10-15-correctness-cleanup/plan.md), [input contract](input-provenance.md), [checker feature](../specs/033-documentation-checks/spec.md) | [v0.32.0 delivery](evidence/2026-10-15-correctness-cleanup/delivery.md) | Five-GPU/NFS obligations are [closed by waiver](evidence/2026-10-16-acceptance-closure/decision.md); delivery links completed CPU/single-GPU/ClearML and installed-package checks |
| Readable output, shared configuration and archives (034) | [Specification](../specs/034-readable-shared-queue/spec.md), [verification](../specs/034-readable-shared-queue/verification.md), [review](../specs/034-readable-shared-queue/review.md) | [v0.33.0 delivery](../specs/034-readable-shared-queue/release.md) | Routine checks, real two-user ownership/workers and CPU/single-GPU publication passed; physical multi-GPU, two-host NFS and browser interaction remain unverified |

The constitution's [9.0.0 amendment](../.specify/memory/constitution.md#governance)
reconciles approved queue, backend/export and historical recovery behavior. It changes
governance authority, not historical task outcomes or evidence. Original plans remain
dated intent; their current-status amendments point to the governing contracts.
