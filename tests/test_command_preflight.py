"""Invalid command configuration fails before the invocation creates its ClearML task."""

import re
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import DictConfig, OmegaConf

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - register Hydra configs
from clearml_yolo.adapters.clearml.session import RemoteReplay, _plain_config_document, sanitize_configuration
from clearml_yolo.application.use_cases.compare import compare
from clearml_yolo.application.use_cases.export import export_model
from clearml_yolo.application.use_cases.ground_truth import ground_truth
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.application.use_cases.report import report
from clearml_yolo.application.use_cases.train import train
from clearml_yolo.application.use_cases.val import validate
from clearml_yolo.entrypoints.hydra import common
from clearml_yolo.entrypoints.hydra.validation import validate_pipeline_configuration

COMMANDS: dict[str, Callable[..., Any]] = {
    "pipeline": run_pipeline,
    "train": train,
    "predict": predict,
    "val": validate,
    "metrics": compute_metrics,
    "compare": compare,
    "report": report,
    "export": export_model,
    "ground_truth": ground_truth,
}


class TaskCreated(Exception):  # noqa: N818 - a sentinel, not an error condition
    """Raised by the fake invocation: reaching it means a ClearML task would exist."""


@pytest.fixture
def owner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Replace every effect entered before or by the task-creating invocation."""
    entered: list[str] = []

    @contextmanager
    def runtime() -> Iterator[None]:
        entered.append("runtime")
        yield

    @contextmanager
    def lifecycle() -> Iterator[bool]:
        yield False

    def invocation(*_args: Any, **_kwargs: Any) -> AbstractContextManager[Any]:
        entered.append("invocation")
        raise TaskCreated

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "detector_runtime", runtime)
    monkeypatch.setattr(common, "execution_lifecycle", lifecycle)
    monkeypatch.setattr(common, "invocation", invocation)
    return entered


def _compose(name: str, overrides: list[str]) -> DictConfig:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        return compose(config_name=name, overrides=overrides)


INVALID = [
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "weights=w.pt"],
        "weights is only valid with skip_train=true; training chooses its model",
        id="pipeline-weights-without-skip-train",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.project=${oc.env:CY_HOME}/project"],
        "Native pipeline output overrides require an explicit run_dir",
        id="pipeline-native-route-without-run-dir",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.name=other"],
        "Native pipeline output overrides require an explicit run_dir",
        id="pipeline-native-name-without-run-dir",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "run_id=123"],
        "Invalid pipeline setting run_id",
        id="pipeline-numeric-run-id",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "run_dir=${oc.env:CY_HOME}/run", "dataset_cache_dir=${oc.env:CY_HOME}/run/cache"],
        "dataset_cache_dir must be outside run_dir",
        id="pipeline-cache-inside-run-dir",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.model=null"],
        "Set ultralytics.model explicitly; no training model fallback is provided",
        id="pipeline-empty-model",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.resume=true"],
        "resume is unsupported with ground_truth; use model weights to fine-tune",
        id="pipeline-resume",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "metrics.evaluation.backend=other"],
        "Frozen thresholds require the native digital-metrics backend",
        id="pipeline-evaluation-backend",
    ),
    pytest.param(
        "train",
        ["ground_truth=truth.csv", "ultralytics.model=null"],
        "Set ultralytics.model explicitly; no training model fallback is provided",
        id="train-empty-model",
    ),
    pytest.param(
        "train",
        ["ground_truth=truth.csv", "ultralytics.resume=true"],
        "resume is unsupported with ground_truth; use model weights to fine-tune",
        id="train-resume",
    ),
    pytest.param(
        "train",
        ["ground_truth=truth.csv", "ultralytics.imgsz=0"],
        "ultralytics.imgsz must contain positive integer image dimensions",
        id="train-native-value",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv"],
        "Prediction requires weights=<checkpoint> or ultralytics_predict.model",
        id="predict-no-model",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv", "model=fcos/resnet50_fpn"],
        "Prediction requires weights=<checkpoint> or ultralytics_predict.model",
        id="predict-detector-no-weights",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv", "weights=w.pt", "fiftyone.preflight_timeout_seconds=0"],
        "Input should be greater than 0",
        id="predict-fiftyone-settings",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv", "weights=w.pt", "fiftyone=null"],
        "fiftyone=null is not supported; use fiftyone.enabled=false to turn FiftyOne publication off",
        id="predict-null-fiftyone",
    ),
    pytest.param(
        "val",
        ["ground_truth=truth.csv", "model=deimv2/s"],
        "Prediction requires weights=<checkpoint> or ultralytics_predict.model",
        id="val-detector-no-weights",
    ),
    pytest.param(
        "val",
        ["ground_truth=truth.csv", "weights=w.pt", "splits=[all]"],
        "split='all' is unsupported for frozen evaluation; name concrete splits",
        id="val-all-split",
    ),
    pytest.param(
        "val",
        ["ground_truth=truth.csv", "weights=w.pt", "evaluation.matching_strategy=bad"],
        "matching_strategy",
        id="val-evaluation",
    ),
    pytest.param(
        "val",
        ["ground_truth=truth.csv", "weights=w.pt", "evaluation.backend=other"],
        "Frozen thresholds require the native digital-metrics backend",
        id="val-evaluation-backend",
    ),
    pytest.param(
        "metrics",
        ["predictions=p.csv", "ground_truth=truth.csv", "evaluation.backend=other"],
        "Frozen thresholds require the native digital-metrics backend",
        id="metrics-evaluation-backend",
    ),
    pytest.param(
        "metrics",
        ["predictions=p.csv", "ground_truth=truth.csv", "~evaluation"],
        "Required setting evaluation is missing",
        id="metrics-removed-required-evaluation",
    ),
    pytest.param(
        "metrics",
        ["predictions=p.csv", "ground_truth=truth.csv", "calibration_split=test"],
        "calibration_split must be exactly 'val'; test data must never calibrate thresholds",
        id="metrics-calibration-split",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "q=2"],
        "q must be a finite probability in [0, 1]",
        id="compare-q",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "bootstrap_iterations=0"],
        "bootstrap_iterations must be a positive integer",
        id="compare-bootstrap",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "evaluation.backend=other"],
        "Frozen thresholds require the native digital-metrics backend",
        id="compare-evaluation-backend",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "ultralytics_predict.model=m.pt"],
        "Prediction ['model'] are owned by comparison; use baseline_model/candidate_model and output_dir",
        id="compare-owned-prediction-model",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv"],
        "candidate_model is not specified",
        id="compare-default-candidate",
    ),
    pytest.param(
        "report",
        ["comparison_dir=comparison", "report_config_path=3"],
        "report_config_path must be a path string or null",
        id="report-config-path-type",
    ),
    pytest.param(
        "export",
        [],
        "ONNX export requires weights",
        id="export-missing-weights",
    ),
    pytest.param(
        "ground_truth",
        ["data_yaml=data.yaml", "test_fraction=1.5"],
        "test_fraction must be within [0.0, 1.0), got 1.5",
        id="ground-truth-test-fraction",
    ),
]


@pytest.mark.parametrize(("name", "overrides", "message"), INVALID)
def test_invalid_configuration_fails_before_the_task_exists(
    owner: list[str], name: str, overrides: list[str], message: str
) -> None:
    config = _compose(name, overrides)
    # Validators raise TypeError for a wrong value type and ValueError otherwise.
    with pytest.raises((TypeError, ValueError), match=re.escape(message)):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner == []


VALID = [
    pytest.param("pipeline", ["ground_truth=truth.csv"], id="pipeline"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "~fiftyone"], id="pipeline-removed-fiftyone"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "weights=w.pt", "skip_train=true"], id="pipeline-weights"),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "weights=w.pt", "skip_train=true", "ultralytics.model=null"],
        id="pipeline-skip-train-without-training-model",
    ),
    pytest.param("pipeline", ["ground_truth=truth.csv", "run_dir=${oc.env:CY_HOME}/run"], id="pipeline-run-dir"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "model=fasterrcnn/resnet50_fpn"], id="pipeline-detector"),
    # The direct run used skip flags only for truthiness and read model_label only
    # for a checkpoint without provenance, so loose values ran on the base commit.
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "skip_compare=1", "skip_report=1", "skip_metrics=0"],
        id="pipeline-integer-skip-flags",
    ),
    pytest.param("pipeline", ["ground_truth=truth.csv", "model_label=2024"], id="pipeline-integer-model-label"),
    # run_pipeline accepts a native name equal to the stage name it routes.
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.name=train", "ultralytics_predict.name=predict"],
        id="pipeline-stage-names-without-run-dir",
    ),
    pytest.param("train", ["ground_truth=truth.csv"], id="train"),
    pytest.param("train", ["ground_truth=truth.csv", "model=rfdetr/small"], id="train-detector"),
    pytest.param("predict", ["ground_truth=truth.csv", "weights=w.pt"], id="predict"),
    # A removed fiftyone group stays absent: the run published with defaults, as on the base commit.
    pytest.param("predict", ["ground_truth=truth.csv", "weights=w.pt", "~fiftyone"], id="predict-removed-fiftyone"),
    pytest.param("predict", ["ground_truth=truth.csv", "ultralytics_predict.model=m.pt"], id="predict-native-model"),
    pytest.param(
        "predict", ["ground_truth=truth.csv", "weights=w.pt", "model=fcos/resnet50_fpn"], id="predict-detector"
    ),
    pytest.param("val", ["ground_truth=truth.csv", "weights=w.pt"], id="val"),
    pytest.param("val", ["ground_truth=truth.csv", "weights=w.pt", "model=deimv2/s"], id="val-detector"),
    pytest.param("val", ["ground_truth=truth.csv", "weights=w.pt", "~splits"], id="val-removed-splits"),
    pytest.param("metrics", ["predictions=p.csv", "ground_truth=truth.csv"], id="metrics"),
    pytest.param(
        "metrics", ["predictions=p.csv", "ground_truth=truth.csv", "fiftyone.enabled=false"], id="metrics-no-fiftyone"
    ),
    pytest.param(
        "metrics", ["predictions=p.csv", "ground_truth=truth.csv", "~calibration_split"], id="metrics-removed-split"
    ),
    pytest.param("compare", ["ground_truth=truth.csv", "candidate_model.task_id=candidate"], id="compare"),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "~q", "~seed", "~evaluation"],
        id="compare-removed-optional-settings",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "model=fasterrcnn/resnet50_fpn"],
        id="compare-detector",
    ),
    pytest.param("report", ["comparison_dir=comparison"], id="report"),
    pytest.param("report", ["comparison_dir=comparison", "report_config_path=report.yaml"], id="report-config"),
    pytest.param("export", ["weights=w.pt"], id="export"),
    pytest.param("ground_truth", ["data_yaml=data.yaml"], id="ground-truth"),
    pytest.param("ground_truth", ["data_yaml=data.yaml", "~test_fraction"], id="ground-truth-removed-fraction"),
]


@pytest.mark.parametrize(("name", "overrides"), VALID)
def test_valid_configuration_reaches_the_task(owner: list[str], name: str, overrides: list[str]) -> None:
    config = _compose(name, overrides)
    with pytest.raises(TaskCreated):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner[-1] == "invocation"


class Published(Exception):  # noqa: N818 - a sentinel, not an error condition
    """Raised by the fake publication: the replayed configuration passed the preflight."""


@pytest.mark.parametrize(("name", "overrides"), VALID)
def test_valid_replayed_configuration_reaches_publication(
    owner: list[str], monkeypatch: pytest.MonkeyPatch, name: str, overrides: list[str]
) -> None:
    @contextmanager
    def invocation(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        owner.append("invocation")
        yield type("Task", (), {"running_locally": staticmethod(lambda: True)})()

    def publish(*_args: Any) -> None:
        raise Published

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", lambda _task, values, **_kwargs: values)
    monkeypatch.setattr(common, "publish_run_configuration", publish)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    config = _compose(name, overrides)
    with pytest.raises(Published):
        common.execute_owned(name, config, COMMANDS[name])


def test_replayed_configuration_is_checked_again_before_publication(
    owner: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    published: list[Any] = []

    @contextmanager
    def invocation(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        owner.append("invocation")
        yield type("Task", (), {"running_locally": staticmethod(lambda: False)})()

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(
        common, "replay_configuration", lambda _task, values, **_kwargs: values | {"calibration_split": "test"}
    )
    monkeypatch.setattr(common, "publish_run_configuration", lambda *args: published.append(args))
    monkeypatch.setattr(common, "initialize_naming", lambda _task: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    config = _compose("metrics", ["predictions=p.csv", "ground_truth=truth.csv"])
    with pytest.raises(ValueError, match="calibration_split must be exactly 'val'"):
        common.execute_owned("metrics", config, compute_metrics)
    assert owner[-1] == "invocation"
    assert published == []


QUEUE_STRICT = [
    pytest.param(["skip_compare=1"], "Invalid pipeline setting skip_compare", id="integer-skip-flag"),
    pytest.param(["model_label=2024"], "Invalid pipeline setting model_label", id="integer-model-label"),
    pytest.param(["ultralytics.name=train"], "Native pipeline output overrides require an explicit run_dir", id="name"),
]


@pytest.mark.parametrize(("overrides", "message"), QUEUE_STRICT)
def test_queue_admission_keeps_its_strict_rules(overrides: list[str], message: str) -> None:
    # cy-queue calls validate_pipeline_configuration(config); the direct preflight
    # relaxes only its own call.
    config = _compose("pipeline", ["ground_truth=truth.csv", *overrides])
    with pytest.raises(ValueError, match=re.escape(message)):
        validate_pipeline_configuration(config)
    validate_pipeline_configuration(config, direct=True)


def test_queue_admission_keeps_indexing_removed_keys() -> None:
    # A saved YAML or a replayed run can omit keys that the structured schema keeps.
    config = OmegaConf.create(OmegaConf.to_container(_compose("pipeline", ["ground_truth=truth.csv"])))
    assert isinstance(config, DictConfig)
    del config["skip_report"]
    del config.metrics["calibration_split"]
    with pytest.raises(KeyError):
        validate_pipeline_configuration(config)
    validate_pipeline_configuration(config, direct=True)


def test_relative_run_dir_is_resolved_like_the_use_case(
    owner: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path.resolve() / "runs" / "x" / "detect"
    config = _compose("pipeline", ["ground_truth=truth.csv", "run_dir=runs/x", f"ultralytics.project={project}"])
    with pytest.raises(ValueError, match="conflicts with pipeline run_dir"):
        validate_pipeline_configuration(config)
    with pytest.raises(TaskCreated):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner[-1] == "invocation"
    # The preflight resolves paths only; the run directory is created after the task exists.
    assert not (tmp_path / "runs").exists()


def _published_run(name: str, overrides: list[str]) -> dict[str, Any]:
    """Build the canonical ``run`` the way publish_run_configuration stores it."""
    published = sanitize_configuration(_plain_config_document(common._publication_inputs(_compose(name, overrides))))
    assert isinstance(published, dict)
    return published


def _replay(monkeypatch: pytest.MonkeyPatch, canonical: dict[str, Any]) -> None:
    monkeypatch.setattr(common, "fetch_remote_replay", lambda: RemoteReplay("agent-task", canonical, {}))


@pytest.mark.parametrize(("name", "overrides"), VALID)
def test_valid_agent_snapshot_reaches_the_task(
    owner: list[str], monkeypatch: pytest.MonkeyPatch, name: str, overrides: list[str]
) -> None:
    _replay(monkeypatch, _published_run(name, overrides))
    # An Agent composes the bare entrypoint; the snapshot supplies every input.
    config = _compose(name, [])
    with pytest.raises(TaskCreated):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner[-1] == "invocation"


INVALID_SNAPSHOTS = [
    pytest.param(
        "metrics",
        ["predictions=p.csv", "ground_truth=truth.csv"],
        {"calibration_split": "test"},
        "calibration_split must be exactly 'val'",
        id="metrics",
    ),
    pytest.param(
        "compare",
        ["ground_truth=truth.csv", "candidate_model.task_id=candidate", "model=fasterrcnn/resnet50_fpn"],
        {"q": 2},
        "q must be a finite probability in [0, 1]",
        id="compare-detector",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "model=fasterrcnn/resnet50_fpn"],
        {"weights": "w.pt"},
        "weights is only valid with skip_train=true; training chooses its model",
        id="pipeline-detector",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv", "weights=w.pt", "model=fcos/resnet50_fpn"],
        {"weights": None},
        "Prediction requires weights=<checkpoint> or ultralytics_predict.model",
        id="predict-detector",
    ),
]


@pytest.mark.parametrize(("name", "overrides", "change", "message"), INVALID_SNAPSHOTS)
def test_invalid_agent_snapshot_fails_before_the_task(
    owner: list[str],
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    overrides: list[str],
    change: dict[str, Any],
    message: str,
) -> None:
    _replay(monkeypatch, _published_run(name, overrides) | change)
    config = _compose(name, [])
    with pytest.raises(ValueError, match=re.escape(message)):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner == []
