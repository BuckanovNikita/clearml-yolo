#!/usr/bin/env bash
# Remove what one agent run created: its ClearML project(s) on the shared stand and its
# run directory. Run it on success and on failure, in the shell that sourced
# scripts/agent_env.sh (or with the tag and directory named explicitly).
#
#   scripts/agent_cleanup.sh                                  # CY_RUN_TAG / INFRA_RUN_TAG and CY_RUN_DIR
#   scripts/agent_cleanup.sh --tag <run-tag> [--run-dir <dir>]
#   scripts/agent_cleanup.sh --dry-run                        # list, delete nothing
#
# The stand side is `clearml.py --project clearml-yolo cleanup --prefix <tag>`, followed by
# `ls --prefix <tag>` so the proof of an empty listing is in the output. The directory is
# removed only when it is named after the tag: the run directory an agent points a run at
# is <scratch>/<tag>, and anything else is somebody's directory, not this run's.

set -euo pipefail

CY_INFRA_PROJECT="clearml-yolo"

tag="${CY_RUN_TAG:-${INFRA_RUN_TAG:-}}"
run_dir="${CY_RUN_DIR:-}"
dry_run=""

while (( $# > 0 )); do
    case "$1" in
        --tag) tag="$2"; shift 2 ;;
        --run-dir) run_dir="$2"; shift 2 ;;
        --dry-run) dry_run="--dry-run"; shift ;;
        *) echo "agent_cleanup.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$tag" ]]; then
    echo "agent_cleanup.sh: no run tag: source scripts/agent_env.sh first or pass --tag <run-tag>" >&2
    exit 2
fi

resolve_skill_dir() {
    local candidate
    for candidate in "${CY_INFRA_SKILL_DIR:-}" "${K8S_INFRA_SKILL_DIR:-}" "$HOME/.agents/skills/k8s-infra" "$HOME/.claude/skills/k8s-infra"; do
        if [[ -n "$candidate" && -f "$candidate/scripts/clearml.py" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    echo "agent_cleanup.sh: no k8s-infra skill found; set K8S_INFRA_SKILL_DIR" >&2
    return 1
}

skill_dir="$(resolve_skill_dir)"
clearml_py="$skill_dir/scripts/clearml.py"

# shellcheck disable=SC2086  # $dry_run is either empty or one flag
python3 "$clearml_py" --project "$CY_INFRA_PROJECT" cleanup --prefix "$tag" $dry_run
echo "agent_cleanup.sh: what is left under $tag on the stand:"
python3 "$clearml_py" --project "$CY_INFRA_PROJECT" ls --prefix "$tag"

if [[ -z "$run_dir" ]]; then
    echo "agent_cleanup.sh: no run directory named (CY_RUN_DIR unset); only the stand was cleaned"
    exit 0
fi
if [[ "$(basename "$run_dir")" != "$tag" ]]; then
    echo "agent_cleanup.sh: refusing to remove $run_dir: it is not named after $tag" >&2
    exit 1
fi
if [[ -n "$dry_run" ]]; then
    echo "agent_cleanup.sh: would remove $run_dir"
elif [[ -d "$run_dir" ]]; then
    rm -rf "$run_dir"
    echo "agent_cleanup.sh: removed $run_dir"
else
    echo "agent_cleanup.sh: $run_dir is already gone"
fi
