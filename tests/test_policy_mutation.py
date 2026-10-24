"""Boundary cases and actionable diagnostics for offline dataset/evaluation policy."""

import pandas as pd
import pytest

from clearml_yolo.core.datasets import validate_training_box
from clearml_yolo.core.evaluation import policy


@pytest.mark.parametrize(
    ("coordinates", "reason"),
    [
        (("", "1", "2", "3"), "missing label; incomplete coordinates"),
        (("bad", "1", "2", "3"), "missing label; coordinates must be numeric"),
        (("nan", "1", "2", "3"), "missing label; coordinates must be finite"),
        (
            ("-1", "3", "2", "3"),
            (
                "missing label; box width and height must be positive; "
                "coordinates are outside image bounds 0..10 x 0..20"
            ),
        ),
    ],
)
def test_invalid_training_rows_retain_all_actionable_reasons(
    coordinates: tuple[str, str, str, str], reason: str
) -> None:
    assert validate_training_box("", coordinates, 10, 20) == (None, reason)


def test_threshold_endpoints_are_valid_and_preserve_exact_values() -> None:
    assert policy.validate_thresholds({"a": 0, "b": 1, "c": 0.37123}, ["b", "a"]) == {
        "a": 0.0, "b": 1.0, "c": 0.37123,
    }


def test_class_vocabulary_excludes_missing_values_but_retains_lexical_labels() -> None:
    truth = pd.DataFrame({"instance_label": ["z", None, 7, "NA", "None", 7, "a"]})
    assert policy.classes_from_ground_truth(truth) == ["7", "NA", "None", "a", "z"]
    assert policy.classes_from_ground_truth(truth.iloc[:0]) == []
    with pytest.raises(ValueError, match=r"^Ground truth is missing the 'instance_label' column$"):
        policy.classes_from_ground_truth(pd.DataFrame())


@pytest.mark.parametrize("columns", [[], ["image_name"], ["split"]])
def test_split_membership_requires_both_identity_columns(columns: list[str]) -> None:
    with pytest.raises(ValueError, match="membership column") as error:
        policy.validate_split_membership(pd.DataFrame(columns=columns))
    expected = {
        (): "['image_name', 'split']", ("image_name",): "['split']", ("split",): "['image_name']",
    }
    assert str(error.value) == "Ground truth is missing membership column(s): " + expected[
        tuple(columns)
    ]


def test_split_membership_allows_duplicates_within_split_and_training_membership() -> None:
    policy.validate_split_membership(pd.DataFrame({
        "image_name": ["v", "v", "t", "t"], "split": ["val", "val", "train", "test"],
    }))
    with pytest.raises(ValueError, match="overlapping image_name") as error:
        policy.validate_split_membership(pd.DataFrame({
            "image_name": ["z", 7, "z", 7], "split": ["val", "test", "test", "val"],
        }))
    assert str(error.value) == (
        "A logical image cannot belong to both val and test; overlapping image_name(s): ['7', 'z']"
    )


@pytest.mark.parametrize("mode", [None, "name"])
def test_canonical_prediction_names_accept_explicit_and_default_modes(mode: str | None) -> None:
    truth = pd.DataFrame({"image_name": ["a.jpg", "b.jpg"]})
    policy.validate_prediction_identity(truth, truth.iloc[:1], image_name=mode)


@pytest.mark.parametrize("mode", ["stem", "path"])
def test_identity_validation_rejects_export_only_naming_before_matching(mode: str) -> None:
    truth = pd.DataFrame({"image_name": ["a.jpg"]})
    with pytest.raises(ValueError, match="raw prediction export") as error:
        policy.validate_prediction_identity(truth, truth, image_name=mode)
    assert str(error.value) == (
        "Comparison and evaluation require image_name='name'; "
        f"{mode!r} is supported only for raw prediction export"
    )


@pytest.mark.parametrize(("index", "label"), [(0, "Ground truth"), (1, "Predictions")])
@pytest.mark.parametrize("invalid", [None, "", "missing-column"])
def test_prediction_identity_reports_which_input_has_missing_names(
    index: int, label: str, invalid: str | None
) -> None:
    frames = [pd.DataFrame({"image_name": ["a.jpg"]}) for _ in range(2)]
    frames[index] = pd.DataFrame({"image_name": [invalid]})
    if invalid == "missing-column":
        frames[index] = pd.DataFrame({"other": ["a.jpg"]})
    with pytest.raises(ValueError, match=label) as error:
        policy.validate_prediction_identity(*frames)
    reason = (
        "is missing the 'image_name' column" if invalid == "missing-column"
        else "contains empty canonical image names"
    )
    assert str(error.value) == f"{label} {reason}"


def test_unknown_prediction_diagnostic_lists_the_actual_sorted_names() -> None:
    with pytest.raises(ValueError, match="outside canonical") as error:
        policy.validate_prediction_identity(
            pd.DataFrame({"image_name": ["known.jpg"]}),
            pd.DataFrame({"image_name": ["z.jpg", "known.jpg", "a.jpg"]}),
        )
    assert str(error.value) == (
        "Prediction image_name values are outside canonical ground-truth membership: "
        "['a.jpg', 'z.jpg']; evaluation requires image_name='name'"
    )
