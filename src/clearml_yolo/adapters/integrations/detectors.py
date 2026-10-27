"""Bridge native detector adapters to the shared workflow model port."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
import yaml

from clearml_yolo.adapters.assets.execution import prepare_model_assets
from clearml_yolo.adapters.clearml.session import active_task, publish_model_assets
from clearml_yolo.adapters.storage.checkpoint import bind_checkpoint, read_checkpoint_descriptor
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.adapters.storage.identity import checkpoint_sha256
from clearml_yolo.adapters.yolo.config import (
    native_defaults,
    prediction_defaults,
    requested_settings,
)
from clearml_yolo.application.contracts import (
    ImageNameMode,
    ModelRef,
    PreparedDataset,
    ScoredResolution,
    TrainResult,
    VocabularyReport,
)
from clearml_yolo.application.ports import ModelRunner, Stage, TaskHandle
from clearml_yolo.core.models import (
    CheckpointDescriptor,
    ModelConfig,
    PredictSettings,
    TrainSettings,
)
from clearml_yolo.core.redaction import sanitize_configuration
from clearml_yolo.core.transforms import TransformConfig

_ROUTING = frozenset(
    {
        "model",
        "backend",
        "preset",
        "task",
        "mode",
        "project",
        "name",
        "save_dir",
        "data",
        "classes",
        "single_cls",
        "fraction",
        "cls_remap",
        "split",
        "source",
        "exist_ok",
    }
)
_FP16_BITS = 16
_PREDICTION_ROUTING = _ROUTING - {"classes", "single_cls", "fraction", "cls_remap", "data", "split"}


class _ReinferArguments(TypedDict):
    conf: float | None
    iou: float
    imgsz: int | list[int]
    batch: int
    device: str | int | list[int] | None
    image_name: str
    native_project: Path
    native_name: str
    native_kwargs: dict[str, object] | None
    reuse_existing: bool


class DetectorRunner:
    """Keep legacy YOLO behavior while resolving described checkpoints independently."""

    def __init__(
        self, config: ModelConfig, legacy: ModelRunner, *, transforms: TransformConfig | None = None
    ) -> None:
        self.config = config
        self.legacy = legacy
        self.transforms = transforms
        self._references: dict[Path, ModelRef] = {}

    def bind_reference(self, weights: Path, reference: ModelRef) -> None:
        """Bind external assertions per checkpoint without changing the source archive."""
        key = weights.resolve()
        previous = self._references.get(key)
        previous_descriptor = self._descriptor(weights) if previous is not None else None
        self._references[key] = reference.model_copy(deep=True)
        try:
            descriptor = self._descriptor(weights)
        except Exception:
            if previous is None:
                self._references.pop(key, None)
            else:
                self._references[key] = previous
            raise
        if previous is not None and descriptor != previous_descriptor:
            # Candidate and baseline resolve before either predicts. One
            # checkpoint cannot silently acquire the last reference's design.
            self._references[key] = previous
            raise ValueError("Conflicting model metadata for the same checkpoint")

    def _descriptor(self, weights: str | Path) -> CheckpointDescriptor | None:
        path = Path(weights)
        descriptor = read_checkpoint_descriptor(path)
        reference = self._references.get(path.resolve())
        if reference is None and self.config.backend != "ultralytics":
            if descriptor is None:
                raise ValueError(
                    "Native detector weights require a bound checkpoint descriptor; "
                    "raw comparison weights require explicit ModelRef metadata"
                )
            if (self.config.backend, self.config.preset) != (descriptor.backend, descriptor.preset):
                raise ValueError(
                    "Explicit model selection disagrees with the checkpoint descriptor"
                )
        if reference is None or reference.backend is None:
            return descriptor
        if descriptor is not None:
            self._validate_reference(reference, descriptor)
            return descriptor
        if reference.backend == "ultralytics":
            return None
        if reference.class_names is None or reference.preprocessing is None:
            raise ValueError(
                "Raw detector checkpoints require explicit class_names and preprocessing"
            )
        return CheckpointDescriptor.model_validate(
            {
                "backend": reference.backend,
                "preset": reference.preset,
                "class_names": reference.class_names,
                "preprocessing": reference.preprocessing,
                "checkpoint_sha256": checkpoint_sha256(path),
            }
        )

    @staticmethod
    def _validate_reference(reference: ModelRef, descriptor: CheckpointDescriptor) -> None:
        if (reference.backend, reference.preset) != (descriptor.backend, descriptor.preset):
            raise ValueError("Model reference disagrees with the checkpoint descriptor")
        if reference.class_names is not None and reference.class_names != descriptor.class_names:
            raise ValueError("Model reference vocabulary disagrees with checkpoint descriptor")
        if (
            reference.preprocessing is not None
            and reference.preprocessing != descriptor.preprocessing
        ):
            raise ValueError("Model reference preprocessing disagrees with checkpoint descriptor")

    def _legacy_prediction(
        self, values: dict[str, Any], *, comparison: bool = False
    ) -> dict[str, Any]:
        from clearml_yolo.adapters.yolo.reinfer import COMPARISON_KEYS

        # A native selected group has no YOLO-only controls. Supply their defaults
        # at this boundary while leaving shared comparison inputs with their owner.
        defaults = (
            prediction_defaults(inherit=False) if self.config.backend != "ultralytics" else {}
        )
        if comparison:
            defaults = {key: value for key, value in defaults.items() if key not in COMPARISON_KEYS}
        result = {key: value for key, value in values.items() if key not in {"backend", "preset"}}
        if "half" in result:
            result["quantize"] = 16 if result.pop("half") else 32
        return defaults | result

    @staticmethod
    def _native_prediction(values: dict[str, Any]) -> PredictSettings:
        """Translate shared controls; reject changed YOLO-only controls in mixed comparisons."""
        result = {key: value for key, value in values.items() if key not in _PREDICTION_ROUTING}
        if result.get("verbose") is False:
            result.pop("verbose")
        if "quantize" in result:
            precision = result.pop("quantize")
            if precision not in {None, 16, 32}:
                raise ValueError("Native detectors support only FP32 or FP16 prediction")
            result["half"] = precision == _FP16_BITS
        defaults = native_defaults() | {"rect": True, "save": False}
        for key in tuple(result):
            if key not in PredictSettings.model_fields:
                if key not in defaults or result[key] != defaults[key]:
                    raise ValueError(f"Unsupported native detector prediction setting: {key}")
                result.pop(key)
        if "conf" in result and result["conf"] is None:
            raise ValueError("Native detector comparisons require an explicit confidence threshold")
        return PredictSettings.model_validate(result)

    def stage_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
        if self.config.backend == "ultralytics":
            return self.legacy.stage_settings(settings, stage)
        values = {key: value for key, value in settings.items() if key not in _ROUTING}
        schema = TrainSettings if stage == "train" else PredictSettings
        validated = schema.model_validate(values).model_dump(mode="json")
        return validated | {key: value for key, value in settings.items() if key in _ROUTING}

    def execution_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
        if self.config.backend == "ultralytics":
            return self.legacy.execution_settings(settings, stage)
        return self.stage_settings(settings, stage)

    def requested_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
        if self.config.backend == "ultralytics":
            return self.legacy.requested_settings(settings, stage)
        return requested_settings(settings, stage, group=f"model.{stage}")

    def prediction_settings(
        self, ultralytics_predict: dict[str, Any], weights: str | Path | None = None
    ) -> dict[str, Any]:
        if self.config.backend == "ultralytics":
            return self.legacy.prediction_settings(ultralytics_predict, weights)
        values = self.config.predict.model_dump(mode="json") | ultralytics_predict
        result = self.stage_settings(values, "predict")
        if result.get("source") is not None:
            raise ValueError("Prediction source is owned by ground_truth image membership")
        if result.get("task", "detect") != "detect":
            raise ValueError("Prediction task must be detect")
        if result.get("mode", "predict") != "predict":
            raise ValueError("Prediction mode must be predict")
        native_model = result.get("model")
        if weights is not None and native_model is not None and str(weights) != str(native_model):
            raise ValueError("weights conflicts with the native prediction model")
        result["model"] = str(weights) if weights is not None else result.get("model")
        if result["imgsz"] is None and weights is None:
            result["imgsz"] = self.config.train.model_dump(mode="json")["imgsz"]
        result.update(backend=self.config.backend, preset=self.config.preset)
        return result

    def trained_imgsz(self, weights: str | Path) -> int | list[int] | None:
        descriptor = self._descriptor(weights)
        if descriptor is None:
            return self.legacy.trained_imgsz(weights)
        size = descriptor.preprocessing.size
        return size if isinstance(size, int) else list(size)

    def resolution_of(self, weights: str | Path, imgsz: int | list[int] | None) -> ScoredResolution:
        descriptor = self._descriptor(weights)
        if descriptor is None:
            return self.legacy.resolution_of(weights, imgsz)
        recorded = descriptor.preprocessing.size
        size = recorded if isinstance(recorded, int) else list(recorded)
        return ScoredResolution(
            trained_at=size,
            scored_at=size if imgsz is None else imgsz,
        )

    def write_native_yaml(self, path: Path, settings: dict[str, Any], stage: Stage) -> Path:
        path = write_path(path)
        if self.config.backend == "ultralytics" and "backend" not in settings:
            weights = settings.get("model")
            # Native training recipes may use 'model' for a registry name or a
            # nested architecture. Only prediction uses it as a checkpoint path.
            described = (
                stage == "predict"
                and isinstance(weights, (str, Path))
                and self._descriptor(weights) is not None
            )
            if not described:
                return self.legacy.write_native_yaml(path, settings, stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(sanitize_configuration(settings), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return path

    def _predict_native(
        self,
        descriptor: CheckpointDescriptor,
        weights: Path,
        image_paths: Sequence[str],
        settings: PredictSettings,
    ) -> pd.DataFrame:
        reference = self._references.get(weights.resolve())
        source = (
            reference.source_dir
            if reference is not None and reference.source_dir is not None
            else self.config.source_dir
        )
        config = ModelConfig.model_validate(
            {
                "backend": descriptor.backend,
                "preset": descriptor.preset,
                "source_dir": source if descriptor.backend == "deimv2" else None,
            }
        )
        config, assets = prepare_model_assets(config, training=False)
        publish_model_assets(active_task(), assets)
        if descriptor.backend == "deimv2":
            from clearml_yolo.adapters.deim.backend import predict
        elif descriptor.backend == "rfdetr":
            from clearml_yolo.adapters.rfdetr.backend import predict
        elif descriptor.backend == "fasterrcnn":
            from clearml_yolo.adapters.fasterrcnn.backend import predict
        elif descriptor.backend == "fcos":
            from clearml_yolo.adapters.fcos.backend import predict
        else:
            raise ValueError(f"Unsupported described detector: {descriptor.backend}")
        return predict(config, descriptor, weights, image_paths, settings)

    def predict_on_images(
        self,
        weights: str | Path,
        image_paths: Sequence[str],
        *,
        image_name: ImageNameMode = "name",
        manifest_dir: Path | None = None,
        **model_kwargs: Any,
    ) -> pd.DataFrame:
        descriptor = self._descriptor(weights)
        if descriptor is None:
            return self.legacy.predict_on_images(
                weights,
                image_paths,
                image_name=image_name,
                manifest_dir=manifest_dir,
                **self._legacy_prediction(model_kwargs),
            )
        if image_name not in {"name", "stem", "path"}:
            raise ValueError(f"Unsupported image_name mode: {image_name}")
        settings = self._native_prediction(model_kwargs)
        output = write_path(
            Path(model_kwargs.get("project", ".")) / str(model_kwargs.get("name", "predict"))
        )
        output.mkdir(parents=True, exist_ok=True)
        directory = write_path(manifest_dir or output / "inputs")
        directory.mkdir(parents=True, exist_ok=True)
        manifest = write_path(directory / "images.txt")
        paths = list(dict.fromkeys(str(path) for path in image_paths))
        manifest.write_text(
            "\n".join(str(Path(path).absolute()) for path in paths), encoding="utf-8"
        )
        frame = self._predict_native(descriptor, Path(weights), paths, settings)
        if set(frame.attrs.get("image_paths", ())) != set(paths):
            raise ValueError("Native detector did not score every requested image")
        if image_name != "path":
            frame["image_name"] = frame["image_name"].map(
                lambda value: Path(value).stem if image_name == "stem" else Path(value).name
            )
        effective = model_kwargs | dict(frame.attrs.get("effective_args", {}))
        effective.update(
            model=str(weights),
            backend=descriptor.backend,
            preset=descriptor.preset,
            source=str(manifest.absolute()),
            mode="predict",
        )
        frame.attrs.update(
            effective_args=effective,
            requested_args=self.requested_settings(model_kwargs, "predict"),
            checkpoint_design=descriptor.model_dump(mode="json"),
            save_dir=str(output.absolute()),
        )
        return frame

    def _class_names(self, weights: str | Path) -> dict[int, str]:
        descriptor = self._descriptor(weights)
        if descriptor is None:
            raise ValueError("Native detector checkpoint has no embedded class vocabulary")
        return dict(enumerate(descriptor.class_names))

    def reinfer_split(
        self,
        weights: str | Path,
        ground_truth: pd.DataFrame,
        split: str,
        output: Path,
        *,
        conf: float | None,
        iou: float,
        imgsz: int | list[int],
        batch: int,
        device: str | int | list[int] | None,
        image_name: str,
        native_project: Path,
        native_name: str,
        native_kwargs: dict[str, object] | None = None,
        reuse_existing: bool = True,
    ) -> tuple[pd.DataFrame, VocabularyReport]:
        arguments: _ReinferArguments = {
            "conf": conf,
            "iou": iou,
            "imgsz": imgsz,
            "batch": batch,
            "device": device,
            "image_name": image_name,
            "native_project": native_project,
            "native_name": native_name,
            "native_kwargs": native_kwargs,
            "reuse_existing": reuse_existing,
        }
        if self._descriptor(weights) is None:
            arguments["native_kwargs"] = self._legacy_prediction(
                arguments["native_kwargs"] or {}, comparison=True
            )
            return self.legacy.reinfer_split(weights, ground_truth, split, output, **arguments)
        from clearml_yolo.adapters.yolo.reinfer import reinfer_split

        return reinfer_split(
            weights,
            ground_truth,
            split,
            output,
            predictor=self.predict_on_images,
            class_names=self._class_names,
            write_settings=self.write_native_yaml,
            **arguments,
        )

    def train(
        self,
        task: TaskHandle | None,
        architecture: str | Path,
        settings: dict[str, Any],
        prepared: PreparedDataset,
    ) -> TrainResult:
        if self.config.backend == "ultralytics":
            return self.legacy.train(task, architecture, settings, prepared)
        if str(architecture) not in {
            self.config.preset,
            f"{self.config.backend}/{self.config.preset}",
        }:
            raise ValueError("Training architecture disagrees with the selected model preset")
        if task is None:
            raise ValueError("Native training requires an invocation-owned ClearML task")
        from clearml_yolo.adapters.clearml.detectors import (
            publish_detector_model,
            record_detector_arguments,
            report_metric,
        )

        native_values = {key: value for key, value in settings.items() if key not in _ROUTING}
        config = self.config.model_copy(
            update={"train": TrainSettings.model_validate(native_values)}
        )
        output = write_path(Path(settings["project"]) / str(settings["name"]))
        output.mkdir(parents=True, exist_ok=True)
        from clearml_yolo.adapters.clearml.session import record_run_configuration
        from clearml_yolo.adapters.integrations.batch_resolution import resolve_native_batch
        from clearml_yolo.adapters.runtime.distributed import (
            global_batch_per_rank,
            selected_gpu_indices,
        )

        config, batch_estimate = resolve_native_batch(config, prepared, self.transforms)
        if batch_estimate is not None:
            record_run_configuration(task, {"training_batch_estimate": batch_estimate})
        devices = selected_gpu_indices(config.train.device)
        global_batch_per_rank(config.train.batch, max(len(devices), 1))
        if config.backend == "deimv2":
            from clearml_yolo.adapters.deim.backend import train
        elif config.backend == "rfdetr":
            from clearml_yolo.adapters.rfdetr.backend import train
        elif config.backend == "fcos":
            from clearml_yolo.adapters.fcos.backend import train
        else:
            from clearml_yolo.adapters.fasterrcnn.backend import train

        arguments = {"transforms": self.transforms} if self.transforms is not None else {}
        if len(devices) > 1:
            from clearml_yolo.adapters.integrations.distributed_training import train_distributed

            result = train_distributed(
                config,
                prepared,
                output,
                lambda name, value, step: report_metric(task, name, value, step),
                devices=devices,
                transforms=self.transforms,
            )
        else:
            result = train(
                config,
                prepared,
                output,
                lambda name, value, step: report_metric(task, name, value, step),
                **arguments,
            )
        effective = settings | result.effective_args
        self.write_native_yaml(output / "native_train.yaml", effective, "train")
        record_detector_arguments(task, effective)
        descriptor = bind_checkpoint(result.weights, result.metadata)
        publish_detector_model(task, result.weights, descriptor, str(settings["name"]))
        return TrainResult(
            weights=result.weights,
            save_dir=output,
            effective_args=effective,
            cleaned_ground_truth=prepared.ground_truth,
            dataset_reference=prepared.data,
        )
