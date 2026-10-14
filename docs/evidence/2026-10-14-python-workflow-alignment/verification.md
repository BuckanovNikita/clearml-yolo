# Python workflow alignment verification

Date: 2026-10-14. Baseline: `665dfd3`.

This evidence covers documentation maintenance only. Application, GPU and live
ClearML checks are not required for the policy change and have not been run.
Required native commit/release hooks remain applicable at delivery.

## Planning

Inspected repository instructions, workflow/development guidance, Python/build
configuration, import contracts, release helper and hooks. The isolated baseline
has no task-unrelated modifications; the original checkout is preserved.
Architecture planning validation passed before policy edits (exit 0).

## Verification and acceptance

- `git diff --check`: passed.
- Markdownlint 0.41.1: five changed/new Markdown files passed, with only MD013
  disabled to preserve the existing long-prose/table style.
- A one-off read-only local-link/anchor check: five Markdown files, 34 local
  links/anchors, no errors. Nested task evidence was included explicitly.
- Inspected the complete policy diff: only agent/workflow/development guidance
  and this evidence directory change before native hook-generated output.
- Routing review covers native feature and bug routes, append-only resumed work,
  docs-only evidence, Plan mode, explicit stopping points, missing skills and
  docs-only release evaluation. Existing architecture checks, usage-skill
  maintenance, source overrides and dependency constraints remain in place.

The one-off lint invocation initially used the wrong library export and failed
before checking content. The corrected invocation used the installed synchronous
API and produced the passing result above; no tool or project files were changed
to work around the failure.

Fresh independent review, architecture acceptance and delivery remain pending.

## Final review

Fresh independent reviewer `/root/alignment_final_review`, requested GPT-6.1 Sol
with high effort, returned **ship** after parent integration and verification.
The reviewer independently checked architecture plan records, local links/anchors,
Markdown and whitespace, and inspected native workflow/release contracts. No
blocking findings affect this repository. Runtime model settings are not exposed.
The reviewed scope contains only the three policy files and this evidence, with
any native hook-generated changelog refresh to be inspected during delivery.
Architecture acceptance validation and native delivery follow this state.

Architecture acceptance validation passed (exit 0) after complete-diff
reconciliation and review. Markdown and whitespace checks passed on the updated
evidence. Implementation and acceptance are complete; native delivery is pending.

## Native delivery

Contributor commit `38dada3fdd730caf38606aa8c1529cf164f34b6b`
(`docs: align agent workflow with shared Python lifecycle`) passed the applicable
native hooks. The first attempt required the expected generated changelog refresh;
that diff was inspected and staged before the successful retry. No application
checks were claimed for the documentation-only change.

The commit was fast-forwarded into an isolated `master` delivery checkout with
the native hooks installed. `uv run --locked --no-sync python
scripts/local_release.py` exited 0 with `No unreleased semantic changes.` The
authorized atomic push of `master` succeeded, and the remote branch was verified
at the contributor commit. The peeled `v0.28.0` tag remained
`05aa05ca61d615540a7fb17cbf63abba21c5e8f4`; no version tag was created.

Both task and delivery checkouts contain no local source overrides. The original
checkout, including its queue/GPU/testing work and dependency overrides, was
preserved. Its local branch was not advanced through the unrelated dirty work.
Acceptance, documentation and whitespace checks passed again for this delivery
record before its native commit and push. The final record commit and pushed refs
are reported in the completion handoff.
