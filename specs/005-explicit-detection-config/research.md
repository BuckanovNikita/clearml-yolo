# Research: Explicit Detection Configuration

## Decisions

- Installed distribution and locked source are the compatibility authority; no upgrade.
- Upstream predict supplies batch=1, rect=true, save=false for its Python API. Encode these
  in the prediction group rather than inherit conflicting training defaults.
- compile=true and nms=true are user-selected project defaults, not upstream defaults.
- nms is consumed by training validation and predictor setup; export-only classification is wrong.
- Task-only losses/augmentations and video-only settings are irrelevant to detection over
  ground-truth image manifests. Embedding output is incompatible with detection records.
- Helpers currently default confidence/IoU/batch/device/rect and infer resolution from
  checkpoints. Replace those with required resolved settings; retain checkpoint size as diagnostics.
- Retain template comments and ordering. Never populate absent effective values from the
  template while rendering an execution record.

## Alternatives Rejected

Sparse prediction overrides hide configuration; implicit runtime merges make ownership
ambiguous; independent literals for every shared value discard the user's chosen references.
Rounding 906 in the wrapper obscures the requested setting and duplicates native behavior.

The reviewed parameter inventory below was completed from installed consumers before implementation.


## Reviewed Parameter Inventory (2026-09-29)

The installed locked Ultralytics 8.4.165 template contains 113 keys. The following
mutually exclusive groups cover every template key. Paths below are relative to the
Ultralytics package and describe reviewed source evidence, not a machine setup.

### Active in both stages (28 keys)

`task`, `mode`, `model`, `data`, `batch`, `imgsz`, `save`, `device`, `project`, `name`,
`exist_ok`, `verbose`, `rect`, `compile`, `channels_last`, `conf`, `iou`, `max_det`,
`quantize`, `nms`, `visualize`, `augment`, `agnostic_nms`, `classes`, `save_txt`,
`save_conf`, `show_labels`, `show_conf`.

Applicability does not imply identical ownership or defaults. Model, data and output
routing remain subject to the documented command-owned input contract. Prediction
uses references only for shared keys whose defaults are not explicitly stage-specific.

### Active only in training (52 keys)

`epochs`, `time`, `patience`, `save_period`, `cache`, `workers`, `pretrained`,
`cls_remap`, `optimizer`, `seed`, `deterministic`, `single_cls`, `cos_lr`,
`close_mosaic`, `resume`, `amp`, `fraction`, `profile`, `freeze`, `multi_scale`,
`val`, `split`, `save_json`, `plots`, `lr0`, `lrf`, `momentum`, `weight_decay`,
`warmup_epochs`, `warmup_momentum`, `warmup_bias_lr`, `distill_model`, `dis`,
`box`, `cls`, `cls_pw`, `dfl`, `nbs`, `hsv_h`, `hsv_s`, `hsv_v`, `degrees`,
`translate`, `scale`, `shear`, `perspective`, `flipud`, `fliplr`, `bgr`,
`mosaic`, `mixup`, `cutmix`.

### Active only in image prediction (6 keys)

`dnn`, `source`, `show`, `save_crop`, `show_boxes`, `line_width`.

`source` is present as an explicitly reserved null setting; image membership supplies
its actual value. A user-supplied non-null source fails rather than being discarded.
DNN selects an ONNX backend; training and its final checkpoint validation use PT.

### Inactive in both stages (27 keys)

- Other tasks: `overlap_mask`, `mask_ratio`, `dropout`, `retina_masks`, `pose`,
  `kobj`, `rle`, `angle`, `dlog`, `dgrad`, `dlam`, `copy_paste`,
  `copy_paste_mode`, `auto_augment`, `erasing`.
- Videos/streams outside the image-manifest contract: `vid_stride`, `stream_buffer`,
  `save_frames`.
- Export: `format`, `optimize`, `dynamic`, `simplify`, `opset`, `workspace`.
- Other workflow/unsupported input: `embed`, `cfg`, `tracker`.

Non-null `embed` must fail explicitly: native embeddings replace detection Results
with tensors. Non-null `cfg` already requires migration guidance. Other known inactive
settings are commented in examples and excluded from calls.

### Parameters absent from the template

Native compatibility aliases `end2end`, `half` and `int8` are deprecated; canonical
replacement keys are `nms` and `quantize`. Explicit canonical precision takes priority
upstream, so accepting a legacy precision flag beside a populated canonical null could
silently discard the user's intent. Reject these aliases with migration guidance.
Removed upstream `keras` is also rejected. Legacy visualization aliases (`boxes`,
`hide_labels`, `hide_conf`, `line_thickness`) should not be introduced by this phase.
`augmentations` is an upstream-supported additional train key, not an old custom
augmentation JSON option; retain existing native handling without adding a template
entry or changing the project's removed custom augmentation JSON contract. `save_dir`
is an internal output-routing key, not an editable template parameter.

## Runtime Evidence and Default Implications

- Native Python prediction method defaults are `conf=0.25`, `batch=1`, `save=false`,
  `mode=predict`, `rect=true`, `embed=null` (`engine/model.py:536`). The project
  deliberately chooses `conf=0.001` for calibration; other selected stage defaults
  should be visible literals rather than accidental inheritance from training.
- Detection loss gains are read in `utils/loss.py:469-471`; class weighting in
  `models/yolo/detect/train.py:159-169`; distillation weight in
  `nn/distill_model.py:107`. `cls` and `cls_pw` are useful for detection.
- Copy-paste exits without segments (`data/augment.py:1981`). Detection CutMix,
  MixUp and spatial/color transforms remain active (`data/augment.py:2869-2909`);
  BGR applies during training (`data/dataset.py:345`).
- `profile` is consumed in `utils/torch_utils.py:619`. Final training validation
  runs standalone (`engine/trainer.py:992-1005`), so `augment` remains relevant
  even though per-epoch validation disables it (`engine/validator.py:164`).
- Detection visualization/text output consumes `visualize`, `show_labels`,
  `show_conf`, `save_txt`, `save_conf` (`models/yolo/detect/val.py:262-281`).
- `nms` is active in both stages (`engine/validator.py:166-167`,
  `engine/predictor.py:469`). False requests an end-to-end head where supported;
  true and null both select ordinary external NMS for these stages. True does not
  imply export-embedded NMS in prediction or validation.
- `compile=true` maps to Inductor mode `default`; upstream can warn and fall back
  uncompiled (`utils/torch_utils.py:1205-1224`). QAT rejects compilation (line 1203),
  distillation disables it (`engine/trainer.py:368-370`), and final validation
  explicitly disables it (line 1004). Requested true is not proof of compilation.
- Native image-size normalization rounds upward to stride
  (`utils/checks.py:278-283`); 906 becomes 928 for stride 32. Training rewrites
  `trainer.args.imgsz` (`engine/trainer.py:350`). Prediction stores normalization
  in `predictor.imgsz` while `predictor.args.imgsz` can remain requested 906
  (`engine/predictor.py:294`). Record requested args and effective shape separately.
  Fixed exported models may use metadata shape (lines 292-293), which remains
  native behavior rather than a wrapper fallback.

## Requirements Review

Reviewed spec, plan, tasks and native-configuration contract together. All six custom
checklist criteria are satisfied as requirements-quality criteria, not implementation
claims. Every functional requirement has an implementation task and acceptance route.
The inventory above resolves stage relevance and alias handling before code changes.
No blocking contradiction was found. Native normalization and automatic behavior remain
explicitly permitted, including compilation fallback; they must be accurately recorded.
