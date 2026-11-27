# ADR-0322 · Publish executable settings and a redacted differences view

Operators need the effective command inputs for [Agent replay](0304-agent-replay.md) and a shorter description of what an experiment changed.

**Decision.** Publish a sanitized JSON `run` configuration object and a `run_overrides` comparison against packaged defaults that omits output-routing settings. Record additional provenance and selected source configurations where applicable. The file attachment boundary preserves a private execution copy when a resolved input contains secrets.

**Consequences.** The effective settings and the convenient review view have different consumers. Arbitrary exception text is excluded from remote failure status. [Credential redaction](0013-credential-redaction.md) covers recognized credentials and URL forms; the [raw console journal](0314-console-and-scalars.md) captures bytes from native processes.

[Configuration publication and file attachment](../src/clearml_yolo/adapters/clearml/session.py) · [Structured redaction](../src/clearml_yolo/core/redaction.py) · [Configuration publication cases](../tests/test_configuration_publication.py) · [Configuration objects](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
