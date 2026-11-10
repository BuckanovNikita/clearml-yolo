# Machine workflow for clearml-yolo

Read this reference before an agent's live run, using the host GPU, or diagnosing
ClearML authentication. It adds clearml-yolo-specific machine facts to the
[test environment contract](../../../../specs/012-own-test-infra/contracts/test-environment.md);
`tests/integration/lifecycle.py` owns the environment's creation, selection and
deletion.

## Contents

- [The run's own test environment](#the-runs-own-test-environment)
- [Host ClearML (do not touch)](#host-clearml-do-not-touch)
- [FiftyOne database](#fiftyone-database)
- [Run shape and GPU](#run-shape-and-gpu)
- [Cleanup](#cleanup)
- [Diagnose ClearML 401 and missing tasks](#diagnose-clearml-401-and-missing-tasks)

## The run's own test environment

An agent run uses a test environment that this project creates in the
`docker-desktop` Kubernetes cluster: one namespace `cy-it-<6 hex>` with a
`ResourceQuota` and a `LimitRange`, MongoDB, Redis, Elasticsearch and the ClearML API
and file servers, every volume `emptyDir`. No web UI runs in it. The environment's
API and file servers and its database are reached through `kubectl port-forward` to
loopback ports that kubectl chooses, over plain HTTP inside the tunnel; no host name,
ingress or certificate is involved, and no port is fixed.

`agent_env.sh` runs `lifecycle up --components all` and evaluates `lifecycle env` in
the checkout that contains the skill. The credential pair is generated per
environment, held in the namespace's Secret and the shell environment, and never
printed. Do not write a ClearML configuration file, run `clearml-init`, or print the
pair. A pytest session started in the same shell adopts the environment (its exported
`INTEGRATION_RUN_TAG` equals the record) and leaves it for `agent_cleanup.sh`.

One checkout records at most one environment (`tests/integration/.run-tag`). While a
live one is recorded, `agent_env.sh` and `lifecycle up` refuse; remove it first. A
record whose namespace has vanished (the platform sweeper deletes every unprotected
namespace 48 hours after its creation or after a Docker Desktop or PC restart) is
cleared and replaced by the next `agent_env.sh`, so a run must finish inside that
window.

## Host ClearML (do not touch)

The user-owned host ClearML is distinct: its UI/API ports are 8580/8008. It
contains user experiments. Do not redirect a run to it, read or write its
configuration, or start, stop, or reconfigure it. A port-forward never takes port
8008. If `check_env.sh` warns about a host endpoint, or names a host port or a
configuration file, source `agent_env.sh` again and re-check before proceeding.

## FiftyOne database

The environment's MongoDB server also holds the FiftyOne database (FiftyOne's own
database name). `agent_env.sh` exports `FIFTYONE_DATABASE_URI` pointing at its
port-forward and defaults `FIFTYONE_DATABASE_DIR` to
`$HOME/.cache/clearml-yolo/fiftyone`, the publisher's lock directory; preserve a
shared lock directory for publishers on this host using the same database. The
database dies with the environment.

The FiftyOne persistence tests take the database from their session fixture, not
from the shell: run them through the release-acceptance FiftyOne step (or with
`CY_TEST_FIFTYONE=1` and a fresh task-owned `FIFTYONE_DATABASE_DIR`). The tests clean
only their UUID dataset prefixes.

## Run shape and GPU

Each invocation owns one task and one tag-scoped project named
`$CY_RUN_TAG clearml-yolo`. Run under `run_dir=$CY_RUN_DIR` (or a child of it),
with `ground_truth` supplied for a pipeline or standalone training, which derives
its dataset. Pass the explicit project name and tag list from the SKILL.md
checklist. Pipeline stages must not select separate output routes.

Native device selection belongs to Ultralytics. Use explicit
`ultralytics.device=0` and `ultralytics_predict.device=0` only when the
requested run needs the host GPU. Do not infer a free GPU from an old result or
change another workload. The GPU is used by host processes; the environment's pods
request none, and the environment runs no ClearML agent or queue, so never enqueue
work on `CLEARML_QUEUE` for it. CPU runs remain valid where GPU execution is not
requested.

## Cleanup

Execute this skill's `scripts/agent_cleanup.sh` in the shell that holds
`CY_RUN_TAG`. It runs `lifecycle stop --env <id>`: the deletion guard refuses any name
that is not `cy-it-<6 hex>` or whose namespace lacks the project label, then the
recorded port-forwards stop, the namespace is deleted and its absence proven. It
then removes only a local directory whose basename exactly equals the identifier.
Use `--dry-run` to inspect cleanup without deleting anything.

## Diagnose ClearML 401 and missing tasks

`debug.ping` is unauthenticated and therefore does not prove a usable run. For
`LoginError: 401`, missing provided credentials, a hanging `Task.init`, or an
unexpectedly empty baseline lookup, run these checks from the application
checkout:

```bash
project_root="$(git rev-parse --show-toplevel)"
skill_dir="$project_root/.agents/skills/clearml-yolo-environment"
head -1 "$project_root/tests/integration/.run-tag"
kubectl --context docker-desktop get pods --namespace "$CY_RUN_TAG"
"$skill_dir/scripts/check_env.sh"
```

The record and the namespace listing show whether the environment still exists and
its components are ready. `check_env.sh` authenticates with the effective SDK
environment/configuration and names the endpoint and source. An unreachable
loopback endpoint usually means a stopped port-forward or a deleted environment:
remove it with `agent_cleanup.sh` and source `agent_env.sh` again. If the check names
a host port or configuration file, follow
[Host ClearML](#host-clearml-do-not-touch). A complete auth check with absent tasks
can still indicate the wrong tagged project; inspect the project name before
changing application code.
