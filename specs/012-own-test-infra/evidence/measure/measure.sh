#!/usr/bin/env bash
# Measurement driver (2026-11-10), not the implementation. Creates namespace $1 with
# stack.yaml (Elasticsearch heap $2, request $3, limit $4), times readiness, runs the embedded probe
# through kubectl port-forward on random local ports, prints a JSON summary. Credentials are
# generated here, passed to the Secret and the embedded probe through stdin/environment, never printed
# or written to disk. The namespace is left for inspection; delete it with
#   kubectl --context docker-desktop delete namespace "$1" --wait
set -euo pipefail
ns="$1" heap="${2:-512m}" esreq="${3:-768Mi}" eslim="${4:-1536Mi}"
case "$ns" in cy-it-*) ;; *) echo "namespace must start with cy-it-" >&2; exit 2 ;; esac
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../../.." && pwd)"
k=(kubectl --context docker-desktop)
gen() { python3 -c 'import secrets,string;a=string.ascii_uppercase+string.digits;print("".join(secrets.choice(a) for _ in range(24)))'; }
gens() { python3 -c 'import secrets;print(secrets.token_urlsafe(36))'; }
apiserver_key=$(gen) apiserver_secret=$(gens)
token_secret=$(gens) test_key=$(gen) test_secret=$(gens)

t0=$(date +%s.%N)
"${k[@]}" create namespace "$ns" >/dev/null
"${k[@]}" label namespace "$ns" app.kubernetes.io/part-of=clearml-yolo-tests >/dev/null
printf 'apiserver_key=%s\napiserver_secret=%s\ntoken_secret=%s\ntest_key=%s\ntest_secret=%s\n' \
  "$apiserver_key" "$apiserver_secret" "$token_secret" "$test_key" "$test_secret" |
  "${k[@]}" -n "$ns" create secret generic cy-it-credentials --from-env-file=/dev/stdin >/dev/null
sed -e "s/NAMESPACE/$ns/g" -e "s/__HEAP__/$heap/g" -e "s/__ESREQ__/$esreq/g" -e "s/__ESLIM__/$eslim/g" "$here/stack.yaml" |
  "${k[@]}" apply -f - >/dev/null
"${k[@]}" -n "$ns" wait --for=condition=Available deployment --all --timeout=600s >/dev/null
t_ready=$(date +%s.%N)

pf_log_api=$(mktemp) pf_log_files=$(mktemp)
"${k[@]}" -n "$ns" port-forward svc/apiserver :8008 >"$pf_log_api" 2>&1 & pf_api=$!
"${k[@]}" -n "$ns" port-forward svc/fileserver :8081 >"$pf_log_files" 2>&1 & pf_files=$!
trap 'kill $pf_api $pf_files 2>/dev/null; rm -f "$pf_log_api" "$pf_log_files"' EXIT
port() { for _ in $(seq 50); do p=$(sed -n 's/.*127.0.0.1:\([0-9]*\) ->.*/\1/p' "$1" | head -1); [[ -n "$p" ]] && { echo "$p"; return; }; sleep 0.2; done; return 1; }
api_port=$(port "$pf_log_api") files_port=$(port "$pf_log_files")

scratch_home=$(mktemp -d)
for _ in $(seq 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "$test_key:$test_secret" "http://127.0.0.1:$api_port/auth.login" || true)
  [[ "$code" == 200 ]] && break; sleep 1
done
t_auth=$(date +%s.%N)
read -r -d '' probe_src <<'PROBE' || true
"""Measurement probe (2026-11-10): one authenticated ClearML write through a port-forward.

Reads CLEARML_API_HOST, CLEARML_FILES_HOST, CLEARML_WEB_HOST, CLEARML_API_ACCESS_KEY and
CLEARML_API_SECRET_KEY from the environment and never prints them. Creates one task, uploads
one artifact and one output model to the fileserver, reads them back by id, and prints
timings. Run it under a throwaway HOME so no ~/clearml.conf is read.
"""

import json
import sys
import tempfile
import time
from pathlib import Path

started = time.monotonic()
from clearml import OutputModel, Task  # noqa: E402

task = Task.init(project_name="cy-it-probe", task_name="probe", auto_connect_frameworks=False, reuse_last_task_id=False)
initialized = time.monotonic()
task.upload_artifact("probe", artifact_object={"value": 1}, wait_on_upload=True)
with tempfile.TemporaryDirectory() as scratch:
    weights = Path(scratch) / "probe.pt"
    weights.write_bytes(b"0" * 1024 * 1024)
    model = OutputModel(task=task, name="probe-model")
    model.update_weights(weights_filename=str(weights), auto_delete_file=False, async_enable=False)
task.flush(wait_for_uploads=True)
task.close()
uploaded = time.monotonic()
again = Task.get_task(task_id=task.id)
artifact = again.artifacts["probe"]
downloaded = artifact.get()
models = again.models["output"]
result = {
    "task_status": again.get_status(),
    "artifact_roundtrip": downloaded == {"value": 1},
    "output_models": len(models),
    "model_url_is_fileserver": bool(models) and models[0].url.startswith(task.session.get_files_server_host()),
    "import_and_init_s": round(initialized - started, 1),
    "write_and_upload_s": round(uploaded - initialized, 1),
}
print(json.dumps(result))
sys.exit(0 if result["artifact_roundtrip"] and result["output_models"] == 1 else 1)
PROBE
probe=$(HOME="$scratch_home" CLEARML_CONFIG_FILE=/nonexistent \
  CLEARML_API_HOST="http://127.0.0.1:$api_port" CLEARML_FILES_HOST="http://127.0.0.1:$files_port" \
  CLEARML_WEB_HOST="http://127.0.0.1:$api_port" \
  CLEARML_API_ACCESS_KEY="$test_key" CLEARML_API_SECRET_KEY="$test_secret" \
  uv run --project "$repo" --frozen --no-sync python -c "$probe_src" 2>"$scratch_home/probe.err" | tail -1) || {
  echo "probe failed; stderr tail:" >&2; tail -20 "$scratch_home/probe.err" >&2; probe='{}'; }
rm -rf "$scratch_home"
# Optional: run a follow-up command (argument 5) against the same stack, with the endpoints and
# the test key pair in CY_IT_* variables. Its output goes to stderr; its time is reported.
then_s=null then_rc=null
if [[ -n "${5:-}" ]]; then
  t_then=$(date +%s.%N)
  CY_IT_API="http://127.0.0.1:$api_port" CY_IT_FILES="http://127.0.0.1:$files_port" \
    CY_IT_KEY="$test_key" CY_IT_SECRET="$test_secret" bash -c "$5" >&2 && then_rc=0 || then_rc=$?
  then_s=$(python3 -c "print(round($(date +%s.%N)-$t_then,1))")
fi

python3 - "$ns" "$t0" "$t_ready" "$t_auth" "$code" "$probe" "$heap" "$then_s" "$then_rc" <<'PY'
import json, subprocess, sys
from datetime import datetime
ns, t0, t_ready, t_auth, code, probe, heap, then_s, then_rc = sys.argv[1:]
pods = json.loads(subprocess.run(["kubectl","--context","docker-desktop","-n",ns,"get","pods","-o","json"],capture_output=True,text=True,check=True).stdout)
created = datetime.fromisoformat(json.loads(subprocess.run(["kubectl","--context","docker-desktop","get","ns",ns,"-o","json"],capture_output=True,text=True,check=True).stdout)["metadata"]["creationTimestamp"].replace("Z","+00:00"))
ready = {}
for pod in pods["items"]:
    app = pod["metadata"]["labels"]["app"]
    cond = next(c for c in pod["status"]["conditions"] if c["type"] == "Ready")
    ready[app] = {"ready_after_ns_s": round((datetime.fromisoformat(cond["lastTransitionTime"].replace("Z","+00:00")) - created).total_seconds()),
                  "restarts": sum(s["restartCount"] for s in pod["status"]["containerStatuses"])}
quota = json.loads(subprocess.run(["kubectl","--context","docker-desktop","-n",ns,"get","resourcequota","cy-it","-o","json"],capture_output=True,text=True,check=True).stdout)["status"]["used"]
print(json.dumps({"namespace": ns, "es_heap": heap, "all_available_s": round(float(t_ready)-float(t0),1),
                  "first_auth_s": round(float(t_auth)-float(t0),1), "auth_http": code, "pods": ready,
                  "quota_used": quota, "probe": json.loads(probe or "{}"),
                  "follow_up_s": json.loads(then_s), "follow_up_rc": json.loads(then_rc)}, indent=1))
PY
