# Delivery — 2026-10-16

Application **0.33.0** and portable usage collection **0.2.7** are published as
annotated Git tags. The application master branch and tag, and the companion main
branch and tag, were pushed atomically in their respective repositories. Remote
branch, tag object and peeled tag references matched their local counterparts.
No GitHub Release object, release asset or registry package was published.

## Delivered behavior

- Human CLI, TUI, console and report labels use readable names and distinct aliases;
  queue references use durable job numbers. Exact machine provenance, hyperlink
  targets and original invocation captures remain available through their documented
  interfaces. Scalar aliases remain stable across updates.
- Owner-controlled archive and restore hide obsolete terminal jobs without deleting
  history or changing execution state. Recovery-required jobs resurface automatically.
- File storage is retained. Required `CY_QUEUE_CONFIG` selects one shared TOML file
  with explicit metadata and host-local coordination locations. Frozen settings and
  a protected host binding prevent cooperating users from selecting independent locks.

Follow the [queue configuration and migration instructions](../../docs/queue.md#shared-configuration)
before using the upgraded queue. Configure every participating user and worker;
retain existing metadata and coordination locations. Scripts consuming machine
mutation output must add `--json`.

## Acceptance and preservation

- The complete final feature suite passed 2,927 tests; 30 were skipped and seven
  deselected. Ruff, strict mypy, Vulture, all 43 import contracts and negative
  architecture cases passed. Independent queue, output and usage reviews accepted
  their final scopes after all reproduced findings were corrected.
- Both the feature commit and native release commit passed their required hooks,
  including complete pytest runs. Integration onto the separately released 0.32.1
  preserved its ten-minute finalization setting; 183 affected tests passed afterward.
  No other feature source or test changed during that integration.
- Final 0.33.0 wheel and source-distribution builds were installed separately outside
  the checkout. Both passed all 12 command helps, nine configuration selections,
  alternate model families, Hydra composition, overwrite preservation and read-only
  shared settings checks.
- [Real two-user acceptance](multiuser-evidence.md) verified separate Unix identities,
  permissions, owner actions, concurrent submissions, workers/guardians and cleanup,
  including injected-failure cleanup. Its GPU facts were synthetic.
- [Native acceptance](native-evidence.md) verified CPU and single-GPU validation,
  active ClearML readback, artifact downloads, exact provenance recovery, distinct
  labels and original capture receipts. All task-owned service records were removed.
- [Independent review](review.md), [verification](verification.md) and the reconciled
  [architecture record](architecture.json) provide the acceptance trail. Final
  documentation/link and architecture validation passed before the delivery-record
  commit. The companion passed Markdown, discovery, frontmatter, local-link and
  no-impact architecture checks; its source tree is clean after publication.
- The unrelated grid-search draft and original local editable-source section were
  preserved exactly. Dependency pins and sources were unchanged; the release changed
  only the root application version in the lockfile. The temporary users, installation
  environments and merged feature worktree were removed. Dated raw check evidence
  remains outside the repository. Existing services and GPU workloads were preserved.

The portable guidance is published in
[corp-skills 0.2.7](https://github.com/BuckanovNikita/corp-skills/tree/v0.2.7/skills/clearml-yolo),
with its [dated verification](https://github.com/BuckanovNikita/corp-skills/blob/v0.2.7/verification/2026-10-16-readable-shared-queue.md).
Installed skill copies were not replaced.

## Limits

Physical multi-GPU execution, two-host NFS and browser interaction were not exercised.
Textual pilot/link tests cover the changed TUI boundaries. Synthetic fixtures establish
execution and publication contracts, not model accuracy. Skill scenarios do not
establish automatic routing or live OpenCode/DeepSeek behavior. Historical waivers
remain scoped to their original targets. Production queue configuration was not changed.
