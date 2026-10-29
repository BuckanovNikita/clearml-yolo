# Independent review — 2026-10-29

## Initial integrated review

Fresh native reviewer `final_review` was requested as gpt-6.1-sol/high with no
inherited conversation and no write ownership. It inspected the complete feature
007 tracked/untracked implementation and artifacts, queue compatibility and
portable-skill diffs, actual SDK source, canonical test output, native/live
evidence and architecture boundaries. It ran read-only whitespace checks and
in-memory diagnostic probes; it made no writes, downloads or stand calls.

Verdict: **fix-first**. The reviewer found no additional blockers in catalogue
coverage, native promotion/validation, HF configuration readiness/provenance,
receipt retry/interruption/concurrency, invocation policy, custom configuration,
inward architecture, queue metadata or portable guidance.

The confirmed blocker was HF SDK diagnostic leakage. `_sdk_call` sanitized a
raised exception, but native transport/download warnings had already emitted
raw URLs and exception text. A probe of actual `http_backoff` with a mocked
failing client observed opaque credential text and a URL token in logging.
The required correction is scoped SDK diagnostic protection with real warning
path, concurrent-call and logger-restoration regressions.

A synthetic nested-exception probe also identified fragile cause traversal in
preparation reporting. Further inspection showed normal transport paths discard
that cause before raising the public resolver failure, so this was explicitly
withdrawn as a separately proven reachable bug. A defensive boundary regression
will preserve actionable public error text without traversing opaque causes.

## Isolation and remaining review

Concurrent feature 008 began writing runtime files in the shared checkout.
The parent captured exactly 41 owned feature 007 paths into a fresh isolated
clone of the same base, preserving original feature 008 files and local source
configuration. The private isolation manifest records matching bytes. Further
corrections, checks and release use that isolated checkout and an independent
normally resolved environment with immutable paired queue/dependency sources.

The initial all-command pass remains recorded in [verification](verification.md);
its canonical receipt was withheld for concurrent sibling-documentation drift.
The confirmed finding, defensive correction and final isolated check receipt
must be resolved before fresh final review and architecture acceptance.

## Diagnostic correction review

The first correction passed 297 Hub/architecture cases and 45 preparation cases.
It added ContextVar-scoped, reference-counted redaction for SDK logger records,
including exception/custom fields, overlapping calls and logger restoration;
the defensive preparation boundary retained only public outer error text.

A second fresh reviewer (`acceptance_review`, requested gpt-6.1-sol/high, no
inherited context or writes) accepted those tested paths and the full feature's
architecture/functional boundaries, but returned **fix-first** for the same
credential requirement at an additional layer. Actual HF `http_backoff` calling
an actual `httpx2.Client` with `MockTransport` emitted a credential-bearing URL
through the transport's INFO logger, outside the initial SDK-only filter.
No network was needed to reproduce it. The correction must cover the actual
transport logger graph as well; the next fresh review will assess that change.

The next correction covered the inspected HTTPX2, HTTPcore2 and HPACK logging
graph, including lazy first-request loggers, signed redirects and HTTP/1.1/HTTP/2
header diagnostics. A public resolver regression exercised real HF metadata,
signed CDN download and commit-pinned configuration through an in-memory HTTP
transport. Hub/architecture checks passed 304 cases.

A fresh bounded Astra/high reviewer (`privacy_acceptance`) found those logging,
concurrency/restoration and cause-handling paths sound, but reproduced a remaining
terminal-only leak: native progress bars printed signed weight/config URLs when
stderr reported a TTY and the CDN omitted a display filename. This was a direct
terminal-output path, outside logging filters. Its verdict remained **fix-first**.

Both native download calls now use the public per-call `tqdm_class` hook with a
real native tqdm subclass, a fixed safe description and disabled rendering.
Global progress flags/environment are unchanged; actual native Xet progress
construction/update/close remains supported. Real public HF request paths with
TTY/non-TTY captures now assert no token/signature in stderr or log records.
The final focused Hub suite passes 32 cases; Hub plus architecture passes 305.
Preparation's 45 cases, Ruff, formatting and strict mypy pass. Final independent
review and the complete isolated canonical receipt remain pending.

## Accepted correction

Fresh independent reviewer `privacy_final` was requested as Astra/high with no
inherited context or write ownership. It inspected the actual installed SDK
progress factory, native tqdm subclass and Xet reporter alongside the final
implementation and real public-resolution regression. It independently ran both
Hub/preparation test files: **77 passed**, with four existing Pydantic warnings.
Its verdict is **ship for the focused correction**: the known terminal-progress
finding is closed and no new blocker was found. It did not claim a new live Xet
transfer or waive final canonical/paired delivery gates.

The parent accepts the combined review: the earlier fresh full-scope reviewers
found no other functional or architecture blocker, and each confirmed diagnostic
finding now has reproduced failure, corrected real-path regression and fresh
independent closure. The complete owned diff includes core request/result records,
native adapters and storage, command/invocation policy, exact import contracts,
tests, package metadata and feature/user documentation. Concurrent feature 008
and all unrelated source/configuration changes are excluded by isolated capture.
Queue and portable-skill changes remain limited to their reviewed compatibility,
regression tests and usage/release records. Final acceptance still requires the
canonical receipt, architecture check and final committed paired metadata.

Final delivery gates subsequently passed as recorded in
[verification](verification.md): the isolated canonical receipt, architecture
acceptance and exact committed CY 0.42.0/queue 0.1.3 compatibility check. The
release-generated changelog/root-version changes are included in the final
scope; they introduce no additional runtime behavior.
