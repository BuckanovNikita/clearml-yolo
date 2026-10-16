# Data model

No persisted schema changes. QueueSettings retains name, root, coordination_root,
config_path and root_source. Strict [queue] TOML fields remain mandatory. The selected
config path is explicit or derived from user config home; frozen paths are passed
to workers and guardians. Mountinfo parsing uses mountpoint, filesystem and effective
superblock options only during initial validation. No new on-disk record is added.
