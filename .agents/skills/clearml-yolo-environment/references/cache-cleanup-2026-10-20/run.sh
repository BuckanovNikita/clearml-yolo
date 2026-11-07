#!/usr/bin/env bash
set -euo pipefail
evidence_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
evidence_output="${CY_ACCEPT_EVIDENCE:-$evidence_dir}"
mkdir -p "$evidence_output"
skill_dir=/mnt/wsl/data/nkt/.agents/skills/clearml-yolo-environment
export CY_PROJECT_ROOT=/mnt/wsl/data/nkt/clearml-yolo
export INFRA_HARNESS=codex
source "$skill_dir/scripts/agent_env.sh" cache-cleanup
trap '"$skill_dir/scripts/agent_cleanup.sh" > "$evidence_output/cleanup.log" 2>&1' EXIT
printf '%s\n' "$CY_RUN_TAG" > "$evidence_output/run-tag.txt"
export CY_HOME="$CY_RUN_DIR"
cd "$CY_PROJECT_ROOT"
uv run --frozen --no-sync python "$evidence_dir/live_acceptance.py"
