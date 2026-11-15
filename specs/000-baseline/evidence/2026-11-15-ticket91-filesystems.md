# Ticket 91: local filesystem deduplication

Date: 2026-11-15. Outcome: **deferred**, because successful native reflink and
copy-on-write verification requires a filesystem that supports Linux FICLONE.
The supported local exclusion and preservation checks below passed. No product
code, dependencies, contracts, source datasets, or host mount configuration changed.

## Scope and identities

- Ticket: [91: Verify local filesystem deduplication](../../../.scratch/verification-gap-closure/issues/91-verify-local-filesystem-deduplication.md).
- Requirements: [baseline local cache maintenance](../spec.md#local-cache-maintenance)
  and [deduplication contract](../../../docs/experiment-records.md#explicit-cache-deduplication).
- Source baseline/tip: `bce7df823f85f4c52ad7785ca2800dce691e20c1`, local `master`;
  remote references were not fetched. Unrelated working-tree changes were preserved.
- Product implementation SHA-256:
  `98d2332b733f1c62977297bed21c227f14012ec03c674b980f11b09752240027`.
- Python 3.12.13; Linux `6.18.58.1-microsoft-standard-WSL2`.
- No GPU or service environment was needed. Processes ran with `nice -n 19`,
  `ionice -c3`, two BLAS/OpenMP threads, and at most two pytest workers.

## Native observations

The transient manual probe called the public product API
`clearml_yolo.adapters.storage.dedup.deduplicate` without monkeypatching.
Each probe used a new `TemporaryDirectory(prefix="cy-ticket91-", dir=mount)` as
`CY_HOME`, containing independent `a/image.jpg` and `b/image.jpg` files. Each file
contained `b"native fixture\0" * 4096` (61,440 bytes). The destination was assigned
mode `0640`, fixed timestamps, and the `user.cy-ticket91` xattr. Files are deliberately
not decoded, as required by the filename/byte-based contract.

`findmnt -n -T <owned-directory> -o TARGET,SOURCE,FSTYPE` established each topology.
Recorded inode, device, size, mode, owner/group, mtime, xattrs and SHA-256 were compared
before and after the dry run and real invocation. Reads may update atime under the
contract; native successful-replacement atime restoration remains unverified.

| Observed topology | Actual result | Check status |
| --- | --- | --- |
| Workspace: `/dev/sde1`, ext4, device 2113 | FICLONE returned EOPNOTSUPP | Passed unsupported-operation preservation; successful reflink deferred |
| Root: `/dev/sdd`, ext4, device 2096 | FICLONE returned EOPNOTSUPP | Passed unsupported-operation preservation; successful reflink deferred |
| `/tmp`, tmpfs, device 76 | FICLONE returned EOPNOTSUPP | Passed unsupported-operation preservation; successful reflink deferred |
| C:, E:, F: through 9p, devices 71/72/73 | FICLONE returned EOPNOTSUPP on each | Passed unsupported-operation preservation; successful reflink deferred |

On all six mounts, dry-run found one duplicate without replacing it. Native invocation
reported one unsupported skip, zero reflinks, and zero failures. Both original files
remained byte-identical with the recorded destination metadata and inode preserved;
no temporary `.cy-dedup-*` sibling remained. This establishes absence of copy/hardlink
fallback for the actual unsupported operations; it does not establish successful cloning.

Further native checks passed:

- Existing hardlink destination: one skip, unchanged inode/link identities and bytes.
  File and directory symlinks were excluded from traversal.
- External directory: dry-run allowed, real write rejected with the containment error;
  original bytes, identities and recorded metadata remained unchanged.
- Real cross-device duplicate: an owned tmpfs directory was bind-mounted beneath an
  owned ext4 directory **only inside** `unshare --user --map-root-user --mount`.
  The unmodified product observed distinct `st_dev` values 2113 and 76 and reported
  `Skipped cross-device duplicate`, with zero reflinks/failures and preserved files.
  The subprocess unmounted its bind mount in `finally`, then exited successfully.

Raw product results, identities and cleanup assertions:
[native filesystem evidence](2026-11-15-ticket91-native-filesystems.json).

## Automated checks

Executed through `nice -n 19 ionice -c3 uv run --locked python`, with a temporary
pytest base directory and these child arguments:

```text
python -m pytest tests/test_dedup.py tests/test_dedup_cli.py -n 2 --basetemp <owned-temp> -ra -q
```

Result: **passed**, 30 passed and 1 skipped in 1.67 seconds, exit 0.
The skip is `test_native_reflink_independent_write`, explicitly reporting unsupported
FICLONE. Other tests include simulated clone/error paths; their success is unit
behavior evidence, not native reflink or physical topology evidence.
[Exact output](2026-11-15-ticket91-pytest.txt).

No product mutation or typechecking run was selected for this evidence-only ticket.
The campaign's final automatic pass and independent review are owned by its coordinator.
This focused run does not establish the full suite or global coverage floor.

## Deferred checks and local provisioning limit

Successful native cloning, independent subsequent writes, and successful-replacement
metadata restoration remain **deferred**, not waived. No tested mount supports FICLONE.
`/proc/filesystems` lists XFS, but neither `mkfs.xfs` nor `mkfs.btrfs` is installed.
`sudo -n true` returned exit 1, `interactive authentication is required`; no privileged
filesystem provisioning, packages, kernel modules or host storage changes were attempted.
Unprivileged bind-mount capability does not grant permission to mount an XFS block device.

Resume on a disposable reflink-capable local filesystem, run the existing native test
with its temporary directory on that filesystem, and verify destination metadata and
independent writes through the product API. No external hosts or two-host NFS evidence
are claimed. No product defect was observed, so no defect ticket was created.

## Cleanup and acceptance

All ten manual-probe fixture directories and the separate pytest temporary tree were
removed after assertions and evidence capture. The private bind mount was unmounted;
all probe/pytest processes exited. No input fixture bytes, loop device, filesystem
image, mount, or service remains owned by ticket 91. Only the small dated evidence
files remain; source data and other sessions' resources were untouched.

Ticket 91 is **not accepted** while native reflink success remains deferred. The
unavailable check must run or receive an explicit user waiver before acceptance.
