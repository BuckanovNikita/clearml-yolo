# Research decisions

- Existing `core.batch_estimation.model_catalogue` supplies all maintained model
  selections; bulk eligibility excludes gated DEIM l/x and dinov3_small only.
- Current resolver downloads into CY-managed locations and merely reads native
  caches. Native discovery therefore requires an explicit native destination and
  atomic promotion rather than changing model selectors.
- Installed timm prefers HF over URL for the eligible registered models. A URL
  checkpoint is not evidence of an equivalent HF representation. Use native source
  selection and actual HF commit/representation metadata; preserve configured URL
  mode. Standard HF constants retain import-time selector semantics.
- Ultralytics searches effective settings weights_dir for native names, aliases,
  nested pretrained loads and AMP's auxiliary model. No model/config rewriting is
  needed. Read settings without calling update/reset.
- HF cache metadata and config are part of native reuse. Use supported Hub APIs;
  promote legacy bytes only against known matching representation metadata.
- Existing DEIM managed source extraction and manifest validation remain authoritative.
- Pipeline execution boundary follows config inspection and precedes construction;
  command import/help, standalone stages and queue submission must not prepare.
