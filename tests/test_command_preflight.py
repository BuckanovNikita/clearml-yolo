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
from clearml_yolo.entrypoints.hydra import common, validation
from clearml_yolo.entrypoints.hydra.validation import validate_pipeline_configuration, validate_wrapper_keys

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


_NULL_FIFTYONE = "fiftyone=null is not supported; use fiftyone.enabled=false to turn FiftyOne publication off"


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
    # The run compares the default cache location too: it lies inside a run_dir of CY_HOME.
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "run_dir=${oc.env:CY_HOME}"],
        "dataset_cache_dir must be outside run_dir",
        id="pipeline-default-cache-inside-run-dir",
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
        ["ground_truth=truth.csv", "skip_train=true", "weights=w.pt", "metrics.evaluation.backend=other"],
        "Frozen thresholds require the native digital-metrics backend",
        id="pipeline-evaluation-backend",
    ),
    # zen instantiates the evaluation record after the task even when no stage reads it.
    pytest.param(
        "pipeline",
        [
            "ground_truth=truth.csv",
            "skip_metrics=true",
            "skip_compare=true",
            "metrics.evaluation.matching_strategy=bad",
        ],
        "matching_strategy",
        id="pipeline-skipped-evaluation-record",
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
        ["ground_truth=truth.csv", "dataset_format=bad"],
        "dataset_format must be one of: ndjson, flat, coco",
        id="train-dataset-format",
    ),
    pytest.param(
        "train",
        ["ground_truth=truth.csv", "dataset_format=coco"],
        "Ultralytics training requires ndjson or flat dataset_format",
        id="train-yolo-coco",
    ),
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "skip_train=true", "weights=w.pt", "dataset_format=coco"],
        "Ultralytics training requires ndjson or flat dataset_format",
        id="pipeline-yolo-coco-without-training",
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
        "missing a required argument: 'evaluation'",
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
    pytest.param("pipeline", ["ground_truth=truth.csv", "run_dir=${oc.env:CY_HOME}/run"], id="pipeline-run-dir"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "model=fasterrcnn/resnet50_fpn"], id="pipeline-detector"),
    # run_pipeline accepts a native name equal to the stage name it routes.
    pytest.param(
        "pipeline",
        ["ground_truth=truth.csv", "ultralytics.name=train", "ultralytics_predict.name=predict"],
        id="pipeline-stage-names-without-run-dir",
    ),
    pytest.param("train", ["ground_truth=truth.csv"], id="train"),
    pytest.param("train", ["ground_truth=truth.csv", "model=rfdetr/small"], id="train-detector"),
    # A detector run always prepares a COCO dataset copy, whatever dataset_format says.
    pytest.param(
        "train", ["ground_truth=truth.csv", "model=rfdetr/small", "dataset_format=flat"], id="train-detector-format"
    ),
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


_SKIP_TRAIN = ["skip_train=true", "weights=w.pt"]


def _pipeline(overrides: list[str], *, removed: tuple[str, ...] = ()) -> DictConfig:
    """Compose cy; ``removed`` deletes nested keys as a saved YAML or a replayed run can."""
    composed = _compose("pipeline", ["ground_truth=truth.csv", *overrides])
    config = OmegaConf.create(OmegaConf.to_container(composed, resolve=True))
    assert isinstance(config, DictConfig)
    for dotted in removed:
        parent, _, key = dotted.rpartition(".")
        del OmegaConf.select(config, parent)[key]
    return config


# (bad settings, overrides that skip the stage reading them, message). The direct
# preflight rejects every value a validator rejects, with training on and with the
# stage skipped; before, a skipped stage never read it and, after training, the run
# marked the failing later stage failed and exited 0.
REJECTED_IN_EVERY_STAGE = [
    pytest.param(["dataset_format=bad"], _SKIP_TRAIN, "Invalid pipeline setting dataset_format", id="dataset-format"),
    pytest.param(["ultralytics.epochs=0"], _SKIP_TRAIN, "ultralytics.epochs must be at least 1", id="train-range"),
    pytest.param(
        ["~ultralytics.epochs"], _SKIP_TRAIN, "Missing ultralytics parameters ['epochs']", id="train-completeness"
    ),
    pytest.param(
        ["ultralytics.model=null"],
        _SKIP_TRAIN,
        "Set ultralytics.model explicitly; no training model fallback is provided",
        id="train-empty-model",
    ),
    pytest.param(
        ["ultralytics.resume=true"],
        _SKIP_TRAIN,
        "resume is unsupported with ground_truth; use model weights to fine-tune",
        id="train-resume",
    ),
    pytest.param(
        ["metrics.calibration_split=test"],
        ["skip_metrics=true"],
        "calibration_split must be exactly 'val'",
        id="calibration-split",
    ),
    pytest.param(
        ["metrics.evaluation.backend=other"],
        ["skip_metrics=true", "skip_compare=true"],
        "Frozen thresholds require the native digital-metrics backend",
        id="evaluation-backend",
    ),
    pytest.param(
        ["metrics.evaluation=null"],
        ["skip_metrics=true"],
        "EvaluationConfig settings must be a mapping",
        id="null-evaluation",
    ),
    pytest.param(["compare.q=2"], ["skip_compare=true"], "q must be a finite probability in [0, 1]", id="compare-q"),
    pytest.param(
        ["compare.bootstrap_iterations=0"],
        ["skip_compare=true"],
        "bootstrap_iterations must be a positive integer",
        id="compare-bootstrap",
    ),
    pytest.param(
        ["compare.seed=-1"],
        ["skip_compare=true"],
        "Comparison seed must be a nonnegative integer or null",
        id="compare-seed",
    ),
    pytest.param(
        ["compare.seed=true"],
        ["skip_compare=true"],
        "Comparison seed must be a nonnegative integer or null",
        id="compare-boolean-seed",
    ),
    pytest.param(["compare.baseline_model.source=bad"], ["skip_compare=true"], "source", id="compare-baseline-record"),
    pytest.param(
        ["report.report_config_path=3"],
        ["skip_report=true"],
        "report_config_path must be a path string or null",
        id="report-config-path",
    ),
    pytest.param(
        ["splits=[all]"],
        ["skip_metrics=true", "skip_predict=true"],
        "split='all' is unsupported for frozen evaluation; name concrete splits",
        id="all-split",
    ),
    pytest.param(["model_label=2024"], _SKIP_TRAIN, "Invalid pipeline setting model_label", id="integer-model-label"),
    pytest.param(["run_id=0"], _SKIP_TRAIN, "Invalid pipeline setting run_id", id="falsy-integer-run-id"),
    pytest.param(["skip_compare=yes"], _SKIP_TRAIN, "Invalid pipeline setting skip_compare", id="string-skip-flag"),
]


@pytest.mark.parametrize(("bad", "skipped", "message"), REJECTED_IN_EVERY_STAGE)
@pytest.mark.parametrize("stage", ["running", "skipped"])
def test_invalid_setting_fails_before_the_task_whether_or_not_its_stage_runs(
    owner: list[str], bad: list[str], skipped: list[str], message: str, stage: str
) -> None:
    config = _pipeline([*(skipped if stage == "skipped" else []), *bad])
    with pytest.raises((TypeError, ValueError), match=re.escape(message)):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner == []


@pytest.mark.parametrize(
    ("removed", "skipped"),
    [
        pytest.param(("compare.baseline_model",), ["skip_compare=true"], id="compare-baseline"),
        pytest.param(("metrics.evaluation",), ["skip_metrics=true", "skip_compare=true"], id="metrics-evaluation"),
    ],
)
@pytest.mark.parametrize("stage", ["running", "skipped"])
def test_removed_required_stage_setting_fails_before_the_task(
    owner: list[str], removed: tuple[str, ...], skipped: list[str], stage: str
) -> None:
    config = _pipeline(skipped if stage == "skipped" else [], removed=removed)
    # The run passes the stage settings to the stage call, which binds them like this.
    name = removed[0].rpartition(".")[2]
    with pytest.raises(TypeError, match=re.escape(f"missing a required argument: '{name}'")):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner == []


@pytest.mark.parametrize(
    ("name", "overrides", "removed"),
    [
        pytest.param("report", ["comparison_dir=comparison"], "output_dir", id="report"),
        pytest.param(
            "compare", ["ground_truth=truth.csv", "candidate_model.task_id=c"], "baseline_model", id="compare"
        ),
    ],
)
def test_removed_required_command_setting_fails_before_the_task(
    owner: list[str], name: str, overrides: list[str], removed: str
) -> None:
    # A saved YAML or a replayed run can lack a key; the command call binds it like this.
    config = OmegaConf.create(OmegaConf.to_container(_compose(name, overrides), resolve=True))
    assert isinstance(config, DictConfig)
    del config[removed]
    with pytest.raises(TypeError, match=re.escape(f"missing a required argument: '{removed}'")):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner == []


def test_stage_record_without_its_target_keeps_its_value_rules(owner: list[str]) -> None:
    bad = ["skip_compare=true", "compare.baseline_model.source=bad"]
    config = _pipeline(bad, removed=("compare.baseline_model._target_",))
    with pytest.raises(ValueError, match="source"):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner == []


_EVALUATION_ALIAS = "clearml_yolo.application.use_cases.metrics.EvaluationConfig"
_MODEL_REF_ALIAS = "clearml_yolo.application.use_cases.pipeline.ModelRef"
_CLEARML_ALIAS = "clearml_yolo.application.use_cases.pipeline.ClearMLConfig"
_FIFTYONE_ALIAS = "clearml_yolo.application.use_cases.pipeline.FiftyOneConfig"

# (overrides, nested keys removed). The loose but valid forms the direct preflight accepts.
LOOSE_FORMS = [
    pytest.param(["skip_compare=1", "skip_report=1", "skip_metrics=0"], (), id="integer-skip-flags"),
    pytest.param(
        [],
        ("skip_report", "metrics.calibration_split", "compare.q", "compare.seed", "report.report_config_path"),
        id="removed-optional-keys",
    ),
    pytest.param(["model=fasterrcnn/resnet50_fpn"], ("ultralytics",), id="detector-without-ultralytics"),
    pytest.param(
        ["model=fasterrcnn/resnet50_fpn"], ("ultralytics_predict",), id="detector-without-ultralytics-predict"
    ),
    pytest.param(
        [
            f"metrics.evaluation._target_={_EVALUATION_ALIAS}",
            f"compare.baseline_model._target_={_MODEL_REF_ALIAS}",
            f"clearml._target_={_CLEARML_ALIAS}",
            f"fiftyone._target_={_FIFTYONE_ALIAS}",
        ],
        (),
        id="aliased-targets",
    ),
    pytest.param(
        [
            "+metrics.evaluation._convert_=all",
            "+compare.baseline_model._recursive_=false",
            "+clearml._args_=[]",
            "+fiftyone._partial_=false",
        ],
        (),
        id="hydra-reserved-keys",
    ),
    pytest.param(["run_dir=${oc.env:CY_HOME}/run", "run_id=42"], (), id="numeric-run-id-with-run-dir"),
]


@pytest.mark.parametrize(("overrides", "removed"), LOOSE_FORMS)
def test_direct_preflight_accepts_loose_but_valid_forms(
    owner: list[str], overrides: list[str], removed: tuple[str, ...]
) -> None:
    with pytest.raises(TaskCreated):
        common.execute_owned("pipeline", _pipeline(overrides, removed=removed), run_pipeline)
    assert owner[-1] == "invocation"


# cy-queue admission keeps rejecting each loose form master's strict call rejected.
STRICT_REJECTS = [
    pytest.param(["skip_compare=1"], (), "Invalid pipeline setting skip_compare", id="integer-skip-flag"),
    pytest.param([], ("compare.q",), "'q'", id="removed-optional-key"),
    pytest.param(
        [f"metrics.evaluation._target_={_EVALUATION_ALIAS}"],
        (),
        "Submission requires the supported configuration target",
        id="aliased-target",
    ),
    pytest.param(["+fiftyone._partial_=false"], (), "_partial_", id="hydra-reserved-key"),
    pytest.param(
        ["run_dir=${oc.env:CY_HOME}/run", "run_id=42"], (), "Invalid pipeline setting run_id", id="numeric-run-id"
    ),
    pytest.param(
        ["ultralytics.name=train"], (), "Native pipeline output overrides require an explicit run_dir", id="stage-name"
    ),
]


@pytest.mark.parametrize(("overrides", "removed", "message"), STRICT_REJECTS)
def test_queue_admission_keeps_its_strict_rules(overrides: list[str], removed: tuple[str, ...], message: str) -> None:
    # cy-queue calls validate_pipeline_configuration(config); only the direct call is loose.
    config = _pipeline(overrides, removed=removed)
    with pytest.raises((KeyError, TypeError, ValueError), match=re.escape(message)):
        validate_pipeline_configuration(config)
    validate_pipeline_configuration(config, direct=True)


def test_queue_admission_accepts_the_default_configuration() -> None:
    validate_pipeline_configuration(_pipeline([]))
    validate_pipeline_configuration(_pipeline(_SKIP_TRAIN))


@pytest.mark.parametrize("direct", [False, True], ids=["queue", "direct"])
def test_both_admissions_reject_null_fiftyone(direct: bool) -> None:
    # SIP-210: cy-queue's admission and the direct preflight both reject it.
    with pytest.raises(ValueError, match=re.escape(_NULL_FIFTYONE)):
        validate_pipeline_configuration(_pipeline(["fiftyone=null"]), direct=direct)


def test_queue_admission_rejects_null_fiftyone_in_the_wrapper_keys() -> None:
    with pytest.raises(ValueError, match=re.escape(_NULL_FIFTYONE)):
        validate_wrapper_keys(_pipeline(["fiftyone=null"]), run_pipeline)


def test_direct_preflight_accepts_a_removed_fiftyone_group() -> None:
    config = _pipeline([])
    del config["fiftyone"]
    validate_pipeline_configuration(config, direct=True)


# (overrides, whether cy-queue admits it, whether the direct preflight admits it). The
# queue routes against the literal run_dir and checks only an explicit dataset_cache_dir,
# while the direct preflight resolves both as run_pipeline does.
ROUTES = [
    pytest.param(["run_dir=../runs/x", "ultralytics.project=../runs/x/detect"], True, False, id="relative-project"),
    pytest.param(["run_dir=${oc.env:CY_HOME}"], True, False, id="default-cache-inside-run-dir"),
    # The working directory is run_dir: read literally, ~/cache lies inside it.
    pytest.param(["run_dir=${oc.env:CY_HOME}/work", "dataset_cache_dir='~/cache'"], False, True, id="home-cache"),
    pytest.param(["run_dir=${oc.env:CY_HOME}/run", "ultralytics.name=train"], True, True, id="stage-name-with-run-dir"),
]


@pytest.mark.parametrize(("overrides", "queue", "direct"), ROUTES)
def test_queue_and_direct_routes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: list[str], queue: bool, direct: bool
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    config = _pipeline(overrides)
    for strict, admitted in ((True, queue), (False, direct)):
        if admitted:
            validate_pipeline_configuration(config, direct=not strict)
        else:
            with pytest.raises(ValueError, match="run_dir"):
                validate_pipeline_configuration(config, direct=not strict)
    assert not (tmp_path / "runs").exists()


def test_strict_admission_still_rejects_the_detector_inactive_group_removal() -> None:
    config = _pipeline(["model=fasterrcnn/resnet50_fpn"], removed=("ultralytics",))
    with pytest.raises(KeyError):
        validate_pipeline_configuration(config)
    validate_pipeline_configuration(config, direct=True)


# Standalone commands accept an importable alias of the supported class and Hydra's
# reserved keys, and keep the value rules of the record.
STANDALONE_LOOSE_FORMS = [
    pytest.param(
        "val",
        ["ground_truth=truth.csv", "weights=w.pt", f"evaluation._target_={_EVALUATION_ALIAS}"],
        id="val-evaluation",
    ),
    pytest.param(
        "metrics",
        ["predictions=p.csv", "ground_truth=truth.csv", "fiftyone._target_=" + _FIFTYONE_ALIAS],
        id="metrics-fiftyone",
    ),
    pytest.param(
        "predict",
        ["ground_truth=truth.csv", "weights=w.pt", "+fiftyone._convert_=all"],
        id="predict-fiftyone-reserved-key",
    ),
    pytest.param(
        "compare",
        [
            "ground_truth=truth.csv",
            "candidate_model.task_id=candidate",
            f"candidate_model._target_={_MODEL_REF_ALIAS}",
            f"baseline_model._target_={_MODEL_REF_ALIAS}",
            "+evaluation._recursive_=false",
        ],
        id="compare-model-refs",
    ),
]


@pytest.mark.parametrize(("name", "overrides"), STANDALONE_LOOSE_FORMS)
def test_standalone_records_accept_loose_but_valid_forms(owner: list[str], name: str, overrides: list[str]) -> None:
    with pytest.raises(TaskCreated):
        common.execute_owned(name, _compose(name, overrides), COMMANDS[name])
    assert owner[-1] == "invocation"


@pytest.mark.parametrize(
    ("name", "overrides"),
    [
        pytest.param("train", ["ground_truth=truth.csv"], id="train"),
        pytest.param("predict", ["ground_truth=truth.csv", "weights=w.pt"], id="predict"),
        pytest.param("val", ["ground_truth=truth.csv", "weights=w.pt"], id="val"),
    ],
)
def test_standalone_detector_accepts_a_removed_ultralytics_group(
    owner: list[str], name: str, overrides: list[str]
) -> None:
    # The run executes the detector's model.train and model.predict in place of the group.
    composed = _compose(name, [*overrides, "model=fasterrcnn/resnet50_fpn"])
    config = OmegaConf.create(OmegaConf.to_container(composed, resolve=True))
    assert isinstance(config, DictConfig)
    del config["ultralytics"]
    with pytest.raises(TaskCreated):
        common.execute_owned(name, config, COMMANDS[name])
    assert owner[-1] == "invocation"


@pytest.mark.parametrize(
    ("name", "overrides", "message"),
    [
        pytest.param(
            "val",
            [
                "ground_truth=truth.csv",
                "weights=w.pt",
                f"evaluation._target_={_EVALUATION_ALIAS}",
                "evaluation.backend=other",
            ],
            "Frozen thresholds require the native digital-metrics backend",
            id="aliased-record-value",
        ),
        pytest.param(
            "metrics",
            ["predictions=p.csv", "ground_truth=truth.csv", "fiftyone._target_=clearml_yolo.core.publication.Missing"],
            "Submission requires the supported configuration target clearml_yolo.core.publication.FiftyOneConfig",
            id="unresolvable-target",
        ),
        pytest.param(
            "compare",
            [
                "ground_truth=truth.csv",
                "candidate_model.task_id=candidate",
                f"baseline_model._target_={_CLEARML_ALIAS}",
            ],
            "Submission requires the supported configuration target clearml_yolo.application.contracts.ModelRef",
            id="other-class-target",
        ),
    ],
)
def test_standalone_records_keep_their_rules(owner: list[str], name: str, overrides: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        common.execute_owned(name, _compose(name, overrides), COMMANDS[name])
    assert owner == []


# Checks the composed configuration cannot decide before the task, or that no
# validator of the run applies: the command reaches the task and the run decides.
LEFT_TO_THE_RUN = [
    # Without run_dir or run_id the run directory is named after the task.
    pytest.param("pipeline", ["ground_truth=truth.csv", "ultralytics.project=${oc.env:CY_HOME}/p"], id="route-project"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "ultralytics.name=other"], id="route-name"),
    pytest.param("pipeline", ["ground_truth=truth.csv", "+ultralytics.save_dir=null"], id="route-save-dir"),
    # cy-compare and cy-report have no such value rule; cy checks these values as cy-queue does.
    pytest.param(
        "compare", ["ground_truth=truth.csv", "candidate_model.task_id=c", "bootstrap_iterations=0"], id="bootstrap"
    ),
    pytest.param("compare", ["ground_truth=truth.csv", "candidate_model.task_id=c", "seed=true"], id="seed"),
    pytest.param("report", ["comparison_dir=comparison", "report_config_path=3"], id="report-config-path"),
]


@pytest.mark.parametrize(("name", "overrides"), LEFT_TO_THE_RUN)
def test_checks_left_to_the_run_reach_the_task(owner: list[str], name: str, overrides: list[str]) -> None:
    with pytest.raises(TaskCreated):
        common.execute_owned(name, _compose(name, overrides), COMMANDS[name])
    assert owner[-1] == "invocation"


def _tree(root: Path) -> list[tuple[str, int]]:
    return sorted((str(path.relative_to(root)), path.stat().st_mtime_ns) for path in root.rglob("*"))


@pytest.mark.parametrize(("name", "overrides"), VALID)
def test_preflight_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, overrides: list[str]
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = _compose(name, overrides)
    before = _tree(tmp_path)
    validation.validate_command_configuration(config, COMMANDS[name])
    assert _tree(tmp_path) == before


# run_pipeline routed the prediction group after the CSV dataset policy and the
# prediction projection, which drops save_dir and, when training, sets task=detect.
ROUTED_PREDICTION = [
    pytest.param(["+ultralytics_predict.save_dir=${oc.env:CY_HOME}/x"], id="save-dir-without-run-dir"),
    pytest.param(
        ["run_dir=${oc.env:CY_HOME}/run", "+ultralytics_predict.save_dir=${oc.env:CY_HOME}/x"],
        id="save-dir-with-run-dir",
    ),
    pytest.param(["ultralytics_predict.task=null"], id="null-task-when-training"),
]


@pytest.mark.parametrize("overrides", ROUTED_PREDICTION)
def test_direct_preflight_checks_the_routed_prediction_group(owner: list[str], overrides: list[str]) -> None:
    config = _compose("pipeline", ["ground_truth=truth.csv", *overrides])
    with pytest.raises(ValueError, match=r"run_dir|task must be detect"):
        validate_pipeline_configuration(config)
    with pytest.raises(TaskCreated):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner[-1] == "invocation"


def test_prediction_task_is_checked_without_training(owner: list[str]) -> None:
    config = _compose("pipeline", ["ground_truth=truth.csv", *_SKIP_TRAIN, "ultralytics_predict.task=null"])
    with pytest.raises(ValueError, match=re.escape("ultralytics_predict.task must be detect")):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner == []


def test_training_rejects_a_prediction_task_other_than_detect(owner: list[str]) -> None:
    config = _compose("pipeline", ["ground_truth=truth.csv", "ultralytics_predict.task=segment"])
    with pytest.raises(ValueError, match=re.escape("CSV ground-truth training supports task=detect only")):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner == []


def test_direct_pipeline_preflight_calls_the_public_validator(
    owner: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []
    public = validation.validate_pipeline_configuration

    def spy(config: DictConfig, *, direct: bool = False) -> None:
        calls.append(direct)
        public(config, direct=direct)

    monkeypatch.setattr(validation, "validate_pipeline_configuration", spy)
    with pytest.raises(TaskCreated):
        common.execute_owned("pipeline", _compose("pipeline", ["ground_truth=truth.csv"]), run_pipeline)
    assert calls == [True]
    assert owner[-1] == "invocation"


def test_dataset_cache_dir_expands_the_home_directory_like_the_run(
    owner: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The run expands ~ before comparing; read literally, ~/cache would lie inside run_dir.
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(work)
    config = _compose("pipeline", ["ground_truth=truth.csv", f"run_dir={work}", "dataset_cache_dir='~/cache'"])
    with pytest.raises(TaskCreated):
        common.execute_owned("pipeline", config, run_pipeline)
    assert owner[-1] == "invocation"


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
