# Fix record — 2026-11-01

The fixture extracts only tool.semantic_release tables and descendants, validates
the extracted policy with tomllib, and preserves protected lock and real-hook tests.
Three regressions cover local uv sources, similarly prefixed tables and later project
extras; they failed before the fix and passed afterward. Fixture setup optimization
is a separate measured change and does not justify weakening isolation assertions.

The assigned agent reports focused red/green checks; parent inspected the actual diff.
Final integrated verification and native/review acceptance remain pending in the
[cleanup ledger](../../../specs/010-cleanup/tasks.md). No assessment deviation was needed.
