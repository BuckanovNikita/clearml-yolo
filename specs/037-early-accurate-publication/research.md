# Inspected decisions — 2026-10-19

- Decision: retain stable-cache partial replay work. Hydra common currently keeps native
  inputs; session publishes JSON and handles legacy General-only replay. Queue bug files
  are unrelated. Isolated snapshot prevents concurrent source writes.
- Decision: explicit contributor barrier. Results currently assemble/upload in finalizers;
  moving that wholesale to each stage would upload incomplete prediction contexts.
- Decision: publish dashboards at evaluation boundary. Metrics already uploads per split;
  comparison currently waits through statistics. Exact threshold upload already follows CSV
  completion and remains there.
- Decision: optional export callback preserves standalone exporter callers and allows files
  to survive a later build/metadata/verification failure without adapter SDK dependencies.
- Decision: reuse import-linter and injected negative architecture tests; extend scoped
  checks for new interfaces instead of introducing import exceptions.
