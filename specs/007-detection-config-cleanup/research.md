# Research and decisions

- Decision: add an explicit example-rendering mode. Runtime render_native_yaml currently
  serves durable replay artifacts; changing its default would lose derived values.
  Alternative rejected: remove controlled keys from native defaults.
- Decision: adapter reads actual task project/name/ID; filesystem helper accepts plain
  strings. Alternative rejected: use requested ClearMLConfig names or import SDK in paths.
- Decision: percent-encode unsafe UTF-8 bytes and special components to prevent path
  traversal while retaining readable ordinary names. Explicit routes retain precedence.
- Superseded decision: the initial plan centralized 13 split kinds. The current publication
  contract instead uploads one consolidated evaluation workbook per selected split and one
  exact validation-threshold CSV, while retaining component files locally for validation.
- Decision: keep publication service/schema unchanged; validate existing owner integration.
- Clarification review: supplied plan resolves all material questions. Empty selections
  retain existing default fallback; duplicates are evaluated once.
