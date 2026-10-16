# Validation guide

Each user creates the selected file, normally `~/.config/clearml-yolo/queue.toml`:

```toml
[queue]
name = "Shared experiments"
root = "/srv/cy-queue/metadata"
coordination_root = "/srv/cy-queue/coordination"
```

All users on one host select the same coordination path. Run `cy-queue config` to
inspect settings without creating storage/bindings. Explicit shared override:

```bash
export CY_QUEUE_CONFIG=/etc/clearml-yolo/queue.toml
cy-queue config
```

For NFS coordination, administrators arrange hard,local_lock=flock (or all) with
shared cache, consistent UIDs and a common mount/client namespace per host. Check
effective options with `findmnt --target /srv/cy-queue/coordination`; this task does
not mount anything. Existing relocation errors still require offline maintenance.

Run `uv run --frozen --no-sync pytest tests/test_queue_settings.py` for isolated
lookup/mountinfo and binding regressions. Simulated mount records do not prove
actual NFS locking, reconnect, outage or multi-host behavior.
