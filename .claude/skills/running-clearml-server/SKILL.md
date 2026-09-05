---
name: running-clearml-server
description: >
  Use when clearml-yolo needs the local ClearML service: before a ClearML-backed
  pipeline run, when authentication fails, or when checking the shared service's
  endpoints and ownership. Trigger on ClearML server, clearml.conf, LoginError,
  port 8580, port 8008, or ClearML credentials.
---

# Use the shared ClearML server safely

The server is a machine-level service shared with other work. It is not part of
`clearml-yolo`; this repository neither owns nor discovers its deployment
checkout or compose project.

Read [the shared-server contract](references/shared-server-contract.md) before
any server-dependent run.

## Verify the dependency

From this repository, use:

```bash
./scripts/check_env.sh
```

It checks an authenticated SDK login using the credentials already configured
for the user. A successful unauthenticated `debug.ping` does not prove that a
run can create a task; it can still fail with `LoginError` when credentials are
missing or stale.

## Respect ownership

Do not adopt, restart, stop, reset, or reconfigure an existing shared server.
Do not overwrite `~/clearml.conf`, reset server data, or run an unqualified
`docker compose down`.

When an explicitly task-owned setup identifies its own deployment and services,
it may clean up only those named resources after the task. If the service is
already present, authentication or deployment problems belong to its owner:
report the failed authenticated check and the endpoint rather than changing the
shared service.

Docker tooling in WSL can report success without reaching Docker Desktop. Treat
an authenticated check and actual service state as evidence, not a compose
command's exit status alone.
