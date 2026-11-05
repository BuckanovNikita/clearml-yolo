# Preserve successful training outcomes

Date: 2026-11-05. Verdict: valid. User approved implementation of the conversational plan.

## Observation and evidence
Report ClassFilter rejects missing training counts; dashboard left joins can yield NA. Pipeline stage exceptions propagate to invocation failure. Exact user workbook unavailable; reproduce with synthetic real workbooks. Never infer training population from evaluation-only data.

## Proposed remediation
Keep unknown counts visible and exclude from eligibility aggregates. Preserve verified training success through downstream failures, with typed stage outcomes, durable atomic local summaries and honest best-effort remote publication. Cancellation and standalone failures stay strict. No digital-metrics modifications or source revision changes.

## Scope and architecture
See architecture.json. Reporting adapters own dataframe/workbook effects, core owns pure policy and outcome models, application owns stage orchestration via ports, tracking/storage adapters own effects. Existing inward dependency and negative architecture tests apply.

## Tasks
- [ ] Implement count classification, report warning worksheets and real workbook regressions.
- [ ] Implement stage outcomes, dependency skips and atomic persistence.
- [ ] Implement tracking/finalization warning semantics and regressions.
- [ ] Reconcile count provenance at producers; prevent test-population counts impersonating training counts.
- [ ] Integrate, run canonical checks, native reproduction and paired queue verification.
- [ ] Update documentation and portable skill; fresh independent review and architecture acceptance.
- [ ] Complete authorized Git-only release after all gates pass.

## Risks
Unknown data must never become fabricated zeros; upstream model publication can fail before training returns. Required native checks and remote publication evidence remain mandatory. Preserve independent workloads and obey pcboard.
