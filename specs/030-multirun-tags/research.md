# Decisions — 2026-10-14

- **Decision**: Group in the launch layer, passing the resulting tags through the existing
  tracking configuration. **Reason**: `session.invocation` already sends `config.tags`
  to `Task.init`; it should not know Hydra or queue semantics.
- **Decision**: Use invocation-local state and freeze queue tags during submission.
  **Reason**: Workers may execute later in separate processes; process globals and
  environment variables risk unrelated launches sharing identity.
- **Alternatives**: A new Hydra callback/plugin adds unnecessary registration and dynamic
  import contracts. Deriving a tag from paths/timestamps is not random and couples
  grouping to output routing. Config-store random defaults also tag ordinary runs.
