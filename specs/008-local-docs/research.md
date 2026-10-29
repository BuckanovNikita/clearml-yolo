# Research and decisions

- Current evidence: nine Hydra command schemas use anonymous `make_config` nodes; model
  groups come from Pydantic presets, native groups from installed dependency defaults.
  Decision: named dataclasses project into the same `make_config` shape. Structured typed
  dataclasses would tighten permissive composition, so are not passed directly to Hydra.
- Current evidence: public configuration models live across core and application contracts.
  Decision: attach Russian field descriptions there; never move targets or import docs
  assets from those models. Missing descriptions must fail docs checks, not runtime imports.
- Decision: separate worker process for every preview, bounded by the serving adapter.
  Entrypoint performs composition with trusted plugins and named in-memory inputs staged by
  an adapter; no instantiation or runtime preparation. Custom/env resolvers are not evaluated.
- Decision: packaged generated HTML uses existing Markdown tooling only during maintenance.
  Vanilla JS consumes JSON catalog/preview responses; no runtime frontend dependencies.
- Current evidence: `007`, corp-skills and cy-queue have independent uncommitted work.
  Preserve it and record exact task-owned hunks; acceptance/release must not claim ownership.
- Installed Spec Kit setup helpers persist feature selection. Use template resolution and
  explicit `--paths-only` prerequisite checks instead to preserve 007 workflow state.
