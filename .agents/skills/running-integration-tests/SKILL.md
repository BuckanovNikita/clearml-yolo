---
name: running-integration-tests
description: Use when running live integration or acceptance, selecting GPU/FiftyOne checks, or recovering a recorded test environment.
---

# Run live verification

Read `docs/development.md` (Acceptance tiers) for scope and
`specs/012-own-test-infra/contracts/test-environment.md` for lifecycle rules.
`Taskfile.ops.yml` owns invocation; `tests/integration/lifecycle.py` implements
ownership and deletion. Paths start at the repository root. Use
`clearml-yolo-environment` for manual runs and authentication diagnosis.

1. Inspect the recorded environment and ownership before live actions. Run bounded
   `infra-check` before expensive checks; inspect pcboard capacity where available
   before GPU work and preserve unrelated workloads.
2. Select Task `integration`, `acceptance` or `release-acceptance`; explicit commands
   retain full scope. Focused diagnosis requires preflight, concrete `tests/integration`
   selectors and configured loadgroup distribution; its evidence covers only those checks.
3. Supply single-GPU Severstal options from pytest help and `docs/augmentation.md`
   (Severstal execution checks). Task owns FiftyOne database selection and temporary
   lock-directory cleanup.
4. Preserve logs before deletion removes published data. Record environment identity,
   selectors, results and deletion proof. For native direct/queued execution,
   publication/readback and standalone charts, also use `running-end-to-end-tests`.

## Ownership and recovery

- Create an owned environment or explicitly adopt its owner's exports. A live record
  without matching adoption refuses replacement. Inspect lifecycle recovery commands;
  deletion must target the owned identity, never a broad namespace selector.
- The creator deletes; adopters leave deletion to that owner. Deliberate
  `INTEGRATION_KEEP_DATA=1` retention must record cleanup command and contract deadline.
- Use Task `infra-up`, `infra-env`, `infra-down` for manual operations. Keep credentials
  in the process environment, out of logs. Prove deletion; failed guards/incomplete
  deletion retain the recovery record. Preserve unrelated services and host credentials.
- Use a fresh environment for each CPU smoke result: repeated adoption can make
  name-based readback select an earlier task. Test sessions hide user SDK configuration;
  live credentials come exclusively from the owned environment.

## Interpret outcomes

`infra-check`: AVAILABLE/0 means availability, UNAVAILABLE/3 defers setup, ERROR/1
needs diagnosis. A busy GPU also defers supported checks. Assertions after setup remain
failures; interruption proves no success. Preserve permissions and ownership guards.

Use `verification-workflow` for deferred checks: they block acceptance, integration and
release. Continue independent work and retry after availability changes without polling;
report the unresolved decision when only blocked checks remain. Report cleanup failures
with the owned identifier and recovery command.
