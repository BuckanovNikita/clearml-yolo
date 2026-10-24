"""Real Albumentations geometry and portable Mosaic operate on aligned targets."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import albumentations
import numpy as np
import pytest


def _snapshot(transform: Any) -> Any:
    from clearml_yolo.core.transforms import TransformSnapshot, pipeline_digest

    document = albumentations.to_dict(transform)
    return TransformSnapshot(
        pipeline=document, sha256=pipeline_digest(document), source="test.json"
    )


def _sample(index: int = 0, *, empty: bool = False) -> Any:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample

    return DetectionSample(
        image=np.full((32, 32, 3), 40 * index, dtype=np.uint8),
        boxes=np.array([] if empty else [[8, 8, 24, 24]], dtype=np.float32).reshape(-1, 4),
        labels=np.array([] if empty else [index + 1], dtype=np.int64),
        instance_ids=np.array([] if empty else [0], dtype=np.int64),
        iscrowd=np.array([] if empty else [index % 2], dtype=np.int64),
    )


def _apply(transform: Any, sample: Any, *, size: int = 1, loader: Any = None) -> Any:
    from clearml_yolo.adapters.augmentation.pipeline import TrainingPipeline

    pipeline = TrainingPipeline(_snapshot(transform), seed=7)
    return pipeline.apply(sample, index=0, size=size, load_sample=loader or _sample, seed=7)


def test_spatial_crop_retains_transformed_empty_sample() -> None:
    sample = _sample()
    sample.boxes[:] = [[0, 0, 4, 4]]
    transform = albumentations.Compose(
        [albumentations.Crop(x_min=16, y_min=16, x_max=32, y_max=32, p=1)],
        bbox_params=albumentations.BboxParams(format="pascal_voc", label_fields=["labels"]),
    )
    result = _apply(transform, sample)
    assert result.image.shape == (16, 16, 3)
    assert result.boxes.shape == (0, 4)
    assert result.labels.shape == result.instance_ids.shape == result.iscrowd.shape == (0,)
    assert sample.image.shape == (32, 32, 3)
    np.testing.assert_array_equal(sample.boxes, [[0, 0, 4, 4]])


@pytest.mark.parametrize("bbox_format", ["pascal_voc", "coco", "yolo", "albumentations"])
def test_bbox_formats_preserve_geometry_and_metadata(bbox_format: str) -> None:
    sample = _sample()
    sample.boxes[:] = [[1, 2, 9, 12]]
    sample.instance_ids[:] = [2**40]
    transform = albumentations.Compose(
        [albumentations.HorizontalFlip(p=1)],
        bbox_params=albumentations.BboxParams(format=bbox_format, label_fields=["category"]),
    )
    result = _apply(transform, sample)
    np.testing.assert_allclose(result.boxes, [[23, 2, 31, 12]], atol=1e-5)
    np.testing.assert_array_equal(result.labels, sample.labels)
    np.testing.assert_array_equal(result.instance_ids, sample.instance_ids)
    np.testing.assert_array_equal(result.iscrowd, sample.iscrowd)


def test_pipeline_supplies_missing_bbox_processor_and_preserves_rgb() -> None:
    sample = _sample()
    sample.image[:, :, 0] = 255
    result = _apply(albumentations.Compose([albumentations.Resize(height=16, width=16)]), sample)
    np.testing.assert_allclose(result.boxes, [[4, 4, 12, 12]])
    assert (result.image[:, :, 0] == 255).all()
    assert (result.image[:, :, 1:] == 0).all()


@pytest.mark.parametrize(
    ("empty_primary", "empty_donors"), [(False, False), (True, False), (True, True)]
)
def test_mosaic_tracks_donor_classes_crowd_and_unique_instances(
    empty_primary: bool, empty_donors: bool
) -> None:
    loaded: list[int] = []

    def load(index: int) -> Any:
        loaded.append(index)
        return _sample(index, empty=empty_donors)

    transform = albumentations.Compose(
        [
            albumentations.Mosaic(
                target_size=(64, 64),
                cell_shape=(32, 32),
                center_range=(0.5, 0.5),
                fit_mode="contain",
                metadata_key="training_donors",
                p=1,
            )
        ],
        bbox_params=albumentations.BboxParams(format="pascal_voc", label_fields=["labels"]),
    )
    result = _apply(transform, _sample(empty=empty_primary), size=4, loader=load)
    assert sorted(loaded) == [1, 2, 3]
    assert result.image.shape == (64, 64, 3)
    expected = ([] if empty_primary else [1]) + ([] if empty_donors else [2, 3, 4])
    assert sorted(result.labels.tolist()) == expected
    assert len(set(result.instance_ids.tolist())) == len(result.labels)
    for label, crowd in zip(result.labels, result.iscrowd, strict=True):
        assert crowd == (label - 1) % 2


def test_mosaic_nondefault_grid_samples_full_donor_population() -> None:
    loaded: list[int] = []

    def load(index: int) -> Any:
        loaded.append(index)
        return _sample(index)

    transform = albumentations.Compose(
        [
            albumentations.Mosaic(
                grid_yx=(2, 3),
                target_size=(64, 96),
                cell_shape=(32, 32),
                center_range=(0.5, 0.5),
                fit_mode="contain",
                p=1,
            )
        ]
    )
    result = _apply(transform, _sample(), size=6, loader=load)
    assert sorted(loaded) == [1, 2, 3, 4, 5]
    assert sorted(result.labels.tolist()) == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize(("size", "expected"), [(1, {0}), (2, {1})])
def test_small_mosaic_populations_use_only_available_training_donors(
    size: int, expected: set[int]
) -> None:
    loaded: list[int] = []

    def load(index: int) -> Any:
        loaded.append(index)
        return _sample(index)

    transform = albumentations.Compose(
        [albumentations.Mosaic(target_size=(64, 64), cell_shape=(32, 32), p=1)]
    )
    result = _apply(transform, _sample(), size=size, loader=load)
    assert len(loaded) == 3
    assert set(loaded) == expected
    assert len(set(result.instance_ids.tolist())) == len(result.labels)


def test_disabled_mosaic_never_loads_donors() -> None:
    transform = albumentations.Compose(
        [albumentations.Mosaic(target_size=(64, 64), cell_shape=(32, 32), p=0)]
    )
    result = _apply(transform, _sample(), size=4, loader=lambda _: pytest.fail("donor read"))
    assert result.image.shape == (32, 32, 3)


def test_worker_seed_changes_are_reproducible_without_reseeding_every_image() -> None:
    from clearml_yolo.adapters.augmentation.pipeline import TrainingPipeline

    snapshot = _snapshot(albumentations.Compose([albumentations.RandomBrightnessContrast(p=1)]))

    def values(seed: int) -> list[int]:
        pipeline = TrainingPipeline(snapshot, seed=0)
        return [
            int(
                pipeline.apply(_sample(2), index=0, size=1, load_sample=_sample, seed=seed).image[
                    0, 0, 0
                ]
            )
            for _ in range(5)
        ]

    assert values(7) == values(7)
    assert len(set(values(7))) > 1
    assert values(7) != values(8)


@pytest.mark.parametrize(
    ("transform_factory", "match"),
    [
        (lambda: albumentations.Compose([albumentations.Normalize()]), "Normalize"),
        (lambda: albumentations.Compose([albumentations.ToFloat()]), "ToFloat"),
        (
            lambda: albumentations.Compose([albumentations.OneOf([albumentations.Mosaic()])]),
            "Mosaic",
        ),
        (
            lambda: albumentations.Compose(
                [albumentations.HorizontalFlip(), albumentations.Mosaic()]
            ),
            "Mosaic",
        ),
        (
            lambda: albumentations.Compose([albumentations.Mosaic(), albumentations.Mosaic()]),
            "Mosaic",
        ),
    ],
)
def test_preprocessing_and_mosaic_conflicts_fail_before_execution(
    transform_factory: Callable[[], Any], match: str
) -> None:
    from clearml_yolo.adapters.augmentation.configuration import validate_pipeline

    with pytest.raises(ValueError, match=match):
        validate_pipeline(albumentations.to_dict(transform_factory()))


def test_unknown_constructor_argument_does_not_fall_back_to_native_default() -> None:
    from clearml_yolo.adapters.augmentation.configuration import validate_pipeline

    document = albumentations.to_dict(albumentations.Compose([albumentations.HorizontalFlip()]))
    document["transform"]["transforms"][0]["probabilty"] = 0.9
    with pytest.raises(ValueError, match=r"transforms\[0\].*probabilty"):
        validate_pipeline(document)


def test_snapshot_file_errors_do_not_construct_fallback_pipeline(tmp_path: Path) -> None:
    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.core.transforms import TransformConfig

    with pytest.raises(ValueError, match=r"missing\.json"):
        resolve_transform_config(
            TransformConfig(mode="albumentations", pipeline_file=tmp_path / "missing.json")
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("__class_fullname__", "external.Compose", "external"),
        ("p", 1.5, "transform.p"),
        ("p", "often", "transform.p"),
        ("bbox_params", {"min_visibility": -0.1}, "min_visibility"),
        ("bbox_params", {"min_area": "large"}, "min_area"),
        ("bbox_params", {"clip": "false"}, "clip"),
        ("bbox_params", {"min_area": None}, "min_area"),
        ("bbox_params", [], "bbox_params"),
        ("bbox_params", {"label_fields": ""}, "label_fields"),
    ],
)
def test_malformed_compose_and_bbox_parameters_fail_early(
    field: str, value: Any, match: str
) -> None:
    from clearml_yolo.adapters.augmentation.configuration import validate_pipeline

    document = albumentations.to_dict(albumentations.Compose([]))
    document["transform"][field] = value
    with pytest.raises(ValueError, match=match):
        validate_pipeline(document)


@pytest.mark.parametrize("metadata_key", ["image", "bboxes", "class_labels", "_cy_iscrowd"])
def test_mosaic_metadata_key_must_not_overwrite_detection_fields(metadata_key: str) -> None:
    from clearml_yolo.adapters.augmentation.configuration import validate_pipeline

    document = albumentations.to_dict(
        albumentations.Compose([albumentations.Mosaic(metadata_key=metadata_key)])
    )
    with pytest.raises(ValueError, match="metadata_key"):
        validate_pipeline(document)


def test_nested_composition_preserves_probability_and_order() -> None:
    sample = _sample()
    sample.boxes[:] = [[1, 2, 9, 12]]
    transform = albumentations.Compose(
        [
            albumentations.OneOf([albumentations.HorizontalFlip(p=1)], p=1),
            albumentations.Sequential([albumentations.VerticalFlip(p=1)], p=0),
            albumentations.Resize(height=16, width=16),
        ]
    )
    result = _apply(transform, sample)
    np.testing.assert_allclose(result.boxes, [[11.5, 1, 15.5, 6]], atol=1e-5)


def test_clipping_and_filtering_keep_surviving_metadata_aligned() -> None:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample

    sample = DetectionSample(
        image=_sample().image,
        boxes=np.array([[-2, -2, 4, 4], [8, 8, 24, 24]], dtype=np.float32),
        labels=np.array([7, 9], dtype=np.int64),
        instance_ids=np.array([42, 43], dtype=np.int64),
        iscrowd=np.array([1, 0], dtype=np.int64),
    )
    result = _apply(
        albumentations.Compose(
            [albumentations.Crop(x_min=4, y_min=4, x_max=32, y_max=32)],
            bbox_params=albumentations.BboxParams(format="pascal_voc", clip=True),
        ),
        sample,
    )
    np.testing.assert_allclose(result.boxes, [[4, 4, 20, 20]])
    np.testing.assert_array_equal(result.labels, [9])
    np.testing.assert_array_equal(result.instance_ids, [43])
    np.testing.assert_array_equal(result.iscrowd, [0])


def test_disabled_root_compose_never_loads_mosaic_donors() -> None:
    transform = albumentations.Compose([albumentations.Mosaic(p=1)], p=0)
    result = _apply(transform, _sample(), size=4, loader=lambda _: pytest.fail("donor read"))
    np.testing.assert_array_equal(result.image, _sample().image)


@pytest.mark.parametrize(
    ("transform_factory", "match"),
    [
        (albumentations.MaskDropout, "target"),
        (lambda: albumentations.Pad3D(padding=1), "target"),
        (lambda: albumentations.ToGray(num_output_channels=1), "RGB"),
        (lambda: albumentations.Mosaic(metadata_key="mask"), "metadata_key"),
    ],
)
def test_unsupported_targets_fail_at_configuration_boundary(
    transform_factory: Callable[[], Any], match: str
) -> None:
    from clearml_yolo.adapters.augmentation.configuration import validate_pipeline

    document = albumentations.to_dict(albumentations.Compose([transform_factory()]))
    with pytest.raises(ValueError, match=match):
        validate_pipeline(document)


def test_mutating_snapshot_content_invalidates_runtime_replay() -> None:
    from clearml_yolo.adapters.augmentation.pipeline import TrainingPipeline

    snapshot = _snapshot(albumentations.Compose([]))
    snapshot.pipeline["__version__"] = "changed"
    with pytest.raises(ValueError, match="sha256"):
        TrainingPipeline(snapshot)
