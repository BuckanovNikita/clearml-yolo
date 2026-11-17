# Linear migration evidence — 2026-11-17

Project: [P-SIP-1](https://linear.app/sip-ds-team/project/clearml-yolo-5758ab2667aa). Workflow implementation: [SIP-64](https://linear.app/sip-ds-team/issue/SIP-64/migrate-project-workflow-to-linear-and-github-prs-archive-spec-kit). Release-tool replacement: [SIP-63](https://linear.app/sip-ds-team/issue/SIP-63/replace-local-release-integration-with-a-human-merged-github-release).

## Reconciliation and preservation

Inventoried 103 local tickets under `.scratch/verification-gap-closure/issues/`. Campaign status and ticket completion evidence identify 45 accepted tickets (01–29, 86–92, 94–100, 102–103). These remain historical records and were not recreated as active issues. Migrated 58 active tickets (30–85, 93, 101). Original ticket files were not edited or removed. The old Markdown tracker is superseded; update Linear from now on.

Full ticket requirements, acceptance checkboxes and discussion were transferred. Active execution paragraphs now use Linear and GitHub PRs instead of Spec Kit; archive references retain historical provenance. Standing ticket branch/PR authorization replaces obsolete campaign push prohibitions; deployment and release remain separately authorized. No GPU work or infrastructure operation was executed by this migration.

GPU dispatch remains paused by local ticket101 / SIP-62. The pause blocks GPU execution for 30–85; harmless CPU preparation may continue within existing limits. Export tickets also depend on their qualifying checkpoint. Final reconciliation depends on all remaining campaign work. Historical accepted prerequisites remain in descriptions, not live blockers. Established 125 live dependency edges.

## Verification

- Passed: project list readback returned exactly 60 issues (58 migrated, release follow-up, workflow migration), with no additional page.
- Passed: full get_issue readback for all 58 migrated issues confirmed source identifiers, acceptance checkbox counts and all expected blocking relationships. Large relation arrays return at most 50 entries; remaining reconciliation edges were confirmed from the prerequisite's inverse blocks relation. Connector Markdown normalization changes checked boxes to uppercase X; byte identity is not claimed.
- Passed: initial workspace lookup found no existing migrated source paths; each source was created once. Future retries must match the source path before creating an issue.
- Native/GPU acceptance: not executed; historical successful checks and ongoing failures retain their original limitations. Migration closes no campaign ticket.
- Instruction verification and independent review: see [workflow transition evidence](2026-11-17-workflow-transition.md).
- Delivery follow-up: the user authorized commit and PR creation. Task-owned changes are prepared in an isolated worktree; committed-tip results and the PR link are recorded in SIP-64 and the PR. Migration completion does not imply a human merge.

## Source mapping

| Original source | Linear issue |
| --- | --- |
| `.scratch/verification-gap-closure/issues/30-rf-detr-large-json-verification.md` | [SIP-5](https://linear.app/sip-ds-team/issue/SIP-5/rf-detr-large-json-verification) |
| `.scratch/verification-gap-closure/issues/31-rf-detr-large-json-mosaic-verification.md` | [SIP-6](https://linear.app/sip-ds-team/issue/SIP-6/rf-detr-large-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/32-faster-r-cnn-resnet50-fpn-native-verification.md` | [SIP-7](https://linear.app/sip-ds-team/issue/SIP-7/faster-r-cnn-resnet50-fpn-native-verification) |
| `.scratch/verification-gap-closure/issues/33-faster-r-cnn-resnet50-fpn-json-verification.md` | [SIP-8](https://linear.app/sip-ds-team/issue/SIP-8/faster-r-cnn-resnet50-fpn-json-verification) |
| `.scratch/verification-gap-closure/issues/34-faster-r-cnn-resnet50-fpn-json-mosaic-verification.md` | [SIP-9](https://linear.app/sip-ds-team/issue/SIP-9/faster-r-cnn-resnet50-fpn-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/35-faster-r-cnn-resnet101-fpn-native-verification.md` | [SIP-10](https://linear.app/sip-ds-team/issue/SIP-10/faster-r-cnn-resnet101-fpn-native-verification) |
| `.scratch/verification-gap-closure/issues/36-faster-r-cnn-resnet101-fpn-json-verification.md` | [SIP-11](https://linear.app/sip-ds-team/issue/SIP-11/faster-r-cnn-resnet101-fpn-json-verification) |
| `.scratch/verification-gap-closure/issues/37-faster-r-cnn-resnet101-fpn-json-mosaic-verification.md` | [SIP-12](https://linear.app/sip-ds-team/issue/SIP-12/faster-r-cnn-resnet101-fpn-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/38-faster-r-cnn-convnext-tiny-native-verification.md` | [SIP-13](https://linear.app/sip-ds-team/issue/SIP-13/faster-r-cnn-convnext-tiny-native-verification) |
| `.scratch/verification-gap-closure/issues/39-faster-r-cnn-convnext-tiny-json-verification.md` | [SIP-14](https://linear.app/sip-ds-team/issue/SIP-14/faster-r-cnn-convnext-tiny-json-verification) |
| `.scratch/verification-gap-closure/issues/40-faster-r-cnn-convnext-tiny-json-mosaic-verification.md` | [SIP-15](https://linear.app/sip-ds-team/issue/SIP-15/faster-r-cnn-convnext-tiny-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/41-faster-r-cnn-swin-tiny-native-verification.md` | [SIP-16](https://linear.app/sip-ds-team/issue/SIP-16/faster-r-cnn-swin-tiny-native-verification) |
| `.scratch/verification-gap-closure/issues/42-faster-r-cnn-swin-tiny-json-verification.md` | [SIP-17](https://linear.app/sip-ds-team/issue/SIP-17/faster-r-cnn-swin-tiny-json-verification) |
| `.scratch/verification-gap-closure/issues/43-faster-r-cnn-swin-tiny-json-mosaic-verification.md` | [SIP-18](https://linear.app/sip-ds-team/issue/SIP-18/faster-r-cnn-swin-tiny-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/44-faster-r-cnn-dinov2-small-native-verification.md` | [SIP-19](https://linear.app/sip-ds-team/issue/SIP-19/faster-r-cnn-dinov2-small-native-verification) |
| `.scratch/verification-gap-closure/issues/45-faster-r-cnn-dinov2-small-json-verification.md` | [SIP-20](https://linear.app/sip-ds-team/issue/SIP-20/faster-r-cnn-dinov2-small-json-verification) |
| `.scratch/verification-gap-closure/issues/46-faster-r-cnn-dinov2-small-json-mosaic-verification.md` | [SIP-21](https://linear.app/sip-ds-team/issue/SIP-21/faster-r-cnn-dinov2-small-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/47-faster-r-cnn-dinov3-small-native-verification.md` | [SIP-22](https://linear.app/sip-ds-team/issue/SIP-22/faster-r-cnn-dinov3-small-native-verification) |
| `.scratch/verification-gap-closure/issues/48-faster-r-cnn-dinov3-small-json-verification.md` | [SIP-23](https://linear.app/sip-ds-team/issue/SIP-23/faster-r-cnn-dinov3-small-json-verification) |
| `.scratch/verification-gap-closure/issues/49-faster-r-cnn-dinov3-small-json-mosaic-verification.md` | [SIP-24](https://linear.app/sip-ds-team/issue/SIP-24/faster-r-cnn-dinov3-small-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/50-fcos-resnet50-fpn-native-verification.md` | [SIP-25](https://linear.app/sip-ds-team/issue/SIP-25/fcos-resnet50-fpn-native-verification) |
| `.scratch/verification-gap-closure/issues/51-fcos-resnet50-fpn-json-verification.md` | [SIP-26](https://linear.app/sip-ds-team/issue/SIP-26/fcos-resnet50-fpn-json-verification) |
| `.scratch/verification-gap-closure/issues/52-fcos-resnet50-fpn-json-mosaic-verification.md` | [SIP-27](https://linear.app/sip-ds-team/issue/SIP-27/fcos-resnet50-fpn-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/53-fcos-resnet101-fpn-native-verification.md` | [SIP-28](https://linear.app/sip-ds-team/issue/SIP-28/fcos-resnet101-fpn-native-verification) |
| `.scratch/verification-gap-closure/issues/54-fcos-resnet101-fpn-json-verification.md` | [SIP-29](https://linear.app/sip-ds-team/issue/SIP-29/fcos-resnet101-fpn-json-verification) |
| `.scratch/verification-gap-closure/issues/55-fcos-resnet101-fpn-json-mosaic-verification.md` | [SIP-30](https://linear.app/sip-ds-team/issue/SIP-30/fcos-resnet101-fpn-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/56-fcos-convnext-tiny-native-verification.md` | [SIP-31](https://linear.app/sip-ds-team/issue/SIP-31/fcos-convnext-tiny-native-verification) |
| `.scratch/verification-gap-closure/issues/57-fcos-convnext-tiny-json-verification.md` | [SIP-32](https://linear.app/sip-ds-team/issue/SIP-32/fcos-convnext-tiny-json-verification) |
| `.scratch/verification-gap-closure/issues/58-fcos-convnext-tiny-json-mosaic-verification.md` | [SIP-33](https://linear.app/sip-ds-team/issue/SIP-33/fcos-convnext-tiny-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/59-fcos-swin-tiny-native-verification.md` | [SIP-34](https://linear.app/sip-ds-team/issue/SIP-34/fcos-swin-tiny-native-verification) |
| `.scratch/verification-gap-closure/issues/60-fcos-swin-tiny-json-verification.md` | [SIP-35](https://linear.app/sip-ds-team/issue/SIP-35/fcos-swin-tiny-json-verification) |
| `.scratch/verification-gap-closure/issues/61-fcos-swin-tiny-json-mosaic-verification.md` | [SIP-36](https://linear.app/sip-ds-team/issue/SIP-36/fcos-swin-tiny-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/62-fcos-dinov2-small-native-verification.md` | [SIP-37](https://linear.app/sip-ds-team/issue/SIP-37/fcos-dinov2-small-native-verification) |
| `.scratch/verification-gap-closure/issues/63-fcos-dinov2-small-json-verification.md` | [SIP-38](https://linear.app/sip-ds-team/issue/SIP-38/fcos-dinov2-small-json-verification) |
| `.scratch/verification-gap-closure/issues/64-fcos-dinov2-small-json-mosaic-verification.md` | [SIP-39](https://linear.app/sip-ds-team/issue/SIP-39/fcos-dinov2-small-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/65-fcos-dinov3-small-native-verification.md` | [SIP-40](https://linear.app/sip-ds-team/issue/SIP-40/fcos-dinov3-small-native-verification) |
| `.scratch/verification-gap-closure/issues/66-fcos-dinov3-small-json-verification.md` | [SIP-41](https://linear.app/sip-ds-team/issue/SIP-41/fcos-dinov3-small-json-verification) |
| `.scratch/verification-gap-closure/issues/67-fcos-dinov3-small-json-mosaic-verification.md` | [SIP-42](https://linear.app/sip-ds-team/issue/SIP-42/fcos-dinov3-small-jsonmosaic-verification) |
| `.scratch/verification-gap-closure/issues/68-qualify-resnet50-fpn-checkpoint.md` | [SIP-43](https://linear.app/sip-ds-team/issue/SIP-43/qualify-resnet50-fpn-checkpoint) |
| `.scratch/verification-gap-closure/issues/69-qualify-resnet101-fpn-checkpoint.md` | [SIP-44](https://linear.app/sip-ds-team/issue/SIP-44/qualify-resnet101-fpn-checkpoint) |
| `.scratch/verification-gap-closure/issues/70-qualify-convnext-tiny-checkpoint.md` | [SIP-45](https://linear.app/sip-ds-team/issue/SIP-45/qualify-convnext-tiny-checkpoint) |
| `.scratch/verification-gap-closure/issues/71-qualify-swin-tiny-checkpoint.md` | [SIP-46](https://linear.app/sip-ds-team/issue/SIP-46/qualify-swin-tiny-checkpoint) |
| `.scratch/verification-gap-closure/issues/72-qualify-dinov2-small-checkpoint.md` | [SIP-47](https://linear.app/sip-ds-team/issue/SIP-47/qualify-dinov2-small-checkpoint) |
| `.scratch/verification-gap-closure/issues/73-qualify-dinov3-small-checkpoint.md` | [SIP-48](https://linear.app/sip-ds-team/issue/SIP-48/qualify-dinov3-small-checkpoint) |
| `.scratch/verification-gap-closure/issues/74-resnet50-fpn-fp32-export-verification.md` | [SIP-49](https://linear.app/sip-ds-team/issue/SIP-49/resnet50-fpn-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/75-resnet50-fpn-fp16-export-verification.md` | [SIP-50](https://linear.app/sip-ds-team/issue/SIP-50/resnet50-fpn-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/76-resnet101-fpn-fp32-export-verification.md` | [SIP-51](https://linear.app/sip-ds-team/issue/SIP-51/resnet101-fpn-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/77-resnet101-fpn-fp16-export-verification.md` | [SIP-52](https://linear.app/sip-ds-team/issue/SIP-52/resnet101-fpn-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/78-convnext-tiny-fp32-export-verification.md` | [SIP-53](https://linear.app/sip-ds-team/issue/SIP-53/convnext-tiny-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/79-convnext-tiny-fp16-export-verification.md` | [SIP-54](https://linear.app/sip-ds-team/issue/SIP-54/convnext-tiny-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/80-swin-tiny-fp32-export-verification.md` | [SIP-55](https://linear.app/sip-ds-team/issue/SIP-55/swin-tiny-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/81-swin-tiny-fp16-export-verification.md` | [SIP-56](https://linear.app/sip-ds-team/issue/SIP-56/swin-tiny-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/82-dinov2-small-fp32-export-verification.md` | [SIP-57](https://linear.app/sip-ds-team/issue/SIP-57/dinov2-small-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/83-dinov2-small-fp16-export-verification.md` | [SIP-58](https://linear.app/sip-ds-team/issue/SIP-58/dinov2-small-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/84-dinov3-small-fp32-export-verification.md` | [SIP-59](https://linear.app/sip-ds-team/issue/SIP-59/dinov3-small-fp32-export-verification) |
| `.scratch/verification-gap-closure/issues/85-dinov3-small-fp16-export-verification.md` | [SIP-60](https://linear.app/sip-ds-team/issue/SIP-60/dinov3-small-fp16-export-verification) |
| `.scratch/verification-gap-closure/issues/93-reconcile-campaign-evidence-and-clean-up.md` | [SIP-61](https://linear.app/sip-ds-team/issue/SIP-61/reconcile-campaign-evidence-and-clean-up) |
| `.scratch/verification-gap-closure/issues/101-diagnose-gpu-telemetry-timeout.md` | [SIP-62](https://linear.app/sip-ds-team/issue/SIP-62/diagnose-gpu-telemetry-timeout-during-ticket15-admission) |
