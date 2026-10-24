"""Native DEIM solver and postprocessing behind the portable detector interface.

The un-packaged upstream registry, config and model objects are intentionally opaque
here. No SDK, task or telemetry ownership is imported from ClearML.
"""

import importlib
import importlib.metadata
import math
from collections.abc import Callable, Sequence
from contextlib import chdir
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from clearml_yolo.adapters.deim.source import REVISION, load_source, native_coco_modules
from clearml_yolo.adapters.deim.transforms import (
    TrainingTransform,
    bridge_transforms,
    custom_training_recipe,
)
from clearml_yolo.adapters.observability.progress import image_progress
from clearml_yolo.adapters.storage.filesystem import validate_output_tree
from clearml_yolo.application.contracts import PREDICTION_COLUMNS, PreparedDataset
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    Device,
    ImageSize,
    ModelConfig,
    PredictSettings,
    Preprocessing,
)
from clearml_yolo.core.transforms import TransformConfig

_DEFAULT_IOU = 0.7
_MINIMUM_SIZE = 128
_STRIDE = 32


def _size(value: ImageSize) -> tuple[int, int]:
    height, width = (value, value) if isinstance(value, int) else value
    if min(height, width) < _MINIMUM_SIZE or height % 32 or width % 32:
        raise ValueError("DEIMv2 dimensions must be divisible by 32 and at least 128")
    return height, width


def _device(value: Device) -> str:
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("DEIMv2 multi-device execution is unsupported by this adapter")
        value = value[0]
    if isinstance(value, int) or (isinstance(value, str) and value.isdecimal()):
        return f"cuda:{value}"
    if value is None:
        torch = importlib.import_module("torch")
        return "cuda" if torch.cuda.is_available() else "cpu"
    if "," in value:
        raise ValueError("DEIMv2 multi-device execution is unsupported by this adapter")
    if value not in {"cpu", "cuda"} and not value.startswith("cuda:"):
        raise ValueError(f"DEIMv2 device {value!r} is unsupported; use CPU or one CUDA device")
    return value


class _OwnerWriter:
    def __init__(self, report: Callable[[str, float, int], None]) -> None:
        self.report = report
        self.metrics: dict[str, float] = {}

    def add_scalar(self, tag: str, value: float, step: int) -> None:
        if math.isfinite(value):
            self.metrics[tag] = value
            self.report(tag, value, step)

    def add_text(self, _tag: str, _value: str, _step: int) -> None:
        """Native config is returned as structured effective_args, not text telemetry."""

    def close(self) -> None:
        """The writer owns no files or background resources."""


def _native_writer(report: Callable[[str, float, int], None]) -> _OwnerWriter:
    tensorboard = importlib.import_module("torch.utils.tensorboard")
    # BaseConfig's public writer setter requires an actual SummaryWriter instance.
    # Our mixin handles every native call and owns no TensorBoard resources.
    writer_type = type("OwnerWriter", (_OwnerWriter, tensorboard.SummaryWriter), {})
    return cast(_OwnerWriter, writer_type(report))


def _config(config: ModelConfig, names: tuple[str, ...], size: tuple[int, int]) -> Any:
    source = config.source_dir
    if source is None:
        from clearml_yolo.adapters.assets.sources import prepare_deim_source

        source, _ = prepare_deim_source()
    core, _ = load_source(source)
    path = source / "configs" / "deimv2" / f"deimv2_dinov3_{config.preset}_coco.yml"
    cfg = core.YAMLConfig(
        str(path.resolve()),
        num_classes=len(names),
        remap_mscoco_category=False,
        eval_spatial_size=list(size),
    )
    # Even prediction must not accidentally initialize from an upstream cwd-relative asset.
    cfg.yaml_cfg["DINOv3STAs"]["weights_path"] = None
    return cfg


def _prepare_loaders(
    cfg: Any,
    prepared: PreparedDataset,
    config: ModelConfig,
    transforms: TransformConfig | None = None,
) -> None:
    height, width = _size(config.train.imgsz)
    if height != width:
        raise ValueError("DEIMv2 native multiscale training requires a square imgsz")
    for split, folder_name in (("train", "train"), ("val", "valid")):
        folder = prepared.data.parent / folder_name
        loader = cfg.yaml_cfg[f"{split}_dataloader"]
        loader["dataset"].update(
            img_folder=str(folder), ann_file=str(folder / "_annotations.coco.json")
        )
        loader.update(total_batch_size=config.train.batch, num_workers=config.train.workers)
        loader["drop_last"] = False
        if split == "train" and transforms is not None and transforms.mode == "albumentations":
            custom_training_recipe(loader["dataset"]["transforms"], loader["collate_fn"])
        for operation in loader["dataset"]["transforms"]["ops"]:
            if operation["type"] == "Resize":
                operation["size"] = [height, width]
            elif operation["type"] == "Mosaic":
                operation["output_size"] = height // 2
        loader["collate_fn"]["base_size"] = height
    for loader in (cfg.train_dataloader, cfg.val_dataloader):
        # The native dataset deliberately exposes its configured callable through this
        # pinned private field. Replacing objects here leaves the upstream registry intact.
        bridge_transforms(loader.dataset._transforms)  # noqa: SLF001
        if loader.collate_fn.scales is not None:
            loader.collate_fn.scales = [
                scale for scale in loader.collate_fn.scales if scale >= _MINIMUM_SIZE
            ]
    if transforms is not None and transforms.mode == "albumentations":
        dataset = cfg.train_dataloader.dataset
        # Replace only this training dataset instance, never the upstream registry.
        dataset._transforms = TrainingTransform(  # noqa: SLF001
            dataset,
            dataset._transforms,  # noqa: SLF001
            transforms,
            config.train.seed,
        )


def _validate_training(config: ModelConfig) -> None:
    if config.source_dir is None:
        raise ValueError("DEIMv2 requires source_dir pointing to the approved upstream checkout")
    if config.train.grad_accum_steps != 1:
        raise ValueError("DEIMv2 native grad_accum_steps other than 1 is unsupported")
    for weights in (config.train.weights, config.train.backbone_weights):
        if weights is not None and not weights.is_file():
            raise FileNotFoundError(weights)
    if (
        config.train.pretrained
        and config.train.weights is None
        and config.train.backbone_weights is None
    ):
        raise ValueError("DEIMv2 pretrained training requires explicit weights or backbone_weights")


def _validate_tuning(model: Any, weights: Path) -> None:
    torch = importlib.import_module("torch")
    payload = torch.load(weights, map_location="cpu", weights_only=True)
    expected = payload["ema"]["module"] if "ema" in payload else payload["model"]
    backbone = {
        key: value for key, value in model.state_dict().items() if key.startswith("backbone.")
    }
    # Native tuning silently drops incompatible keys. Require the full unchanged
    # backbone while retaining its native class-head adjustment for new vocabularies.
    if not backbone or not all(
        key in expected and value.shape == expected[key].shape for key, value in backbone.items()
    ):
        raise ValueError("DEIMv2 full weights do not contain a compatible backbone")


def _fit(solver: Any, output: Path) -> None:
    output = validate_output_tree(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Native numerical diagnostics use cwd-relative NaN.pth; keep them in this run.
    with chdir(output):
        solver.fit()


def train(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
    *,
    transforms: TransformConfig | None = None,
) -> BackendTrainResult:
    output = validate_output_tree(output)
    _validate_training(config)
    output = output.resolve()
    prepared = prepared.model_copy(update={"data": prepared.data.resolve()})
    contents = yaml.safe_load(prepared.data.read_text())
    configured_names = contents["names"]
    names = (
        tuple(configured_names[key] for key in sorted(configured_names))
        if isinstance(configured_names, dict)
        else tuple(configured_names)
    )
    size = _size(config.train.imgsz)
    device = _device(config.train.device)
    cfg = _config(config, names, size)
    _, solver_module = load_source(config.source_dir)
    native_misc = importlib.import_module(
        solver_module.__package__.rsplit(".", 1)[0] + ".misc.dist_utils"
    )
    native_misc.setup_seed(config.train.seed)
    cfg.yaml_cfg.update(
        device=device,
        epoches=config.train.epochs,
        output_dir=str(output),
        use_amp=config.train.amp and device != "cpu",
        use_ema=config.train.use_ema,
        sync_bn=False,
    )
    # YAMLConfig copies scalar fields into BaseConfig during __init__, before these changes.
    cfg.device = device
    cfg.epoches = config.train.epochs
    cfg.output_dir = str(output)
    cfg.use_amp = config.train.amp and device != "cpu"
    cfg.use_ema = config.train.use_ema
    cfg.sync_bn = False
    cfg.yaml_cfg["DINOv3STAs"]["weights_path"] = (
        str(config.train.backbone_weights.resolve()) if config.train.backbone_weights else None
    )
    cfg.yaml_cfg["optimizer"]["lr"] = config.train.lr
    cfg.yaml_cfg["optimizer"]["weight_decay"] = config.train.weight_decay
    writer = _native_writer(report)
    cfg.writer = writer
    with native_coco_modules():
        _prepare_loaders(cfg, prepared, config, transforms)
    if config.train.weights is not None:
        cfg.tuning = str(config.train.weights.resolve())
        cfg.yaml_cfg["tuning"] = cfg.tuning
        _validate_tuning(cfg.model, config.train.weights.resolve())
    solver = solver_module.TASKS["detection"](cfg)
    try:
        _fit(solver, output)
    finally:
        writer.close()
    stage_two = output / "best_stg2.pth"
    weights = stage_two if stage_two.is_file() else output / "best_stg1.pth"
    if not weights.is_file():
        raise RuntimeError("DEIMv2 native training did not produce a stage-best checkpoint")
    metadata = CheckpointMetadata(
        backend="deimv2",
        preset=config.preset,
        class_names=names,
        preprocessing=Preprocessing(resize="stretch", size=config.train.imgsz),
        dependencies={
            name: importlib.metadata.version(name)
            for name in ("torch", "torchvision", "faster-coco-eval")
        },
        source_revision=REVISION,
    )
    return BackendTrainResult(
        weights=weights,
        metadata=metadata,
        effective_args=cfg.yaml_cfg,
        metrics=writer.metrics,
        artifacts=[path for path in (output / "log.txt",) if path.is_file()],
    )


def _load_weights(model: Any, weights: Path) -> None:
    torch = importlib.import_module("torch")
    payload = torch.load(weights, map_location="cpu", weights_only=True)
    state = payload["ema"]["module"] if "ema" in payload else payload["model"]
    model.load_state_dict(state)


def _native_predict(
    cfg: Any,
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
    size: tuple[int, int],
) -> list[dict[str, Any]]:
    torch = importlib.import_module("torch")
    functional = importlib.import_module("torchvision.transforms.v2.functional")
    image_module = importlib.import_module("PIL.Image")
    device = _device(settings.device)
    model = cfg.model.to(device).eval()
    _load_weights(model, weights)
    postprocessor = cfg.postprocessor.to(device)
    rows: list[dict[str, Any]] = []
    with image_progress(len(image_paths)) as advance, torch.inference_mode():
        for offset in range(0, len(image_paths), settings.batch):
            paths = image_paths[offset : offset + settings.batch]
            tensors, originals = [], []
            for path in paths:
                with image_module.open(path) as source:
                    image = source.convert("RGB")
                    # Native xyxy scaling repeats [width, height], unlike many DETR APIs.
                    originals.append([image.width, image.height])
                    tensor = functional.pil_to_tensor(image).float() / 255
                tensor = functional.resize(tensor, list(size))
                tensors.append(
                    functional.normalize(
                        tensor, descriptor.preprocessing.mean, descriptor.preprocessing.std
                    )
                )
            outputs = model(torch.stack(tensors).to(device))  # noqa: PD013 -- Torch, not pandas
            predictions = postprocessor(outputs, torch.tensor(originals, device=device))
            for path, prediction in zip(paths, predictions, strict=True):
                rows.extend(_rows(path, prediction, descriptor.class_names, settings))
            advance(len(paths))
    return rows


def _rows(
    path: str,
    prediction: Any,
    names: tuple[str, ...],
    settings: PredictSettings,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for box, score, label in zip(
        prediction["boxes"].cpu().tolist(),
        prediction["scores"].cpu().tolist(),
        prediction["labels"].cpu().tolist(),
        strict=True,
    ):
        if not 0 <= label < len(names) or score < settings.conf:
            continue
        rows.append(
            dict(
                zip(
                    PREDICTION_COLUMNS,
                    [path, names[label], float(score), *map(float, box)],
                    strict=True,
                )
            )
        )
        if len(rows) >= settings.max_det:
            break
    return rows


def predict(
    config: ModelConfig,
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    if descriptor.preprocessing.resize != "stretch" or descriptor.preprocessing.stride != _STRIDE:
        raise ValueError("Checkpoint preprocessing is incompatible with native DEIMv2")
    if settings.iou != _DEFAULT_IOU or settings.half:
        raise ValueError("DEIMv2 nondefault iou and half controls are unsupported")
    size = _size(settings.imgsz or descriptor.preprocessing.size)
    rows: list[dict[str, Any]] = []
    if image_paths:
        if not weights.is_file():
            raise FileNotFoundError(weights)
        native_config = config.model_copy(update={"preset": descriptor.preset})
        cfg = _config(native_config, descriptor.class_names, size)
        cfg.yaml_cfg["PostProcessor"]["num_top_queries"] = min(
            settings.max_det,
            cfg.yaml_cfg["DEIMTransformer"]["num_queries"] * len(descriptor.class_names),
        )
        rows = _native_predict(cfg, descriptor, weights, image_paths, settings, size)
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    frame.attrs.update(
        image_paths=list(image_paths),
        normalized_imgsz=list(size),
        effective_args=settings.model_dump(mode="json")
        | {
            "backend": config.backend,
            "preset": descriptor.preset,
            "imgsz": list(size),
            "nms": False,
            "model": str(weights),
        },
    )
    return frame
