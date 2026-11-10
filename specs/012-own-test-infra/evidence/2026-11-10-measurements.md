# Measurements, 2026-11-10

Throwaway namespaces `cy-it-m1` to `cy-it-m8` on context `docker-desktop` (Docker Desktop
Kubernetes, one node, 32 CPUs, 62 GB), created from [measure/stack.yaml](measure/stack.yaml)
by [measure/measure.sh](measure/measure.sh) (its embedded SDK probe included), each with
a `ResourceQuota` and a `LimitRange` applied with the namespace. All were deleted afterwards;
`kubectl get ns` listed no `cy-it-` namespace at the end, and no port-forward remained. The
manifest and driver are measurement tools, not the implementation. During the runs the SDK probe was
a separate `probe.py`; for the commit it is embedded verbatim in `measure.sh` (repository
linters apply to tracked `.py` files) and the embedded form was only syntax-checked
(`bash -n`), not re-run. Likewise `stack.yaml` was a multi-document file during the runs and is
committed as one equivalent `kind: List` document (the repository's `check-yaml` hook accepts
one document per file); the List form was checked with `kubectl apply --dry-run=client` only. Source tip measured:
`f1a3755`.

All images were already present on the node (`Pulled ... already present on machine`):
`allegroai/clearml:2.0.0-613` (1.46 GB), `docker.elastic.co/elasticsearch/elasticsearch:7.17.28`
(1.02 GB), `mongo:7.0.22` (1.13 GB), `redis:7.2.11-alpine` (60 MB). Cold start with image pulls
was **not** measured; it would add the pull of about 3.7 GB.

## Runs

| Run | Change | All Available (s) | First authenticated call (s) | Probe | Notes |
| --- | --- | --- | --- | --- | --- |
| m1 | first manifest, fileserver with its own key pair | not reached in 600 s | - | - | file server exits 401: the API server does not know a separate file-server pair; fixed by giving the file server the system pair |
| m2 | file server uses the system pair; ES heap 512 MiB | 47.7 | 48.2 | pass | API server ready at 39 s, file server restarted twice before the API server answered |
| m2 | FiftyOne suite on the same MongoDB (`FIFTYONE_DATABASE_URI` via port-forward) | - | - | 29 passed in 36 s | databases afterwards: `admin auth backend config fiftyone local`; `FIFTYONE_DATABASE_DIR` held only `clearml-yolo-locks` |
| m3 | ES heap 256 MiB, request 512 MiB, limit 1 GiB | 47.3 | 47.8 | pass | API server log: Elasticsearch refused at start, "Retry 1 of 4. Waiting for 30sec" |
| m4 | init containers: API server waits for ES, file server for API server | 23.7 | 24.1 | pass | no restarts |
| m5 | as m4, then the real CPU stand smoke test | 44.5 | 44.9 | pass | `tests/integration/test_cpu_stand_smoke.py`: **1 passed in 362.6 s**; init wait took 30 s because `curl` without `-m` hung on the Service before ES had endpoints |
| m6 | `curl -m 2` in the waits; termination grace 2 s | 23.2 | 23.6 | pass | delete namespace 11.2 s |
| m7 | as m6 | 24.6 | 25.1 | pass | delete namespace 11.3 s |
| m8 | MongoDB only (FiftyOne-only session) | 2.6 | - | - | FiftyOne suite **29 passed in 37.5 s**; delete 10.6 s |

The m5 smoke run used a throwaway stand-in for the retired helpers, outside the repository
(`K8S_INFRA_SKILL_DIR` pointing at two stub scripts that printed the measurement endpoints and
did nothing else), so that the unchanged `lifecycle.py` could drive the unchanged smoke test.
That stand-in was deleted; it is not part of the design. The probe's
`model_url_is_fileserver` field was false in every run; it compares URL strings that the SDK
normalises differently and is inconclusive. The model upload itself is shown by
`output_models: 1` and by the smoke test's own Output Model assertion.

Namespace deletion with default 30 s grace periods took 42.9-43.0 s (m2, m3, m5); with a 2 s
grace period 10.6-11.3 s (m6, m7, m8).

## Resource use

Quota used with all components (identical in m4-m7): pods 5, requests.cpu 550m,
requests.memory 1184Mi, limits.cpu 6500m, limits.memory 3840Mi, PVC 0, GPU 0.
MongoDB only: pods 1, requests 100m / 256Mi, limits 1 / 1Gi.

Peak memory (`memory.peak` of each pod's cgroup) after the CPU smoke test (m5):

| Component | Peak | Limit |
| --- | --- | --- |
| apiserver | 105 MiB | 1 GiB |
| elastic (heap 256 MiB) | 634 MiB | 1 GiB |
| fileserver | 61 MiB | 512 MiB |
| mongo | 246 MiB | 1 GiB |
| redis | 12 MiB | 256 MiB |

After the probe only (m2, heap 512 MiB): elastic 890 MiB, mongo 232 MiB peak.

## What this establishes

- The minimal component set (MongoDB, Redis, Elasticsearch, API server, file server; no web UI,
  async-delete or agent) is enough for the SDK writes the probe makes and for the real CPU
  stand smoke test.
- The server's built-in `tests` credential (`CLEARML__SECURE__CREDENTIALS__TESTS__*`) works as
  the SDK user; the file server must use the API server's system pair.
- The FiftyOne suite passes unchanged against a MongoDB in the namespace, alone or shared with
  ClearML.
- `emptyDir` only, no claim, no GPU request; the quota and limit range admitted every pod.

## Not established

- Cold start with uncached images; behaviour under node memory pressure; the GPU suites and
  the release-acceptance stage against the environment (GPU work is out of scope here).
- Long sessions near the 48-hour sweep; port-forward stability across pod restarts.
