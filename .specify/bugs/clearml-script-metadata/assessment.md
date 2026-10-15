# Bug Assessment: Missing ClearML script metadata

- **Slug**: clearml-script-metadata (generated from the reported symptom)
- **Created**: 2026-10-15
- **Source**: user conversation and live task readback
- **Verdict**: valid
- **Severity**: medium; new experiments lack source identity and executable entrypoint.

## Report

“Enable these all so tool must fill all these fields”: repository, script entrypoint,
branch, commit and working directory on new ClearML tasks.

## Symptom and reproduction

A normal CPU `cy-ground-truth` invocation completed successfully. Fresh API readback
of task `52567e01e7f84e508ac24c6455eba9e6` returned empty `script.repository` and
`script.entry_point`; branch, version_num and working_dir were absent.
Run the same three-image conversion after the change and read the exact saved task.
Historical tasks must remain unchanged.

## Root cause

`adapters.clearml.session.invocation` disables automatic repository detection. This
avoids arbitrary checkout diff capture but also prevents source metadata publication.
Native SDK detection also records console wrappers or raw module arguments, so merely
enabling it does not preserve the existing sanitized-publication boundary.

## Proposed remediation

Publish metadata explicitly through public `Task.set_script`, inside the existing
owner lifetime and before workflow execution. A cohesive ClearML script adapter owns
bounded, read-only Git discovery from the imported source checkout. Record origin URL,
current branch (HEAD for a detached checkout), exact commit, repository-root working
directory `.` and the stage's canonical `-m clearml_yolo.entrypoints.<module>` command.
Strip URL credentials using existing redaction. Do not capture raw arguments, source
contents or diffs. Skip mutation during remote replay. Source distributions without
Git must still report their module entrypoint and cannot invent Git identity; warn
when Git identity is unavailable. SDK publication errors use existing task failure handling.

No public CLI/configuration changes, new dependencies or upstream modifications.
Python >=3.12.13,<3.14, uv, Ruff, strict mypy, pytest and existing build backend remain.

## Architecture

See [architecture.json](architecture.json). The new adapter encapsulates Git discovery
and script publication; session retains lifetime/effect ownership. Existing inward
import contracts and negative SDK-owner tests cover these modules. No application or
core imports of infrastructure are added.

## Tasks and acceptance

- [x] Capture the live failure and inspect SDK behavior and existing staged work.
- [x] Validate architecture plan, add regression and observe failure.
- [x] Implement adapter and owner integration; cover real Git, nested stages, remote
  replay, missing metadata, detached HEAD, credential redaction and publication failure.
- [x] Run focused checks, Ruff, mypy, import-linter, architecture negative cases and full pytest/hooks.
- [x] Repeat real CPU conversion and assert all five saved fields, empty diff and exactly one completed task.
- [x] Update tracking publication contract; validate Markdown and local links.
- [x] Obtain fresh independent review after parent verification and reconcile architecture acceptance.
- [ ] Complete task-only commit and native Git-tag release/delivery within standing authorization.

Parent owns implementation/integration; a bounded read-only SDK investigation can run
in parallel. Fresh review depends on integrated code and executed checks. Isolated
worktree excludes unrelated staged queue changes and local dependency overrides.

## Documentation scope

Update `specs/010-native-clearml-integration/contracts/tracking-publication.md`.
Inspected corp-skills clearml-yolo SKILL.md, usage and evaluation references at commit
`ce33ce5ef1ba1fa6470399d028835f295b90f389`: command selection, examples and invocation
parameters do not change, and none promises a different Git/script contract. No
portable usage-package change is required for this automatic metadata correction.
README/current contract index already route to the maintained publication contract.

## Risks and limits

Missing Git/origin and source installed outside a checkout cannot yield fabricated
repository identity. Detached HEAD has no named branch and is reported as HEAD.
Uncommitted edits remain excluded, so the commit identifies the base revision only.
Existing shared checkout and external usage-skill edits belong to other work.
