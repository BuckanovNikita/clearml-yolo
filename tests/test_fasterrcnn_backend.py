"""Native Faster R-CNN recipes retain geometry, labels, losses and checkpoint identity."""

import importlib
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from PIL import Image

from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import CheckpointMetadata, ModelConfig, PredictSettings, Preprocessing

PRESETS = [
    "resnet50_fpn",
    "resnet101_fpn",
    "convnext_tiny",
    "swin_tiny",
    "dinov2_small",
    "dinov3_small",
]


@pytest.fixture
def single_thread_torch() -> Iterator[Any]:
    torch = importlib.import_module("torch")
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        yield torch
    finally:
        torch.set_num_threads(previous)


def _prepared(tmp_path: Path) -> PreparedDataset:
    root = tmp_path / "data"
    root.mkdir()
    for split in ("train", "valid"):
        folder = root / split
        folder.mkdir()
        image = np.full((64, 96, 3), 128, dtype=np.uint8)
        image[10:42, 20:60] = (220, 10, 20)
        Image.fromarray(image).save(folder / "object.png")
        Image.new("RGB", (96, 64), color=(100, 100, 100)).save(folder / "empty.png")
        payload = {
            "images": [
                {"id": 1, "file_name": "object.png", "height": 64, "width": 96},
                {"id": 2, "file_name": "empty.png", "height": 64, "width": 96},
            ],
            "categories": [{"id": 0, "name": "класс-01"}],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [20, 10, 40, 32],
                    "area": 1280,
                    "iscrowd": 0,
                }
            ],
        }
        (folder / "_annotations.coco.json").write_text(json.dumps(payload))
    data = root / "data.yaml"
    data.write_text(
        yaml.safe_dump(
            {"path": str(root), "train": "train", "val": "valid", "names": {0: "класс-01"}}
        )
    )
    truth = root / "truth.csv"
    truth.write_text("image_name,instance_label\n")
    manifest = root / "manifest.json"
    manifest.write_text("{}\n")
    return PreparedDataset(
        data=data, ground_truth=truth, manifest=manifest, dataset_format="coco", artifacts=[]
    )


def test_backend_import_is_lazy(tmp_path: Path) -> None:
    script = """
import sys
import clearml_yolo.adapters.fasterrcnn.backend
assert not {'torch', 'torchvision', 'timm', 'clearml'} & sys.modules.keys()
"""
    result = subprocess.run(  # noqa: S603 - fixed script with current interpreter
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("preset", PRESETS)
def test_every_backbone_has_exportable_stride_pyramid(
    preset: str, single_thread_torch: Any
) -> None:
    from clearml_yolo.adapters.fasterrcnn.model import build_model

    torch = single_thread_torch
    model = build_model(preset, 1, pretrained=False, image_size=(64, 96))
    model.eval()
    with torch.inference_mode():
        features = model.backbone(torch.zeros(1, 3, 64, 96))
        detections = model([torch.zeros(3, 64, 96)])
    assert list(features) == ["0", "1", "2", "3", "pool"]
    assert [tuple(feature.shape) for feature in features.values()] == [
        (1, 256, 16, 24),
        (1, 256, 8, 12),
        (1, 256, 4, 6),
        (1, 256, 2, 3),
        (1, 256, 1, 2),
    ]
    assert len(detections) == 1
    assert torch.isfinite(detections[0]["boxes"]).all()
    assert (detections[0]["labels"] == 1).all()


def test_letterbox_roundtrip_preserves_original_geometry(single_thread_torch: Any) -> None:
    from clearml_yolo.adapters.fasterrcnn.transform import LetterboxTransform

    torch = single_thread_torch
    transform = LetterboxTransform((64, 96))
    transform.eval()
    original = torch.tensor([[5.0, 10.0, 25.0, 40.0]])
    images, targets = transform(
        [torch.ones(3, 100, 50)], [{"boxes": original.clone(), "labels": torch.tensor([1])}]
    )
    assert images.image_sizes == [(64, 32)]
    assert tuple(images.tensors.shape) == (1, 3, 64, 96)
    assert torch.count_nonzero(images.tensors[:, :, :, 32:]) == 0
    assert targets is not None
    result = transform.postprocess([{"boxes": targets[0]["boxes"]}], [(64, 32)], [(100, 50)])
    torch.testing.assert_close(result[0]["boxes"], original)


def test_roi_pool_uses_canvas_strides_for_short_valid_images(single_thread_torch: Any) -> None:
    from clearml_yolo.adapters.fasterrcnn.model import build_model

    torch = single_thread_torch
    ops = importlib.import_module("torchvision.ops")
    model = build_model("resnet50_fpn", 1, pretrained=False, image_size=(64, 96))
    features = {
        str(index): torch.arange(height * width).reshape(1, 1, height, width).float()
        for index, (height, width) in enumerate(((16, 24), (8, 12), (4, 6), (2, 3)))
    }
    boxes = [torch.tensor([[4.0, 2.0, 24.0, 12.0]])]
    expected = ops.roi_align(
        features["0"], boxes, output_size=7, spatial_scale=0.25, sampling_ratio=2
    )
    actual = model.roi_heads.box_roi_pool(features, boxes, [(16, 96)])
    torch.testing.assert_close(actual, expected)


@pytest.mark.parametrize("preset", PRESETS)
def test_native_training_updates_weights_and_reloads_all_presets(
    preset: str, tmp_path: Path, single_thread_torch: Any
) -> None:
    from clearml_yolo.adapters.fasterrcnn.backend import predict, train
    from clearml_yolo.adapters.fasterrcnn.model import build_model

    torch = single_thread_torch
    prepared = _prepared(tmp_path)
    config = ModelConfig.model_validate(
        {
            "backend": "fasterrcnn",
            "preset": preset,
            "train": {
                "device": "cpu",
                "epochs": 1,
                "batch": 2,
                "imgsz": [64, 96],
                "workers": 0,
                "pretrained": False,
                "amp": False,
                "use_ema": False,
            },
        }
    )
    torch.manual_seed(0)
    initial = build_model(preset, 1, pretrained=False, image_size=(64, 96))
    before = initial.roi_heads.box_predictor.cls_score.weight.detach().clone()
    del initial
    emitted: list[tuple[str, float, int]] = []
    result = train(
        config,
        prepared,
        tmp_path / "run",
        lambda name, value, epoch: emitted.append((name, value, epoch)),
    )
    checkpoint = torch.load(result.weights, map_location="cpu", weights_only=True)
    after = checkpoint["state_dict"]["roi_heads.box_predictor.cls_score.weight"]
    assert not torch.equal(before, after)
    assert result.metadata.class_names == ("класс-01",)
    assert checkpoint["epoch"] == 0
    assert checkpoint["selection_metric"] == result.metrics["val/map50_95"]
    assert 0 <= result.metrics["val/map50_95"] <= 1
    assert any(name == "train/loss" for name, _, _ in emitted)
    paths = [
        str(prepared.data.parent / "valid" / filename) for filename in ("object.png", "empty.png")
    ]
    frame = predict(
        config,
        result.metadata,
        result.weights,
        paths,
        PredictSettings(device="cpu", batch=2, conf=1.0),
    )
    assert frame.empty
    assert frame.attrs["image_paths"] == paths
    assert frame.attrs["normalized_imgsz"] == [64, 96]


def test_missing_explicit_backbone_weights_fails_before_training(tmp_path: Path) -> None:
    from clearml_yolo.adapters.fasterrcnn.model import build_model

    with pytest.raises(FileNotFoundError):
        build_model("resnet50_fpn", 1, pretrained=True, backbone_weights=tmp_path / "missing.pth")


def test_multidevice_request_is_explicitly_rejected(tmp_path: Path) -> None:
    from clearml_yolo.adapters.fasterrcnn.backend import train

    config = ModelConfig.model_validate(
        {"backend": "fasterrcnn", "preset": "resnet50_fpn", "train": {"device": [0, 1]}}
    )
    with pytest.raises(ValueError, match="multi-device"):
        train(config, _prepared(tmp_path), tmp_path / "run", lambda *_: None)


def test_prediction_rejects_unknown_preprocessing_instead_of_ignoring_it(tmp_path: Path) -> None:
    from clearml_yolo.adapters.fasterrcnn.backend import predict

    config = ModelConfig(backend="fasterrcnn", preset="resnet50_fpn")
    descriptor = CheckpointMetadata(
        backend="fasterrcnn",
        preset="resnet50_fpn",
        class_names=("object",),
        preprocessing=Preprocessing(resize="stretch", size=64),
    )
    with pytest.raises(ValueError, match="preprocessing"):
        predict(config, descriptor, tmp_path / "absent.pth", [], PredictSettings(device="cpu"))


def test_training_ema_accumulation_and_callback_failures_are_explicit(
    tmp_path: Path, single_thread_torch: Any
) -> None:
    from clearml_yolo.adapters.fasterrcnn.backend import train

    config = ModelConfig.model_validate(
        {
            "backend": "fasterrcnn",
            "preset": "resnet50_fpn",
            "train": {
                "device": "cpu",
                "epochs": 1,
                "batch": 1,
                "imgsz": [64, 96],
                "workers": 0,
                "pretrained": False,
                "amp": True,
                "use_ema": True,
                "grad_accum_steps": 3,
            },
        }
    )
    prepared = _prepared(tmp_path)

    def rejected(_name: str, _value: float, _epoch: int) -> None:
        raise RuntimeError("owner callback rejected")

    with pytest.raises(RuntimeError, match="owner callback rejected"):
        train(config, prepared, tmp_path / "failed", rejected)
    assert not (tmp_path / "failed" / "best.pth").exists()
    result = train(config, prepared, tmp_path / "successful", lambda *_: None)
    assert result.effective_args["ema_decay"] == 0.999
    assert result.effective_args["amp"] is False
    assert result.effective_args["grad_accum_steps"] == 3
    assert result.weights.is_file()
