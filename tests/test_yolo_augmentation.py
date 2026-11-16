"""Native YOLO training retains custom geometry and portable worker state."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image


def test_fixed_recipe_rejects_batch_reduction_and_repeated_epochs_before_training() -> None:
    import cloudpickle  # type: ignore[import-untyped]  # Native DDP serializer.

    from clearml_yolo.adapters.integrations.native_trainer import (
        OwnedDetectionTrainer,
        fixed_training_recipe,
        trainer_with_transforms,
    )

    with fixed_training_recipe(batch=16, epochs=2):
        selected = trainer_with_transforms(None)
    restored = cloudpickle.loads(cloudpickle.dumps(selected))
    trainer: Any = restored.__new__(restored)
    trainer.batch_size, trainer.epochs, trainer.epoch = 16, 2, 0
    trainer.callbacks = {"on_train_epoch_start": []}
    trainer.run_callbacks("on_train_epoch_start")
    with pytest.raises(RuntimeError, match="repeated"):
        trainer.run_callbacks("on_train_epoch_start")
    trainer.epoch = 1
    trainer.run_callbacks("on_train_epoch_start")
    trainer.epoch = 2
    with pytest.raises(RuntimeError, match="epoch"):
        trainer.run_callbacks("on_train_epoch_start")
    trainer.batch_size = 8
    with pytest.raises(RuntimeError, match="batch"):
        trainer._build_train_pipeline()
    assert trainer_with_transforms(None) is OwnedDetectionTrainer


def test_owned_trainer_round_trips_frozen_pipeline_without_source_file(tmp_path: Path) -> None:
    import cloudpickle

    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.adapters.integrations import native_trainer
    from clearml_yolo.core.transforms import TransformConfig

    path = tmp_path / "pipeline.json"
    path.write_text(
        json.dumps(
            {
                "transform": {
                    "__class_fullname__": "Compose",
                    "transforms": [{"__class_fullname__": "HorizontalFlip", "p": 1.0}],
                }
            }
        ),
        encoding="utf-8",
    )
    transforms = resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=path))
    trainer = native_trainer.trainer_with_transforms(transforms)
    serialized = cloudpickle.dumps(trainer)
    path.unlink()
    restored = cloudpickle.loads(serialized)
    assert restored.transform_config == transforms
    assert restored.transform_config.snapshot is not transforms.snapshot
    assert native_trainer.OwnedDetectionTrainer.transform_config.mode == "native"


def test_yolo_custom_crop_keeps_empty_result_and_raw_source_geometry(tmp_path: Path) -> None:
    from ultralytics.cfg import get_cfg
    from ultralytics.utils import IterableSimpleNamespace

    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.adapters.yolo.augmentation import AugmentedYOLODataset
    from clearml_yolo.core.transforms import TransformConfig

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    pixels = np.zeros((40, 80, 3), dtype=np.uint8)
    pixels[:, :, 0] = 255
    Image.fromarray(pixels).save(images / "sample.png")
    (labels / "sample.txt").write_text("0 0.125 0.5 0.125 0.5\n")
    path = tmp_path / "pipeline.json"
    path.write_text(
        json.dumps(
            {
                "__version__": "2.0.8",
                "transform": {
                    "__class_fullname__": "Compose",
                    "p": 1.0,
                    "transforms": [
                        {
                            "__class_fullname__": "Crop",
                            "x_min": 40,
                            "y_min": 0,
                            "x_max": 80,
                            "y_max": 40,
                            "p": 1.0,
                        }
                    ],
                },
            }
        )
    )
    transforms = resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=path))
    settings = IterableSimpleNamespace(**vars(get_cfg()))
    dataset = AugmentedYOLODataset(
        img_path=str(images),
        imgsz=32,
        batch_size=1,
        augment=True,
        hyp=settings,
        data={"names": {0: "defect"}, "nc": 1, "channels": 3},
        transforms=transforms,
    )
    raw = dataset.raw_sample(0)
    assert raw.image.shape == (40, 80, 3)
    output = dataset[0]
    assert tuple(output["img"].shape) == (3, 32, 32)
    assert output["bboxes"].shape == (0, 4)
    assert output["cls"].shape == (0, 1)
    assert float(output["img"][0].float().mean()) > 250
    assert float(output["img"][2].float().mean()) == 0
    dataset.close_mosaic(settings)
    assert dataset[0]["bboxes"].shape == (0, 4)


@pytest.mark.parametrize("orientation", [2, 6, 8])
def test_yolo_raw_reader_matches_native_exif_geometry(tmp_path: Path, orientation: int) -> None:
    from ultralytics.cfg import get_cfg
    from ultralytics.utils.patches import imread

    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.adapters.yolo.augmentation import AugmentedYOLODataset
    from clearml_yolo.core.transforms import TransformConfig

    images = tmp_path / "images"
    labels = tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    pixels = np.zeros((20, 40, 3), dtype=np.uint8)
    pixels[:10, :20, 0] = 240
    pixels[10:, 20:, 1] = 200
    image = Image.fromarray(pixels)
    exif = image.getexif()
    exif[274] = orientation
    path = images / "oriented.jpg"
    image.save(path, exif=exif, quality=100, subsampling=0)
    (labels / "oriented.txt").write_text("0 0.25 0.25 0.5 0.5\n", encoding="utf-8")
    pipeline = tmp_path / "pipeline.json"
    pipeline.write_text(
        json.dumps({"transform": {"__class_fullname__": "Compose", "transforms": []}}),
        encoding="utf-8",
    )
    transforms = resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=pipeline))
    dataset = AugmentedYOLODataset(
        img_path=str(images),
        imgsz=32,
        batch_size=1,
        augment=True,
        hyp=get_cfg(),
        data={"names": {0: "defect"}, "nc": 1, "channels": 3},
        transforms=transforms,
    )
    native = imread(str(path))
    assert native is not None
    raw = dataset.raw_sample(0)
    assert raw.image.shape == native.shape
    np.testing.assert_allclose(raw.image, native[:, :, ::-1], atol=2)
    height, width = native.shape[:2]
    np.testing.assert_allclose(raw.boxes, [[0, 0, width / 2, height / 2]])
