---
name: running-clearml-server
description: |
  Use when anything in clearml-yolo needs the local self-hosted ClearML server on this box: before an end-to-end `cy` run,
  when deciding whether ClearML is up, when a run dies on LoginError 401 / "failed to locate provided credentials",
  when `Task.init` hangs or a baseline lookup finds no tasks, or when starting, stopping or re-credentialing the server.
  Trigger on: "start ClearML", "is ClearML up", "ClearML 401", "clearml.conf", "clearml-server", "docker compose up clearml",
  "LoginError", "ClearML credentials", "port 8580", "port 8008".
---

# Running the local ClearML server

`clearml-yolo` talks to a self-hosted ClearML at `/home/nkt/clearml-server` (docker compose + its own
README). It is a **machine-level service shared with other work**, not part of this repo.

## Check before you start anything

```bash
./scripts/check_env.sh
```

This is the only check that tells the truth. `debug.ping` answers **without any credentials**, so a
reachable server proves nothing — `check_env.sh` makes a real authenticated `auth.login` call with the
key pair from `~/clearml.conf`. A stale conf looks perfectly healthy until `Task.init()` raises
`LoginError ... 401 ... (failed to locate provided credentials)` partway into a run.

## Where it lives

| Service | URL |
|---|---|
| Web UI | http://localhost:8580 |
| API server | http://localhost:8008 |
| File server | http://localhost:8081 |

The UI is on 8580, not the standard 8080, because the CVAT stack's `traefik` container owns 8080 on this
host. The API and file server keep their defaults, which is what the SDK expects.

SDK credentials live in `~/clearml.conf` (gitignored here). Web UI login is the fixed user `nkt` /
`clearml` from `/home/nkt/clearml-server/config/apiserver.conf`.

## Starting and stopping

```bash
docker compose -f /home/nkt/clearml-server/docker-compose.yml up -d
docker compose -f /home/nkt/clearml-server/docker-compose.yml ps
docker compose -f /home/nkt/clearml-server/docker-compose.yml down
```

State lives in `/home/nkt/clearml-server/data` (elastic, mongo, redis, fileserver), so no root is needed.
`down` keeps it; deleting `data/` resets the server to empty — **and invalidates every credential in
`~/clearml.conf`**, which is the usual cause of a sudden 401 against a server that pings fine.

## Never touch the other stacks

CVAT, keycloak and lakefs run on the same Docker daemon. Never `docker compose down` from a directory
other than `/home/nkt/clearml-server`, and never stop a container you did not start.

## Minting credentials after a reset

Anonymous access is disabled in the open-source server, so the fixed user is the only headless route:
`auth.login` with basic auth (`nkt`/`clearml`), then `auth.create_credentials`, then write the returned
access/secret pair into `~/clearml.conf`.

```bash
curl -s -u nkt:clearml http://localhost:8008/auth.login
```

A 401 here means the apiserver on 8008 does not know that fixed user — it is not the
`/home/nkt/clearml-server` deployment, or its mongo volume was replaced. Check
`/home/nkt/clearml-server/logs/apiserver.log`: its last "Adding fixed users" line is the last time this
deployment actually started.

## Known quirks

**Docker Desktop shim.** In this WSL distro `docker` may be a Docker Desktop stub that prints
`The command 'docker' could not be found in this WSL 2 distro` **and exits 0**. Compose commands then do
nothing while appearing to succeed. `check_env.sh` detects this. When it reports the shim, you cannot
start or stop the server from this shell — say so and ask the user to run it where Docker Desktop
integration is enabled, rather than reporting a start that never happened.

**`Task.init()` in a standalone script** blocks for 300 s at `close()` on "repository and package
requirement analysis". The `cy*` apps are unaffected — they never call `close()`, so the process exits
without waiting. Do not add a `close()` to reproduce something.

## Common mistakes

| Mistake | What actually happens |
|---|---|
| Treating `curl .../debug.ping` as a health check | Passes with no credentials at all; the run still dies on 401 |
| Trusting `docker compose up -d`'s exit code | The WSL shim exits 0 without starting anything |
| `docker compose down` from the wrong directory | Takes down CVAT or keycloak, which you did not start |
| Deleting `data/` to "reset" | Also invalidates `~/clearml.conf`; re-mint credentials afterwards |
