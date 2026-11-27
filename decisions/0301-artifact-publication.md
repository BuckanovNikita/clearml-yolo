# ADR-0301 · Track required ClearML artifacts through finalization

An experiment can finish its computation while a required table or file is still missing remotely.

**Decision.** Stages declare required artifacts or register them on upload. The owner checks local paths, requests synchronous SDK upload, requires an affirmative acknowledgement, and checks outstanding manifest entries and the task flush. For a published table, identical bytes can satisfy aliases and distinct contents under one name receive disambiguating suffixes.

**Consequences.** A rejected upload or an unfulfilled declaration blocks normal completion. A [trained pipeline](0002-pipeline-outcome.md) can preserve its checkpoint and record a warning outcome. The technical reference requires readback of every upload. For ordinary artifacts CY records the SDK acknowledgement and flush without fetching the remote artifact. [Output Models](0302-output-model-verification.md) have a separate byte check.

[Upload and manifest implementation](../src/clearml_yolo/adapters/clearml/session.py) · [Rejected, missing and aliased artifacts](../tests/test_clearml_session.py) · [Publication reference](../DOCS.md#clearml-publication) · [Artifact catalog](../docs/publication.md) · [Contract discrepancy SIP-348](https://linear.app/sip-ds-team/issue/SIP-348) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
