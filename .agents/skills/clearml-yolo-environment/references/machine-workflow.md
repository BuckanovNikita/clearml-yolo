# Machine workflow for clearml-yolo

Read this reference before touching the shared ClearML stand, using the host
GPU, or diagnosing ClearML authentication. It adds clearml-yolo-specific machine
facts to the generic contract; `k8s-infra` owns stand lifecycle, registry,
capacity, Secret access, tags, and cleanup guards.

## Contents

- [Shared ClearML stand and identity](#shared-clearml-stand-and-identity)
- [TLS trust](#tls-trust)
- [Host ClearML (do not touch)](#host-clearml-do-not-touch)
- [FiftyOne and shared MongoDB](#fiftyone-and-shared-mongodb)
- [Run shape and GPU](#run-shape-and-gpu)
- [Cleanup](#cleanup)
- [Diagnose ClearML 401 and missing tasks](#diagnose-clearml-401-and-missing-tasks)

## Shared ClearML stand and identity

This application's agent runs use the docker-desktop shared ClearML stand as
project identity `clearml-yolo`. The UI is
`https://clearml.k8s.docker.internal/`, the SDK API endpoint is
`https://api.clearml.k8s.docker.internal/`, and the files endpoint is
`https://files.clearml.k8s.docker.internal/`. `agent_env.sh` obtains the credential
pair only by evaluating the k8s-infra helper's `clearml.py --project clearml-yolo
env` output. Do not write a ClearML configuration file, run `clearml-init`, or
print the pair.

Before the first live run, read the installed k8s-infra
`references/run-contract.md` and `references/clearml-stand.md`; `agent_env.sh`
resolves it from `K8S_INFRA_SKILL_DIR`, then the installed `.agents` or `.claude`
path. It runs `infra.py room`, treats exit status 3 as WAIT, gets credentials,
mints one tag unless `INFRA_RUN_TAG` is already present, and sets `CY_RUN_TAG`
and `CY_RUN_DIR`. It refuses rather than falling back to host credentials.

## TLS trust

The stand's certificate comes from the k8s-infra local CA. The same helper
output exports `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` and `AWS_CA_BUNDLE`, pointing
at the host bundle `/etc/ssl/certs/ca-certificates.crt` whenever it exists (it
trusts the stand only once the local CA is installed into it), and
`NODE_EXTRA_CA_CERTS` when the local CA file itself is installed.

- A `check_env.sh` line containing `TLS verification failed` (for `debug.ping` or
  for `auth.login`) is a trust problem, not a stand outage.
- A `TLS handshake failed` line (curl exit 35) may also mean the stand is down
  or not serving TLS yet. Re-source `agent_env.sh` and check the installed CA
  through the k8s-infra references.

Never disable verification. The old `http://*.k8s.localhost` names remain served
only so artifact URLs recorded by earlier tasks keep resolving; new runs use the
HTTPS names.

## Host ClearML (do not touch)

The user-owned host ClearML is distinct: its UI/API ports are 8580/8008. It
contains user experiments. Do not redirect a run to it, read or write its
configuration, or start, stop, or reconfigure it. If `check_env.sh` warns about a
host endpoint, or names a host port or a configuration file, source
`agent_env.sh` again and re-check before proceeding.

## FiftyOne and shared MongoDB

`agent_env.sh` also consumes `mongodb.py --project clearml-yolo env` from the
k8s-infra skill for optional FiftyOne publication. Its project user is
scoped to the durable `clearml_yolo` and `clearml_yolo_tests` databases on the
separate shared MongoDB stand, not ClearML's backing database. Missing MongoDB
access warns and lets computation continue. The default local FiftyOne lock
directory is `$HOME/.cache/clearml-yolo/fiftyone`; preserve a shared directory
for publishers on this host using the same database.

For actual persistence tests, consume the k8s-infra helper's `env --test` output
directly, set a fresh task-owned `FIFTYONE_DATABASE_DIR`, and run the opt-in
FiftyOne test module. Set these variables before importing FiftyOne. The tests
clean only their UUID dataset prefixes. Cross-host publishers need unique
dataset prefixes or external serialization because local file locks cannot
coordinate different machines. Read the k8s-infra `references/mongodb-stand.md`
for deployment, credentials, and current endpoint configuration.

## Run shape and GPU

Each invocation owns one task and one tag-scoped project named
`$CY_RUN_TAG clearml-yolo`. Run under `run_dir=$CY_RUN_DIR` (or a child of it),
with `ground_truth` supplied for a pipeline or standalone training, which derives
its dataset. Pass the explicit project name and tag list from the SKILL.md
checklist. Pipeline stages must not select separate output routes.

Native device selection belongs to Ultralytics. Use explicit
`ultralytics.device=0` and `ultralytics_predict.device=0` only when the
requested run needs the host GPU. Do not infer a free GPU from an old result or
change another workload. GPU tasks must not be enqueued on `CLEARML_QUEUE`: its
task pods are CPU-only and cannot reach the host GPU. CPU runs remain valid where
GPU execution is not requested.

## Cleanup

Execute this skill's `scripts/agent_cleanup.sh` in the environment that holds the
tag. It calls the k8s-infra ClearML helper with that exact prefix, lists what
remains, and removes only a local directory whose basename exactly equals the
tag. Use `--dry-run` to inspect cleanup without deleting anything.

## Diagnose ClearML 401 and missing tasks

`debug.ping` is unauthenticated and therefore does not prove a usable run. For
`LoginError: 401`, missing provided credentials, a hanging `Task.init`, or an
unexpectedly empty baseline lookup, run these checks from the application
checkout:

```bash
project_root="$(git rev-parse --show-toplevel)"
skill_dir="$project_root/.agents/skills/clearml-yolo-environment"
infra_skill_dir="${CY_INFRA_SKILL_DIR:-${K8S_INFRA_SKILL_DIR:-}}"
if [[ -z "$infra_skill_dir" ]]; then
  for candidate in "$HOME/.agents/skills/k8s-infra" "$HOME/.claude/skills/k8s-infra"; do
    [[ -f "$candidate/scripts/clearml.py" ]] && { infra_skill_dir="$candidate"; break; }
  done
fi
: "${infra_skill_dir:?set K8S_INFRA_SKILL_DIR to the installed sibling before a pre-environment diagnosis}"
python3 "$infra_skill_dir/scripts/clearml.py" \
  --project clearml-yolo whoami
"$skill_dir/scripts/check_env.sh"
```

`whoami` identifies a failed Secret, ingress, pod, token, or queue without
showing secret values. `check_env.sh` authenticates with the effective SDK
environment/configuration and names the endpoint and source. If the former
fails, report the stand dependency and stop. If the latter names a host port or
configuration file, follow [Host ClearML](#host-clearml-do-not-touch). A complete
auth check with absent tasks can still indicate the wrong tagged project;
inspect the stand's project name before changing application code.
