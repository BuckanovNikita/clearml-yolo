# Design research

- Existing direct startup imports queue via common, execution, gpu_runtime and composition.
  Remove those edges; disabling switches is insufficient. Keep generic cleanup separate.
- Current stale queue reaping trusts absent supervisor/worker locks and can free capacity
  while detached ranks remain. Durable local UUID claims must quarantine guardian death.
- NFS stores atomic per-owner records; host-local coordination avoids SQLite WAL on NFS.
- Existing ClearML Python auto-capture misses native file descriptors. A local capture and
  independent attach-only publisher preserve terminal output and bounded failure semantics.
- Existing prediction verbose inherits training. Override it explicitly and retain shared
  progress across backends. Scalar DDP relay remains owner-only.
- Current environment provides one physical GPU. Five-GPU evidence is unavailable here;
  isolated SIGILL investigation is distinct from successful retries.

Primary references checked for the design:

- [SQLite WAL constraints](https://www.sqlite.org/wal.html): WAL requires same-host
  shared-memory coordination, so the queue uses atomic NFS records and host-local locks.
- [Ultralytics prediction arguments](https://docs.ultralytics.com/modes/predict/#inference-arguments):
  `verbose=false` suppresses detailed inference output independently of training.
- [Textual DataTable](https://textual.textualize.io/widgets/data_table/): optional job table
  and selection mechanics; mutations remain behind the queue application interface.
