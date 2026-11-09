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
    # Hooks verify exactly the staged content: no unstaged tracked change is exempt.
    if ! git diff --quiet --ignore-submodules=none; then
        echo 'Unstaged tracked changes: run task fix, then stage inputs before committing.' >&2
        git diff --name-only --ignore-submodules=none >&2
        exit 1
    fi
    if IFS= read -r -d '' path < <(git ls-files --others --exclude-standard -z); then
        echo "Nonignored untracked inputs: stage or ignore them before committing: $path" >&2
        exit 1
    fi
fi
exec uv run --frozen --no-sync prek hook-impl --hook-dir "$hook_dir" --script-version 4 --hook-type "$hook_type" -- "$@"
