#!/usr/bin/env bash
# Install worktree-aware dispatchers, preserving the previous installation.
# Linked worktrees share one hooks directory, so the dispatcher resolves the
# committing worktree at run time and never records installation paths.
set -eu
cd "$(git rev-parse --show-toplevel)"
hook_dir=$(git rev-parse --path-format=absolute --git-path hooks)
mkdir -p "$hook_dir"
backup=$(mktemp -d "$hook_dir/clearml-yolo-backup.XXXXXX")
for hook_type in pre-commit commit-msg; do
    if [ -e "$hook_dir/$hook_type" ]; then
        cp -p -- "$hook_dir/$hook_type" "$backup/$hook_type"
    else
        touch "$backup/$hook_type.absent"
    fi
    cat > "$backup/$hook_type.new" <<'HOOK'
#!/usr/bin/env bash
# clearml-yolo worktree dispatcher: no installation-worktree paths.
set -eu
hook_dir=$(cd "$(dirname "$0")" && pwd)
hook_type=$(basename "$0")
root=$(git rev-parse --show-toplevel)
cd "$root"
export UV_PROJECT_ENVIRONMENT="$root/.venv"
tracked() {
    [ -f "$1" ] || git cat-file -e "HEAD:$1" 2>/dev/null || git cat-file -e ":$1" 2>/dev/null
}
# A deleted working-tree file must not masquerade as a legacy checkout. Commits that
# predate scripts/git-hook.sh (it is absent from the tree, HEAD and the index) use prek.
if tracked scripts/git-hook.sh; then
    if [ ! -f Taskfile.yml ] || [ ! -f scripts/git-hook.sh ]; then
        echo 'Task workflow files are missing; restore them before committing.' >&2
        exit 1
    fi
    exec bash scripts/git-hook.sh "$hook_type" "$hook_dir" "$@"
fi
if tracked Taskfile.yml && [ ! -f Taskfile.yml ]; then
    echo 'Taskfile.yml is missing; restore it before committing.' >&2
    exit 1
fi
# Older worktrees keep their own prek configuration and environment.
exec uv run --frozen --no-sync prek hook-impl --hook-dir "$hook_dir" --script-version 4 --hook-type "$hook_type" -- "$@"
HOOK
    chmod +x "$backup/$hook_type.new"
    mv -- "$backup/$hook_type.new" "$hook_dir/$hook_type"
done
printf 'Installed worktree-aware hooks. Previous hooks: %s\n' "$backup"
printf 'Rollback: restore each saved hook; remove hooks marked .absent.\n'
