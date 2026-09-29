# Research and decisions

- Decision: add an explicit example-rendering mode. Runtime render_native_yaml currently
  serves durable replay artifacts; changing its default would lose derived values.
  Alternative rejected: remove controlled keys from native defaults.
- Decision: adapter reads actual task project/name/ID; filesystem helper accepts plain
  strings. Alternative rejected: use requested ClearMLConfig names or import SDK in paths.
- Decision: percent-encode unsafe UTF-8 bytes and special components to prevent path
  traversal while retaining readable ordinary names. Explicit routes retain precedence.
- Decision: centralize all 13 split kinds in artifact_names and validate produced files
  before uploads. Existing scoring already calibrates once and records exact payloads.
- Decision: keep publication service/schema unchanged; validate existing owner integration.
- Clarification review: supplied plan resolves all material questions. Empty selections
  retain existing default fallback; duplicates are evaluated once.
