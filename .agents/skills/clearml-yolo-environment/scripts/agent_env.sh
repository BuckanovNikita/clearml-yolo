#!/usr/bin/env bash
# Source this before an agent's `cy` run: it makes the shell act as the project
# `clearml-yolo` on the shared ClearML stand and gives the run a tag and a directory.
#
#   source <skill-dir>/scripts/agent_env.sh [<slug>]  # slug: what the run is for, default "run"
#
# Steps, each one a refusal rather than a warning when it fails:
#   1. resolve the k8s-infra skill: $K8S_INFRA_SKILL_DIR, else ~/.agents/skills/k8s-infra,
#      else ~/.claude/skills/k8s-infra;
#   2. preflight with `infra.py room` and obey WAIT (return status 3);
#   3. eval `clearml.py --project clearml-yolo env`, so the ClearML SDK reads the stand's
#      CLEARML_* credentials from the environment and never from ~/clearml.conf; the same
#      output exports the CA trust (SSL_CERT_FILE, REQUESTS_CA_BUNDLE, AWS_CA_BUNDLE,
#      NODE_EXTRA_CA_CERTS) for the stand's https://*.k8s.docker.internal names;
#   4. mint INFRA_RUN_TAG with `infra.py newtag` unless one is already exported (an agent
#      that minted its own, with --keep say, keeps it);
#   5. export CY_RUN_TAG=$INFRA_RUN_TAG and CY_RUN_DIR=<scratch>/<tag>, where <scratch> is
#      $INFRA_SCRATCH_DIR or /tmp/clearml-yolo-runs;
#   6. run this skill's check_env.sh, which reports the endpoint it authenticated against.
#
# It is sourced, so it sets no shell options and returns instead of exiting. Nothing it
# prints is a secret: the credentials go straight from the helper into the environment.
#
# Undo everything it created with this skill's agent_cleanup.sh.

CY_INFRA_PROJECT="clearml-yolo"
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "agent_env.sh: source it, do not run it: source ${BASH_SOURCE[0]} [<slug>]" >&2
    exit 1
fi

cy_resolve_skill_dir() {
    local candidate
    for candidate in "${K8S_INFRA_SKILL_DIR:-}" "$HOME/.agents/skills/k8s-infra" "$HOME/.claude/skills/k8s-infra"; do
        if [[ -n "$candidate" && -f "$candidate/scripts/infra.py" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    echo "agent_env.sh: no k8s-infra skill found; set K8S_INFRA_SKILL_DIR or install the skill under ~/.agents/skills or ~/.claude/skills" >&2
    return 1
}

cy_agent_env() {
    local slug="${1:-run}"
    local environment_skill_dir skill_dir room_status env_exports scratch_root
    environment_skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    skill_dir="$(cy_resolve_skill_dir)" || return 1
    export CY_INFRA_SKILL_DIR="$skill_dir"

    python3 "$skill_dir/scripts/infra.py" room
    room_status=$?
    if (( room_status == 3 )); then
        echo "agent_env.sh: infra.py room says WAIT; nothing was minted, try again later" >&2
        return 3
    elif (( room_status != 0 )); then
        echo "agent_env.sh: infra.py room could not read the cluster (status $room_status)" >&2
        return 1
    fi

    if ! env_exports="$(python3 "$skill_dir/scripts/clearml.py" --project "$CY_INFRA_PROJECT" env)"; then
        echo "agent_env.sh: clearml.py env refused; the project Secret is missing, the cluster is unreachable, or its TLS certificate is not trusted, see above" >&2
        return 1
    fi
    eval "$env_exports"
    export INFRA_PROJECT="$CY_INFRA_PROJECT"

    # Visualization is optional: unavailable MongoDB must not block computation.
    # Clear prior helper exports so a failed refresh cannot publish to an old database.
    unset FIFTYONE_DATABASE_URI FIFTYONE_DATABASE_NAME
    if [[ -f "$skill_dir/scripts/mongodb.py" ]]; then
        if env_exports="$(python3 "$skill_dir/scripts/mongodb.py" --project "$CY_INFRA_PROJECT" env)"; then
            eval "$env_exports"
            export FIFTYONE_DATABASE_DIR="${FIFTYONE_DATABASE_DIR:-$HOME/.cache/clearml-yolo/fiftyone}"
        else
            echo "agent_env.sh: warning: shared MongoDB access unavailable; publication may be skipped" >&2
        fi
    else
        echo "agent_env.sh: warning: shared MongoDB helper unavailable; publication may be skipped" >&2
    fi

    if [[ -z "${INFRA_RUN_TAG:-}" ]]; then
        INFRA_RUN_TAG="$(python3 "$skill_dir/scripts/infra.py" newtag --project "$CY_INFRA_PROJECT" --slug "$slug")" || {
            unset INFRA_RUN_TAG
            echo "agent_env.sh: infra.py newtag refused; nothing was exported" >&2
            return 1
        }
        export INFRA_RUN_TAG
    else
        echo "agent_env.sh: keeping the exported INFRA_RUN_TAG=$INFRA_RUN_TAG"
    fi
    export CY_RUN_TAG="$INFRA_RUN_TAG"

    scratch_root="${INFRA_SCRATCH_DIR:-/tmp/clearml-yolo-runs}"
    CY_RUN_DIR="$scratch_root/$CY_RUN_TAG"
    mkdir -p "$CY_RUN_DIR" || return 1
    export CY_RUN_DIR

    cat <<EOF
agent_env.sh: project $CY_INFRA_PROJECT on ${CLEARML_API_HOST:-<no CLEARML_API_HOST>}
  CY_RUN_TAG=$CY_RUN_TAG
  CY_RUN_DIR=$CY_RUN_DIR
  run:     uv run cy run_dir=\$CY_RUN_DIR clearml.project_name="\$CY_RUN_TAG clearml-yolo" clearml.tags=[\$CY_RUN_TAG] ultralytics.device=0 ultralytics_predict.device=0 <your keys>
  cleanup: $environment_skill_dir/scripts/agent_cleanup.sh
EOF
    "$environment_skill_dir/scripts/check_env.sh"
}

cy_agent_env "$@"
