#!/usr/bin/env bash
# Report whether everything an end-to-end `cy` run needs is actually usable.
#
# Reachable is not the same as usable: the ClearML server answers `debug.ping`
# without any credentials at all, so this makes a real authenticated call. A
# stale ~/clearml.conf is the failure this script exists to catch — it looks
# healthy right up to the moment `Task.init()` raises LoginError 401.
#
# Always exits 0. This reports; it never blocks a session or a test run.
#
#   scripts/check_env.sh          human-readable report
#   scripts/check_env.sh --json   one JSON object for the SessionStart hook

set -uo pipefail

CLEARML_CONF="${CLEARML_CONFIG_FILE:-$HOME/clearml.conf}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

lines=()
problems=0

record() {
    lines+=("$1")
    case "$1" in
        FAIL*|WARN*) problems=$((problems + 1)) ;;
    esac
}

check_uv() {
    local version
    if ! version="$(uv --version 2>/dev/null)"; then
        record "FAIL uv — not on PATH; every project command runs through it"
        return
    fi
    record "OK   $version"
}

check_gpu() {
    local gpu
    if ! gpu="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null)"; then
        record "WARN nvidia-smi — no GPU visible; train/predict fall back to CPU or refuse to start"
        return
    fi
    record "OK   GPU $(echo "$gpu" | paste -sd '; ')"
}

# Docker Desktop leaves a shim on PATH in WSL distros where integration is off.
# It prints "could not be found in this WSL 2 distro" and exits 0, so a caller
# that trusts the exit code believes it started the server.
check_docker() {
    local output
    output="$(docker compose version 2>&1)"
    if [[ "$output" == *"could not be found in this WSL 2 distro"* ]]; then
        record "WARN docker — Docker Desktop shim only; compose commands do nothing here (and still exit 0)"
        return
    fi
    if [[ -z "$output" || "$output" != *"ompose"* ]]; then
        record "WARN docker — no working docker compose; you cannot start or stop the ClearML server from this shell"
        return
    fi
    record "OK   $(echo "$output" | head -1)"
}

read_conf_value() {
    sed -n "s/.*$1:[[:space:]]*//p" "$CLEARML_CONF" 2>/dev/null | tr -d '",' | head -1
}

check_clearml() {
    if [[ ! -f "$CLEARML_CONF" ]]; then
        record "FAIL clearml.conf — $CLEARML_CONF missing; mint credentials per the running-clearml-server skill"
        return
    fi

    local api
    api="$(read_conf_value api_server)"
    if [[ -z "$api" ]]; then
        record "FAIL clearml.conf — no api_server line in $CLEARML_CONF"
        return
    fi

    if ! curl -sf -m 5 "$api/debug.ping" >/dev/null 2>&1; then
        record "FAIL ClearML $api — unreachable; start it per the running-clearml-server skill"
        return
    fi

    local key secret body
    key="$(grep -oP '"access_key"\s*=\s*"\K[^"]+' "$CLEARML_CONF" 2>/dev/null | head -1)"
    secret="$(grep -oP '"secret_key"\s*=\s*"\K[^"]+' "$CLEARML_CONF" 2>/dev/null | head -1)"
    if [[ -z "$key" || -z "$secret" ]]; then
        record "FAIL ClearML $api — reachable, but $CLEARML_CONF holds no credentials pair"
        return
    fi

    body="$(curl -s -m 10 -u "$key:$secret" "$api/auth.login" 2>/dev/null)"
    if [[ "$body" != *'"result_code":200'* ]]; then
        record "FAIL ClearML $api — reachable but credentials rejected; \`cy\` will die on LoginError 401 mid-run"
        return
    fi
    record "OK   ClearML $api — reachable and authenticated"
}

check_uv
check_clearml
check_gpu
check_docker

if [[ "${1:-}" == "--json" ]]; then
    report="clearml-yolo environment ($REPO_ROOT):"
    for line in "${lines[@]}"; do
        report+=$'\n'"  $line"
    done
    if (( problems > 0 )); then
        report+=$'\n'"Anything marked FAIL breaks end-to-end \`cy\` runs; unit tests (\`uv run pytest\`) are fully mocked and unaffected."
    fi
    printf '%s' "$report" | python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":sys.stdin.read()}}))'
    exit 0
fi

echo "clearml-yolo environment ($REPO_ROOT):"
printf '  %s\n' "${lines[@]}"
exit 0
