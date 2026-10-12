"""Checkpoint bytes retain their detector identity across standalone copies."""

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

from clearml_yolo.adapters.storage.checkpoint import (
    bind_checkpoint,
    read_checkpoint_descriptor,
)
from clearml_yolo.core.models import CheckpointMetadata, Preprocessing, model_preset


@pytest.fixture
def metadata() -> CheckpointMetadata:
    return CheckpointMetadata(
        backend="fasterrcnn",
        preset="resnet50_fpn",
        class_names=("0001", "施工"),
        preprocessing=Preprocessing(resize="letterbox", size=(608, 960)),
    )


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    path = tmp_path / "best.pth"
    with ZipFile(path, "w") as archive:
        archive.writestr("best/data.pkl", b"weights-fixture")
    return path


def test_copy_of_checkpoint_retains_vocabulary_without_sidecar(
    checkpoint: Path, metadata: CheckpointMetadata, tmp_path: Path
) -> None:
    expected = bind_checkpoint(checkpoint, metadata)
    copy = tmp_path / "download.pth"
    shutil.copyfile(checkpoint, copy)
    observed = read_checkpoint_descriptor(copy)
    assert observed == expected
    assert observed.class_names == ("0001", "施工")


def test_modified_checkpoint_does_not_reuse_old_descriptor(
    checkpoint: Path, metadata: CheckpointMetadata
) -> None:
    bind_checkpoint(checkpoint, metadata)
    with ZipFile(checkpoint, "a") as archive:
        archive.writestr("best/data/0", b"changed-weights")
    with pytest.raises(ValueError, match="hash"):
        read_checkpoint_descriptor(checkpoint)


def test_sidecar_cannot_replace_checkpoint_classes(
    checkpoint: Path, metadata: CheckpointMetadata
) -> None:
    bind_checkpoint(checkpoint, metadata)
    sidecar = checkpoint.with_name(checkpoint.name + ".model.json")
    value = json.loads(sidecar.read_text())
    value["class_names"] = ["different"]
    sidecar.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="metadata"):
        read_checkpoint_descriptor(checkpoint)


def test_explicit_selection_cannot_override_described_backend(
    checkpoint: Path, metadata: CheckpointMetadata
) -> None:
    bind_checkpoint(checkpoint, metadata)
    with pytest.raises(ValueError, match="selection"):
        read_checkpoint_descriptor(checkpoint, expected=model_preset("rfdetr/small"))


def test_legacy_checkpoint_has_no_invented_backend(checkpoint: Path) -> None:
    assert read_checkpoint_descriptor(checkpoint) is None


def test_binding_metadata_preserves_torch_loading(
    tmp_path: Path, metadata: CheckpointMetadata
) -> None:
    import torch

    path = tmp_path / "native.pth"
    torch.save({"model": {"weight": torch.tensor([1.0, 2.0])}}, path)
    bind_checkpoint(path, metadata)
    loaded = torch.load(path, weights_only=True)
    assert loaded["model"]["weight"].tolist() == [1.0, 2.0]
