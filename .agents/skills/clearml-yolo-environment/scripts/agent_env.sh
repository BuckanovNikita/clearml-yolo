#!/usr/bin/env bash
# Source to create/export a fresh owned environment; see ../SKILL.md for decisions.
# Lifecycle owns refusal, capacity and deletion policy. This helper returns to its caller.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "agent_env.sh: source it, do not run it: source ${BASH_SOURCE[0]}" >&2
    exit 1
fi

cy_agent_env() {
    local environment_skill_dir project_root env_exports status
    environment_skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    project_root="$(cd "$environment_skill_dir/../../.." && pwd)"
    if (( $# > 0 )); then
        echo "agent_env.sh: the argument '$1' is ignored; environment identifiers carry no slug"
    fi

    # Clear prior exports so a failed start cannot publish to an old database.
    unset FIFTYONE_DATABASE_URI FIFTYONE_DATABASE_NAME

    status=0
    (cd "$project_root" && uv run --locked python -m tests.integration.lifecycle up --components all) || status=$?
    if (( status != 0 )); then
        if (( status == 3 )); then
            echo "agent_env.sh: the cluster is unavailable; nothing was left behind, try again later" >&2
            return 3
        fi
        echo "agent_env.sh: environment setup failed; follow any recovery command above or use $environment_skill_dir/scripts/agent_cleanup.sh" >&2
        return 1
    fi

    if ! env_exports="$(cd "$project_root" && uv run --locked python -m tests.integration.lifecycle env)"; then
        echo "agent_env.sh: the environment's variables could not be read (see above); remove it with $environment_skill_dir/scripts/agent_cleanup.sh" >&2
        return 1
    fi
    eval "$env_exports"
    export CY_RUN_TAG="$INTEGRATION_RUN_TAG"
    export FIFTYONE_DATABASE_DIR="${FIFTYONE_DATABASE_DIR:-$HOME/.cache/clearml-yolo/fiftyone}"

    CY_RUN_DIR="${CY_SCRATCH_DIR:-/tmp/clearml-yolo-runs}/$CY_RUN_TAG"
    mkdir -p "$CY_RUN_DIR" || return 1
    export CY_RUN_DIR

    cat <<EOF
agent_env.sh: environment $CY_RUN_TAG, ClearML on ${CLEARML_API_HOST:-<no CLEARML_API_HOST>}
  CY_RUN_TAG=$CY_RUN_TAG
  CY_RUN_DIR=$CY_RUN_DIR
  run:     uv run cy run_dir=\$CY_RUN_DIR clearml.project_name="\$CY_RUN_TAG clearml-yolo" clearml.tags=[\$CY_RUN_TAG] ultralytics.device=0 ultralytics_predict.device=0 <your keys>
  cleanup: $environment_skill_dir/scripts/agent_cleanup.sh
EOF
    CY_PROJECT_ROOT="${CY_PROJECT_ROOT:-$project_root}" "$environment_skill_dir/scripts/check_env.sh"
}

cy_agent_env "$@"
