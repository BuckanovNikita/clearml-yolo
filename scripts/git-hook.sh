#!/usr/bin/env bash
# Invoked by the shared hook after resolving the current worktree.
# The guard only inspects: it never stages, stashes or deletes anything.
set -eu
hook_type=$1
hook_dir=$2
shift 2
cd "$(git rev-parse --show-toplevel)"
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
if [ "$hook_type" = pre-commit ]; then
    uv run --locked task --exit-code staging-check
    export CY_VERIFY_SCOPE=staged
fi
exec uv run --frozen --no-sync prek hook-impl --hook-dir "$hook_dir" --script-version 4 --hook-type "$hook_type" -- "$@"
