# Invocation publication state

- Executable configuration: detached plain mapping, sanitized only for storage. Defaults
  and differences are separate mappings; provenance merges do not overwrite selected values.
- Result contributors: declared set and completed subset of predict/metrics/compare;
  all must finish before the aggregate is immutable and uploaded. No completion on failure.
- Artifact: canonical name, finalized local path, upload status; failures propagate.
- Export notification: name/path callback after final write, before the next producer step.
