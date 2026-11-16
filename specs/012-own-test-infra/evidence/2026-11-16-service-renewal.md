# Service renewal handoff — 2026-11-16

The coordinator replaced owned environment `cy-it-e3dd8d` with `cy-it-adb183` after the WSL
interruption. The coordinator reports lifecycle deletion proof for the former and readiness of all
replacement services in 28 seconds. This handoff adopted the replacement through
`lifecycle.recorded_environment` and its in-memory exports; it created or deleted no environment.
`tests/integration/.run-tag` remained authoritative. The coordinator retains environment ownership.

## Executed observations

The worktree was local `master` at `/mnt/wsl/data/nkt/clearml-yolo`; local `HEAD` and `master`
matched, and remote references were not fetched. Existing product changes were preserved. The
machine was away/locked with about 40.9 GiB RAM free. Both renewal processes were constrained to
two CPU cores and two numerical threads at nice 19; neither launched GPU work or an Agent.

| Selected check | Outcome | Evidence |
| --- | --- | --- |
| Historical bundle integrity before restoration | passed | All eight manifest entries in each of `cy-it-37fa32` and `cy-it-e3dd8d`, plus both entries in `renewal-correction`, matched SHA-256 |
| Native FiftyOne restoration | passed | Persistent dataset `cy-it-adb183-verification-gap-closure-renewal-durable` restored from saved JSON |
| Independent native FiftyOne readback | passed | Separate process loaded one persistent sample, verified `owned-probe` and box `[0.1, 0.2, 0.3, 0.4]`, hashed and decoded its 32×32 PNG |
| ClearML publication | passed | New completed task `d52636e263434b7db932a5d9f67df9e2`, explicitly tagged/projected under `cy-it-adb183`, uploaded three saved handoff artifacts |
| Independent forced remote artifact readback | passed | Separate process fetched the task, required replacement fileserver URLs, used `get_local_copy(force_download=True, raise_on_error=True)` into a fresh owned cache, and verified all three SHA-256 values |
| Historical bundle integrity after cleanup | passed | All original manifest entries still matched; neither historical bundle nor correction receipt was rewritten |
| Task-owned cleanup | passed | Both Python processes exited zero; four disposable configuration/cache files totaling 2,107 bytes were removed |

The restored media path is the actual immutable file
`runs/verification-gap-closure/service-handoffs/cy-it-37fa32/sample.png`, not the obsolete temporary
path embedded in old JSON. Its SHA-256 is
`28b2bf7909c230f4c8217fe71682120e8e54a5398a3de5b45e043f92fbd69be2`.
The previous durable-correction receipt determined this binding. No historical restoration script
was rerun. The new exported JSON also retains this durable media binding.

| Uploaded artifact | Forced-download SHA-256 |
| --- | --- |
| `previous-service-handoff` | `46c316969ae3920bb5dc0cc24baf1b55aa7995590fd2e83246f9463434d0d4e6` |
| `durable-media-correction` | `45b67070d7363cde0e840b6ac84a530a22192db7d5c4a9581e635b8e1a17df5a` |
| `restored-fiftyone` | `8eb6480a292bc32cc44a2fbc5df10e77768e9fe7a265f7c6ded2997fa53e31ed` |

## Durable handoff and limits

The new bundle is `runs/verification-gap-closure/service-handoffs/cy-it-adb183/`.
It retains `renew.py`, separate `restore.log`/`readback.log`, `fiftyone-restored.json`, `receipt.json`,
`cleanup.json`, and a SHA-256 manifest covering the six payload files. Commands were separate
invocations of `.venv/bin/python <bundle>/renew.py restore` and `readback`, under the CPU limits above.
Lifecycle exports and credentials existed only in process memory; SDK configuration was isolated
in `.tmp/service-renewal-cy-it-adb183`, which was removed after readback. User caches/settings,
shared FiftyOne lock directory, retained database, fixture/model assets and other agents' resources
were preserved. Disk had about 697 GiB free before these small operations.

The secret-free `runs/verification-gap-closure/service-owner.json` now identifies the replacement,
the current bundle and successful readback time `2026-11-16T06:34:07.855310+00:00`; it retains the
48-hour renewal limit. The coordinator checked the namespace creation timestamp
`2026-11-16T06:29:11Z` and corrected the owner deadline to before
`2026-11-18T06:29:11+00:00`; readback time is not the start of that limit. The root owner
remains responsible for lifecycle teardown and final campaign cleanup under ticket 93.

These are fresh live database/publication/readback observations, not mocked outcomes. They do not
repeat Agent scheduling already established by tickets 02/86, establish GPU execution, or restore
every historical service object. The old service task/queue identifiers inside the uploaded handoff
are historical provenance; the new publication task above is the live replacement identifier.
No product code, dependency, upstream pin, user configuration, commit or staging action changed.
