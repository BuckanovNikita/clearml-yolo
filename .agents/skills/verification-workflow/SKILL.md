---
name: verification-workflow
description: Use when selecting verification for a change, committing, reporting completion or deciding whether earlier results can be reused.
---

# Select and report verification

Paths start at the repository root. `docs/development.md` owns every command and the
selection policy; the Verification section of `docs/agents/issue-template.md` is the
checklist you fill in.

1. Record the comparison base and tip: the whole task branch against its merge base with
   `master`, never only its last commit. Done when both SHAs are written in the issue.
2. Copy the template's Verification section into the Linear issue if it is not there, and
   delete every line that does not apply. Select lines with
   `docs/development.md#acceptance-tiers`; use `#automatic-routing` to see what the hooks
   will run on their own. Add `running-integration-tests` lines for live claims and
   `mutation-testing` for product changes. Done when every remaining line is one you will
   run, defer or ask the user to waive.
3. Before running checks, review documentation consistency against the issue's
   acceptance criteria and the diff. If no documentation change is needed, write the
   reviewed scope and the reason in the issue; a missing required update blocks completion.
4. Run the selected checks in the order of `docs/development.md#order-and-evidence-reuse`.
   Reuse an earlier result only while its inputs are unchanged, and write the reuse
   reason next to the line.
5. Commit by `docs/development.md#commit-procedure`, ending with the final
   `prek run --all-files` pass on the committed tip.
6. Request the independent review the change type requires, after step 5.
7. Write one status after every kept line and tick boxes as the template says. Done when
   no kept line lacks a status.

Use `release` for merge readiness and after-merge inspection.
