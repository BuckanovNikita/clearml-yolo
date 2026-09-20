# Data model

- Native settings: sparse string-keyed mapping; explicit values are never inferred from equality.
- Run: unique identity, absolute directory, owner task and stage-specific required artifact manifest.
- ModelRef: source local/clearml, task/project/tags or checkpoint; exact class -> confidence mapping.
  Required thresholds must be finite and within [0,1]; missing required classes fail explicitly.
- Dataset tables: preserve existing image_name, instance_label, bounding-box and split fields;
  ground truth includes image_path. Empty-image placeholder rows remain in membership.
  A logical image cannot belong to both val and test; missing images fail before scoring.
- Evaluation: frozen thresholds, matches, per-class TP/FP/FN, dashboard and image membership.
  Threshold optimization uses only val; test must never call optimization.
- Comparison: baseline and candidate evaluated on one membership/settings tuple; exclusions,
  statistical outcomes and paired dashboards are shared with report builders.
- Manifest: stage, artifact name, local path when applicable, required/uploaded state.
  Missing or unsuccessful required uploads prevent completed state.
