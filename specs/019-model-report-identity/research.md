# Research decisions

- Reuse `clearml_naming.resolve_model_name`; it checks exact active/archived names
  and rechecks after writes. No separate uniqueness algorithm is needed.
- Bind sidecars to SHA-256 values so local/recovered inputs cannot silently inherit
  stale source identity. Existing report tasks never become training sources.
- Excel headers cannot hold arbitrary long identity text. Use visible banner rows
  repeated through print titles, translating generated workbook references and
  preserving original body formatting and page breaks.
- Existing readers assume fixed dashboard header rows. Normalize annotated inputs
  in memory before calling pinned readers; retain original files and old inputs.
- Custom labels are fallbacks for unknown provenance; verified source names win.
