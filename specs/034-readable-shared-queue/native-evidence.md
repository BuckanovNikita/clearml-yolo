# Native publication verification — 2026-10-16

## Scope and environment preflight

The bounded acceptance workstream followed `running-end-to-end-tests` and the
global `clearml-yolo-environment` workflow, including the sibling stand and run
contracts. The maintained capacity helper returned GO; the project identity
authenticated against the shared ClearML stand. No host ClearML service,
credentials, settings, or unrelated workload was changed.

Execution used a minted tag, an explicitly named isolated project, and an external
invocation workspace. Machine-specific harnesses, logs, raw task references,
retained capture files, and cleanup receipts are outside this repository.

## Native CPU and publication evidence

The external harness used the checkout's existing environment:

```text
uv run --no-sync python <external acceptance harness> <external evidence directory>
```

It initialized a random YOLO detector from the installed architecture definition,
saved its checkpoint, and wrote a hash-checked model identity sidecar. Four small
synthetic images comprised disjoint validation and test splits, with one annotated
image and one empty image in each. This establishes native execution and output
contracts; it does not establish detector accuracy or pretrained-model quality.

The harness invoked the real `validate` workflow with production dependencies,
one invocation-owned task, explicit CPU inference, eager execution, image size 64,
batch size 1, and the normal validation-calibration/test evaluation sequence.
Optional FiftyOne publication was disabled by the validation workflow.

Observed results from the first strict acceptance run after the startup fix:

- The native workflow finished and a fresh server read confirmed `completed`.
- A separate reader process observed a Unicode console marker and a scalar while
  the task was still `in_progress`. Its polling took 0.405 seconds; total reader
  subprocess duration was 1.328 seconds. The published scalar retained value
  0.125 and iteration 7.
- Fresh server readback returned 32 console records and zero opaque references.
  Neither the current task reference nor the checkpoint digest appeared in the
  published console. The independent active-task reader also found no raw task
  reference. The complete terminal log also contained zero opaque references;
  both SDK startup announcements appeared exactly once in server readback.
- The injected native console marker split a task reference and checkpoint digest
  across several writes. Terminal output showed semantic labels. The original
  capture retained the exact original marker bytes.
- The final publisher receipt equalled all original file sizes: stdout 353 bytes,
  stderr 5,565 bytes, and scalar journal 78 bytes.
- All seven task artifacts were force-downloaded: canonical ground truth and
  predictions, validation thresholds, and full/DTRK dashboards for validation
  and test.
- All four downloaded workbook sheets displayed the readable model name without
  opaque references. All four hidden model identities equalled the original
  fixture identity, including the exact checkpoint digest.
- Six published plot events contained no opaque references in their plot payloads.
  Interactive browser controls were not exercised.

## Reproduced and resolved SDK startup finding

The first attempt failed the independent live-console assertion before inference.
A second fresh invocation captured the offending server records and completed the
remaining native checks. Both attempts were cleaned up independently.

The initial server console contained an SDK startup event that directly published
the created task reference and results-page URL. It bypassed the project's sanitized
FD publisher. Fresh server readback found three opaque occurrences in that event;
the injected checkpoint digest was absent from the published console.

Inspection of the installed SDK confirms two direct `logger.report_text` calls
inside task initialization: task creation and results-page announcement. The
terminal mirror already sanitized both lines, but this did not prevent their
direct server publication.

The application session boundary now temporarily routes the SDK's known task
creation, results-page, and offline-path announcements into the existing raw FD
capture. The existing console publisher performs their single public delivery.
The wrapper applies only to its owning process and thread and is restored on
success or failure. Ordinary messages and concurrent background messages retain
the SDK's original behavior. No installed dependency source was changed.

A real offline SDK regression reproduced the original duplicate/raw startup
publication before the fix. Focused tests verify the original method is restored,
unrelated messages pass through, startup publication is readable and occurs once,
and raw startup references remain in the local original capture. A third fresh
live invocation then passed strict active and completed console assertions plus
all native/artifact/receipt checks above. **Human-readable console acceptance
passed for this live CPU validation scope.**

## Focused regression checks

```text
uv run --no-sync pytest tests/test_clearml_session.py tests/test_trace_subprocess.py tests/test_console_capture.py -q
uv run --no-sync pytest tests/test_console_deadline.py -q
uv run --no-sync ruff check src/clearml_yolo/adapters/clearml/session.py tests/test_clearml_session.py tests/test_trace_subprocess.py
uv run --no-sync mypy src/clearml_yolo/adapters/clearml/session.py tests/test_clearml_session.py tests/test_trace_subprocess.py
uv run --no-sync python scripts/check_docs.py specs/034-readable-shared-queue/native-evidence.md
```

The lifecycle/trace/capture group passed 169 tests; the deadline group passed nine.
Scoped Ruff and mypy checks passed. The evidence Markdown/link check passed.
Distinct table contents now receive readable ordinal labels; regression tests
cover exact-byte deduplication, repeated aliases, and collisions with caller-named
artifacts. Internal digest and alias matching remains exact.

## Cleanup and limits

The maintained cleanup helper deleted only each attempt's tagged project and
owned invocation directory. Its final listings reported zero matching projects
and tasks after the initial three attempts. Task-owned copies of the diagnostic
and successful attempts' local evidence remain outside the repository for review.

The initial GPU inspections had an existing consumer, which was left intact.
Subsequent direct GPU validation is recorded below; the queue's automatic memory
admission threshold does not govern explicitly requested direct inference.
Physical multi-GPU execution, two-host NFS coordination, full training, paired
model comparison, and browser interaction are not established by these smokes.
Real two-user queue checks and the parent regression/architecture checks are
separate acceptance workstreams.

## Review regression closure and fresh CPU/GPU acceptance

Independent review identified a checkpoint watermark ending inside a UTF-8
character, incomplete identifier prefixes following punctuation, raw class names
in plots/workbooks, and literal JSON braces being incorrectly formatted by the
diagnostic adapter. Added regressions reproduced those failures before fixes.

- Checkpoints can read at most the remaining three bytes of one UTF-8 character
  beyond the requested watermark. Pending bytes are never acknowledged before
  publication; the completed character remains intact.
- Checkpoint prefix protection covers bracket, dash, underscore, period, and ANSI
  boundaries, including incomplete ANSI escapes and prior complete identifiers.
- Distinct opaque classes receive distinct readable labels in confusion axes,
  hover text, PR legends, confidence figures, and workbook cells. Raw numeric
  payloads and source frames remain unchanged. Generated workbook checks confirm
  these outputs have no embedded raster media requiring separate text handling.
- A separate integrity-checked presentation envelope preserves the exact original
  workbook and alias mapping. Existing identity extraction remains compatible;
  dashboard readers recover original class keys. Tampered visible data is rejected.
- Diagnostic calls without arguments retain literal braces; calls with arguments
  retain formatting behavior before readable presentation.

The affected stream, capture, diagnostics, interactive evaluation, evaluation
rendering/identity, workbook, comparison, and report group passed **148 tests**.
The only warnings were 16 existing missing-glyph font warnings. Scoped Ruff and
18-file mypy checks passed; all 15 formatted source/test files passed the format
check. No full suite was started by this bounded workstream.

Two further tagged native validations ran from the frozen source. The harness
used an opaque synthetic class key, a barrier ending after the first byte of a
three-byte Unicode character, and a delayed writer providing the continuation.
The CPU run used explicit CPU inference. The GPU run followed a fresh capacity
inspection and used explicit device `0` in both production prediction stages;
no other process, service, or GPU reservation was changed.

| Observed result | CPU | Single GPU |
| --- | --- | --- |
| Split-character barrier duration | 0.907 s | 0.781 s |
| Task status from fresh server read | completed | completed |
| Opaque references in published console | 0 | 0 |
| Console records read back | 34 | 36 |
| Exact acknowledged stdout bytes | 376 | 422 |
| Exact acknowledged stderr bytes | 5,438 | 5,561 |
| Exact acknowledged scalar bytes | 78 | 78 |
| Downloaded artifacts | 7 | 7 |
| Readable workbook sheets with exact class-key recovery | 4 | 4 |
| Exact hidden model identities | 4 | 4 |
| Published plot payloads without opaque labels | 6 | 6 |

Both live runs preserved the complete original split-character marker in raw
capture, published its Unicode character without replacement, and exposed the
console/scalar marker before task completion. The scalar remained 0.125 at
iteration 7. The first GPU inference emitted one native NMS time-limit warning;
the random initialized fixture establishes execution and publication contracts,
not detection accuracy. All five invocations were cleaned by the maintained
tag-scoped helper, with zero matching projects/tasks remaining after each. Raw
evidence and exact references remain in task-owned external evidence. No live
smoke process remains.

## Final scalar and table collision regression

A final independent review found that replacing each label independently could
merge distinct class names and scalar destinations. Fixed-set tables now use one
collision-aware mapping for string cells, index labels, column headers, and axis
names. Numeric columns, including nullable and narrow integer/float dtypes, retain
their types and values; source frames remain unchanged.

Scalar aliases now retain their assignments for the lifetime of their owner.
Direct scalar reporting uses the existing invocation resource cache; the console
worker keeps a separate registry in its publication state across journal batches
and checkpoints. Reordered calls, subset calls, and later literal names matching
an existing fallback cannot reassign or merge a previously issued destination.
No process-global task registry was introduced. Direct scalar reporting enforces
the active invocation owner, and its focused tests establish that owner explicitly.

Four new regressions reproduced the collision/missing-owner failures and then
passed. The affected report, stream, capture, deadline, interactive, identity,
workbook, and comparison group passed **123 tests**, with the same 16 existing
font warnings. The four regressions also passed against the final frozen source.
Scoped Ruff, five-file mypy, and five-file format checks passed.

A sixth tagged live invocation independently read back the following values while
the task remained `in_progress`; the reader observed them in 0.289 seconds:

- Three distinct journal titles, including a later literal fallback collision.
- Three distinct series under the first title. The second source retained the
  same series across checkpoints, with values 12.25 and 13.5 at iterations 1 and 2.
- Three distinct direct scalar series after subset updates, with final values
  21.125, 23.5, and 24.75 at iteration 0.
- One readable table with three distinct class labels and no opaque text.

Fresh readback confirmed task completion and no opaque scalar/table/console
labels. The six original scalar journal records retained exact source titles and
series. Final receipts matched stdout 216 bytes, stderr 805 bytes, and scalar
journal 693 bytes. The maintained cleanup helper left zero matching projects and
tasks; only task-owned external raw evidence remains. This bounded scalar-only
run did not repeat native GPU inference, whose earlier acceptance remains recorded
above.
