# Research and analysis — 2026-10-14

The reported AttributeError was reproduced by deleting os.pidfd_open only in a
disposable interpreter and calling the guardian signal boundary. No signal was
sent. Local Python exposes the attribute; ordinary host runs cannot reproduce its
absence without fault injection. Existing native CPU DDP and real subprocess
coverage remain valuable but cannot prove physical multi-GPU or other-interpreter
compatibility. Focused existing tests passed (74 tests during planning).

GPUInventory already distinguishes physical_index and logical_index. Its private
identity-only enumeration can support a public administrative identity interface;
CUDA visibility and memory health must not gate administrative selection.

Spec Kit analysis: all FR-01 through FR-10 map to tasks T003–T010 and verification
T011–T016. No critical/high inconsistencies identified. Required external results
remain an intentional acceptance gap, not a prerequisite to writing the harness.
Extension configuration has no registered hooks. Native helpers that persist
.specify/feature.json are not used because project instructions prohibit those
changes; this feature directory is the explicit workflow context.
