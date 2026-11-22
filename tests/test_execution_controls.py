"""Removed scheduling controls require migration for every command schema."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - register Hydra configs
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.entrypoints.hydra import common
from clearml_yolo.entrypoints.hydra.validation import validate_command_configuration, validate_wrapper_keys


@pytest.mark.parametrize("setting", ["queue", "autogpu", "auto_gpu"])
@pytest.mark.parametrize("enabled", [True, False])
def test_direct_commands_reject_legacy_controls(setting: str, enabled: bool) -> None:
    config = OmegaConf.create({"ultralytics": {"device": "cpu"}, setting: {"enabled": enabled}})
    with pytest.raises(ValueError, match="cy-queue submit"):
        validate_wrapper_keys(config, lambda ultralytics: None)


@pytest.mark.parametrize("setting", ["queue", "autogpu", "auto_gpu"])
def test_non_model_commands_also_reject_legacy_controls(setting: str) -> None:
    config = OmegaConf.create({"predictions": "outside.csv", setting: {"enabled": False}})
    with pytest.raises(ValueError, match="saved YAML"):
        validate_wrapper_keys(config, lambda predictions: None)


def _metrics_settings(fiftyone: object) -> dict[str, object]:
    return {
        "predictions": "p.csv",
        "ground_truth": "truth.csv",
        "output_dir": None,
        "clearml": {},
        "evaluation": {},
        "fiftyone": fiftyone,
    }


def test_direct_commands_reject_null_fiftyone_with_hint() -> None:
    config = OmegaConf.create(_metrics_settings(None))
    with pytest.raises(ValueError, match=r"fiftyone=null is not supported; use fiftyone\.enabled=false"):
        validate_command_configuration(config, compute_metrics)


def test_direct_commands_accept_disabled_fiftyone_mapping() -> None:
    config = OmegaConf.create(_metrics_settings({"enabled": False}))
    validate_command_configuration(config, compute_metrics)


@pytest.mark.parametrize(
    ("name", "function", "overrides"),
    [
        ("predict", predict, ["ground_truth=truth.csv", "weights=w.pt", "fiftyone=null"]),
        ("metrics", compute_metrics, ["predictions=p.csv", "ground_truth=truth.csv", "fiftyone=null"]),
    ],
    ids=["predict", "metrics"],
)
def test_null_fiftyone_fails_before_the_task_is_created(
    monkeypatch: pytest.MonkeyPatch, name: str, function: Callable[..., Any], overrides: list[str]
) -> None:
    entered: list[str] = []

    @contextmanager
    def runtime() -> Iterator[None]:
        entered.append("runtime")
        yield

    @contextmanager
    def lifecycle() -> Iterator[bool]:
        yield False

    def invocation(*_args: Any, **_kwargs: Any) -> None:
        entered.append("invocation")
        pytest.fail("fiftyone=null must be rejected before the ClearML task is created")

    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "detector_runtime", runtime)
    monkeypatch.setattr(common, "execution_lifecycle", lifecycle)
    monkeypatch.setattr(common, "invocation", invocation)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=name, overrides=overrides)
    with pytest.raises(ValueError, match=r"fiftyone=null is not supported; use fiftyone\.enabled=false"):
        common.execute_owned(name, config, function)
    assert entered == []
