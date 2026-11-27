# ADR-0312 · Reflink identical cached images with cy-dedup

Prepared datasets can occupy separate files containing the same image. Replacing their contents must retain independent file semantics and preserve the original on errors.

**Decision.** `cy-dedup` scans the chosen cache for regular image files with matching names and sizes, compares SHA-256 and bytes, then uses a verified same-filesystem reflink and atomic replacement. The command skips unsupported reflinks, hardlinked destinations and cross-device pairs. `--dry-run` permits a read-only scan outside `CY_HOME`.

**Consequences.** A run prints scanned, duplicate, reflinked, skipped and failure counts. A skipped pair can leave the command successful; recorded failures give exit 1. Operators should run it on a quiescent cache. Dry-run counts candidates without establishing filesystem reflink support.

[Command entry](../src/clearml_yolo/entrypoints/dedup.py) · [Comparison and replacement](../src/clearml_yolo/adapters/storage/dedup.py) · [Filesystem scenarios](../tests/test_dedup.py) · [Command and exit codes](../docs/commands/cy-dedup.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d9d6fcdf2d1f2a8ea986cf72e6dc2aa70d483497)
