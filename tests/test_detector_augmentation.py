"""Real native dataset geometry around the shared JSON training pipeline."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from PIL import Image


def _config(tmp_path: Path, operations: list[Any]) -> Any:
    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.core.transforms import TransformConfig

    augmentation = importlib.import_module("albumentations")
    path = tmp_path / "augmentation.json"
    pipeline = augmentation.Compose(
        operations,
        bbox_params=augmentation.BboxParams(format="pascal_voc", label_fields=["labels"]),
    )
    path.write_text(json.dumps(augmentation.to_dict(pipeline)), encoding="utf-8")
    return resolve_transform_config(TransformConfig(mode="albumentations", pipeline_file=path))


def _records(tmp_path: Path) -> Path:
    images, annotations = [], []
    for index in range(4):
        name = f"image-{index}.png"
        pixels = np.zeros((16, 32, 3), dtype=np.uint8)
        pixels[:, :, index % 3] = 255
        Image.fromarray(pixels).save(tmp_path / name)
        images.append({"id": index, "file_name": name, "height": 16, "width": 32})
        annotations.append(
            {
                "id": index,
                "image_id": index,
                "category_id": index,
                "bbox": [2, 4, 6, 8],
                "area": 48,
                "iscrowd": 0,
            }
        )
    path = tmp_path / "_annotations.coco.json"
    path.write_text(
        json.dumps(
            {
                "images": images,
                "annotations": annotations,
                "categories": [{"id": index, "name": str(index)} for index in range(4)],
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("empty", [False, True])
def test_fasterrcnn_custom_geometry_preserves_rgb_labels_and_empty_targets(
    tmp_path: Path, empty: bool
) -> None:
    from clearml_yolo.adapters.fasterrcnn.data import CocoDataset

    augmentation = importlib.import_module("albumentations")
    operation = (
        augmentation.Crop(x_min=16, y_min=0, x_max=32, y_max=16)
        if empty
        else augmentation.HorizontalFlip(p=1)
    )
    records = _records(tmp_path)
    native = CocoDataset(records, tuple(map(str, range(4))))
    custom = CocoDataset(
        records, tuple(map(str, range(4))), transforms=_config(tmp_path, [operation])
    )
    image, target = custom[0]
    assert image.dtype.is_floating_point
    assert image[0].min() == 1
    assert image[1:].max() == 0
    assert target["boxes"].tolist() == ([] if empty else [[24.0, 4.0, 30.0, 12.0]])
    assert target["labels"].tolist() == ([] if empty else [1])
    assert target["area"].tolist() == ([] if empty else [48.0])
    assert tuple(target["boxes"].shape) == (0 if empty else 1, 4)
    assert native[0][1]["boxes"].tolist() == [[2.0, 4.0, 8.0, 12.0]]


def test_fasterrcnn_mosaic_reads_raw_donors_and_keeps_foreground_offset(tmp_path: Path) -> None:
    from clearml_yolo.adapters.fasterrcnn.data import CocoDataset

    augmentation = importlib.import_module("albumentations")
    records = _records(tmp_path)
    pipeline = _config(
        tmp_path,
        [
            augmentation.Mosaic(
                target_size=(32, 64),
                cell_shape=(16, 32),
                center_range=(0.5, 0.5),
                fit_mode="contain",
                p=1,
            )
        ],
    )
    dataset = CocoDataset(records, tuple(map(str, range(4))), transforms=pipeline)
    image, target = dataset[0]
    assert image.shape == (3, 32, 64)
    assert sorted(target["labels"].tolist()) == [1, 2, 3, 4]
    assert target["area"].tolist() == [48.0] * 4
    assert dataset.raw_sample(0).image.shape == (16, 32, 3)


def test_rfdetr_custom_pipeline_keeps_native_normalization_and_validation(tmp_path: Path) -> None:
    from clearml_yolo.adapters.rfdetr.transforms import install_training_transforms

    augmentation = importlib.import_module("albumentations")
    coco = importlib.import_module("rfdetr.datasets.coco")
    records = _records(tmp_path)
    native = coco.make_coco_transforms_square_div_64("train", 32, aug_config={}, scale_jitter=False)
    train = coco.CocoDetection(tmp_path, records, native, draft_size=8)
    validation = coco.CocoDetection(tmp_path, records, native)
    module = SimpleNamespace(_dataset_train=train, _dataset_val=validation)
    config = _config(tmp_path, [augmentation.HorizontalFlip(p=1)])
    install_training_transforms(module, config, seed=7)
    installed = train._transforms
    install_training_transforms(module, config, seed=7)
    assert train._transforms is installed
    image, target = train[0]
    assert image.shape == (3, 32, 32)
    assert target["boxes"].tolist()[0] == pytest.approx([0.84375, 0.5, 0.1875, 0.5])
    assert target["labels"].tolist() == [0]
    assert float(image[0].mean()) == pytest.approx((1 - 0.485) / 0.229)
    assert train._draft_size is None
    assert validation._transforms is native
    assert validation[0][1]["boxes"].tolist()[0] == pytest.approx([0.15625, 0.5, 0.1875, 0.5])


def test_deim_custom_pipeline_retains_required_finalization_and_disables_schedule(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.deim.transforms import custom_training_recipe

    transforms: dict[str, Any] = {
        "ops": [
            {"type": "Mosaic", "probability": 1},
            {"type": "RandomHorizontalFlip"},
            {"type": "Resize", "size": [128, 128]},
            {"type": "SanitizeBoundingBoxes", "min_size": 1},
            {"type": "ConvertPILImage", "dtype": "float32", "scale": True},
            {"type": "Normalize", "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
            {"type": "ConvertBoxes", "fmt": "cxcywh", "normalize": True},
        ],
        "policy": {"name": "stop_epoch", "epoch": [4, 64, 120], "ops": ["Mosaic"]},
        "mosaic_prob": 0.5,
    }
    collate = {"mixup_prob": 0.5, "copyblend_prob": 0.5, "base_size_repeat": 20, "stop_epoch": 120}
    custom_training_recipe(transforms, collate)
    assert [item["type"] for item in transforms["ops"]] == [
        "Resize",
        "ConvertPILImage",
        "Normalize",
        "ConvertBoxes",
    ]
    assert transforms["policy"] is None
    assert transforms["mosaic_prob"] == 0
    assert collate == {
        "mixup_prob": 0,
        "copyblend_prob": 0,
        "base_size_repeat": None,
        "stop_epoch": 120,
    }


def test_native_target_boundary_rebuilds_shape_area_and_crowd_after_geometry() -> None:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample
    from clearml_yolo.adapters.augmentation.torch_data import tensor_target

    torch = importlib.import_module("torch")
    original = {
        "image_id": torch.tensor(9),
        "size": torch.tensor([16, 32]),
        "orig_size": torch.tensor([16, 32]),
        "area": torch.tensor([48.0, 48.0]),
        "labels": torch.tensor([0, 1]),
        "iscrowd": torch.tensor([0, 1]),
    }
    sample = DetectionSample(
        image=np.zeros((8, 12, 3), dtype=np.uint8),
        boxes=np.array([[1, 2, 3, 6]], dtype=np.float32),
        labels=np.array([1], dtype=np.int64),
        instance_ids=np.array([1], dtype=np.int64),
        iscrowd=np.array([1], dtype=np.int64),
    )
    target = tensor_target(sample, original, bounding_boxes=True)
    assert target["size"].tolist() == [8, 12]
    assert target["orig_size"].tolist() == [16, 32]
    assert target["area"].tolist() == [8.0]
    assert target["iscrowd"].tolist() == [1]
    assert target["labels"].tolist() == [1]
    assert target["boxes"].canvas_size == (8, 12)
    assert original["area"].tolist() == [48.0, 48.0]


class _DeimRawDataset:
    """Exercise DEIM's raw triple protocol using real images and torchvision targets."""

    def __init__(self, records: Path, epoch: int) -> None:
        from clearml_yolo.adapters.fasterrcnn.data import CocoDataset

        self.source = CocoDataset(records, tuple(map(str, range(4))))
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.source)

    def load_item(self, index: int) -> tuple[Image.Image, dict[str, Any]]:
        from clearml_yolo.adapters.augmentation.torch_data import tensor_target

        torch = importlib.import_module("torch")
        sample = self.source.raw_sample(index)
        target = tensor_target(sample, {"idx": torch.tensor([index])}, bounding_boxes=True)
        return Image.fromarray(sample.image), target


def _deim_finalization(
    image: Image.Image, target: dict[str, Any], dataset: _DeimRawDataset
) -> tuple[Any, dict[str, Any], _DeimRawDataset]:
    torch = importlib.import_module("torch")
    v2 = importlib.import_module("torchvision.transforms.v2")
    boxes = importlib.import_module("torchvision.ops")
    pipeline = v2.Compose(
        [
            v2.Resize((32, 64)),
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
        ]
    )
    tensor, target = pipeline(image, target)
    target["boxes"] = boxes.box_convert(target["boxes"], "xyxy", "cxcywh")
    target["boxes"] = target["boxes"] / torch.tensor([64, 32, 64, 32])
    return tensor, target, dataset


@pytest.mark.parametrize("epoch", [0, 130])
def test_deim_custom_pipeline_survives_native_epoch_schedule_and_recomputes_area(
    tmp_path: Path, epoch: int
) -> None:
    from clearml_yolo.adapters.deim.transforms import TrainingTransform

    augmentation = importlib.import_module("albumentations")
    dataset = _DeimRawDataset(_records(tmp_path), epoch)
    config = _config(tmp_path, [augmentation.HorizontalFlip(p=1)])
    transform = TrainingTransform(dataset, _deim_finalization, config, seed=3)
    raw_image, raw_target = dataset.load_item(0)
    image, target, returned_dataset = transform(raw_image, raw_target, dataset)
    assert returned_dataset is dataset
    assert image.shape == (3, 32, 64)
    assert target["boxes"][0].tolist() == pytest.approx([0.84375, 0.5, 0.1875, 0.5])
    assert target["area"].tolist() == [192.0]
    assert target["labels"].tolist() == [0]
    assert target["iscrowd"].tolist() == [0]
    assert float(image[0].mean()) == pytest.approx((1 - 0.485) / 0.229)


def test_deim_custom_pipeline_preserves_subpixel_boxes(tmp_path: Path) -> None:
    from clearml_yolo.adapters.deim.transforms import TrainingTransform

    dataset = _DeimRawDataset(_records(tmp_path), epoch=0)
    annotation = dataset.source.annotations[0][0]
    annotation.bbox = (2, 4, 0.25, 0.25)
    annotation.area = 0.0625
    transform = TrainingTransform(dataset, _deim_finalization, _config(tmp_path, []), seed=0)
    raw_image, raw_target = dataset.load_item(0)
    _, target, _ = transform(raw_image, raw_target, dataset)
    assert len(target["boxes"]) == 1
    assert target["area"].tolist() == [0.25]
    assert target["labels"].tolist() == [0]


@pytest.mark.parametrize("backend", ["deimv2", "rfdetr"])
@pytest.mark.parametrize("mosaic", [False, True])
def test_native_bridges_accept_empty_crops_and_raw_mosaic_donors(
    tmp_path: Path, backend: str, mosaic: bool
) -> None:
    augmentation = importlib.import_module("albumentations")
    operation = (
        augmentation.Mosaic(
            target_size=(32, 64),
            cell_shape=(16, 32),
            center_range=(0.5, 0.5),
            fit_mode="contain",
            metadata_key="donors",
            p=1,
        )
        if mosaic
        else augmentation.Crop(x_min=16, y_min=0, x_max=32, y_max=16)
    )
    config = _config(tmp_path, [operation])
    records = _records(tmp_path)
    if backend == "deimv2":
        from clearml_yolo.adapters.deim.transforms import TrainingTransform

        deim = _DeimRawDataset(records, epoch=0)
        transform = TrainingTransform(deim, _deim_finalization, config, seed=0)
        raw_image, raw_target = deim.load_item(0)
        image, target, _ = transform(raw_image, raw_target, deim)
        assert image.shape == (3, 32, 64)
    else:
        from clearml_yolo.adapters.rfdetr.transforms import install_training_transforms

        coco = importlib.import_module("rfdetr.datasets.coco")
        native = coco.make_coco_transforms_square_div_64(
            "train", 32, aug_config={}, scale_jitter=False
        )
        dataset = coco.CocoDetection(tmp_path, records, native, draft_size=8)
        module = SimpleNamespace(_dataset_train=dataset)
        install_training_transforms(module, config, seed=0)
        image, target = dataset[0]
        assert image.shape == (3, 32, 32)
    assert sorted(target["labels"].tolist()) == ([0, 1, 2, 3] if mosaic else [])
    assert target["boxes"].shape == (4 if mosaic else 0, 4)
    assert len(target["area"]) == len(target["iscrowd"]) == len(target["boxes"])


def test_fasterrcnn_dataloader_workers_are_reproducible(tmp_path: Path) -> None:
    from clearml_yolo.adapters.fasterrcnn.data import CocoDataset, collate_detection

    torch = importlib.import_module("torch")
    augmentation = importlib.import_module("albumentations")
    config = _config(
        tmp_path,
        [augmentation.RandomBrightnessContrast(brightness_limit=(0, 0.5), contrast_limit=0, p=1)],
    )
    dataset = CocoDataset(_records(tmp_path), tuple(map(str, range(4))), transforms=config, seed=7)

    def values() -> list[float]:
        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=1,
            num_workers=2,
            multiprocessing_context="spawn",
            collate_fn=collate_detection,
            generator=torch.Generator().manual_seed(19),
        )
        return [float(images[0].mean()) for images, _ in loader]

    first, second = values(), values()
    assert first == second
    assert len(set(first)) > 1


@pytest.mark.parametrize("variant", ["Nano", "Small", "Medium", "Large"])
def test_rfdetr_repeated_native_setup_keeps_custom_training_only(
    tmp_path: Path, variant: str
) -> None:
    from clearml_yolo.adapters.rfdetr.transforms import install_training_transforms

    config_sdk = importlib.import_module("rfdetr.config")
    training_sdk = importlib.import_module("rfdetr.training")
    augmentation = importlib.import_module("albumentations")
    for split in ("train", "valid"):
        folder = tmp_path / split
        folder.mkdir()
        _records(folder)
    model = getattr(config_sdk, f"RFDETR{variant}Config")(
        num_classes=4, pretrain_weights=None, device="cpu"
    )
    train = config_sdk.TrainConfig(
        dataset_dir=str(tmp_path),
        dataset_file="roboflow",
        class_names=list(map(str, range(4))),
        num_workers=0,
        aug_config={},
        augmentation_backend="torchvision",
        multi_scale="off",
        scale_jitter=False,
    )
    module = training_sdk.RFDETRDataModule(model, train)
    module.setup("fit")
    config = _config(tmp_path, [augmentation.HorizontalFlip(p=1)])
    validation = module._dataset_val._transforms
    install_training_transforms(module, config, seed=0)
    installed = module._dataset_train._transforms
    module.setup("fit")
    assert module._dataset_train._transforms is installed
    assert module._dataset_val._transforms is validation
    image, target = module._dataset_train[0]
    assert tuple(image.shape) == (3, model.resolution, model.resolution)
    assert target["boxes"][0].tolist() == pytest.approx([0.84375, 0.5, 0.1875, 0.5])
