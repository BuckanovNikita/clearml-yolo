# Bug Assessment: Silent queue worker

- **Slug**: queue-default-logs (generated from the report)
- **Created**: 2026-10-15
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: medium — operators cannot distinguish idle, waiting and running workers.

## Report

> Make cy-queue more verbose by defult now no logs at all. Land chnages on master and release

## Symptom and reproduction

Run `cy-queue --root QUEUE_ROOT worker` with an isolated empty queue, wait for
`worker.json`, then send SIGTERM. The current CLI and worker loop emit no startup,
idle or shutdown diagnostics. QueueProcesses redirects guardian output to DEVNULL;
the guardian separately retains pipeline output in the submitting project's
`.cy/queue-logs/JOB_ID.log`. Confirm the silent CLI with a regression test before fixing.

## Root cause and inspected paths

High confidence: `entrypoints/queue.py` installs signal handlers but never configures
or emits worker diagnostics; `application/queue.py` only ticks and sleeps.
`adapters/queue/runtime.py` and `guardian.py` own process effects and retained child logs.

## Proposed remediation and architecture

Keep scheduling unchanged. Add an optional typed QueueView observer to the worker
loop, invoked after registration and ticks. The CLI owns Loguru rendering, INFO
stderr by default, worker `--log-level DEBUG|INFO|WARNING|ERROR`, startup identity/root,
changed own-job state/allocation/wait/progress/error, a 60-second status heartbeat,
and clean shutdown. DEBUG adds poll summaries. Deduplicate unchanged jobs and omit
private snapshots/configuration. Preserve stdout IDs/JSON and the optional TUI.
The observer is supplied explicitly; application/core must not import Loguru or
concrete adapters. Reuse import-linter and architecture negative-edge tests.
See [architecture record](architecture.json).

## Task contract and ledger

Python >=3.12,<3.13; existing uv/Hatch package and dependencies remain unchanged.
Use the existing prepared environment without dependency resolution. The main
checkout has unrelated staged compatibility changes: preserve it and integrate
from an isolated checkout. Authorized endpoint: verified master commit and Git tag
push through the native release helper, no GitHub Release or package publication.

- [x] Inspect code, contracts, hooks, current work and portable usage skill.
- [ ] Reproduce silent worker and add behavioral regression coverage.
- [ ] Validate architecture plan; implement CLI diagnostics and observer.
- [ ] Verify focused queue behavior, import rules, static checks and commit gates.
- [ ] Update docs/queue.md and README queue guidance; inspect diagnostics/current
  contracts and preserve existing specs as dated history. Update canonical
  corp-skills usage/evaluation references with independent documentation ownership.
- [ ] Validate Markdown, links, help examples and portable skill package.
- [ ] Fresh independent final Python/architecture review after parent checks.
- [ ] Reconcile diff, accept architecture, commit, land master and release.

## Risks and scope

Repeated poll logs must stay DEBUG; job notifications exclude timestamp-only changes.
Only this owner's jobs are rendered. Worker exceptions remain failures; do not
claim successful shutdown after a failed tick. Child output remains in its existing
file rather than changing guardian lifetime or buffering. No scheduler, GPU policy,
ClearML, dependency or persisted-format changes. No material open questions.
