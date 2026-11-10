# Live acceptance of the own test environment, 2026-11-10

All runs on 2026-11-10 (Moscow time) in the worktree of branch `feat/own-test-infra`, context
`docker-desktop`, with `kubectl` from the user's kubeconfig. The shared stands had already
been wiped; the cluster held only the platform namespaces and the owner's dedicated `clearml`
and `mongodb`, which no run contacted. The storage class was `hostpath` only. Code under test:
`d09e60b` (lifecycle with the killed-session port-forward fix) unless a row says otherwise.

Run conditions, because the user was gaming on the machine: every heavy command ran under
`nice -n19` with `OMP_NUM_THREADS=4` and `CUDA_VISIBLE_DEVICES=""` (the CPU smoke test needs no
GPU), one environment at a time. The CPU smoke run's `cy` pipeline prepares the whole model
catalogue in its temporary `CY_HOME` (docs/model-assets.md "Catalogue and automatic
execution"); GitHub release downloads ran at about 1.7 MB/s and twice stalled without end, so
the smoke runs below set `CY_WEIGHTS_DOWNLOAD_TIMEOUT` (20 s, later 3 s). Automatic preparation
failures warn and continue by design; the selected model is the local `yolo11n.pt`. Two
earlier smoke runs in an adopted environment were stopped by hand during such a stall; they
are not counted as results.

## Environment start, quota and endpoints (T027 quota part, SC-004, SC-005)

`lifecycle check` exit 0; `lifecycle up --components all` created `cy-it-0369fd`, all five
components ready **24 s** after the namespace (cold start with cached images; `up` took 26.1 s
end to end). Later `up` runs: 22 s, 22 s, 21 s, 22 s, 21 s. The informational image line named
only `redis:7.2.11-alpine`, which the node's capped list omits although the start pulled
nothing.

First application of the designed quota (data-model.md), read while `cy-it-0369fd` existed:

| Resource | Hard | Used |
| --- | --- | --- |
| pods | 8 | 5 |
| requests.cpu | 1 | 550m |
| requests.memory | 2Gi | 1184Mi |
| limits.cpu | 8 | 6500m |
| limits.memory | 6Gi | 3840Mi |
| persistentvolumeclaims | 0 | 0 |
| requests.nvidia.com/gpu | 0 | 0 |

Every pod was admitted (5/5 Running, 0 restarts); `limitrange/cy-it` present; no
PersistentVolumeClaim. Namespace labels: `app.kubernetes.io/part-of=clearml-yolo-tests`,
`clearml-yolo/environment=cy-it-0369fd`. `eval "$(lifecycle env)"` exported loopback
`CLEARML_API_HOST`, `CLEARML_FILES_HOST`, `FIFTYONE_DATABASE_URI` and `INTEGRATION_RUN_TAG`;
`check_env.sh` reported ClearML authenticated with endpoint and credentials from the
environment, kubectl reachable, no Docker line. T004's server-side dry run is superseded by
these real applications of the same manifests.

## Results

| Task | Case | Result |
| --- | --- | --- |
| T029 | `up`, namespace deleted out of band, `stop`, `up`, `stop` | `stop` exit 0 "already gone", record cleared, the three recorded port-forwards stopped (they had outlived the namespace); next `up` created `cy-it-83b643` |
| T029b (1) | adopted environment `cy-it-83b643`, `CLEARML_API_HOST=http://127.0.0.1:9` exported after `env`; CPU smoke test normally, then with `INTEGRATION_KEEP_DATA=1` | **1 passed** (626 s) and **1 passed** (499 s); both logged "adopted environment cy-it-83b643 ... this session deletes nothing"; namespace and record present after each |
| T029b (2) | same environment, `INTEGRATION_RUN_TAG` unset, then `cy-it-000000` | setup error, pytest exit 1, message names the environment and `stop`; labelled namespace list unchanged |
| T029b (4) | recorded API-server port-forward killed | setup error, exit 1: "no running port-forward to apiserver; nothing was created or deleted", names `stop` and `up`; then `stop` deleted it and proved it absent |
| T029c (1) | `up`, `env`, namespace deleted out of band, `up` with the old identifier exported and recorded | stale record cleared "nothing was deleted", new `cy-it-5fd79d`, `env` exported it; old forwards gone; `stop` exit 0 |
| T029b (3) | `up`, `env`, namespace deleted out of band, smoke test | "INTEGRATION_RUN_TAG=cy-it-263089 names no live recorded environment; this session creates its own", created `cy-it-2630d7`, **1 passed** (178 s), "namespace cy-it-2630d7 deleted and proven absent"; no namespace, record or forward left |
| T029a | `agent_cleanup.sh --tag clearml --dry-run`, `agent_cleanup.sh --tag clearml`, `stop --env default` | each exit 1, "not an environment identifier; nothing was stopped or deleted"; `kubectl get ns` identical before and after (8 namespaces) |
| T029a | retired record `clearml-yolo-claude-20261105-integration-a1b2`: `stop --dry-run`, `stop` | exit 0 both; dry run reports it would be cleared, `stop` cleared it "nothing was deleted"; namespace list unchanged |
| T029a/T029c (2) | unlabelled `cy-it-7d0acf`: `stop --env`, then as the record `up` and `stop` | each exit 1, "exists without the label ... nothing was deleted and the record is kept"; namespace and record kept; then deleted by hand |
| setup failure | `CY_TEST_ENV_START_TIMEOUT=1 lifecycle up` | exit 3 "not ready within 1 s (mongo: Running, elastic: Running, apiserver: Pending, fileserver: Pending)"; `cy-it-c3c011` deleted and proven absent before the report; no record |
| interrupt | `timeout -s INT 12 lifecycle up`; `timeout -s TERM 12 lifecycle up` | "interrupted" (SIGINT); both deleted their namespace (`cy-it-23caf7`, `cy-it-eae150`) and proved it absent; no record or forward left |
| interrupt | `timeout -s INT 60 pytest test_cpu_stand_smoke.py` (session-created environment) | KeyboardInterrupt; teardown deleted `cy-it-6b8244` and proved it absent; no record or forward |
| US4 (5) | session killed with SIGKILL while its test ran | T029 showed that a `kubectl port-forward` outlives its namespace, so a killed session's unrecorded forwards would have stayed (fixed in `d09e60b`); with the fix: namespace `cy-it-792458`, record and two forwards left; `stop --dry-run` "2 port-forward(s) would be stopped"; `stop` stopped both ("left by an ended session"), deleted the namespace and proved it absent; no forward left |
| T028 | FiftyOne step by hand: `CY_TEST_FIFTYONE=1 CY_TASK_VERIFICATION=1 FIFTYONE_DATABASE_DIR=<mktemp> pytest tests/integration/fiftyone -p no:randomly -n 0` | **29 passed** in 44 s; "database components ready in 2 s" (no ClearML component); `cy-it-c2cde7` deleted and proven absent; the lock directory held only `clearml-yolo-locks` and was removed |
| T030/T030a | `env -i HOME PATH` shell, dummy `FIFTYONE_DATABASE_URI`/`NAME` exported, `FIFTYONE_DATABASE_DIR` unset; `source agent_env.sh some-slug` | one notice line for the slug; `cy-it-c531ee` created; `CY_RUN_DIR=/tmp/clearml-yolo-runs/cy-it-c531ee`; URI names the environment's forward, NAME unset, DIR `$HOME/.cache/clearml-yolo/fiftyone`; `check_env.sh` all OK with no Docker line |
| T030a | source again | return 1 naming `agent_cleanup.sh`; namespace list unchanged; URI and NAME unset |
| T030a | smoke test in that shell | adopted `cy-it-c531ee`, **1 passed** (137 s), namespace and record left |
| T030a | namespace deleted out of band, source again | stale record cleared, new `cy-it-f32934` |
| T030 | `agent_cleanup.sh --dry-run`, then `agent_cleanup.sh` | dry run: 3 forwards and the namespace "would", directory "would remove"; real: namespace deleted and proven absent, run directory removed; no forward or record left. The first run's directory (`cy-it-c531ee`, whose environment had been swept) is not this run's and was left, as designed; removed by hand |
| US3 (2), FR-010 | `CY_INFRA_CHECK_TIMEOUT=0.001`: `lifecycle check`; `source agent_env.sh` | exit 3 and return 3 "cluster is unavailable; nothing was left behind"; no namespace or record; database variables and `CY_RUN_TAG` unset |
| T031a | `pytest test_severstal_gpu.py --run-severstal-gpu`; `pytest test_native_ddp_gpu.py --run-ddp-gpu --ddp-devices=x`, both without options or GPU | 63 and 18 setup errors in under 1 s: "Native Severstal selection requires --severstal-dataset ...", "Physical DDP selection requires --ddp-clearml-project --ddp-artifacts"; no `cy-it-` namespace created. `git diff 012-editable-batch-sizes -- src` empty |
| T031 | paired check | passed; see [2026-11-10-paired-check.md](2026-11-10-paired-check.md) |

After every case: no `cy-it-` namespace other than the one under test, and none at the end.

## Not run or deferred

- GPU suites (Severstal single-GPU, multi-GPU DDP) and the real-run gate: **deferred** (the
  user was gaming; out of scope for this feature's change). Only their option validation ran.
- `release-acceptance` as a whole: not run (it includes the GPU suites); its FiftyOne step
  ran by hand (T028) and its paired check ran (T031).
- T032 independent review: **not done** by this implementing session (it may not start
  sub-agents); required before integration.
