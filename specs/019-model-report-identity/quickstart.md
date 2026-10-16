# Model identity validation

Use the [development checks](../../docs/development.md#verification) and the
[end-to-end skill](../../.agents/skills/running-end-to-end-tests/SKILL.md).

For local inputs without provenance, pass `model_label=experiment-name` to
`cy-predict`, `cy-val`, or `cy-metrics`. In standalone comparison supply
`baseline_model.label=baseline-name` and `candidate_model.label=candidate-name`
alongside each local checkpoint and exact threshold map. These outputs show unavailable
training task provenance. For historical comparison manifests pass
`baseline_label=baseline-name candidate_label=candidate-name` to `cy-report`.
For Unicode or punctuation in a CLI label, preserve Hydra's inner quotes, for
example `cy-metrics 'model_label="experiment-Ω"'` alongside the required inputs.

Train twice with the same requested names. Verify each report uses the finalized
unique readable name and source status; recover one model under a new validation task
and verify the hidden identity/provenance retains the original training task ID rather
than the reporting task ID. Open every worksheet and check repeated readable print
titles without visible IDs or hashes; include long Unicode and formula-like custom
labels. This recipe follows the 2026-10-16 [presentation amendment](../../docs/readable-output.md).

Generate reports from annotated and historical dashboards and compare metrics,
class populations, and exact threshold recovery behavior. Verify missing-baseline
candidate outputs retain identity. Recorded results belong in the dated verification.
