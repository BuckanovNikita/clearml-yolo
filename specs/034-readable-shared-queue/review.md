# Independent review — 2026-10-16

## Scope and method

Fresh native read-only reviewers assessed the integrated application and the portable
usage companion after parent verification. Queue and output reviews used separate
contexts, bounded scopes and no delegation. They inspected current implementation,
feature contracts, architecture boundaries and dated check evidence. They did not
claim sandbox-enforced isolation or rerun privileged multi-user provisioning.

## Queue and shared configuration

Initial verdict: **fix-first**. The reviewer reproduced task-name interpolation
failure outside the Hydra job context. Nonblocking findings identified missing
per-row archive markers and duplicate-reference overcounting in confirmations.

Parent regression tests additionally exposed early interpolation during sweep override
iteration. Raw override strings now remain unresolved until the job context exists;
the label comes from the frozen resolved configuration. Tests cover both CLI and saved
configuration task names. Text/TUI state cells mark archived jobs, and confirmations
deduplicate resolved job identities. The feature contract explicitly retains existing
GPU display aliases in JSON while preserving exact public job/host/boot identities.

Scoped independent rereview verdict: **ship**. The original reproduction produced
the two expected job-local names, matching frozen configuration. Three focused cases
passed independently; parent evidence included 78 affected tests and the complete
routine suite. No remaining queue blocker or architecture exception was identified.
Owner sidecars, full-history replay, recovery visibility, frozen settings propagation
and fixed host binding were reviewed. Physical GPU/NFS claims require separate evidence.

## Output and provenance

Initial verdict: **fix-first**. Four independently reproduced gaps require correction:

1. A console barrier ending inside UTF-8 could stall publication indefinitely.
2. Partial opaque tokens following some punctuation could escape across checkpoints.
3. Opaque class labels bypassed human plot/workbook formatting.
4. Preformatted diagnostic messages containing literal braces raised without arguments.

The reviewer ran 48 readability/diagnostic cases and focused reproductions. SDK startup
wrapper ownership/restoration, ordinal table collision handling, hidden model identity
and the narrowly amended extraction baseline looked sound. Correction and independent
rereview were required; this initial review did not establish output acceptance.

The first focused rereview confirmed all four fixes, including exact nested workbook
recovery and rejection of edited visible data; 83 focused cases passed. It found one
additional collision issue: independent formatting mapped different opaque table labels
and scalar series to the same fallback. Tables now share a distinct alias map, and scalar
registries retain assignments under the existing invocation/publication owner across
calls and checkpoints. Source numeric values, extension dtypes and journal records remain
unchanged.

Final independent rereview verdict: **ship**. The reviewer ran 117 focused tests and
checked alias uniqueness and stability across 24 arrival orders. All previous findings
were resolved. The reviewer also assessed parent evidence for 439 affected tests and
fresh active live publication readback. No process-global registry or ownership exception
was introduced; stream receipts, SDK wrapper restoration and reversible workbook
provenance remained sound.

## Documentation and companion package

Fresh usage review verdict: **ship**, after correcting the distinction between original
invocation captures and queue combined logs. Nine reasoned scenarios and actual read-only
help/configuration checks passed. This covers explicit skill reading in the current
agent host, not automatic routing or live OpenCode/DeepSeek execution. Package checks
and limitations are recorded in the linked [documentation evidence](../../docs/evidence/034-readable-shared-queue-docs.md)
and companion source evidence.

## Final reconciliation

The parent reconciled the complete tracked and new feature scope with the architecture
record: pure formatting and stable aliases, queue configuration/archive adapters and
entrypoints, reporting/provenance, regression and multi-user tests, contracts and evidence.
No initial fix-first finding is waived. Dependency sources, installed workflow tooling,
local editable overrides and the unrelated grid-search draft remain outside the feature
diff. Integration preserved the separately delivered ten-minute finalization change;
the feature source and tests were otherwise identical, and 183 affected tests passed.
Full routine and commit gates passed before delivery; their outcomes belong in the
verification and delivery records, not this review verdict.
