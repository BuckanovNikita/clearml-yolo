# Delivery — 2026-10-16

Application **0.34.0** and portable usage collection **0.2.8** are published as
annotated Git tags. Each repository's branch and tag were pushed atomically; remote
branch, tag object and peeled tag references matched the local counterparts.
No GitHub Release, release asset or registry package was published.

## Delivered behavior

Every queue user must fill the selected TOML file with name, metadata root and
coordination root. Without CY_QUEUE_CONFIG, discovery uses absolute XDG_CONFIG_HOME,
otherwise HOME/.config (account home when HOME is absent/empty), then
clearml-yolo/queue.toml. An explicit absolute override remains supported.
Missing/incomplete settings fail without creating queue state; help remains available.

The blanket NFS coordination rejection is replaced with effective mount validation:
NFS/NFSv4 requires hard I/O and host-local flock (local_lock=flock or all), without
soft, softerr or nosharecache. Existing protected bindings and legacy recovery evidence
still prevent online relocation. The [setup contract](../../docs/queue.md#shared-configuration)
describes shared-client/mount/PID/bootstrap assumptions and outage limits.

## Verification and preservation

- Full suite: 2,959 passed, 30 skipped, seven deselected. Separate settings, CLI,
  process/supervision/recovery tests and 227 architecture tests passed.
- All 43 import contracts, Ruff, strict mypy and Vulture passed. Documentation/local
  links and isolated CLI examples passed. Fresh independent application and companion
  reviews accepted their scopes; see [review](review.md) and [verification](verification.md).
- Feature and automatic release commits passed their required hooks. The annotated
  application version tag points to the checked release commit.
- The final 0.34.0 wheel and source distribution were installed and checked outside
  the source checkout. Each passed 12 command helps, nine configuration selections,
  model variants, composition, overwrite preservation and read-only required
  user/shared queue settings. Temporary installation/build resources were removed.
- The companion passed metadata/packaged links, discovery without installation,
  Markdown, isolated examples, fresh native-agent scenarios and no-impact architecture
  acceptance. Its [released guidance](https://github.com/BuckanovNikita/corp-skills/tree/v0.2.8/skills/clearml-yolo)
  and [dated evidence](https://github.com/BuckanovNikita/corp-skills/blob/v0.2.8/verification/2026-10-16-queue-user-config-nfs.md)
  correspond to the application release. Installed skill copies were not replaced.
- The original local uv source section and unrelated user draft were preserved exactly.
  Dependency sources/pins are unchanged; only the root package version changed in
  the lockfile. No production queue state, mounts, users or services were changed.

## Limits

No actual NFS mount was available. Simulated mountinfo tests verify library eligibility,
not remote locking, reconnect, server restart, outage or multi-host behavior. The user
explicitly scoped this request to the library rejection and per-user config setup.
No new native GPU/ML outcome or live OpenCode/target-model result is claimed.
