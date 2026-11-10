#!/usr/bin/env bash
# Report whether everything an end-to-end `cy` run needs is actually usable.
#
# Reachable is not the same as usable: the ClearML server answers `debug.ping`
# without any credentials at all, so this makes a real authenticated call. A
# stale ~/clearml.conf is the failure this script exists to catch — it looks
# healthy right up to the moment `Task.init()` raises LoginError 401.
#
# The endpoint and the credentials are read the way the ClearML SDK reads them:
# CLEARML_API_HOST, CLEARML_API_ACCESS_KEY and CLEARML_API_SECRET_KEY from the
# environment first (what this skill's `agent_env.sh` exports for the run's own
# test environment, reached through a loopback port-forward), the config file for
# whatever the environment leaves unset. The report names which endpoint it
# authenticated against and where each value came from, and warns when that
# endpoint is the user's own host ClearML on localhost:8008 rather than the run's
# own test ClearML. It also reports whether kubectl reaches the docker-desktop
# cluster the test environment lives in.
#
# Always exits 0. This reports; it never blocks a session or a test run.
#
#   <skill-dir>/scripts/check_env.sh          human-readable, on-demand report
#   <skill-dir>/scripts/check_env.sh --json   one JSON object for an explicit caller

set -uo pipefail

CLEARML_CONF="${CLEARML_CONFIG_FILE:-$HOME/clearml.conf}"
CY_PROJECT_ROOT="${CY_PROJECT_ROOT:-$PWD}"
CY_ENV_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# The test environment lives in the docker-desktop cluster; kubectl is how it is
# created and reached (port-forward).
check_kubectl() {
    if ! command -v kubectl >/dev/null 2>&1; then
        record "FAIL kubectl — not on PATH; the run's own test environment is created and reached with it"
        return
    fi
    if ! kubectl config get-contexts docker-desktop -o name >/dev/null 2>&1; then
        record "FAIL kubectl — no docker-desktop context; the test cluster context is missing"
        return
    fi
    if ! timeout 10 kubectl --context docker-desktop get --raw=/readyz >/dev/null 2>&1; then
        record "FAIL kubectl — the docker-desktop cluster does not answer"
        return
    fi
    record "OK   kubectl — docker-desktop cluster reachable"
}

read_conf_value() {
    sed -n "s/.*$1:[[:space:]]*//p" "$CLEARML_CONF" 2>/dev/null | tr -d '",' | head -1
}

read_conf_credential() {
    grep -oP "\"$1\"\s*=\s*\"\K[^\"]+" "$CLEARML_CONF" 2>/dev/null | head -1
}

# The user's own ClearML runs on the host, API on localhost:8008; a run's own test
# ClearML answers on a loopback port that kubectl port-forward chose, never 8008. An
# agent that sees the former has not sourced this skill's agent_env.sh and would write
# into the user's projects.
HOST_STAND_API_PATTERN='^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0):8008/?$'

CLEARML_API_IN_USE=""

check_clearml() {
    local api key secret api_source credentials_source body
    api="${CLEARML_API_HOST:-}"
    api_source="environment"
    if [[ -z "$api" ]]; then
        if [[ ! -f "$CLEARML_CONF" ]]; then
            record "FAIL clearml.conf — $CLEARML_CONF missing and CLEARML_API_HOST unset; agents source $CY_ENV_SCRIPTS_DIR/agent_env.sh, people run clearml-init"
            return
        fi
        api="$(read_conf_value api_server)"
        api_source="$CLEARML_CONF"
        if [[ -z "$api" ]]; then
            record "FAIL clearml.conf — no api_server line in $CLEARML_CONF and CLEARML_API_HOST unset"
            return
        fi
    fi
    api="${api%/}"
    CLEARML_API_IN_USE="$api"

    local status=0
    curl -sf -m 5 "$api/debug.ping" >/dev/null 2>&1 || status=$?
    if (( status != 0 )); then
        record "FAIL ClearML $api (from $api_source) — unreachable (curl exit $status); a stopped port-forward or a deleted environment looks like this"
        return
    fi

    key="${CLEARML_API_ACCESS_KEY:-}"
    secret="${CLEARML_API_SECRET_KEY:-}"
    credentials_source="environment"
    if [[ -z "$key" || -z "$secret" ]]; then
        key="${key:-$(read_conf_credential access_key)}"
        secret="${secret:-$(read_conf_credential secret_key)}"
        credentials_source="$CLEARML_CONF"
    fi
    if [[ -z "$key" || -z "$secret" ]]; then
        record "FAIL ClearML $api (from $api_source) — reachable, but neither the environment nor $CLEARML_CONF holds a credentials pair"
        return
    fi

    status=0
    body="$(curl -s -m 10 -u "$key:$secret" "$api/auth.login" 2>/dev/null)" || status=$?
    # Without -f an HTTP 401 still exits 0, so any other nonzero status is a transport
    # failure (timeout, reset) and says nothing about the credentials.
    if (( status != 0 )); then
        record "FAIL ClearML $api (from $api_source) — auth.login did not complete (curl exit $status); the credentials were not checked"
        return
    fi
    if [[ "$body" != *'"result_code":200'* ]]; then
        record "FAIL ClearML $api (from $api_source) — reachable but the credentials from $credentials_source are rejected; \`cy\` will die on LoginError 401 mid-run"
        return
    fi
    record "OK   ClearML $api — authenticated (endpoint from $api_source, credentials from $credentials_source)"
}

warn_if_host_stand() {
    if [[ "$CLEARML_API_IN_USE" =~ $HOST_STAND_API_PATTERN ]]; then
        record "WARN ClearML $CLEARML_API_IN_USE is the user's host ClearML, not this run's own test ClearML; an agent run sources $CY_ENV_SCRIPTS_DIR/agent_env.sh first"
    fi
}

check_uv
check_clearml
warn_if_host_stand
check_kubectl
check_gpu

if [[ "${1:-}" == "--json" ]]; then
    report="clearml-yolo environment ($CY_PROJECT_ROOT):"
    for line in "${lines[@]}"; do
        report+=$'\n'"  $line"
    done
    if (( problems > 0 )); then
        report+=$'\n'"Anything marked FAIL breaks end-to-end \`cy\` runs; the repository test suite does not require a live ClearML service."
    fi
    printf '%s' "$report" | python3 -c 'import json,sys; print(json.dumps({"report": sys.stdin.read()}))'
    exit 0
fi

echo "clearml-yolo environment ($CY_PROJECT_ROOT):"
printf '  %s\n' "${lines[@]}"
exit 0
