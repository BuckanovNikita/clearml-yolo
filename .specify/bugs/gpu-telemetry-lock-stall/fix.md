# Fix record: gpu-telemetry-lock-stall

Date: 2026-10-04. Status: implemented.

Move telemetry outside registry lock and reread live validated state before admission/contraction.

Regression evidence: `tests/test_gpu_queue.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.
