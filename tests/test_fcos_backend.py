"""FCOS preserves foreground zero and its native stride-eight feature pyramid."""

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.core.models import ModelConfig, PredictSettings
from test_fasterrcnn_backend import PRESETS, _prepared


@pytest.fixture
def native_threads() -> Iterator[Any]:
    torch = importlib.import_module("torch")
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        yield torch
    finally:
        torch.set_num_threads(previous)


@pytest.mark.parametrize("preset", PRESETS)
def test_fcos_pyramid_and_foreground_zero_backward(preset: str, native_threads: Any) -> None:
    from clearml_yolo.adapters.fcos.model import build_model

    torch = native_threads
    model = build_model(preset, 1, pretrained=False, image_size=128)
    model.eval()
    with torch.no_grad():
        features = model.backbone(torch.zeros(1, 3, 128, 128))
    assert [tuple(value.shape[-2:]) for value in features.values()] == [
        (16, 16),
        (8, 8),
        (4, 4),
        (2, 2),
        (1, 1),
    ]
    assert model.anchor_generator.num_anchors_per_location() == [1] * 5
    model.train()
    losses = model(
        [torch.rand(3, 128, 128)],
        [{"boxes": torch.tensor([[20.0, 20.0, 90.0, 100.0]]), "labels": torch.tensor([0])}],
    )
    loss = torch.stack(list(losses.values())).sum()
    assert torch.isfinite(loss)
    loss.backward()
    gradient = model.head.classification_head.cls_logits.weight.grad
    assert gradient is not None
    assert torch.count_nonzero(gradient) > 0
    model.eval()
    with torch.no_grad():
        predictions = model([torch.rand(3, 128, 128)])
    assert (predictions[0]["labels"] == 0).all()


@pytest.mark.parametrize("preset", PRESETS)
def test_fcos_dataset_and_checkpoint_roundtrip(
    preset: str, tmp_path: Path, native_threads: Any
) -> None:
    from clearml_yolo.adapters.fcos.backend import predict, train
    from clearml_yolo.adapters.torchvision.data import prepared_datasets

    prepared = _prepared(tmp_path)
    train_data, _, _ = prepared_datasets(prepared, label_offset=0)
    assert train_data[0][1]["labels"].tolist() == [0]
    config = ModelConfig.model_validate(
        {
            "backend": "fcos",
            "preset": preset,
            "train": {
                "device": "cpu",
                "epochs": 1,
                "batch": 2,
                "imgsz": 128,
                "workers": 0,
                "pretrained": False,
                "amp": False,
                "use_ema": True,
            },
        }
    )
    result = train(config, prepared, tmp_path / "run", lambda *_: None)
    checkpoint = native_threads.load(result.weights, map_location="cpu", weights_only=True)
    assert all(not key.startswith("module.") for key in checkpoint["state_dict"])
    assert result.metadata.backend == "fcos"
    assert result.metadata.class_names == ("класс-01",)
    path = str(prepared.data.parent / "valid" / "object.png")
    frame = predict(config, result.metadata, result.weights, [path], PredictSettings(device="cpu"))
    assert frame.attrs["image_paths"] == [path]
    assert set(frame["instance_label"]) <= {"класс-01"}
    assert result.effective_args["global_batch"] == 2
    assert result.effective_args["per_rank_batch"] == 2


@pytest.mark.parametrize("preset", PRESETS)
def test_fcos_loads_local_pretrained_backbone_without_loading_detector_head(
    preset: str, tmp_path: Path, native_threads: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.fcos.model import build_model
    from clearml_yolo.adapters.torchvision.assets import TIMM_MODELS

    torch = native_threads
    if preset.endswith("_fpn"):
        models = importlib.import_module("torchvision.models")
        backbone = getattr(models, preset.removesuffix("_fpn"))(weights=None)
    else:
        timm = importlib.import_module("timm")
        backbone = timm.create_model(TIMM_MODELS[preset], pretrained=False)
    with torch.no_grad():
        next(backbone.parameters()).fill_(0.125)
    expected = next(backbone.parameters()).detach().clone()
    weights = tmp_path / "backbone.pth"
    torch.save(backbone.state_dict(), weights)
    del backbone
    hub = importlib.import_module("torch.hub")
    monkeypatch.setattr(
        hub, "download_url_to_file", lambda *_args, **_kwargs: pytest.fail("unexpected download")
    )
    model = build_model(preset, 3, pretrained=True, backbone_weights=weights, image_size=128)
    torch.testing.assert_close(next(model.backbone.body.parameters()), expected)
    assert model.head.classification_head.cls_logits.out_channels == 3
    assert model.head.classification_head.cls_logits.weight.requires_grad
