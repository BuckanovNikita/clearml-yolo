# Design decisions

- **Decision**: Reuse demand normalization and NVML inventory; add a stateless poll.
  **Reason**: The user asked to remove queue functionality while retaining waiting.
  A mutex, ticket file or reservation would preserve the coordination being removed.
- **Decision**: Return inherited CUDA logical indices without changing visibility.
  **Reason**: Native execution now shares a process across Hydra sweep jobs. Changing
  visibility after CUDA initialization is unsafe; the installed Ultralytics device
  parser supports logical indices under the inherited visibility restriction.
- **Decision**: Ignore only the current PID in compute-process occupancy.
  **Reason**: CUDA contexts can survive allocation cleanup between sequential jobs;
  treating the caller's context as another workload would wait forever.
- **Decision**: Use Hydra's standard BasicLauncher and direct invocation.
  **Reason**: This removes the queued worker and cleanup aggregation while preserving
  local sequential sweep environment, output directories and failure reporting.

Native DDP processes and the disposable metadata probe remain native/runtime concerns;
they are not queue execution workers. The original remote post-report hang remains
unconfirmed and is not an acceptance claim for this change.
