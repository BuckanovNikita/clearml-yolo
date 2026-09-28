"""Native parameter classification and documented YAML without model-runtime imports."""

import re
from importlib.metadata import distribution
from pathlib import Path
from typing import Any, Literal

import yaml

Stage = Literal["train", "predict"]

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
        "dnn",
        "end2end",
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
# Native get_cfg also accepts compatibility aliases absent from default.yaml.
SHARED_KEYS = SHARED_KEYS | {"half", "int8"}
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
        "overlap_mask",
        "mask_ratio",
        "dropout",
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
        "pose",
        "kobj",
        "rle",
        "angle",
        "dlog",
        "dgrad",
        "dlam",
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
        "copy_paste",
        "copy_paste_mode",
        "auto_augment",
        "erasing",
    ]
)
TRAIN_KEYS = TRAIN_KEYS | {"augmentations"}
PREDICT_KEYS = SHARED_KEYS | frozenset(
    [
        "source",
        "vid_stride",
        "stream_buffer",
        "embed",
        "show",
        "save_frames",
        "retina_masks",
        "save_crop",
        "show_boxes",
        "line_width",
    ]
)
INACTIVE_KEYS = frozenset(
    [
        "format",
        "keras",
        "optimize",
        "dynamic",
        "simplify",
        "opset",
        "workspace",
        "nms",
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
    """Return upstream values, refusing unclassified dependency changes."""
    loaded: dict[str, Any] = yaml.safe_load(native_template())
    unknown = set(loaded) - KNOWN_KEYS
    if unknown:
        raise ValueError(f"Unclassified Ultralytics parameters: {sorted(unknown)}")
    return loaded


def stage_settings(settings: dict[str, Any], stage: Stage) -> dict[str, Any]:
    """Project a complete upstream mapping onto the selected execution stage."""
    unknown = set(settings) - KNOWN_KEYS - {"save_dir"}
    if unknown:
        raise ValueError(f"Unknown Ultralytics parameters: {sorted(unknown)}")
    if settings.get("cfg") is not None:
        raise ValueError("Native cfg loading was removed; use the ultralytics Hydra group")
    allowed = TRAIN_KEYS if stage == "train" else PREDICT_KEYS
    return {key: value for key, value in settings.items() if key in allowed}


def prediction_defaults() -> dict[str, Any]:
    """Inherit shared values lazily so CLI base overrides reach prediction."""
    values: dict[str, Any] = {
        key: f"${{ultralytics.{key}}}" for key in native_defaults() if key in PREDICT_KEYS
    }
    # These values are stage-owned, rather than training hyperparameters to inherit.
    values.update(conf=0.001, model=None, mode="predict", project=None, name=None)
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


def render_native_yaml(
    settings: dict[str, Any], stage: Stage, *, overrides_only: bool = False
) -> str:
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
        active = key in allowed and (not overrides_only or key in values)
        if not active:
            lines.append(f"# {line}")
            continue
        if key not in values:
            lines.append(line)
            continue
        comment = line.partition(" #")[2]
        rendered = _value_yaml(key, values[key])
        lines.append(rendered + (f" #{comment}" if comment else ""))
    additional = values.keys() - native_defaults().keys()
    if additional:
        lines.extend(["", "# Additional native parameters (not listed in upstream default.yaml)"])
        lines.extend(_value_yaml(key, values[key]) for key in sorted(additional))
    return "\n".join(lines) + "\n"


def write_native_yaml(path: Path, settings: dict[str, Any], stage: Stage) -> Path:
    """Write a self-contained native configuration beside its stage outputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_native_yaml(settings, stage), encoding="utf-8")
    return path


def prediction_settings(
    ultralytics: dict[str, Any],
    ultralytics_predict: dict[str, Any] | None = None,
    weights: str | Path | None = None,
) -> dict[str, Any]:
    """Merge stage settings while preserving explicit prediction overrides."""
    overrides = ultralytics_predict or {}
    native_model = overrides.get("model")
    if weights is not None and native_model is not None and str(weights) != str(native_model):
        raise ValueError("weights conflicts with ultralytics_predict.model")
    settings = stage_settings(dict(ultralytics) | overrides, "predict")
    selected_model = weights or native_model or ultralytics.get("model")
    if selected_model is not None:
        settings["model"] = str(selected_model)
    if settings.get("source") is not None:
        raise ValueError("ultralytics source is owned by ground_truth image membership")
    batch = settings.get("batch", 1)
    if isinstance(batch, bool) or not isinstance(batch, int) or batch < 1:
        raise ValueError("Prediction requires a positive integer ultralytics_predict.batch")
    return settings
