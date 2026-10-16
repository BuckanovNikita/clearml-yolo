# Research: configuration and NFS eligibility

Date: 2026-10-16.

## Configuration discovery

Use the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir/latest/):
absolute XDG_CONFIG_HOME selects config home; empty or relative values fall back to
HOME/.config. An explicit CY_QUEUE_CONFIG retains priority. Every user must supply
required settings; defaulting the filename does not default storage or create a file.
A shared absolute override remains useful for service/login environments.

## NFS lock lifetime

The existing GPU lease keeps a flock descriptor open without ongoing file I/O.
Default server-side NFS locks can be lost without asynchronous notification; simply
allowlisting NFS would weaken reservation lifetime. Keep the existing protocol and
require host-local flock via effective local_lock=flock/all, reliable hard I/O and
shared inode cache (reject nosharecache). Read superblock options from mountinfo,
not requested fstab options. Linux NFSv4 also uses nfs_flock and local-lock dispatch.

Sources: [NFS mount semantics](https://man7.org/linux/man-pages/man5/nfs.5.html),
[flock](https://man7.org/linux/man-pages/man2/flock.2.html),
[lost locks](https://man7.org/linux/man-pages/man2/fcntl_locking.2.html),
[mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html),
[Linux NFS file operations](https://github.com/torvalds/linux/blob/master/fs/nfs/file.c),
[NFSv4 operations](https://github.com/torvalds/linux/blob/master/fs/nfs/nfs4file.c),
[effective option reporting](https://github.com/torvalds/linux/blob/master/fs/nfs/super.c).

Retain one client/cache/mount/PID/bootstrap namespace per host and unique machine
identity per host. No live remount/replacement. Existing ownership and UID mapping
requirements still apply. Hard NFS can block open/read/fsync indefinitely even while
local locks remain held; transaction timeouts do not bound filesystem I/O.

Rejected alternatives: blanket remote filesystem allowlist loses lifetime guarantees;
new local-lock/remote-record split changes the protocol and relocation surface;
SQLite does not address this validation request. Real target-NFS certification is
outside this machine's available evidence and is not claimed.
