#!/usr/bin/env bash
# Session-start status for agent sessions (Claude and Codex SessionStart hooks).
# Shows parallel work that a new session should know about before editing:
# the branch against master, uncommitted changes, other worktrees and unmerged
# branches, a held release lock and an active live-test run tag. At most about
# ten lines; never fails the session.
set -u
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "(detached)")
if read -r behind ahead < <(git rev-list --left-right --count master...HEAD 2>/dev/null); then
    echo "clearml-yolo session status: branch $branch, $ahead ahead of master, $behind behind"
else
    echo "clearml-yolo session status: branch $branch"
fi

changed=$(git status --porcelain 2>/dev/null | wc -l)
staged=$(git diff --cached --name-only 2>/dev/null | wc -l)
if [ "$changed" -gt 0 ]; then
    echo "  uncommitted: $changed paths ($staged staged) - may belong to another session; do not stage them"
fi

# Every worktree except this one; from a linked worktree the main one is listed too.
worktrees=$(git worktree list 2>/dev/null | awk -v here="$root" '$1 != here')
if [ -n "$worktrees" ]; then
    echo "  other worktrees:"
    echo "$worktrees" | head -3 | sed 's/^/    /'
fi

unmerged=$(git branch --no-merged master --format='%(refname:short)' 2>/dev/null | grep -Fvx -e "$branch" | head -4 | paste -sd ' ' -)
if [ -n "$unmerged" ]; then
    echo "  unmerged branches: $unmerged"
fi

common=$(git rev-parse --git-common-dir 2>/dev/null) || common=""
lock="$common/clearml-yolo-release.lock"
if [ -n "$common" ] && [ -e "$lock" ] && command -v flock >/dev/null && ! flock -n "$lock" true 2>/dev/null; then
    echo "  release lock held: another session is merging or releasing master"
fi

if [ -s tests/integration/.run-tag ]; then
    echo "  active live run tag: $(head -1 tests/integration/.run-tag) (lifecycle stop when it is yours and done)"
fi
exit 0
