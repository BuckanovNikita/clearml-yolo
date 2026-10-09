# Runtime values

- **Demand**: A nonnegative count derived from enabled native stages. Training uses
  the requested count; inference contributes at most one. CPU/MPS contributes zero.
- **Inventory**: Physical whole-GPU UUID and occupancy by other compute PIDs. Invalid
  process telemetry, unsupported MIG or unmapped visibility fails rather than implying free.
- **Selection**: An ephemeral tuple of inherited CUDA logical indices. It is neither
  persisted nor exclusive. No ticket, reservation, registry or release transition exists.
- **Provenance**: Requested native devices and the effective selected devices are
  recorded under `gpu_selection`, including `selected_devices`. Existing requested
  and effective YAML retain their normal storage locations.

The only wait transition is insufficient availability to sufficient availability.
Interruption and telemetry failures propagate directly before task creation.
