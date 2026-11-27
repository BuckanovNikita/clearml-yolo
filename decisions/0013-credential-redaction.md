# ADR-0013 · Sanitize structured values at publication boundaries

Configuration, URLs and exception messages can carry secrets. CY walks structured configuration and redacts recognized credential fields and sensitive URL content before attaching them. A remote failure status contains an error category and directs the reader to local diagnostics. [File resolution](0008-file-configuration.md) also tracks sensitive inputs through interpolations.

This protection applies to structured publication and sanitized summaries. The [console journal](0314-console-and-scalars.md) captures native stdout and stderr as emitted, so an external program controls what appears in those streams. [Redaction policy](../src/clearml_yolo/core/redaction.py) · [ClearML owner](../src/clearml_yolo/adapters/clearml/session.py) · [Publication cases](../tests/test_configuration_publication.py) · [Contract](../DOCS.md#clearml-publication)
