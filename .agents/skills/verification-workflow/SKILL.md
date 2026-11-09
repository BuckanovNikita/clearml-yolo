---
name: verification-workflow
description: Select clearml-yolo Task stages for explicit fixes, development verification, commits, change and release acceptance, deferred or waived checks, and completion reports. Use before verifying changes or claiming completion, and when infrastructure or a busy GPU defers required verification.
---

# Verification workflow

[Development procedures](../../../docs/development.md#verification) own policy and the
stage table; `Taskfile.yml` owns commands and ordering. Invoke each stage as
`uv run --frozen --no-sync task --exit-code <stage>` and keep its exit status.

1. Inspect worktree ownership and the host's reported load (pcboard where available);
   choose `CY_TEST_WORKERS` (default 2) and postpone heavy stages while the user's
   workload needs the machine. Stop concurrent editing in this worktree. Clear an
   inherited `UV_PROJECT_ENVIRONMENT` before the outer `uv run`. A new worktree runs
   `bash scripts/install-hooks.sh` once.
2. Run `fix`, inspect its changes and stage exact task-owned paths. Commit inputs must
   be fully staged with no nonignored untracked files; the staging guard refuses
   anything else except the documented `[tool.uv.sources]` override.
3. Use `verify` for development verification; the pre-commit hook runs it. Reuse that
   success while inputs remain unchanged. After an intermediate `SKIP=verify` commit,
   clear `SKIP` and run `verify` on the final content. `test-full` is the conservative
   fallback when affected selection cannot represent an input.
4. For code changes, run the `mutation-testing` skill's branch report
   (`mutation -- --base master`). Then run `acceptance` on the clean committed tip, in a
   checkout without source overrides; it already includes checks, properties, the
   complete unit suite with the coverage floor and the live part. Do not precede it with
   an equivalent affected-unit run. Follow `running-integration-tests` for the live part.
5. Before delivering a version, run `release-acceptance` and the real-run gate of
   `running-end-to-end-tests` (CPU and a single GPU); the `release` skill owns delivery.
6. Report the checks actually executed or selected, each as passed, failed, deferred,
   waived or error, plus cleanup leftovers. A deselected test is not a fresh execution;
   an interruption is not success; Task freshness is never proof.

## Deferral and waivers

`infra-check` returns AVAILABLE/0, UNAVAILABLE/3 or ERROR/1. Unavailability, capacity
wait and a GPU busy with the user's workload defer the affected checks: keep the task
incomplete, continue independent local work and retry at a meaningful milestone or after
restored availability, without polling. Deferred verification blocks acceptance,
integration and release. When only blocked verification remains, report the reason and
ask for the user's decision. Errors (credentials, TLS, configuration) need diagnosis
with `clearml-yolo-environment`; assertions remain test failures.

Multi-GPU DDP on a single-GPU host is waived by standing user decision: report it as
waived, never as passed or deferred; it does not block.

Use `properties`, `integration`, `mutation` or `paired-check` separately when the change
needs them. None is cached. Live acceptance is reusable only within the same release
attempt on the unchanged clean tip. Documentation-only changes use native Spec Kit
checks; `acceptance` skips its live part for them and says so.
