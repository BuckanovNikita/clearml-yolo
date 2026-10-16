# Readable output and exact provenance

Human-facing output uses task/model names, comparison roles and stable queue job
numbers. UUIDs, ClearML task identifiers, SHA digests and shortened hashes are not
display labels. This applies to command messages and errors, queue/TUI cells, worker
diagnostics, DEBUG/TRACE output, console forwarding, report banners, plot captions
and application-generated ClearML display text. Canonical artifact names stay stable;
distinct tables sharing one logical name receive readable ordinal suffixes, while exact
content digests remain internal to deduplication and provenance.

## Names and references

Queue jobs display as `Job 17 · Training experiment`. The `job-17` reference derives
from the durable submission sequence within one queue and host; it survives reordering,
archiving and restart. Task names supply labels unless submission provides `--label`.
Duplicate names are distinguished by job number; model reports use comparison roles
and readable context or ordinals. Missing metadata uses a readable role or description,
not an identifier prefix. See [queue operations](queue.md).

GPU output uses physical indexes or collision-checked word aliases for devices absent
from inventory. Older aliases and raw job identifiers remain accepted as inputs.
Hosts display their known names or readable aliases. Task links use descriptive labels
where the output supports links; the TUI opens a selected task with `o`.

New direct and queued multiruns share a readable tag containing UTC date/time and a
random word phrase. Each invocation receives a new tag; a queued sweep freezes one
tag in its snapshots. Existing user tags and historical metadata remain intact.

## Machine data and retained diagnostics

Explicit `--json` output remains available for automation, including exact job
identifiers and provenance fields. Public queue JSON excludes private snapshots,
claim tokens and executable configuration. Link targets preserve exact URLs.
GPU fields retain the existing public display aliases even in JSON.
Readable presentation does not alter checkpoint identities, cache keys, manifests,
source rows, hashes, thresholds or calculated metrics.

Workbooks show model names/roles and whether training-source provenance is recorded.
Their embedded identity metadata retains exact task identifiers and checkpoint hashes;
the original metric layout remains recoverable. Plot captions use names and split
context. Original source identifiers are retained in machine provenance, not visible
captions or banner cells. See [shared reporting](shared-evaluation-reporting.md).
Opaque class labels likewise receive distinct readable aliases in charts and visible
workbook cells. A separate presentation envelope preserves exact original workbook
bytes and labels; application readers validate and restore them before reading metrics.
Ordinary readable labels keep their existing display and layout.

Project-local `stdout.log` and `stderr.log` captures retain original bytes. Queued
execution logs combine child output; while invocation capture is active they receive
the readable mirror, so they are not the source for byte-exact diagnostic recovery.
Terminal mirroring and ClearML console publication apply readable formatting, including
tokens split across input chunks. Source offsets, acknowledgement receipts and bounded
shutdown behavior still refer to the original capture stream. Inspect retained files
when exact identifiers are needed for diagnosis; their raw content is not a sanitized
human report. This presentation rule does not replace the separate secret-redaction
and bounded diagnostic policies in [diagnostics](diagnostics.md).
