"""Stage contracts validate without changing source populations or lineage."""

import numpy as np
import pandas as pd
import pytest

from clearml_yolo.core import validation


def frame(*, prediction: bool = False) -> pd.DataFrame:
    result = pd.DataFrame({
        "image_name": ["001.png", "empty.png"],
        "instance_label": [7, None],
        "bbox_x_tl": [0.0, np.nan], "bbox_y_tl": [0.0, np.nan],
        "bbox_x_br": [10.0, np.nan], "bbox_y_br": [10.0, np.nan],
        "split": ["test", "test"], "image_path": ["001.png", "empty.png"],
        "source_row_id": ["gt:17", "gt:20"], "object_id": ["original", "background"],
        "extra": ["untouched", "retained"],
    }, index=[17, 20])
    if prediction:
        result = result.iloc[:1].copy()
        result["confidence"] = 0.8
        result["source_row_id"] = "pred:17"
    return result


@pytest.mark.parametrize("stage", ["raw_ground_truth", "prepared_ground_truth"])
def test_ground_truth_retains_background_numeric_labels_extra_columns_and_index(stage: str) -> None:
    original = frame()
    result = validation.validate_dataframe(original, stage)
    pd.testing.assert_frame_equal(result, original)
    pd.testing.assert_frame_equal(original, frame())


def test_lexical_raw_ground_truth_retains_recoverable_invalid_boxes() -> None:
    original = frame().astype(object)
    original.loc[17, "bbox_x_tl"] = "not numeric"
    original.loc[17, "instance_label"] = "01"
    original.loc[20, ["instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]] = ""
    pd.testing.assert_frame_equal(validation.validate_dataframe(original, "raw_ground_truth"),
                                  original)


@pytest.mark.parametrize("coordinate", [0, -1, np.nan, np.inf, "malformed"])
def test_raw_predictions_retain_geometry_for_explicit_filtering(coordinate: float | str) -> None:
    original = frame(prediction=True).astype(object)
    original.loc[17, "bbox_x_br"] = coordinate
    pd.testing.assert_frame_equal(validation.validate_dataframe(original, "raw_predictions"),
                                  original)
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "evaluation_predictions")


@pytest.mark.parametrize("stage", ["raw_predictions", "evaluation_predictions"])
@pytest.mark.parametrize("confidence", [-0.1, 1.1, np.inf, np.nan, "bad"])
def test_prediction_confidence_failure_is_fatal_in_every_stage(stage: str,
                                                             confidence: float | str) -> None:
    original = frame(prediction=True).astype(object)
    original.loc[17, "confidence"] = confidence
    with pytest.raises(validation.DataFrameValidationError) as error:
        validation.validate_dataframe(original, stage)
    assert error.value.stage == stage
    assert error.value.findings
    assert any(finding.column == "confidence" for finding in error.value.findings)


def test_validation_reports_original_index_and_missing_columns_without_mutation() -> None:
    original = frame(prediction=True)
    original.loc[17, "confidence"] = 1.5
    before = original.copy(deep=True)
    with pytest.raises(validation.DataFrameValidationError) as error:
        validation.validate_dataframe(original, "raw_predictions")
    assert any(finding.row == 17 for finding in error.value.findings)
    pd.testing.assert_frame_equal(original, before)
    with pytest.raises(validation.DataFrameValidationError) as missing:
        validation.validate_dataframe(original.drop(columns="image_name"), "raw_predictions")
    assert any(finding.column == "image_name" for finding in missing.value.findings)


def test_prepared_ground_truth_rejects_partial_background_and_reserved_label() -> None:
    original = frame()
    original.loc[20, "bbox_x_tl"] = 1
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "prepared_ground_truth")
    original = frame().astype(object)
    original.loc[17, "instance_label"] = "background"
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "prepared_ground_truth")


def test_prepared_frames_require_unique_nonmissing_source_ids_and_row_indices() -> None:
    original = frame()
    original["source_row_id"] = "same"
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "prepared_ground_truth")
    original = frame()
    original.index = [17, 17]
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "prepared_ground_truth")


def test_publication_predictions_preserve_collapsed_boxes_but_truth_rejects_them() -> None:
    original = frame(prediction=True)
    original.loc[17, "bbox_x_br"] = 0
    pd.testing.assert_frame_equal(
        validation.validate_dataframe(original, "publication_predictions"), original)
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "publication_ground_truth")


def test_publication_ground_truth_preserves_duplicate_boxes_and_unicode_labels() -> None:
    original = frame().iloc[:1].copy()
    original["instance_label"] = "Пятна Эмульсии"
    original = pd.concat([original, original]).drop(columns="source_row_id")
    pd.testing.assert_frame_equal(
        validation.validate_dataframe(original, "publication_ground_truth"), original)


def test_results_retain_excluded_geometry_and_validate_status_and_relationship_json() -> None:
    original = frame(prediction=True)
    original.loc[17, "bbox_x_br"] = 0
    original = original.assign(row_type="predict", evaluation_status="excluded",
                               matches_pre_threshold="[]", matches_post_threshold="[]")
    pd.testing.assert_frame_equal(validation.validate_dataframe(original, "results"), original)
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original.assign(evaluation_status="unknown"), "results")
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original.assign(matches_post_threshold="{}"), "results")


def test_prepared_ground_truth_checks_image_split_ownership() -> None:
    original = frame()
    original.loc[20, "image_name"] = "001.png"
    original.loc[20, "split"] = "val"
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(original, "prepared_ground_truth")


def test_schema_configuration_never_coerces_drops_rows_or_filters_columns() -> None:
    for stage in validation.ValidationStage:
        schema = validation.schema_for(stage)
        assert schema.coerce is False
        assert schema.strict is False
        assert schema.drop_invalid_rows is False


def test_training_schema_rejects_duplicate_boxes_and_bounds_without_dropping_rows() -> None:
    original = frame().assign(width=100, height=50)
    pd.testing.assert_frame_equal(
        validation.validate_dataframe(original, "training_ground_truth"), original)
    outside = original.copy()
    outside.loc[17, "bbox_x_br"] = 101
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(outside, "training_ground_truth")
    duplicate = pd.concat([original.iloc[:1], original.iloc[:1]], ignore_index=True)
    duplicate = duplicate.drop(columns="source_row_id")
    with pytest.raises(validation.DataFrameValidationError):
        validation.validate_dataframe(duplicate, "training_ground_truth")
