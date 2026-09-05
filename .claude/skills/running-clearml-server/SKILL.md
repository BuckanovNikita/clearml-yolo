---
name: running-clearml-server
description: >
  Use when a clearml-yolo run needs ClearML: before a ClearML-backed `cy` run,
  when a run dies on LoginError 401 or "failed to locate provided credentials",
  when `Task.init` hangs or a baseline lookup finds no tasks, or when deciding
  which ClearML a run should talk to. Trigger on ClearML stand,
  clearml.k8s.localhost, ClearML 401, LoginError, ClearML credentials,
  clearml.py whoami, agent_env.sh, or "which ClearML".
---

# Use the ClearML stand

An agent's run talks to the shared ClearML stand on the docker-desktop
cluster, as the project `clearml-yolo`, and to nothing else. The stand is
described by the k8s-infra skill at `/mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra`:
`references/clearml-stand.md` is the stand, `references/run-contract.md` the
rules every run there follows. Read both before the first run; this skill only
says how they land on `clearml-yolo`.

| What | Where |
|---|---|
| UI, for looking at a run's project | `http://clearml.k8s.localhost/` |
| API the SDK talks to (`CLEARML_API_HOST`) | `http://api.clearml.k8s.localhost/` |
| Artifacts (`CLEARML_FILES_HOST`) | `http://files.clearml.k8s.localhost/` |
| Identity | fixed user `clearml-yolo`, one credential pair in a cluster Secret |

## Become the project

The credentials exist only in the Secret and reach the SDK only through the
environment. Either line makes the shell act as `clearml-yolo`:

```bash
source scripts/agent_env.sh <slug>     # also mints CY_RUN_TAG and CY_RUN_DIR, then runs check_env.sh
eval "$(python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo env)"
```

The ClearML SDK reads `CLEARML_API_HOST`, `CLEARML_WEB_HOST`,
`CLEARML_FILES_HOST`, `CLEARML_API_ACCESS_KEY` and `CLEARML_API_SECRET_KEY`
from the environment before any config file, so the exports are the whole
setup. Do not write `~/clearml.conf` or `/mnt/wsl/data/nkt/clearml.conf`, do
not run `clearml-init`, and do not paste the pair into files, commits or
messages: `env` prints it for `eval` and for nothing else.

Every run's experiments go to a project named `<run-tag> clearml-yolo`, and
the run is removed at the end; the run tag, the naming and the cleanup are in
`running-end-to-end-tests` and in `AGENTS.md`, "Agent runs".

## The user's ClearML is not the target

The user has a ClearML of their own on this host (its UI answers on port 8580
and its API on port 8008). It holds their experiments. Agents never point a
run at it, never read or write its `clearml.conf`, and never start, stop or
reconfigure it. A run that ends up there has skipped `agent_env.sh`;
`scripts/check_env.sh` names that case with a WARN line. The stand itself is
deployed and torn down by k8s-infra, never from this repository: a stand that
is down is reported, not repaired.

## Diagnose a refused run

`LoginError: ... 401` and `failed to locate provided credentials` share one
cause: the process is not authenticating as `clearml-yolo` against the stand.
`debug.ping` answers without credentials, so "the server is reachable" proves
nothing. Ask in this order:

```bash
python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo whoami
scripts/check_env.sh
```

`whoami` reads the Secret, signs in as the project's fixed user and names the
missing layer when it fails (Secret, ingress, pod, queue); it prints key names
only. `check_env.sh` makes an authenticated `auth.login` with what this shell
would hand the SDK and reports which endpoint it reached and where the
endpoint and the pair came from (environment or config file). A report that
names the config file or the host ports means the shell has not sourced
`scripts/agent_env.sh`; source it and run the check again. A `whoami` that
fails is the stand's or the Secret's problem: report its message and stop.

A `Task.init` that hangs or a baseline lookup that finds nothing usually means
the run authenticated against one ClearML and is looking in another, or in a
project the tag did not name. Check `CLEARML_API_HOST` in the shell and the
project name in the stand's UI before touching the code.
