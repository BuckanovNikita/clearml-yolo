# Data and interface impact

No persistent application schema or public configuration change is planned.

- Export presence policy accepts the existing operation and explicit presence flags
  for graph, engine, weights and ground truth. It returns normally or raises existing
  ValueError messages. Runtime converts paths with `is not None`; preview defers
  unresolved presence while rejecting independently known absences.
- Hub publication uses an internal typed validator callback; its existing resolved
  asset records and native cache layout remain unchanged.
- Test setup seeds are immutable inputs copied into test-owned writable directories;
  they are not shared writable repositories or acceptance receipts.
- Baseline/final measurements record source identity, versions, workload, environment
  and timings in dated evidence. Existing verification receipt trust remains unchanged.
- The pending weight manifest uses its existing schema and a deliberately verified
  immutable snapshot pin; package data remains authoritative.
