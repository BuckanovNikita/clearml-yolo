# Machine workflow for live CY runs

The [test-environment contract](../../../../specs/012-own-test-infra/contracts/test-environment.md)
owns lifecycle and [helpers](../scripts/) implement it. This reference retains only
machine-specific precautions and diagnosis.

## The run's own test environment

Use the `docker-desktop` context and the environment recorded in this checkout's
`tests/integration/.run-tag`. Services are reached through loopback port-forwards;
there is no ClearML web UI. Credentials are generated per environment and exported by
`agent_env.sh`; keep them out of files and logs. Pytest in the same shell adopts that
environment and leaves its deletion to the shell's owner.

A live record causes setup refusal. Inspect ownership before cleanup; a stale record
is handled by the lifecycle. Finish work before the platform's environment lifetime
expires. A vanished environment invalidates remote readback, even if local logs remain.

## Host ClearML (do not touch)

The user-owned host ClearML UI/API ports are 8580/8008 and contain user experiments.
Do not redirect a run there or administer its services/configuration. A host endpoint
warning means inspect the owned environment and exported selectors before continuing;
blindly re-sourcing setup while its live record exists will correctly refuse.

## FiftyOne database

`agent_env.sh` selects the owned database. Its lock-directory default belongs to the
helper; publishers on this host using the same database must share that directory.
Task-driven persistence tests use their own session fixture and clean only their UUID
dataset prefixes. Keep database ownership distinct from lock-directory ownership.

## Run shape and GPU

Use explicit project/tag overrides from the skill and keep output beneath the owned
workspace. Check current pcboard capacity before host GPU work. Pods request no GPU;
this environment runs no ClearML Agent, so do not enqueue on `CLEARML_QUEUE`.
The separate local cy-queue workflow remains available for authorized queue checks.
Native device choices come from the generated backend configuration, not old evidence.

## Cleanup

`agent_cleanup.sh` delegates guarded namespace deletion and port-forward cleanup to
the lifecycle before removing the identifier-named run directory. Inspect its
`--dry-run` output when recovering. Preserve evidence and confirm owned descendants
are idle first; failed deletion is a recorded recovery obligation, never permission
for broad namespace or process cleanup.

## Diagnose ClearML 401 and missing tasks

1. Inspect this checkout's `.run-tag` and that namespace's pods in `docker-desktop`.
2. Run `scripts/check_env.sh` beside the skill. It authenticates with the effective
   endpoint/credentials and names their source; unauthenticated `debug.ping` alone
   proves no usable credentials. The helper's exit zero is only successful reporting.
3. An unreachable loopback endpoint usually means a stopped port-forward or vanished
   environment. Preserve logs, clean only the owned environment, then prepare a fresh
   one. A host port/configuration warning requires correcting the selected source;
   never print the credential pair or modify host configuration.
4. If authentication succeeds but tasks are absent, inspect the explicit tagged project
   and environment identity before changing product code.
