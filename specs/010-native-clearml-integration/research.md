# Research: Native ClearML tracking

## Live event delivery

- **Decision**: use an owner-side incremental journal consumer under copied invocation context.
- **Rationale**: src/clearml_yolo/native_ddp.py already captures worker state and replays installed callbacks, but its current full-journal read is post-training. ContextVars in clearml_session.py identify the owner task and must reach the consumer.
- **Alternatives considered**: worker SDK reporting violates ownership; completion replay cannot show live progress; replacing native callbacks duplicates upstream reporting.

## Completion ordering

- **Decision**: stream epoch events, defer native on_train_end until journal completeness is validated in final drain.
- **Rationale**: native final callback publishes weights; corrupt or interrupted journals must not publish final model state or authorize task completion.
- **Alternatives considered**: dispatching the terminal callback immediately risks model publication from an incomplete journal; waiting for every event until completion loses live progress.

## Artifact and replay baseline

- **Decision**: retain v0.10 behavior and add command-level regressions, correcting only demonstrated remaining violations.
- **Rationale**: clearml_session.connect_config_file already attaches Configuration Objects, tasks/publication keeps receipts local and artifact_names exposes performance names. Feature 009 already resolves/sanitizes consumed files for replay.
- **Alternatives considered**: filtering YAML/JSON filenames misses semantic violations and can remove useful performance data; rebuilding configuration storage risks comments/remote replay.

## Model and comparison compatibility

- **Decision**: preserve native model identity verification, source-task provenance and exact frozen validation threshold readers.
- **Rationale**: constitution 5.0 and existing clearml_native/clearml_models contracts require these behaviors.
- **Alternatives considered**: duplicate weight uploads obscure identity; test threshold recalibration violates paired comparison validity.

## Unknowns resolved

Product decisions are fixed by the approved conversation. Installed versions come from uv.lock; device/backend availability is checked at real acceptance, with unavailable physical DDP documented without claiming a pass.
