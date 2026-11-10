# Data Model: Own Kubernetes Test Infrastructure

## Test environment

| Field | Type | Rule |
| --- | --- | --- |
| identifier | string | `clearml-yolo-it-` + 6 lowercase hex; namespace name; ClearML run tag |
| components | set | `{database}` for FiftyOne-only sessions; `{database, redis, elastic, apiserver, fileserver}` otherwise |
| quota | ResourceQuota | applied first; values below |
| limit range | LimitRange | applied first |
| credentials | Secret | generated per environment; never on disk outside the cluster |
| forwards | list | component → loopback port chosen by kubectl, owning process |

State transitions: absent → creating → ready → stopping → absent. Any state → absent when the
sweeper or a restart removes the namespace; the record is then stale and is cleared by the next
`up` or `stop`.

## Quota (values from the 2026-11-10 measurement)

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
detached port-forwards of a manual `up`. No credentials.

A record whose line 1 does not match `^clearml-yolo-it-[0-9a-f]{6}$` (for example `clearml-yolo-claude-20261105-integration-a1b2`,
left by the retired run-tag lifecycle) is not an environment record: it is cleared without any delete
call. Teardown deletes a namespace only when its name matches that pattern and its live labels
include `app.kubernetes.io/part-of=clearml-yolo-tests` (spec FR-018).
