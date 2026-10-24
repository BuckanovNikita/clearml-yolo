"""Resolve a standard Albumentations JSON file into a portable checked snapshot."""

import json

from pydantic import JsonValue, TypeAdapter

from clearml_yolo.core.transforms import TransformConfig, TransformSnapshot, pipeline_digest


def resolve_transform_config(config: TransformConfig) -> TransformConfig:
    """Existing snapshots remain authoritative after the source file disappears."""
    if config.mode == "native":
        return config
    if config.snapshot is not None:
        snapshot = TransformSnapshot.model_validate(config.snapshot.model_dump(mode="json"))
    else:
        path = config.pipeline_file
        if path is None:
            raise ValueError("Albumentations requires transforms.pipeline_file")
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read augmentation JSON {path}: {error}") from error
        pipeline = TypeAdapter(dict[str, JsonValue]).validate_python(content)
        snapshot = TransformSnapshot(
            pipeline=pipeline, sha256=pipeline_digest(pipeline), source=str(path)
        )
    validate_pipeline(snapshot.pipeline)
    return TransformConfig(mode=config.mode, pipeline_file=config.pipeline_file, snapshot=snapshot)


def validate_pipeline(pipeline: dict[str, JsonValue]) -> None:
    """Validate construction before creating model assets or starting training."""
    from clearml_yolo.adapters.augmentation.serialization import build_pipeline

    build_pipeline(pipeline, seed=0)
