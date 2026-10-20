"""Exercise shared detector workflows with real data/metadata and stubbed SDK calls."""

import importlib
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zipfile import ZipFile

import pandas as pd
import pytest
import yaml
from PIL import Image

from clearml_yolo.adapters.clearml import detectors as publication
from clearml_yolo.adapters.clearml.session import prepare_native_parameters
from clearml_yolo.adapters.integrations.detectors import DetectorRunner
from clearml_yolo.adapters.storage.checkpoint import bind_checkpoint
from clearml_yolo.adapters.storage.identity import (
    checkpoint_sha256,
    write_checkpoint_identity,
)
from clearml_yolo.adapters.yolo.config import execution_settings, requested_devices
from clearml_yolo.adapters.yolo.reinfer import reinfer_split
from clearml_yolo.application.contracts import (
    PREDICTION_COLUMNS,
    ClearMLConfig,
    ModelRef,
    PreparedDataset,
)
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies
from clearml_yolo.application.use_cases.compare import compare
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.application.use_cases.train import train
from clearml_yolo.core.evaluation.models import (
    ComputedEvaluation,
    EvaluationArtifacts,
    EvaluationConfig,
)
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointDescriptor,
    CheckpointMetadata,
    ModelConfig,
    PredictSettings,
    Preprocessing,
    model_preset,
)
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.composition import build_dependencies
from native_config_helpers import prediction_config, training_settings


def _archive(path: Path, metadata: CheckpointMetadata | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr("native/data.pkl", b"SDK checkpoint fixture")
    if metadata is not None:
        bind_checkpoint(path, metadata)
    return path


def _metadata(config: ModelConfig) -> CheckpointMetadata:
    return CheckpointMetadata(
        backend=config.backend,
        preset=config.preset,
        class_names=("thing",),
        preprocessing=Preprocessing(resize="letterbox", size=config.train.imgsz),
    )


def _ground_truth(directory: Path) -> Path:
    rows = []
    for split in ("train", "val", "test"):
        image = directory / f"{split}.png"
        Image.new("RGB", (16, 16)).save(image)
        rows.append([image.name, str(image), "thing", 1, 1, 9, 9, split])
    frame = pd.DataFrame(
        rows,
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    target = directory / "truth.csv"
    frame.to_csv(target, index=False)
    return target


@dataclass
class _Harness:
    config: ModelConfig
    deps: WorkflowDependencies
    truth: Path
    root: Path
    training: list[PreparedDataset] = field(default_factory=list)
    scored: list[tuple[str, Path, list[str], PredictSettings]] = field(default_factory=list)
    published: list[Path] = field(default_factory=list)
    settings: list[dict[str, Any]] = field(default_factory=list)
    native_arguments: list[dict[str, Any]] = field(default_factory=list)
    connection_failure: bool = False

    def native_train(
        self,
        config: ModelConfig,
        prepared: PreparedDataset,
        output: Path,
        report: Callable[[str, float, int], None],
    ) -> BackendTrainResult:
        self.training.append(prepared)
        report("val/map50_95", 0.75, 0)
        return BackendTrainResult(
            weights=_archive(output / "selected_best.pth"),
            metadata=_metadata(config),
            effective_args=config.train.model_dump(mode="json")
            | (
                {"model": {"num_classes": 1}}
                if config.backend == "rfdetr"
                else {"model": "DEIM"}
                if config.backend == "deimv2"
                else {"backend": "fasterrcnn", "preset": config.preset}
            ),
        )

    def native_predict(
        self,
        config: ModelConfig,
        descriptor: CheckpointMetadata,
        weights: Path,
        image_paths: Sequence[str],
        settings: PredictSettings,
    ) -> pd.DataFrame:
        self.scored.append((config.backend, weights, list(image_paths), settings))
        result = pd.DataFrame(
            [[path, "thing", 0.8, 1, 1, 9, 9] for path in image_paths], columns=PREDICTION_COLUMNS
        )
        result.attrs.update(
            image_paths=list(image_paths),
            normalized_imgsz=[64, 64],
            effective_args=settings.model_dump(mode="json"),
        )
        return result


@pytest.fixture
def detector_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[str], _Harness]]:
    loaded = set(sys.modules)

    def create(selection: str = "rfdetr/small") -> _Harness:
        config = model_preset(selection).model_copy(
            update={
                "train": model_preset(selection).train.model_copy(
                    update={"imgsz": 64, "device": "cpu"}
                ),
                "predict": PredictSettings(device="cpu", imgsz=64),
            }
        )
        deps = build_dependencies(config)
        harness = _Harness(config, deps, _ground_truth(tmp_path), tmp_path)

        def connect(values: dict[str, Any], *, name: str, ignore_remote_overrides: bool) -> None:
            assert name == "General"
            assert ignore_remote_overrides is True
            if harness.connection_failure:
                raise RuntimeError("General connection failed")
            harness.native_arguments.append(values)

        task = SimpleNamespace(id="native-owner", connect=connect)

        def publish(
            owner: TaskHandle,
            weights: Path,
            descriptor: CheckpointDescriptor,
            name: str,
        ) -> None:
            harness.published.append(weights)
            write_checkpoint_identity(
                weights,
                ModelIdentity(
                    model_name=name,
                    training_task_id=str(owner.id),
                    model_id="published-best",
                    checkpoint_sha256=descriptor.checkpoint_sha256,
                ),
            )

        for package in ("deim", "rfdetr", "fasterrcnn"):
            backend = importlib.import_module(f"clearml_yolo.adapters.{package}.backend")
            monkeypatch.setattr(backend, "train", harness.native_train)
            monkeypatch.setattr(backend, "predict", harness.native_predict)
        monkeypatch.setattr(publication, "publish_detector_model", publish)
        monkeypatch.setattr(publication, "report_metric", lambda *args: None)
        monkeypatch.setattr(deps.tracking, "init_task", lambda *args, **kwargs: task)
        monkeypatch.setattr(
            deps.tracking,
            "publish_training_parameters",
            lambda owner, values: connect(
                prepare_native_parameters(values), name="General", ignore_remote_overrides=True
            ),
        )
        monkeypatch.setattr(
            deps.tracking, "task_identity", lambda owner: ("project", "native", "native-owner")
        )
        monkeypatch.setattr(
            deps.tracking,
            "record_run_configuration",
            lambda owner, data: harness.settings.append(data),
        )
        for name in (
            "declare_result_producers",
            "complete_result_producer",
            "register_ground_truth",
            "connect_config_file",
            "report_table",
            "register_predictions",
            "publish_evaluation",
            "upload_artifact",
        ):
            monkeypatch.setattr(deps.tracking, name, lambda *args, **kwargs: None)
        monkeypatch.setattr(deps.storage, "runs_root", lambda: tmp_path / "runs")
        monkeypatch.setattr(deps.storage, "point_latest_at", lambda *args: None)
        monkeypatch.setattr(deps.resources, "training_finished", lambda: None)
        return harness

    yield create
    assert not {"torch", "torchvision", "ultralytics", "timm", "rfdetr"} & (
        set(sys.modules) - loaded
    )


def _pipeline(harness: _Harness) -> dict[str, Any]:
    return run_pipeline(
        ultralytics=harness.config.train.model_dump(mode="json") | {"model": harness.config.preset},
        ultralytics_predict=harness.config.predict.model_dump(mode="json"),
        metrics={"evaluation": EvaluationConfig(), "calibration_split": "val"},
        report={"report_config_path": None},
        compare={},
        clearml=ClearMLConfig(),
        ground_truth=str(harness.truth),
        splits=["test"],
        dataset_format="coco",
        dataset_cache_dir=harness.root / "cache",
        run_dir=harness.root / "run",
        skip_metrics=True,
        skip_report=True,
        skip_compare=True,
        fiftyone=FiftyOneConfig(enabled=False),
        deps=harness.deps,
    )


@pytest.mark.parametrize("selection", ["deimv2/s", "rfdetr/small", "fasterrcnn/resnet50_fpn"])
def test_pipeline_uses_selected_best_and_backend_owned_settings(
    detector_harness: Callable[[str], _Harness],
    selection: str,
) -> None:
    harness = detector_harness(selection)
    with requested_devices({"model.train": [-1], "model.predict": [-1]}):
        result = _pipeline(harness)
    best = harness.root / "run/detect/train/selected_best.pth"
    assert result["weights"] == best
    assert harness.published == [best]
    assert harness.training[0].dataset_format == "coco"
    assert [call[2] for call in harness.scored] == [
        [str(harness.root / "val.png")],
        [str(harness.root / "test.png")],
    ]
    assert all(call[1] == best and call[3].device == "cpu" for call in harness.scored)
    identity = harness.deps.tracking.prediction_model_identity(result["predictions"])
    assert identity is not None
    assert identity.model_id == "published-best"
    assert identity.checkpoint_sha256 == checkpoint_sha256(best)
    requested = yaml.safe_load(
        (harness.root / "run/ultralytics_predict_requested.yaml").read_text()
    )
    effective = yaml.safe_load((harness.root / "run/ultralytics_predict.yaml").read_text())
    assert requested["device"] == [-1]
    assert effective["device"] == "cpu"
    recipe = yaml.safe_load((best.parent / "native_train.yaml").read_text())
    assert harness.native_arguments[0]["weight_decay"] == harness.config.train.weight_decay
    published = harness.native_arguments[-1]
    assert not {"device", "project", "name", "save_dir", "exist_ok", "data"} & published.keys()
    assert published == {
        key: value
        for key, value in recipe.items()
        if key not in {"device", "project", "name", "save_dir", "exist_ok", "data"}
    }
    assert recipe["device"] == "cpu"
    assert recipe["use_ema"] == harness.config.train.use_ema
    if selection == "rfdetr/small":
        assert recipe["model"] == {"num_classes": 1}
    elif selection == "deimv2/s":
        assert recipe["model"] == "DEIM"
    else:
        assert recipe["backend"] == "fasterrcnn"


@pytest.mark.parametrize("selection", ["deimv2/s", "rfdetr/small", "fasterrcnn/resnet50_fpn"])
def test_native_general_connection_failure_prevents_publication(
    detector_harness: Callable[[str], _Harness],
    selection: str,
) -> None:
    harness = detector_harness(selection)
    harness.connection_failure = True
    with pytest.raises(RuntimeError, match="General connection failed"):
        _pipeline(harness)
    assert harness.training == []
    assert harness.published == []


def test_programmatic_native_training_selects_coco_by_default(
    detector_harness: Callable[[str], _Harness],
) -> None:
    harness = detector_harness("rfdetr/small")
    train(
        harness.config.train.model_dump(mode="json") | {"model": "small"},
        ClearMLConfig(),
        harness.truth,
        dataset_cache_dir=harness.root / "cache",
        deps=harness.deps,
    )
    assert harness.training[0].dataset_format == "coco"


def test_calibration_association_uses_published_best_prediction_identity(
    detector_harness: Callable[[str], _Harness],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = detector_harness("rfdetr/small")
    result = _pipeline(harness)
    associations: list[tuple[dict[str, float], str]] = []

    class CalibrationReachedError(Exception):
        pass

    def associate(
        owner: TaskHandle, thresholds: dict[str, float], *, prediction_checkpoint_sha256: str
    ) -> None:
        associations.append((thresholds, prediction_checkpoint_sha256))
        # Stop after real calibration and identity binding, before unrelated rendering.
        raise CalibrationReachedError

    monkeypatch.setattr(harness.deps.tracking, "has_owned_native_model", lambda owner: True)
    monkeypatch.setattr(harness.deps.tracking, "associate_calibration_thresholds", associate)
    with pytest.raises(CalibrationReachedError):
        compute_metrics(
            result["predictions"],
            harness.truth,
            harness.root / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            deps=harness.deps,
        )
    assert associations == [({"thing": 0.8}, checkpoint_sha256(result["weights"]))]


def _paired_comparison(
    harness: _Harness,
    baseline: Path,
    candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> list[ComputedEvaluation]:
    evaluated: list[ComputedEvaluation] = []

    class BothEvaluatedError(Exception):
        pass

    def render(
        computed: ComputedEvaluation,
        *,
        output_dir: Path,
        suffix: str,
        dashboard_classes: set[str] | None = None,
    ) -> EvaluationArtifacts:
        evaluated.append(computed)
        # Keep actual matching and provenance; unrelated report rendering is outside this test.
        if len(evaluated) == 2:
            raise BothEvaluatedError
        return EvaluationArtifacts(
            dashboard=pd.DataFrame(),
            dtrk_dashboard=pd.DataFrame(),
            dashboard_path=output_dir / f"{suffix}.xlsx",
            dtrk_dashboard_path=output_dir / f"{suffix}_dtrk.xlsx",
            plot_paths={},
            confusion_matrix_path=output_dir / f"{suffix}.png",
        )

    monkeypatch.setattr(harness.deps.evaluation_writer, "render_evaluation", render)
    legacy = harness.config.backend == "ultralytics"
    prediction = (
        prediction_config(conf=0.001, imgsz=64, device="cpu")
        if legacy
        else harness.config.predict.model_dump(mode="json")
    )
    with pytest.raises(BothEvaluatedError):
        compare(
            ModelRef(source="local", weights=baseline, thresholds={"thing": 0.7}, label="baseline"),
            ModelRef(
                source="local", weights=candidate, thresholds={"thing": 0.6}, label="candidate"
            ),
            harness.truth,
            harness.root / "comparison",
            ClearMLConfig(),
            {"reuse_existing": False},
            ultralytics=training_settings()
            if legacy
            else harness.config.train.model_dump(mode="json"),
            ultralytics_predict=prediction,
            deps=harness.deps,
        )
    return evaluated


@pytest.mark.parametrize("selection", ["rfdetr/small", "ultralytics"])
def test_compare_resolves_each_checkpoint_and_shares_current_images_and_device(
    detector_harness: Callable[[str], _Harness],
    monkeypatch: pytest.MonkeyPatch,
    selection: str,
) -> None:
    harness = detector_harness(selection)
    baseline = _archive(
        harness.root / "baseline.pth", _metadata(model_preset("fasterrcnn/resnet50_fpn"))
    )
    if selection == "ultralytics":
        candidate = _archive(
            harness.root / "candidate.pth", _metadata(model_preset("rfdetr/small"))
        )
    else:
        candidate = _pipeline(harness)["weights"]
        harness.scored.clear()
    evaluated = _paired_comparison(harness, baseline, candidate, monkeypatch)

    assert [(backend, weights) for backend, weights, _, _ in harness.scored] == [
        ("fasterrcnn", baseline),
        ("rfdetr", candidate),
    ]
    assert all(paths == [str(harness.root / "test.png")] for _, _, paths, _ in harness.scored)
    assert all(
        settings.device == "cpu" and settings.imgsz == 64 for _, _, _, settings in harness.scored
    )
    assert [item.image_names for item in evaluated] == [["test.png"], ["test.png"]]
    assert [item.thresholds for item in evaluated] == [{"thing": 0.7}, {"thing": 0.6}]
    identities = [item.model_identity for item in evaluated]
    assert all(identity is not None for identity in identities)
    assert [identity.checkpoint_sha256 for identity in identities if identity] == [
        checkpoint_sha256(baseline),
        checkpoint_sha256(candidate),
    ]
    if selection != "ultralytics":
        assert identities[1] is not None
        assert identities[1].model_id == "published-best"


@pytest.mark.parametrize("selection", ["rfdetr/small", "ultralytics"])
def test_compare_keeps_legacy_baseline_usable_with_native_candidate(
    detector_harness: Callable[[str], _Harness],
    monkeypatch: pytest.MonkeyPatch,
    selection: str,
) -> None:
    harness = detector_harness(selection)
    baseline = _archive(harness.root / "baseline.pt")
    candidate = _archive(harness.root / "candidate.pth", _metadata(model_preset("rfdetr/small")))
    assert isinstance(harness.deps.model, DetectorRunner)
    legacy_calls: list[tuple[Path, list[str], dict[str, Any]]] = []

    def legacy_predict(
        weights: str | Path,
        paths: Sequence[str],
        *,
        image_name: str = "name",
        manifest_dir: Path | None = None,
        **settings: Any,
    ) -> pd.DataFrame:
        # Exercise the exact complete-group validation that runs before YOLO SDK loading.
        values = execution_settings(
            settings | {"model": str(weights), "source": "images.txt"}, "predict"
        )
        legacy_calls.append((Path(weights), list(paths), values))
        return pd.DataFrame(
            [[Path(path).name, "thing", 0.8, 1, 1, 9, 9] for path in paths],
            columns=PREDICTION_COLUMNS,
        )

    def legacy_reinfer(*args: Any, **kwargs: Any) -> Any:
        return reinfer_split(
            *args, **kwargs, predictor=legacy_predict, class_names=lambda _: {0: "thing"}
        )

    monkeypatch.setattr(harness.deps.model.legacy, "reinfer_split", legacy_reinfer)
    monkeypatch.setattr(harness.deps.model.legacy, "trained_imgsz", lambda weights: 640)
    evaluated = _paired_comparison(harness, baseline, candidate, monkeypatch)
    assert len(evaluated) == 2
    assert len(legacy_calls) == 1
    assert legacy_calls[0][0:2] == (baseline, [str(harness.root / "test.png")])
    assert legacy_calls[0][2]["device"] == "cpu"
    assert [(backend, weights) for backend, weights, _, _ in harness.scored] == [
        ("rfdetr", candidate)
    ]
