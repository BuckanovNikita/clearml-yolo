#!/usr/bin/env bash
# Delete the owned environment before its identifier-named output directory.
# See ../SKILL.md for evidence preservation and recovery.

set -euo pipefail

environment_scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$environment_scripts_dir/../../../.." && pwd)"

tag="${CY_RUN_TAG:-}"
run_dir="${CY_RUN_DIR:-}"
dry_run=()

while (( $# > 0 )); do
    case "$1" in
        --tag) tag="${2:-}"; shift 2 ;;
        --run-dir) run_dir="${2:-}"; shift 2 ;;
        --dry-run) dry_run=(--dry-run); shift ;;
        *) echo "agent_cleanup.sh: unknown argument $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$tag" ]]; then
    echo "agent_cleanup.sh: no environment identifier: source $environment_scripts_dir/agent_env.sh first or pass --tag <cy-it-id>" >&2
    exit 2
fi

status=0
(cd "$project_root" && uv run --locked python -m tests.integration.lifecycle stop --env "$tag" "${dry_run[@]}") || status=$?
if (( status != 0 )); then
    echo "agent_cleanup.sh: the environment $tag was not removed (status $status, see above); the run directory is left alone" >&2
    exit "$status"
fi

if [[ -z "$run_dir" ]]; then
    echo "agent_cleanup.sh: no run directory named (CY_RUN_DIR unset); only the environment was removed"
    exit 0
fi
if [[ "$(basename "$run_dir")" != "$tag" ]]; then
    echo "agent_cleanup.sh: refusing to remove $run_dir: it is not named after $tag" >&2
    exit 1
fi
if (( ${#dry_run[@]} > 0 )); then
    echo "agent_cleanup.sh: would remove $run_dir"
elif [[ -d "$run_dir" ]]; then
    rm -rf "$run_dir"
    echo "agent_cleanup.sh: removed $run_dir"
else
    echo "agent_cleanup.sh: $run_dir is already gone"
fi
