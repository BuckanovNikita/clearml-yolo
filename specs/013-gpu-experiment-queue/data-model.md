# Data model: GPU experiment queue

This describes the implemented version-1 JSON schema and its process ownership boundary.

## Registry and requests

`GPUQueue` atomically replaces `registry.json` under a short native registry lock. Concurrent
writers wait for the transaction lock; execution and capacity waiting occur outside it.

| Registry field | Type | Constraint |
|---|---|---|
| `schema_version` | integer | Exactly `1`; other layouts fail closed |
| `next_ticket` | integer | Positive, greater than every request ticket, never reused |
| `requests` | list of requests | Strict ascending ticket order |

Each request has exactly these fields:

| Request field | Type | Constraint |
|---|---|---|
| `ticket` | integer | Positive and unique |
| `count` | integer | Positive initial demand; no larger than visible set |
| `visible` | ordered UUID list | Nonempty unique physical-device identities |
| `devices` | ordered UUID list | Empty while pending; active size is between one and `count` |
| `state` | string | `pending` or `active` |

Active UUIDs must belong to that request's visible set and must be disjoint across requests.
Contraction changes `devices` to its first UUID while preserving initial `count`. Command
configuration, environment values, credentials and PID identities are not persisted in the registry.
Zero-demand jobs bypass registry insertion.

```text
pending -> active -> active with one retained UUID -> removed
   |          |                    |
   +----------+--------------------+-> removed after ownership ends
```

Only FIFO heads with complete available capacity become active. Active publication precedes child
startup; a missing or unadmitted request prevents the child from claiming ownership.

## Native ownership locks

`supervisor-<ticket>.lock` and `worker-<ticket>.lock` names derive from the ticket. The supervisor
acquires its native lock before publishing the request; the child claims its lock under the same
registry transaction boundary. Both files remain stable so their lock identities cannot be replaced
by unlink/recreate races. A request is stale only when neither native lock is held. No PID, heartbeat
or elapsed-time observation can authorize reclamation.

Process-tree ownership uses an isolated POSIX process group or a Windows kill-on-close Job Object.
A private startup gate prevents the worker from importing its target before ownership is established.
Terminal cleanup attempts every job independently and preserves claims if termination is unconfirmed.

## Inventory and demand

`GPUDevice` is an ephemeral immutable pair of physical `uuid` and `busy` boolean. NVML compute users
produce `busy`; incomplete telemetry raises instead of guessing. `GPUInventory.snapshot()` returns
whole-device records, and `visible()` maps the inherited CUDA visibility to ordered UUIDs through a
bounded disposable metadata probe. MIG instances are rejected.

`device_count()` returns training demand. GPU inference caps its demand at one. `job_request()`
returns the maximum of enabled training and inference demand for a pipeline, so it never reacquires
capacity midway. Requested native values remain in invocation configuration and requested YAML.

## Effective assignment

The worker's `CUDA_VISIBLE_DEVICES` contains assigned UUIDs in reservation order. Native training
uses local indices `[0, ..., N-1]`; GPU inference uses `[0]`. CPU/MPS selectors remain unchanged.
Requested selectors, effective selectors and reserved UUIDs are distinct fields in the canonical
ClearML run configuration. Requested YAML retains the original selector; effective native YAML
records actual execution. A replay requiring more GPUs than the reservation fails before model
execution.
