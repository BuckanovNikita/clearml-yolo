# CLI and configuration contract

Eight entrypoints: cy, cy-train, cy-predict, cy-val, cy-metrics, cy-report, cy-compare,
cy-ground-truth. cy-queue and cy-init-config are removed.

Native settings live in `ultralytics` (pipeline: `train.ultralytics`, `predict.ultralytics`).
`cfg` next to a mapping names unchanged native YAML. Sparse mappings track presence.
Precedence: native defaults < cfg YAML < embedded mapping (including explicit default values)
< Hydra CLI overrides. Add an absent key with `+ultralytics.epochs=1`; override an existing
one with `ultralytics.epochs=1`. Unknown native parameters fail at native validation.
Wrapper settings (ClearML, inputs, evaluation, model selection, reports) remain separate.
Raw source configs and resolved configuration are captured before execution.

`run_dir` routes the whole pipeline. Native project/name that disagree with the chosen
pipeline training directory fail. Standalone training honors explicit native project/name;
otherwise it creates an isolated run. Standalone output-producing commands default to a
fresh directory and require explicit input paths; no silently shared output directories.
`cy-val` accepts weights, ground_truth, ultralytics, cfg, evaluation, splits and output_dir;
it predicts required val plus requested splits and evaluates at frozen validation thresholds.

Comparison takes baseline_model/candidate_model references, current ground_truth, inference,
split=test and statistical options. Automatic baseline is latest completed prod excluding
current task. Explicit local models require weights and exact thresholds; explicit invalid
inputs fail. Reports consume the comparison's current-test evaluated dashboards, not stored
historical dashboards. Missing automatic baseline records a skipped comparison.
Standalone `evaluation` is a sparse mapping (`+evaluation.ap_method=continuous`);
its supplied values override legacy `iou_threshold` and `matching_strategy`.
The pipeline forwards the full `metrics.evaluation` configuration to comparison.

Removed auto_gpu, force-gpu, augmentation JSON, generated-tree and clearml.enabled options
must fail rather than be silently ignored. No public disabled-tracking mode.
