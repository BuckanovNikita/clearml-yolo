# Owned service recovery — 2026-11-16

The campaign's owned ClearML/FiftyOne environment was recovered after WSL restart.
Native teardown proved `cy-it-adb183` absent; native creation produced
`cy-it-ded7c4`. A durable probe was restored and independently read back, then the
coordinator reviewed the evidence and updated the current service owner.
This maintenance does not accept another campaign ticket or establish a GPU outcome.

The evidence was prepared at `a4a9ef46955cc6c85aa937200f87ed6d9f842fb7` in the
managed detached worktree, aligned with local `master`; remote references were not
fetched. Exact local source paths and SHA-256 values are in the
[companion receipt](2026-11-16-service-recovery.json).

## Preservation and supported lifecycle

Before teardown, current SHA-256 checks passed for four queue baseline execution
inputs, twenty baseline readback files, the initial weight asset, ten accepted native
case handoffs covering 965 files, thirty ticket88 retained files, twenty-four historical
service bundle files, and nine queue-v2 artifact/checkpoint files. The old owner and
lifecycle record were copied into the recovery evidence directory. Historical bundles
and accepted consumer receipts remain unchanged.

The supported lifecycle dry run passed the namespace ownership guard. Native `stop`
then exited zero and proved the old namespace absent. Native `up --components all
--identifier-only` exited zero; components became ready in 24 seconds. No forward or
lifecycle record was patched manually. Credentials remained in process memory.

The new namespace UID is `4febab82-ebc6-41cc-b11b-a4364ffccc33`. Kubernetes records
creation at **2026-11-16T19:46:56Z**; renew by **2026-11-18T19:46:56Z**, or earlier
if platform restart retires it. Both probe phases observed WSL boot
`5e9f68d1-63db-4188-9995-e686745fda8c`.

## Live proof and cleanup

A new helper, copied from the historical renewal helper, verified the four prior
bundles and restored the one-sample persistent FiftyOne dataset
`cy-it-ded7c4-verification-gap-closure-renewal-durable`. ClearML task
`1a03f52d847b4da29b56e28f78bae98a` completed with three provenance artifacts.

A separate process and fresh SDK cache reloaded the dataset, checked the exact label
and bounding box, decoded its hash-bound 32×32 media, verified the completed tagged
ClearML task, and forced all three artifact downloads with matching hashes. Both
bounded CPU phases exited zero. No GPU work ran.

The helper's two phases completed, and a same-UID process environment scan found no
process using its cache root. Three disposable cache files totaling 3,655 logical bytes
were removed after readback. The durable sample, datasets, task, bundle and lifecycle
forwards were intentionally retained. The coordinator independently rehashed all
thirty historical/new bundle files, reviewed the helper diff, resolved the live native
environment, checked namespace identity/deadline, and updated `service-owner.json`.
Exact snapshots of the new owner and lifecycle record are retained with the recovery
evidence so later renewals can update operational pointers without changing this proof.

## Applicability and remaining work

This is a durable probe restoration, not a database restore. Old published task/model
IDs remain historical; new API readback of deleted tasks is unavailable. The pending
queue scientific comparison reads its old baseline from validated local files and
queries only its future queued run online. The queue-v2 scientific mismatch remains
unresolved even though its historical publication readback passed. Future export
qualification depends on pending producer/checkpoint handoffs, not old remote task IDs.

Queue preparation must bind new project/tags and refresh commands, generated scientific
configuration/snapshots, manifests and boot observations, while preserving old evidence,
SDK/OpenCV identity, scientific baseline and durable coordination storage. Fresh CPU
preparation, independent review and GPU admission remain required. Future backend
preparations resolve the new lifecycle/current-owner binding; accepted historical
handoffs retain their original environment identities.

Native documentation consistency was reviewed against the lifecycle contract and the
bound receipts: **passed**. Owned service recovery and remote probe readback: **passed**.
GPU execution and full campaign acceptance: **deferred**, outside this recovery proof.
No release, deployment, physical multi-GPU or numerical parity outcome is claimed.
