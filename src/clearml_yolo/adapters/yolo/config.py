"""Native parameter classification and documented YAML without model-runtime imports."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from importlib.metadata import distribution
from pathlib import Path
from typing import Any, Literal

import yaml

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


def requested_settings(settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
    values = _REQUESTED_DEVICES.get() or {}
    group = "ultralytics" if stage == "train" else "ultralytics_predict"
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
    return values


def prediction_defaults() -> dict[str, Any]:
    """Expose shared references and literal native prediction-only values."""
    defaults = native_defaults()
    values: dict[str, Any] = {
        key: f"${{ultralytics.{key}}}" if key in TRAIN_KEYS else value
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
