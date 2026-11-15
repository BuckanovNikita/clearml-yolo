# Verification campaign: renewable services — 2026-11-15

Ticket [02: Establish renewable shared services](../../../.scratch/verification-gap-closure/issues/02-establish-renewable-shared-services.md)
uses the existing [environment lifecycle contract](../contracts/test-environment.md).
Source baseline: `bce7df823f85f4c52ad7785ca2800dce691e20c1`, local `master`;
remote references were not fetched. No lifecycle, product, dependency lock, or host SDK
configuration changed. Independent review passed after the corrections below.

## Executed observations

1. `uv run --locked python -m tests.integration.lifecycle check`: **passed**,
   infrastructure available. `task infra-up COMPONENTS=all` created `cy-it-37fa32`;
   services became ready in 34 seconds.
2. A separate lifecycle `Session` adopted the recorded environment with its exact
   `INTEGRATION_RUN_TAG`, then finished. Readback proved the owner environment and
   forwards remained. MongoDB ping and native FiftyOne create/load passed. A persistent
   owned dataset contained one generated image and one labeled detection.
3. An isolated temporary installation of ClearML Agent 4.0.17 serviced only queue
   `verification-gap-closure-cy-it-37fa32`. It pulled task
   `2aa8651b064c406da50f346f8e20104b`, executed it on CPU, and completed it. The remote
   task observed `probe/expected=remote-value` instead of its local default and
   confirmed `running_locally()` was false. Fresh task/artifact readback confirmed
   this payload and its task identity. The bounded operation took 18.64 seconds.
4. A durable local handoff saved the task payload, FiftyOne dataset JSON, image bytes,
   scripts, and redacted Agent log with per-file SHA-256. Consumer validation passed.
   `lifecycle stop --env cy-it-37fa32` stopped its forwards and reported the namespace
   deleted and proven absent. A subsequent namespace query returned no object.
5. `task infra-up COMPONENTS=all` created replacement `cy-it-e3dd8d`, ready in 35
   seconds. Native FiftyOne restored the JSON dataset and read back its sample and
   detection. After validating the durable hashes, a new ClearML task uploaded the
   previous handoff; fresh readback equaled the saved payload. Its new bounded Agent
   run completed task `2f01144dd1864e1fb400d79278ce5868` on queue
   `verification-gap-closure-cy-it-e3dd8d` in 16.58 seconds, again confirming remote
   parameter retrieval and artifact contents. Owner/adopter checks passed again.
6. Both Agent process groups were stopped after readback; process absence was checked.
   Agent-managed temporary output files had already disappeared; retained staging logs were redacted in place. No GPU
   training or compilation ran. Processes used nice 19 and two CPU library threads.

All six observations **passed**. The first probe setup attempt used an unavailable
SDK convenience method (`Task.get_queue_id`) and exited before starting an Agent;
using the installed SDK's queue API resolved that probe error. Its unused task was
removed with the first owned namespace. Agent logs reported an unsupported optional
`workers.get_runtime_properties` endpoint, while scheduling and readback succeeded.
No upstream code or server was changed to suppress that warning.

These are real local services, Agent scheduling, remote SDK configuration, dataset
restoration, and artifact readback. They do not establish CY application replay
(ticket 86), CY publication completeness (88/89), remote-host execution, embedded UI,
or model/GPU outcomes. The Agent used an explicit preinstalled project interpreter
and a local probe script; environment reconstruction and remote Git cloning were not
tested. The 48-hour expiry remains unchanged: early replacement demonstrates renewal,
not survival past the expiry.

## Continuing ownership and recovery

The campaign coordinator, session `codex:01a1e0ab-e153-7ff1-8329-85585fccf79f`, owns
the replacement environment and its lifecycle forwards. The secret-free local record
is `runs/verification-gap-closure/service-owner.json`; authoritative connection and
process ownership remain in `tests/integration/.run-tag`. Consumers acquire fresh
`lifecycle env` exports in memory only after checking successful exit. Never reuse
old credentials or endpoints, and never print or persist credential exports.

Both durable bundles live under `runs/verification-gap-closure/service-handoffs/`,
keyed by environment identifier. Their `sha256.json` files validate every retained
member before restoration. They contain no SDK credentials. Probe scripts and the
small isolated Agent installation remain available for later Agent tickets; their
existence does not mean an Agent is running. Agent processes are bounded to 300 seconds
with owned-group termination and bounded reap in `finally`.

Before each live consumer, check the recorded environment and forward liveness. Before
48 hours from creation (or after a restart/lost environment), save and verify durable
outputs, stop the exact owned environment through the lifecycle, prove absence,
create a replacement, acquire fresh exports, and restore required payloads. Record
its new identity in the owner handoff. Preserve failure evidence before teardown.
Do not rewrite a live record to bypass another owner's refusal.

Ticket 02 may close after review; ownership continues. Ticket 93 owns final environment
teardown and deletion proof. After each consumer, remove only its disposable caches,
staging and temporary logs once processes exit and required evidence/checkpoints are
retained. Keep shared fixtures and downstream handoffs until their consumers finish.
No user SDK settings, source data, shared caches, or unrelated services were removed.

## Review corrections

Independent review caught that the first FiftyOne restoration retained a staging media path. The correction validated the original durable bundle hashes, removed the owned staging JSON and image, restored a new native dataset from the durable JSON with its filepath explicitly rebound to the durable image, and independently loaded the sample, checked its image SHA-256, and decoded its 32×32 pixels. The old owned probe dataset was removed after this passed. The corrected dataset is `verification-gap-closure-renewal-durable`; its receipt and reproducible script are checksummed under `runs/verification-gap-closure/service-handoffs/renewal-correction/`. The original bundles remain immutable historical observations. Raw staging Agent logs were redacted in place to remove access-key diagnostic lines; durable logs were already redacted. No active credential values are retained in either log set. Fresh independent follow-up found both blockers resolved; ticket02 accepted.
