# Queue settings contract amendment

Default file: `$XDG_CONFIG_HOME/clearml-yolo/queue.toml`, falling back to
`$HOME/.config/clearml-yolo/queue.toml`. An explicit absolute `CY_QUEUE_CONFIG` wins.
No file merging, implicit system config search, storage defaults or auto-creation.
Every user fills [queue] name, root and coordination_root; paths remain absolute.
Missing settings identify the selected file and required fields. Help needs no file.

Local coordination filesystem behavior is unchanged. NFS/NFSv4 requires effective
`hard` and `local_lock=flock` or `local_lock=all`, without soft/softerr/nosharecache.
Use the longest matching mountpoint and decoded Linux mount escapes. Unknown or
malformed mount information fails closed. NFS metadata eligibility is unchanged.
Existing bindings, legacy recovery evidence, UID checks and frozen guardian settings
remain authoritative. See [operational assumptions](../spec.md#assumptions).
