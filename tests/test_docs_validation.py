"""Preview reports pure request errors without evaluating resolver or runtime effects."""

import pytest
from omegaconf import OmegaConf

from clearml_yolo.core.documentation import PreviewRequest
from clearml_yolo.entrypoints.documentation.preview import preview
from clearml_yolo.entrypoints.documentation.validation import schema_errors


@pytest.mark.parametrize(
    ("command", "overrides", "message"),
    [
        ("pipeline", ["skip_train=perhaps"], "skip_train"),
        ("pipeline", ["skip_predict=null"], "skip_predict"),
        ("train", ["dataset_format=unknown"], "dataset_format"),
        ("predict", ["splits=3"], "splits"),
        ("predict", ["image_name=unknown"], "image_name"),
        ("compare", ["q=10"], "q"),
        ("compare", ["bootstrap_iterations=0"], "bootstrap_iterations"),
        ("compare", ["seed=-1"], "seed"),
        ("compare", ["inference.reuse_existing=perhaps"], "reuse_existing"),
        ("compare", ["inference.image_name=path"], "image_name"),
        ("pipeline", ["compare.q=-1"], "q"),
        ("pipeline", ["compare.bootstrap_iterations=0"], "bootstrap_iterations"),
        ("pipeline", ["metrics.calibration_split=test"], "calibration_split"),
        ("metrics", ["calibration_split=test"], "calibration_split"),
        ("ground_truth", ["test_fraction=1"], "test_fraction"),
        ("train", ["ground_truth=123"], "ground_truth"),
        ("train", ["clearml=null"], "clearml"),
        ("train", ["ground_truth=''"], "ground_truth"),
    ],
)
def test_known_invalid_wrapper_settings_are_reported(
    command: str, overrides: list[str], message: str
) -> None:
    result = preview(PreviewRequest(command=command, overrides=overrides))
    assert not result.errors
    assert message in "\n".join(result.jobs[0].errors)


@pytest.mark.parametrize(
    ("command", "overrides", "message"),
    [
        ("train", ["model=rfdetr/small", "ultralytics.epochs=2"], "inactive"),
        ("predict", ["model=fcos/resnet50_fpn", "ultralytics_predict.batch=3"], "inactive"),
        ("train", ["model.train.epochs=2"], "inactive"),
        ("predict", ["model.predict.batch=2"], "inactive"),
        ("export", ["model=rfdetr/small"], "Faster R-CNN"),
    ],
)
def test_backend_and_inactive_group_errors_are_reported(
    command: str, overrides: list[str], message: str
) -> None:
    result = preview(PreviewRequest(command=command, overrides=overrides))
    assert not result.errors
    assert message in "\n".join(result.jobs[0].errors)


@pytest.mark.parametrize(
    "override",
    [
        "clearml._target_=os.system",
        "metrics.evaluation._target_=os.system",
        "compare.baseline_model._target_=os.system",
        "+model._target_=os.system",
    ],
)
def test_configuration_target_replacement_is_reported_without_instantiation(override: str) -> None:
    result = preview(PreviewRequest(command="pipeline", overrides=[override]))
    assert not result.errors
    assert "target" in "\n".join(result.jobs[0].errors).lower()


def test_unresolved_leaf_does_not_hide_independent_pydantic_error() -> None:
    errors = schema_errors(
        {
            "model": {
                "backend": "rfdetr",
                "preset": "small",
                "train": {"device": "${oc.env:DEVICE}", "epochs": 0},
            }
        },
        "train",
    )
    assert "epochs" in "\n".join(errors)
    assert "DEVICE" not in "\n".join(errors)


def test_unresolved_native_leaf_does_not_hide_independent_native_error() -> None:
    result = preview(
        PreviewRequest(overrides=["ultralytics.device=${oc.env:DEVICE}", "ultralytics.epochs=0"])
    )
    assert not result.errors
    assert "epochs" in "\n".join(result.jobs[0].errors)
    assert "DEVICE" not in "\n".join(result.jobs[0].errors)


def test_validation_never_invokes_resolvers_and_retains_other_checks() -> None:
    def forbidden() -> str:
        pytest.fail("Schema checking evaluated a resolver")

    OmegaConf.register_new_resolver("docs_validation_forbidden", forbidden)
    try:
        result = preview(
            PreviewRequest(
                command="pipeline",
                overrides=[
                    "skip_train=${docs_validation_forbidden:}",
                    "skip_predict=perhaps",
                    "clearml.output_uri=${docs_validation_forbidden:}",
                    "clearml.tags=3",
                ],
            )
        )
        assert not result.errors
        errors = "\n".join(result.jobs[0].errors)
        assert "skip_predict" in errors
        assert "tags" in errors
        assert "skip_train" not in errors
        assert "docs_validation_forbidden" not in errors
    finally:
        OmegaConf.clear_resolver("docs_validation_forbidden")


@pytest.mark.parametrize(
    ("command", "overrides"),
    [
        ("pipeline", ["skip_train=true", "weights=missing.pt"]),
        ("train", ["model=rfdetr/small", "model.train.epochs=2"]),
        ("predict", ["splits=null", "image_name=path"]),
        ("compare", ["q=0", "bootstrap_iterations=1"]),
        ("compare", ["q=1"]),
        ("compare", ["seed=null"]),
        ("pipeline", ["weights=${oc.env:OPTIONAL_WEIGHTS}"]),
        ("ground_truth", ["test_fraction=0"]),
        ("train", ["transforms=albumentations", "transforms.pipeline_file=/not/opened.json"]),
    ],
)
def test_valid_shapes_and_boundary_values_are_preserved(command: str, overrides: list[str]) -> None:
    result = preview(PreviewRequest(command=command, overrides=overrides))
    assert not result.errors
    assert not result.jobs[0].errors
