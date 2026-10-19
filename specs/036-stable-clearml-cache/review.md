# Independent review: 2026-10-16

## First review

A fresh read-only native agent reviewed the integrated application/companion diff,
contracts, architecture record and executed evidence. It independently reproduced:

1. Historical tasks without canonical native inputs lost General-only execution values.
2. Malformed device mappings could equal the normalized identity of valid allocations.
3. Default JSON Unicode escapes were not decoded by the installed SDK replay parser.

Verdict: **fix-first**. It also required scoped executable enforcement of the pure
helper contract and qualification of CLI versus embedded full-input recording.
The implementation now addresses each finding; dated regressions and integrated
checks are recorded in [verification.md](verification.md).

## Second review

A second fresh reviewer independently reproduced ambiguous SDK/JSON escape
semantics, fallback-project model selection and skipped-stage run-root input
collisions. Verdict: **fix-first**. Source and regression corrections are now
implemented and parent-verified, including the related unresolved escaped
device-list case. The documentation now explains the conditional input identity
and explicit Unicode-safe controller JSON overrides.

## Third review

A third fresh reviewer reproduced device-selector collisions across backends:
strict detector/export consumers reject aliases accepted by generic normalization.
Verdict: **fix-first**. Consumer-specific corrections now preserve unsupported
selectors, including quoted native JSON list strings, strict backend aliases,
typed string lists and unknown checkpoint contexts. Actual consumer validation
and installed SDK hashing reproduced 67 false hits before the correction; the
final focused cache suite passes 233 cases. Architecture and other inspected
changes were coherent in this review.

## Final review

A fourth fresh read-only reviewer assessed the complete integrated application and
companion diff after parent verification. Verdict: **ship**, limited to local source
acceptance, with no blocking implementation findings. Responsibilities, typed
interfaces, inward dependencies and SDK/effect ownership were accepted; executable
pure-helper enforcement remained scoped without weakened import rules.

The reviewer independently checked 210 selector/context combinations and validated
all 50 normalized candidates against actual consumer parsers/validators. SDK
JSON/HOCON probes covered numbers, supported escapes, quotes and literal substitutions.
Application architecture planning and companion no-impact acceptance validators
passed, as did 18 application and three companion Markdown checks and both
repositories' whitespace checks.

The review identified a nonblocking documentation qualification: the SDK updates
connected General parameters without deleting omitted inherited keys. The reviewer
approved the explicit historical-clone caveat now added to the contracts, technical
guide, README and portable usage reference. No historical cleanup was required.

Parent final full pre-commit verification subsequently passed, including pytest.
Live server acceptance, final architecture acceptance and release remain open;
this local review does not waive them.
