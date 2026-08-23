"""A custom albumentations pipeline: the JSON round-trip and the hyperparameters it replaces.

Albumentations is a real dependency of this project and needs neither a GPU nor torch, so
the loading tests write and read genuine pipeline files rather than stubbing the library —
a stub would agree with whatever ``load_augmentations`` did and prove nothing about the
serialisation format the file actually holds.

``replace_duplicated_augmentations`` never touches the disk: what it reads is the composed
``augmentations`` *path*, before the run turns it into transforms, so its tests name a file
that need not exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import albumentations as A
import pytest

from clearml_yolo.augment import (
    KEPT_WITH_CUSTOM_PIPELINE,
    MOSAIC_DEPENDENT_HYPERPARAMETER,
    MOSAIC_SCHEDULE_HYPERPARAMETER,
    REPLACED_BY_CUSTOM_PIPELINE,
    load_augmentations,
    replace_duplicated_augmentations,
)
from clearml_yolo.configs import packaged_ultralytics_params

PIPELINE_PATH = "augmentations.json"

# The packaged train defaults these tests measure "chosen by the caller" against, written
# out here so a test says what it means. `test_the_replaced_hyperparameters_are_real_keys`
# below is what keeps this in step with the file itself.
PACKAGED: dict[str, Any] = {
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "bgr": 0.0,
    "degrees": 0.0,
    "translate": 0.1,
    "shear": 0.0,
    "perspective": 0.0,
    "flipud": 0.0,
    "fliplr": 0.5,
    "scale": 0.5,
    "close_mosaic": 10,
    "mosaic": 1.0,
    "mixup": 0.0,
    "cutmix": 0.0,
    "augmentations": None,
    "epochs": 100,
}


def composed(**overrides: Any) -> dict[str, Any]:
    """One stage's fully composed block: the packaged defaults with the caller's word on top."""
    return {**PACKAGED, **overrides}


def with_pipeline(**overrides: Any) -> dict[str, Any]:
    """The same, for a run that named an albumentations JSON file."""
    return composed(augmentations=PIPELINE_PATH, **overrides)


@pytest.fixture
def pipeline_json(tmp_path: Path) -> Path:
    """A pixel transform and a spatial one, saved the way albumentations' own A.save writes."""
    pipeline = A.Compose(
        [A.RandomBrightnessContrast(p=0.3), A.HorizontalFlip(p=0.5)],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )
    destination = tmp_path / PIPELINE_PATH
    A.save(pipeline, str(destination), data_format="json")
    return destination


def test_no_path_leaves_ultralytics_own_augmentations_alone() -> None:
    """Null is the shipped default, and it has to mean "ultralytics decides its own
    augmentations", never "train this run without any"."""
    assert load_augmentations(None) is None


def test_a_missing_file_fails_loudly_and_names_the_path(tmp_path: Path) -> None:
    """A mistyped path that trained silently without the pipeline would waste the whole run."""
    absent = tmp_path / "absent.json"

    expected = r"Albumentations pipeline not found: .*absent\.json"
    with pytest.raises(FileNotFoundError, match=expected):
        load_augmentations(absent)


def test_the_transforms_are_returned_as_a_list_in_order(pipeline_json: Path) -> None:
    """Ultralytics wraps what it is handed in its own Compose with the yolo bbox_params.

    Returning the Compose instead of its transforms would nest one Compose inside another
    and detach that bbox handling, so the boxes would stop following a spatial transform.
    """
    transforms = load_augmentations(pipeline_json)

    assert transforms is not None
    assert not isinstance(transforms, A.Compose)
    assert [type(transform).__name__ for transform in transforms] == [
        "RandomBrightnessContrast",
        "HorizontalFlip",
    ]


def test_a_path_given_as_a_string_loads_too(pipeline_json: Path) -> None:
    """The composed value arrives from YAML as a string; only the loader knows about Path."""
    transforms = load_augmentations(str(pipeline_json))

    assert transforms is not None
    assert [type(transform).__name__ for transform in transforms] == [
        "RandomBrightnessContrast",
        "HorizontalFlip",
    ]


def test_a_nested_transform_keeps_its_wrapper(tmp_path: Path) -> None:
    """Ultralytics decides spatial-or-not by walking the pipeline for a DualTransform at any
    depth, so flattening a OneOf here would change which branch of that check a run takes."""
    pipeline = A.Compose([A.OneOf([A.Rotate(p=1.0), A.Affine(p=1.0)], p=1.0)])
    destination = tmp_path / "nested.json"
    A.save(pipeline, str(destination), data_format="json")

    transforms = load_augmentations(destination)

    assert transforms is not None
    assert [type(transform).__name__ for transform in transforms] == ["OneOf"]
    assert len(transforms[0].transforms) == 2


def test_the_transforms_survive_the_ddp_serialisation_round_trip(pipeline_json: Path) -> None:
    """Ultralytics ships the override to its DDP children through A.to_dict/A.from_dict.

    A transform that cannot make that trip trains on one card and dies on two.
    """
    transforms = load_augmentations(pipeline_json)
    assert transforms is not None

    rebuilt = [A.from_dict(A.to_dict(transform)) for transform in transforms]

    assert [type(transform).__name__ for transform in rebuilt] == [
        type(transform).__name__ for transform in transforms
    ]


def test_an_empty_pipeline_loads_as_nothing_rather_than_an_empty_list(tmp_path: Path) -> None:
    """An empty list would replace ultralytics' own augmentation block with nothing at all,
    which is a silent way to train unaugmented; None leaves that block in place."""
    destination = tmp_path / "empty.json"
    A.save(A.Compose([]), str(destination), data_format="json")

    assert load_augmentations(destination) is None


def test_without_a_pipeline_the_block_is_handed_back_untouched() -> None:
    """Every train run composes through this hook, so anything it changes without a pipeline
    named is a change to the default training regime of the whole project."""
    block = composed(fliplr=0.9, degrees=10.0, close_mosaic=5, scale=0.7)
    before = dict(block)

    assert replace_duplicated_augmentations(block, PACKAGED) == before
    assert block == before


def test_a_pipeline_switches_off_the_augmentations_it_duplicates() -> None:
    """Each of these runs before or after the custom block in ultralytics' own stack, so
    leaving one enabled augments a second time an image the JSON already augmented."""
    resolved = replace_duplicated_augmentations(with_pipeline(), PACKAGED)

    assert {name: resolved[name] for name in REPLACED_BY_CUSTOM_PIPELINE} == dict.fromkeys(
        REPLACED_BY_CUSTOM_PIPELINE, 0.0
    )


def test_the_path_itself_travels_on() -> None:
    """The run pops it just before calling ultralytics; dropping it here would leave nothing
    to load and the pipeline would never reach training."""
    resolved = replace_duplicated_augmentations(with_pipeline(), PACKAGED)

    assert resolved["augmentations"] == PIPELINE_PATH


def test_a_parameter_that_is_not_an_augmentation_is_left_alone() -> None:
    """The hook rewrites one neighbourhood of the block, not the block."""
    resolved = replace_duplicated_augmentations(with_pipeline(epochs=7), PACKAGED)

    assert resolved["epochs"] == 7


def test_scale_survives_because_mosaic_needs_it_to_resample_the_canvas() -> None:
    """RandomPerspective is what fits the double-sized mosaic canvas back into imgsz, so
    zeroing `scale` under a running mosaic quietly demotes the mosaic to a centre crop."""
    resolved = replace_duplicated_augmentations(with_pipeline(mosaic=1.0), PACKAGED)

    assert resolved[MOSAIC_DEPENDENT_HYPERPARAMETER] == 0.5


def test_the_close_mosaic_schedule_goes_while_scale_is_load_bearing() -> None:
    """close_mosaic rebuilds the transforms with mosaic at zero and everything else untouched,
    which would leave `scale` running as a bare random zoom for the final epochs."""
    resolved = replace_duplicated_augmentations(with_pipeline(mosaic=1.0), PACKAGED)

    assert resolved[MOSAIC_SCHEDULE_HYPERPARAMETER] == 0
    # close_mosaic is an int-only ultralytics argument and a float would be rejected.
    assert isinstance(resolved[MOSAIC_SCHEDULE_HYPERPARAMETER], int)


def test_a_null_mosaic_counts_as_the_mosaic_ultralytics_runs_by_default() -> None:
    """Null in a parameter file means "leave ultralytics' own default alone", and that default
    is a mosaic on every sample — reading it as off would zero `scale` under a running mosaic."""
    resolved = replace_duplicated_augmentations(with_pipeline(mosaic=None), PACKAGED)

    assert resolved[MOSAIC_DEPENDENT_HYPERPARAMETER] == 0.5
    assert resolved[MOSAIC_SCHEDULE_HYPERPARAMETER] == 0


def test_scale_is_switched_off_once_no_mosaic_needs_it() -> None:
    """With mosaic off `scale` is nothing but a random zoom stacked on the custom pipeline."""
    resolved = replace_duplicated_augmentations(with_pipeline(mosaic=0.0), PACKAGED)

    assert resolved[MOSAIC_DEPENDENT_HYPERPARAMETER] == 0.0


def test_the_close_mosaic_schedule_is_harmless_once_mosaic_is_off() -> None:
    """`scale` is already zero there, so the rebuild the schedule triggers changes nothing and
    the caller's schedule need not be taken away."""
    resolved = replace_duplicated_augmentations(with_pipeline(mosaic=0.0, close_mosaic=5), PACKAGED)

    assert resolved[MOSAIC_SCHEDULE_HYPERPARAMETER] == 5


def test_the_multi_image_augmentations_are_kept_as_configured() -> None:
    """Mosaic and friends stitch several images together before the custom pipeline ever sees
    a sample, and no albumentations transform can express that.

    The two copy-paste keys are commented out of the detection parameter file, so this is the
    only place that says what becomes of them if a stage ever carries them.
    """
    requested: dict[str, Any] = {"mosaic": 0.8, "mixup": 0.5, "cutmix": 0.4, "copy_paste": 0.3}
    requested["copy_paste_mode"] = "mixup"

    resolved = replace_duplicated_augmentations(with_pipeline(**requested), PACKAGED)

    assert {name: resolved[name] for name in KEPT_WITH_CUSTOM_PIPELINE} == requested


def test_an_augmentation_the_caller_asked_for_is_refused_rather_than_overruled() -> None:
    """Zeroing a value somebody wrote on the command line would train a regime nobody chose
    and say nothing about it."""
    with pytest.raises(ValueError, match="fliplr"):
        replace_duplicated_augmentations(with_pipeline(fliplr=0.9), PACKAGED)


def test_every_refused_augmentation_is_named_at_once_and_in_order() -> None:
    """One message a caller can act on beats fixing one key per failed run."""
    block = with_pipeline(fliplr=0.9, degrees=10.0)

    with pytest.raises(ValueError, match=r"degrees, fliplr"):
        replace_duplicated_augmentations(block, PACKAGED)


def test_a_close_mosaic_schedule_is_refused_while_scale_is_load_bearing() -> None:
    """It is the one key here that is taken away for the schedule it runs rather than for an
    image it augments, and a caller who named one still has to be told."""
    with pytest.raises(ValueError, match=MOSAIC_SCHEDULE_HYPERPARAMETER):
        replace_duplicated_augmentations(with_pipeline(mosaic=1.0, close_mosaic=5), PACKAGED)


def test_scale_is_refused_only_once_mosaic_no_longer_needs_it() -> None:
    """It is kept while mosaic runs, so it is not a value being overruled there and must not
    be refused; with mosaic off it is switched off and the same rule applies as anywhere."""
    kept = replace_duplicated_augmentations(with_pipeline(mosaic=1.0, scale=0.7), PACKAGED)
    assert kept[MOSAIC_DEPENDENT_HYPERPARAMETER] == 0.7

    with pytest.raises(ValueError, match=MOSAIC_DEPENDENT_HYPERPARAMETER):
        replace_duplicated_augmentations(with_pipeline(mosaic=0.0, scale=0.7), PACKAGED)


def test_a_value_the_caller_switched_off_by_hand_is_not_a_conflict() -> None:
    """Asking for no horizontal flip and getting no horizontal flip is agreement, not a clash."""
    resolved = replace_duplicated_augmentations(with_pipeline(fliplr=0.0), PACKAGED)

    assert resolved["fliplr"] == 0.0


def test_a_value_equal_to_the_packaged_default_was_chosen_by_nobody() -> None:
    """Every composed block carries the whole of the defaults, so treating those as the
    caller's word would refuse every run that names a pipeline at all."""
    resolved = replace_duplicated_augmentations(with_pipeline(fliplr=PACKAGED["fliplr"]), PACKAGED)

    assert resolved["fliplr"] == 0.0


def test_the_replaced_hyperparameters_are_real_keys_of_the_packaged_train_file() -> None:
    """A key renamed in conf/ultralytics/train.yaml but not here would be compared against a
    packaged default that is not there: it would read as caller-chosen and refuse every run
    that names a pipeline at all."""
    packaged = packaged_ultralytics_params("train")
    named = {
        *REPLACED_BY_CUSTOM_PIPELINE,
        MOSAIC_DEPENDENT_HYPERPARAMETER,
        MOSAIC_SCHEDULE_HYPERPARAMETER,
        "mosaic",
        "augmentations",
    }

    assert named <= set(packaged)
    assert {name: PACKAGED[name] for name in named} == {name: packaged[name] for name in named}
