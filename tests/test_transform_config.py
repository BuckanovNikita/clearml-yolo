"""Portable augmentation selectors retain validated replay identity."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest


def _document() -> dict[str, Any]:
    return {
        "__version__": "2.0.8",
        "transform": {"__class_fullname__": "Compose", "transforms": [], "p": 1.0},
    }


def test_native_selector_does_not_accept_a_custom_pipeline() -> None:
    from clearml_yolo.core.transforms import TransformConfig

    assert TransformConfig().mode == "native"
    with pytest.raises(ValueError, match="albumentations"):
        TransformConfig(pipeline_file=Path("augmentations.json"))
    with pytest.raises(ValueError, match=r"pipeline_file|snapshot"):
        TransformConfig(mode="albumentations")


def test_snapshot_checks_canonical_content_hash() -> None:
    from clearml_yolo.core.transforms import TransformSnapshot, pipeline_digest

    document = _document()
    expected = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert pipeline_digest(document) == expected
    snapshot = TransformSnapshot(pipeline=document, sha256=expected, source="recipe.json")
    assert snapshot.model_dump(mode="json")["pipeline"] == document
    with pytest.raises(ValueError, match=r"sha256|digest"):
        TransformSnapshot(pipeline=document, sha256="0" * 64, source="recipe.json")


def test_file_resolution_freezes_content_and_replay_does_not_reopen(tmp_path: Path) -> None:
    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.core.transforms import TransformConfig

    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(_document()))
    resolved = resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=path))
    assert resolved.snapshot is not None
    assert resolved.snapshot.pipeline == _document()
    path.unlink()
    replay = TransformConfig.model_validate(resolved.model_dump(mode="json"))
    assert resolve_transform_config(replay) == resolved


def test_resolver_reports_malformed_json(tmp_path: Path) -> None:
    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.core.transforms import TransformConfig

    path = tmp_path / "broken.json"
    path.write_text("{broken}")
    with pytest.raises(ValueError, match=r"broken\.json"):
        resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=path))
