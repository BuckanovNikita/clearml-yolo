# Data Model: Own Kubernetes Test Infrastructure

## Test environment

| Field | Type | Rule |
| --- | --- | --- |
| identifier | string | `cy-it-` + 6 lowercase hex; namespace name; ClearML run tag |
| components | set | `{database}` for FiftyOne-only sessions; `{database, redis, elastic, apiserver, fileserver}` otherwise |
| quota | ResourceQuota | applied first; values below |
| limit range | LimitRange | applied first |
| credentials | Secret | generated per environment; never on disk outside the cluster |
| forwards | list | component → loopback port chosen by kubectl, owning process |

State transitions: absent → creating → ready → stopping → absent. Any state → absent when the
sweeper or a restart removes the namespace; the record is then stale and is cleared, without
any delete call, by the next `up`, `agent_env.sh`, session setup or `stop`.

Ownership: the process that creates an environment owns its deletion. A pytest session that
created it deletes it at the end (unless `INTEGRATION_KEEP_DATA=1`); one created by `up` or
`agent_env.sh` is deleted by `stop` or `agent_cleanup.sh`. A session that adopts a live recorded
environment (exported `INTEGRATION_RUN_TAG` equal to the record) neither creates nor deletes
it. Selection rule: contract "Environment selection" (spec FR-014).

## Quota (designed from the use measured on 2026-11-10)

The hard values were derived from the measured use with headroom; they were not themselves
applied in the measurement runs, which used a looser quota (requests 2 CPU / 4Gi, limits
8 CPU / 8Gi; `evidence/measure/stack.yaml`). The live acceptance run (tasks T027) is the first
application of these values and records that every pod was admitted.

| Resource | Hard | Measured use (all components) |
| --- | --- | --- |
| pods | 8 | 5 |
| requests.cpu | 1 | 550m |
| requests.memory | 2Gi | 1184Mi |
| limits.cpu | 8 | 6500m |
| limits.memory | 6Gi | 3840Mi |
| persistentvolumeclaims | 0 | 0 |
| requests.nvidia.com/gpu | 0 | 0 |

## Components

| Component | Image | Requests | Limits | Ready after namespace (cached images) |
| --- | --- | --- | --- | --- |
| database (MongoDB) | `mongo:7.0.22` | 100m / 256Mi | 1 / 1Gi | 3-4 s |
| redis | `redis:7.2.11-alpine` | 50m / 32Mi | 500m / 256Mi | 3-4 s |
| elastic | `elasticsearch:7.17.28`, heap 256m | 250m / 512Mi | 2 / 1Gi | 11-12 s |
| apiserver | `allegroai/clearml:2.0.0-613` | 100m / 256Mi | 2 / 1Gi | 20 s (ordered) |
| fileserver | `allegroai/clearml:2.0.0-613` | 50m / 128Mi | 1 / 512Mi | 23 s (ordered) |

## Environment record (`tests/integration/.run-tag`)

Line 1: identifier. Then zero or more `forward <component> <port> <pid> <start-time>` lines for
detached port-forwards of a manual `up` (also through `agent_env.sh`). No credentials. Written
by whoever creates the environment; an adopting session reads it and writes nothing.

| Record state | Meaning |
| --- | --- |
| none | no environment in this worktree |
| retired format | line 1 is not an identifier; cleared without a delete call |
| stale | line 1 is an identifier whose namespace is absent; cleared without a delete call |
| live | line 1 is an identifier whose namespace exists with the project label |
| foreign | line 1 is an identifier whose namespace exists without the project label; refused, kept |

A record whose line 1 does not match `^cy-it-[0-9a-f]{6}$` (for example `clearml-yolo-claude-20261105-integration-a1b2`,
left by the retired run-tag lifecycle) is not an environment record: it is cleared without any delete
call. Teardown deletes a namespace only when its name matches that pattern and its live labels
include `app.kubernetes.io/part-of=clearml-yolo-tests` (spec FR-018).
