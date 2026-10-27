"""Native parameter classification and documented YAML without model-runtime imports."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from importlib.metadata import distribution
from pathlib import Path
from typing import Any, Literal

import yaml

from clearml_yolo.adapters.storage.filesystem import write_path

Stage = Literal["train", "predict"]
_REQUESTED_DEVICES: ContextVar[dict[str, Any] | None] = ContextVar(
    "requested_devices", default=None
)


@contextmanager
def requested_devices(values: dict[str, Any]) -> Iterator[None]:
    """Preserve device intent while availability checks select native execution ordinals."""
    token = _REQUESTED_DEVICES.set(values)
    try:
        yield
    finally:
        _REQUESTED_DEVICES.reset(token)


def requested_settings(
    settings: dict[str, Any], stage: Stage, *, group: str | None = None
) -> dict[str, Any]:
    values = _REQUESTED_DEVICES.get() or {}
    group = group or ("ultralytics" if stage == "train" else "ultralytics_predict")
    return settings | {"device": values[group]} if group in values else dict(settings)


# Classify keys explicitly: a dependency upgrade must not silently assign new settings
# to a stage. Training includes the validator run inside the native trainer.
SHARED_KEYS = frozenset(
    [
        "task",
        "mode",
        "model",
        "data",
        "batch",
        "imgsz",
        "save",
        "device",
        "project",
        "name",
        "exist_ok",
        "verbose",
        "rect",
        "compile",
        "channels_last",
        "conf",
        "iou",
        "max_det",
        "quantize",
        "nms",
        "augment",
        "agnostic_nms",
        "classes",
        "visualize",
        "save_txt",
        "save_conf",
        "show_labels",
        "show_conf",
    ]
)
TRAIN_KEYS = SHARED_KEYS | frozenset(
    [
        "epochs",
        "time",
        "patience",
        "save_period",
        "cache",
        "workers",
        "pretrained",
        "cls_remap",
        "optimizer",
        "seed",
        "deterministic",
        "single_cls",
        "cos_lr",
        "close_mosaic",
        "resume",
        "amp",
        "fraction",
        "profile",
        "freeze",
        "multi_scale",
        "val",
        "split",
        "save_json",
        "plots",
        "lr0",
        "lrf",
        "momentum",
        "weight_decay",
        "warmup_epochs",
        "warmup_momentum",
        "warmup_bias_lr",
        "distill_model",
        "dis",
        "box",
        "cls",
        "cls_pw",
        "dfl",
        "nbs",
        "hsv_h",
        "hsv_s",
        "hsv_v",
        "degrees",
        "translate",
        "scale",
        "shear",
        "perspective",
        "flipud",
        "fliplr",
        "bgr",
        "mosaic",
        "mixup",
        "cutmix",
    ]
)
TRAIN_KEYS = TRAIN_KEYS | {"augmentations"}
PREDICT_KEYS = SHARED_KEYS | frozenset(
    [
        "source",
        "dnn",
        "show",
        "save_crop",
        "show_boxes",
        "line_width",
    ]
)
INACTIVE_KEYS = frozenset(
    [
        "overlap_mask",
        "mask_ratio",
        "dropout",
        "pose",
        "kobj",
        "rle",
        "angle",
        "dlog",
        "dgrad",
        "dlam",
        "copy_paste",
        "copy_paste_mode",
        "auto_augment",
        "erasing",
        "vid_stride",
        "stream_buffer",
        "embed",
        "save_frames",
        "retina_masks",
        "format",
        "optimize",
        "dynamic",
        "simplify",
        "opset",
        "workspace",
        "cfg",
        "tracker",
    ]
)
KNOWN_KEYS = TRAIN_KEYS | PREDICT_KEYS | INACTIVE_KEYS
_KEY_LINE = re.compile(r"^([a-zA-Z_][\w]*):")

# Keep validation independent of the model SDK. These are the native parser's
# typed keys that this adapter forwards; untyped selectors retain native handling.
_NUMERIC_KEYS = frozenset(
    ["warmup_epochs", "box", "cls", "dfl", "dis", "degrees", "shear", "time", "batch"]
)
_FRACTION_KEYS = frozenset(
    [
        "lr0",
        "lrf",
        "cls_pw",
        "momentum",
        "weight_decay",
        "warmup_momentum",
        "warmup_bias_lr",
        "hsv_h",
        "hsv_s",
        "hsv_v",
        "translate",
        "perspective",
        "flipud",
        "fliplr",
        "bgr",
        "mosaic",
        "mixup",
        "cutmix",
        "conf",
        "iou",
        "fraction",
        "multi_scale",
    ]
)
_INTEGER_KEYS = frozenset(
    [
        "epochs",
        "patience",
        "workers",
        "seed",
        "close_mosaic",
        "max_det",
        "line_width",
        "nbs",
        "save_period",
    ]
)
_INTEGER_MINIMUMS = {"epochs": 1, "patience": 0, "nbs": 1, "max_det": 1, "seed": 0}
_BOOLEAN_KEYS = frozenset(
    [
        "save",
        "exist_ok",
        "verbose",
        "deterministic",
        "single_cls",
        "rect",
        "cos_lr",
        "val",
        "save_json",
        "dnn",
        "plots",
        "show",
        "save_txt",
        "save_conf",
        "save_crop",
        "show_labels",
        "show_conf",
        "visualize",
        "augment",
        "agnostic_nms",
        "show_boxes",
        "nms",
        "profile",
        "channels_last",
        "cls_remap",
    ]
)
_STRING_KEYS = frozenset({"optimizer", "split"})
_QUANTIZATION_VALUES = frozenset(
    ["8", "16", "32", "int8", "fp16", "fp32", "w8a8", "w16a16", "w32a32", "w8a16", "w8a32"]
)
_TYPE_GROUPS = (
    (_NUMERIC_KEYS, (int, float), "numeric"),
    (_INTEGER_KEYS, (int,), "an integer"),
    (_BOOLEAN_KEYS, (bool,), "a boolean"),
    (_STRING_KEYS, (str,), "a string"),
)
_SCALE_DIMENSIONS = 2


def _validate_fraction(key: str, value: Any, qualified: str) -> None:
    if key == "fraction":
        if isinstance(value, list):
            if (
                len(value) not in (2, 3)
                or not all(value[:2])
                or not all(
                    (type(item) is int and item >= 0) or (type(item) is float and 0 <= item <= 1)
                    for item in value
                )
            ):
                raise ValueError(f"{qualified} must contain train/val[/test] counts or ratios")
            return
        if isinstance(value, bool):
            raise ValueError(f"{qualified} must be a positive count or a ratio in (0, 1]")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{qualified} must be numeric")  # noqa: TRY004 - invalid configuration boundary
    if key == "fraction":
        if not (0 < value <= 1 or (isinstance(value, int) and value > 1)):
            raise ValueError(f"{qualified} must be a positive count or a ratio in (0, 1]")
    elif not 0 <= value <= 1:
        raise ValueError(f"{qualified} must be between 0 and 1")


def _validate_native_type(key: str, value: Any, qualified: str) -> None:
    for keys, accepted, description in _TYPE_GROUPS:
        if key in keys and not isinstance(value, accepted):
            raise ValueError(f"{qualified} must be {description}")
    minimum = _INTEGER_MINIMUMS.get(key)
    if minimum is not None and value < minimum:
        raise ValueError(f"{qualified} must be at least {minimum}")


def _validate_scale(value: Any, qualified: str) -> None:
    if isinstance(value, (list, tuple)):
        if len(value) != _SCALE_DIMENSIONS or not all(
            isinstance(item, (int, float)) for item in value
        ):
            raise ValueError(f"{qualified} must contain exactly two numeric values")
    elif not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{qualified} must be in [0, 1] or contain two numeric values")


def _validate_native_choice(key: str, value: Any, qualified: str) -> None:
    if key == "compile" and not isinstance(value, (bool, str)):
        raise ValueError(f"{qualified} must be a boolean or a compiler mode string")
    if (
        key == "amp"
        and not isinstance(value, bool)
        and str(value).lower() not in {"fp16", "bf16", "fp32"}
    ):
        raise ValueError(f"{qualified} must be a boolean or fp16, bf16, fp32")
    if key == "quantize" and str(value).lower() not in _QUANTIZATION_VALUES:
        raise ValueError(f"{qualified} must name a supported 8/16/32-bit quantization scheme")


def _validate_native_values(values: dict[str, Any], group: str) -> None:
    """Check native types/ranges without imports, effects or value normalization."""
    defaults = native_defaults()
    typed = (_NUMERIC_KEYS | _FRACTION_KEYS | _INTEGER_KEYS | _BOOLEAN_KEYS | _STRING_KEYS) | {
        "scale",
        "compile",
    }
    for key, value in values.items():
        qualified = f"{group}.{key}"
        if value is None:
            if key == "batch" and group == "ultralytics":
                continue
            if key == "amp" or (key in typed and defaults.get(key) is not None):
                raise ValueError(f"{qualified} must not be null")
            continue
        _validate_native_type(key, value, qualified)
        if key in _FRACTION_KEYS:
            _validate_fraction(key, value, qualified)
        elif key == "scale":
            _validate_scale(value, qualified)
        _validate_native_choice(key, value, qualified)


def native_template() -> str:
    """Locate the installed distribution without importing its expensive package."""
    package = distribution("ultralytics")
    path = Path(str(package.locate_file("ultralytics/cfg/default.yaml")))
    return path.read_text(encoding="utf-8")


def native_defaults() -> dict[str, Any]:
    """Return native values and explicit project defaults; reject unclassified upgrades."""
    loaded: dict[str, Any] = yaml.safe_load(native_template())
    unknown = set(loaded) - KNOWN_KEYS
    if unknown:
        raise ValueError(f"Unclassified Ultralytics parameters: {sorted(unknown)}")
    return loaded | {"imgsz": 960, "compile": True, "nms": True, "model": "yolo11n.pt"}


def stage_settings(settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
    """Project supplied native values onto the selected execution stage."""
    unknown = set(settings) - KNOWN_KEYS - {"save_dir"}
    if unknown:
        raise ValueError(f"Unknown Ultralytics parameters: {sorted(unknown)}")
    if settings.get("cfg") is not None:
        raise ValueError("Native cfg must be null")
    allowed = TRAIN_KEYS if stage == "train" else PREDICT_KEYS
    return {key: value for key, value in settings.items() if key in allowed}


def execution_settings(settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
    """Validate a complete resolved owning group without introducing defaults."""
    values = stage_settings(settings, stage)
    group = "ultralytics" if stage == "train" else "ultralytics_predict"
    allowed = TRAIN_KEYS if stage == "train" else PREDICT_KEYS
    missing = (native_defaults().keys() & allowed) - values.keys()
    if missing:
        raise ValueError(
            f"Missing {group} parameters {sorted(missing)}; compose a complete {group} group"
        )
    if values["task"] != "detect":
        raise ValueError(f"{group}.task must be detect")
    if values["mode"] != stage:
        raise ValueError(f"{group}.mode must be {stage}")
    if settings.get("embed") is not None:
        raise ValueError("embed is unsupported for detection records; remove its override")
    size = values["imgsz"]
    dimensions = size if isinstance(size, list) else [size]
    if (
        not dimensions
        or (stage == "predict" and len(dimensions) not in (1, 2))
        or any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in dimensions)
    ):
        raise ValueError(f"{group}.imgsz must contain positive integer image dimensions")
    if stage == "predict":
        batch = values["batch"]
        if isinstance(batch, bool) or not isinstance(batch, int) or batch < 1:
            raise ValueError("Prediction requires a positive integer ultralytics_predict.batch")
    _validate_native_values(values, group)
    return values


def prediction_defaults(*, inherit: bool = True) -> dict[str, Any]:
    """Expose prediction defaults, optionally resolving inherited training values."""
    defaults = native_defaults()
    values: dict[str, Any] = {
        key: f"${{ultralytics.{key}}}" if inherit and key in TRAIN_KEYS else value
        for key, value in defaults.items()
        if key in PREDICT_KEYS
    }
    values.update(
        conf=0.001,
        model=None,
        mode="predict",
        project=None,
        name=None,
        batch=1,
        rect=True,
        save=False,
        verbose=False,
        device=[-1],
    )
    return values


def _value_yaml(key: str, value: Any) -> str:
    # Flow style keeps nested lists/maps on a single logical parameter line and safely
    # quotes strings containing YAML syntax. A large width avoids folded scalars.
    dumped = yaml.safe_dump(
        {key: value}, default_flow_style=False, width=100000, allow_unicode=True, sort_keys=False
    )
    if "\n" in dumped.rstrip("\n"):
        scalar = (
            yaml.safe_dump(value, default_flow_style=True, width=100000, allow_unicode=True)
            .removesuffix("...\n")
            .strip()
        )
        return f"{key}: {scalar}"
    return dumped.rstrip("\n")


def render_native_yaml(settings: dict[str, Any], stage: Stage, *, example: bool = False) -> str:
    """Keep every upstream comment and comment out inactive parameter entries."""
    values = stage_settings(settings, stage)
    allowed = TRAIN_KEYS if stage == "train" else PREDICT_KEYS
    lines = []
    for line in native_template().splitlines():
        match = _KEY_LINE.match(line)
        if match is None:
            lines.append(line)
            continue
        key = match.group(1)
        active = key in allowed and key in values
        if not active:
            lines.append(f"# {line}")
            continue
        comment = line.partition(" #")[2]
        rendered = _value_yaml(key, values[key])
        lines.append(rendered + (f" #{comment}" if comment else ""))
    additional = values.keys() - native_defaults().keys()
    if additional:
        lines.extend(["", "# Additional native parameters (not listed in upstream default.yaml)"])
        lines.extend(_value_yaml(key, values[key]) for key in sorted(additional))
    if example:
        return _example_sections(lines, stage)
    return "\n".join(lines) + "\n"


def _example_sections(lines: list[str], stage: Stage) -> str:
    """Move documented parameter blocks together without changing runtime rendering."""
    controlled = {"task", "mode", "data", "project", "name"}
    if stage == "predict":
        controlled |= {"source", "model"}
    sections: list[list[str]] = [[], [], []]
    pending: list[str] = []
    for line in lines:
        match = _KEY_LINE.match(line.removeprefix("# "))
        if match is None:
            pending.append(line)
            continue
        section = 1 if match.group(1) in controlled else (2 if line.startswith("# ") else 0)
        rendered = f"# {line}" if section == 1 and not line.startswith("# ") else line
        sections[section].extend([*pending, rendered])
        pending = []
    sections[-1].extend(pending)
    headings = (
        "Active detection settings",
        "cy-controlled settings",
        "Stage-inapplicable settings",
    )
    return (
        "\n\n".join(
            f"# {heading}\n" + "\n".join(section)
            for heading, section in zip(headings, sections, strict=True)
        )
        + "\n"
    )


def write_native_yaml(path: Path, settings: dict[str, Any], stage: Stage) -> Path:
    """Write a self-contained native configuration beside its stage outputs."""
    path = write_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_native_yaml(settings, stage), encoding="utf-8")
    return path


def prediction_settings(
    ultralytics_predict: dict[str, Any],
    weights: str | Path | None = None,
) -> dict[str, Any]:
    """Consume only the resolved prediction group and explicit checkpoint ownership."""
    settings = execution_settings(dict(ultralytics_predict), "predict")
    native_model = settings["model"]
    if weights is not None and native_model is not None and str(weights) != str(native_model):
        raise ValueError("weights conflicts with ultralytics_predict.model")
    if weights is not None:
        settings["model"] = str(weights)
    if settings["source"] is not None:
        raise ValueError("ultralytics source is owned by ground_truth image membership")
    return settings
