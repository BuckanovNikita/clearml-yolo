# Acceptance boundaries

The [product specification](../specs/000-baseline/spec.md) and linked capability
specifications define desired outcomes. They do not report implementation progress.

Acceptance must distinguish local checks from native and remote outcomes. Scientific
results require appropriate reference comparisons; cached assets require byte and
identity verification; publication requires remote readback; Agent execution requires
actual scheduler execution. GPU, distributed and multi-host/NFS claims require the
intended physical topology. Simulated telemetry does not establish physical admission.

Use the [current contract index](current-contracts.md) to select the relevant behavior
and [development guidance](development.md) for execution procedures. Record new check
results with their source, environment, workload and limitations. No release, task
checkbox or past waiver substitutes for a required outcome.
