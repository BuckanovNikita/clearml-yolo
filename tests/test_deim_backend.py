"""DEIM boundaries reject missing weights and retain source and image identity."""

import importlib
import sys
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import (
    CheckpointMetadata,
    ModelConfig,
    PredictSettings,
    Preprocessing,
    TrainSettings,
)


def test_deim_rows_preserve_lexical_labels_and_filter_foreground_indices() -> None:
    import torch

    from clearml_yolo.adapters.deim.backend import _rows

    predictions = {
        "boxes": torch.tensor([[1, 2, 30, 40]] * 6),
        "scores": torch.tensor([0.9, 0.9, 0.1, 0.75, 0.5, 0.9]),
        "labels": torch.tensor([-1, 2, 0, 0, 1, 0]),
    }
    rows = _rows("image.png", predictions, ("0001", "1"), PredictSettings(conf=0.25, max_det=2))
    assert rows == [
        {
            "image_name": "image.png",
            "instance_label": label,
            "confidence": score,
            "bbox_x_tl": 1.0,
            "bbox_y_tl": 2.0,
            "bbox_x_br": 30.0,
            "bbox_y_br": 40.0,
        }
        for label, score in (("0001", 0.75), ("1", 0.5))
    ]


@pytest.mark.parametrize(
    ("device", "expected_device", "expected_amp"), [("cpu", "cpu", False), (2, "cuda:2", True)]
)
def test_deim_train_applies_native_recipe_before_solver_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    device: str | int,
    expected_device: str,
    expected_amp: bool,
) -> None:
    from clearml_yolo.adapters.deim import backend

    data = tmp_path / "data.yaml"
    data.write_text('names: ["0001", "1"]\n')
    prepared = PreparedDataset(
        data=data,
        ground_truth=tmp_path / "gt.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="coco",
        artifacts=[],
    )
    loaders = [
        SimpleNamespace(
            dataset=SimpleNamespace(_transforms=SimpleNamespace(transforms=[])),
            collate_fn=SimpleNamespace(scales=[96, 128, 256]),
        )
        for _ in range(2)
    ]
    native = SimpleNamespace(
        yaml_cfg={
            "DINOv3STAs": {"weights_path": "upstream-default.pth"},
            "optimizer": {"lr": 1.0, "weight_decay": 1.0},
            **{
                f"{split}_dataloader": {
                    "dataset": {"transforms": {"ops": [{"type": "Resize"}, {"type": "Mosaic"}]}},
                    "collate_fn": {},
                }
                for split in ("train", "val")
            },
        },
        train_dataloader=loaders[0],
        val_dataloader=loaders[1],
    )
    constructor_calls: list[tuple[str, dict[str, Any]]] = []
    seeds: list[int] = []
    solver_configs: list[Any] = []
    output = tmp_path / "output"

    def yaml_config(path: str, **kwargs: Any) -> Any:
        constructor_calls.append((path, kwargs))
        return native

    def make_solver(cfg: Any) -> Any:
        solver_configs.append(cfg)
        expected = {
            "device": expected_device,
            "epoches": 7,
            "output_dir": str(output),
            "use_amp": expected_amp,
            "use_ema": False,
            "sync_bn": False,
        }
        assert {name: getattr(cfg, name) for name in expected} == expected
        assert {name: cfg.yaml_cfg[name] for name in expected} == expected
        return SimpleNamespace(fit=lambda: (output / "best_stg1.pth").write_bytes(b"best"))

    solver = SimpleNamespace(__package__="private.engine.solver", TASKS={"detection": make_solver})
    monkeypatch.setattr(
        backend, "load_source", lambda _path: (SimpleNamespace(YAMLConfig=yaml_config), solver)
    )
    monkeypatch.setattr(backend, "native_coco_modules", nullcontext)
    monkeypatch.setattr(backend, "_native_writer", backend._OwnerWriter)
    native_misc = ModuleType("private.engine.misc.dist_utils")
    monkeypatch.setattr(native_misc, "setup_seed", seeds.append, raising=False)
    monkeypatch.setitem(sys.modules, native_misc.__name__, native_misc)
    monkeypatch.setattr(
        "clearml_yolo.adapters.deim.backend.importlib.metadata.version",
        lambda _name: "test-version",
    )
    result = backend.train(
        ModelConfig(
            backend="deimv2",
            preset="s",
            source_dir=tmp_path,
            train=TrainSettings(
                pretrained=False,
                device=device,
                epochs=7,
                imgsz=256,
                batch=3,
                workers=2,
                seed=19,
                amp=True,
                use_ema=False,
                lr=0.002,
                weight_decay=0.003,
            ),
        ),
        prepared,
        output,
        lambda *_args: None,
    )
    assert constructor_calls == [
        (
            str(tmp_path / "configs/deimv2/deimv2_dinov3_s_coco.yml"),
            {"num_classes": 2, "remap_mscoco_category": False, "eval_spatial_size": [256, 256]},
        )
    ]
    assert solver_configs == [native]
    assert seeds == [19]
    assert result.weights == output / "best_stg1.pth"
    assert result.metadata.class_names == ("0001", "1")
    assert result.effective_args == native.yaml_cfg
    assert result.effective_args["DINOv3STAs"]["weights_path"] is None
    assert result.effective_args["optimizer"] == {"lr": 0.002, "weight_decay": 0.003}
    for split, folder in (("train", "train"), ("val", "valid")):
        loader = result.effective_args[f"{split}_dataloader"]
        assert loader["total_batch_size"] == 3
        assert loader["num_workers"] == 2
        assert loader["drop_last"] is False
        assert loader["dataset"]["img_folder"] == str(tmp_path / folder)
        assert loader["dataset"]["ann_file"] == str(tmp_path / folder / "_annotations.coco.json")
        assert loader["dataset"]["transforms"]["ops"] == [
            {"type": "Resize", "size": [256, 256]},
            {"type": "Mosaic", "output_size": 128},
        ]
        assert loader["collate_fn"]["base_size"] == 256
    assert all(loader.collate_fn.scales == [128, 256] for loader in loaders)


def test_deim_missing_source_is_actionable(tmp_path: Path) -> None:
    from clearml_yolo.adapters.deim.backend import train

    prepared = PreparedDataset(
        data=Path("data.yaml"),
        ground_truth=Path("gt.csv"),
        manifest=Path("manifest.json"),
        dataset_format="flat",
        artifacts=[],
    )
    with pytest.raises(ValueError, match="source_dir"):
        train(
            ModelConfig(backend="deimv2", preset="s"), prepared, tmp_path / "out", lambda *_: None
        )


def test_deim_pretrained_never_silently_falls_back_to_random(tmp_path: Path) -> None:
    from clearml_yolo.adapters.deim.backend import train

    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "gt.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="flat",
        artifacts=[],
    )
    config = ModelConfig(backend="deimv2", preset="s", source_dir=tmp_path)
    with pytest.raises(ValueError, match=r"pretrained.*weights"):
        train(config, prepared, tmp_path / "out", lambda *_: None)


def test_deim_empty_request_retains_population_without_upstream_import() -> None:
    from clearml_yolo.adapters.deim.backend import predict

    descriptor = CheckpointMetadata(
        backend="deimv2",
        preset="s",
        class_names=("square",),
        preprocessing=Preprocessing(resize="stretch", size=128),
    )
    frame = predict(
        ModelConfig(backend="deimv2", preset="s"),
        descriptor,
        Path("unused.pth"),
        [],
        PredictSettings(),
    )
    assert frame.empty
    assert frame.attrs["image_paths"] == []
    assert frame.attrs["normalized_imgsz"] == [128, 128]


def test_deim_accumulation_is_not_silently_ignored(tmp_path: Path) -> None:
    from clearml_yolo.adapters.deim.backend import train

    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "gt.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="flat",
        artifacts=[],
    )
    config = ModelConfig(
        backend="deimv2",
        preset="s",
        source_dir=tmp_path,
        train=TrainSettings(pretrained=False, grad_accum_steps=2),
    )
    with pytest.raises(ValueError, match="grad_accum_steps"):
        train(config, prepared, tmp_path / "out", lambda *_: None)


def test_deim_native_writer_forwards_scalars_without_tensorboard_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from torch.utils.tensorboard import SummaryWriter

    from clearml_yolo.adapters.deim.backend import _native_writer

    monkeypatch.chdir(tmp_path)
    reported: list[tuple[str, float, int]] = []
    writer = _native_writer(lambda name, value, step: reported.append((name, value, step)))
    assert isinstance(writer, SummaryWriter)
    writer.add_scalar("Loss/total", 2.5, 3)
    writer.add_scalar("Loss/total", float("nan"), 4)
    writer.close()
    assert reported == [("Loss/total", 2.5, 3)]
    assert not list(tmp_path.iterdir())


def test_deim_legacy_transform_bridge_preserves_native_operation() -> None:
    from clearml_yolo.adapters.deim.transforms import bridge_transforms

    tv_tensors = importlib.import_module("torchvision.tv_tensors")
    v2 = importlib.import_module("torchvision.transforms.v2")

    class LegacyBoxes:
        _transformed_types = (tv_tensors.BoundingBoxes,)

        def __init__(self, fmt: str, *, normalize: bool) -> None:
            v2.Transform.__init__(self)
            self.fmt = fmt
            self.normalize = normalize

        def _transform(self, value: Any, _params: dict[str, Any]) -> Any:
            return value / 64

    legacy_type = type("ConvertBoxes", (LegacyBoxes, v2.Transform), {})
    original = legacy_type("xyxy", normalize=True)
    operation = SimpleNamespace(transforms=[original])
    boxes = tv_tensors.BoundingBoxes([[16.0, 8.0, 32.0, 48.0]], format="XYXY", canvas_size=(64, 64))
    with pytest.raises(NotImplementedError):
        original(boxes)
    bridge_transforms(operation)
    result = operation.transforms[0](boxes)
    assert result.tolist() == [[0.25, 0.125, 0.5, 0.75]]
    # The compatibility object does not mutate the native class or original object.
    with pytest.raises(NotImplementedError):
        original(boxes)


def test_deim_failed_import_removes_partial_private_package(tmp_path: Path) -> None:
    from clearml_yolo.adapters.deim.source import _load_package

    engine = tmp_path / "engine"
    engine.mkdir()
    (engine / "__init__.py").write_text("raise ValueError('failed native import')\n")
    with pytest.raises(ValueError, match="failed native import"):
        _load_package("_test_deim_failed_import", engine)
    assert "_test_deim_failed_import" not in sys.modules


def test_deim_native_failure_scratch_stays_inside_output_and_restores_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.deim.backend import _fit

    monkeypatch.chdir(tmp_path)

    class Solver:
        def fit(self) -> None:
            Path("NaN.pth").write_bytes(b"native diagnostic")
            raise RuntimeError("native numerical failure")

    with pytest.raises(RuntimeError, match="native numerical failure"):
        _fit(Solver(), Path("native-output"))
    assert (tmp_path / "native-output" / "NaN.pth").read_bytes() == b"native diagnostic"
    assert not (tmp_path / "NaN.pth").exists()
    assert Path.cwd() == tmp_path


@pytest.mark.parametrize("failure", ["revision", "tracked", "untracked"])
def test_deim_rejects_unapproved_source_before_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    from clearml_yolo.adapters.deim import source

    engine = tmp_path / "engine"
    engine.mkdir()
    (engine / "__init__.py").write_text("raise AssertionError('source was imported')\n")
    monkeypatch.setattr("clearml_yolo.adapters.deim.source.shutil.which", lambda _: "/usr/bin/git")

    def run(command: list[str], **_kwargs: Any) -> Any:
        if "rev-parse" in command:
            return SimpleNamespace(stdout="wrong" if failure == "revision" else source.REVISION)
        if "diff" in command:
            return SimpleNamespace(returncode=int(failure == "tracked"))
        return SimpleNamespace(stdout=b"engine/core/shadow.py\n" if failure == "untracked" else b"")

    monkeypatch.setattr("clearml_yolo.adapters.deim.source.subprocess.run", run)
    with pytest.raises(ValueError, match=r"revision|differ|untracked"):
        source.load_source(tmp_path)


@pytest.mark.parametrize("case", ["compatible", "wrong_shape", "empty"])
def test_deim_full_pretrained_checkpoint_requires_compatible_backbone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    from clearml_yolo.adapters.deim import backend

    expected = {} if case == "empty" else {"backbone.patch.weight": SimpleNamespace(shape=(2, 2))}
    actual = {
        "backbone.patch.weight": SimpleNamespace(shape=(3, 3) if case == "wrong_shape" else (2, 2))
    }
    native_torch = SimpleNamespace(load=lambda *_args, **_kwargs: {"model": expected})
    monkeypatch.setattr(
        "clearml_yolo.adapters.deim.backend.importlib.import_module", lambda _: native_torch
    )
    model = SimpleNamespace(state_dict=lambda: actual)
    if case == "compatible":
        backend._validate_tuning(model, tmp_path / "weights.pth")
    else:
        with pytest.raises(ValueError, match="compatible backbone"):
            backend._validate_tuning(model, tmp_path / "weights.pth")


@pytest.mark.parametrize("changes", [{"resize": "letterbox"}, {"stride": 16}])
def test_deim_rejects_unsupported_checkpoint_preprocessing(changes: dict[str, Any]) -> None:
    from clearml_yolo.adapters.deim.backend import predict

    preprocessing = Preprocessing.model_validate({"resize": "stretch", "size": 128} | changes)
    descriptor = CheckpointMetadata(
        backend="deimv2",
        preset="s",
        class_names=("square",),
        preprocessing=preprocessing,
    )
    with pytest.raises(ValueError, match="preprocessing"):
        predict(
            ModelConfig(backend="deimv2", preset="s"),
            descriptor,
            Path("unused.pth"),
            [],
            PredictSettings(),
        )


@pytest.mark.parametrize("failure", [None, "ValueError", "KeyboardInterrupt"])
@pytest.mark.parametrize("already_loaded", [True, False])
def test_deim_private_import_restores_coco_modules_even_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    already_loaded: bool,
) -> None:
    from clearml_yolo.adapters.deim.source import _load_package

    for key in list(sys.modules):
        if key == "pycocotools" or key.startswith("pycocotools."):
            monkeypatch.delitem(sys.modules, key)
    if already_loaded:
        for name in (
            "pycocotools",
            "pycocotools.coco",
            "pycocotools.cocoeval",
            "pycocotools.mask",
            "pycocotools._mask",
        ):
            monkeypatch.setitem(sys.modules, name, ModuleType(name))
    original = {
        name: module
        for name, module in sys.modules.items()
        if name == "pycocotools" or name.startswith("pycocotools.")
    }
    namespace = "_test_deim_coco_isolation"
    monkeypatch.setitem(sys.modules, namespace, ModuleType(namespace))
    engine = tmp_path / "engine"
    engine.mkdir()
    body = (
        "import sys\nfrom types import ModuleType\n"
        "for key in ('pycocotools', 'pycocotools.coco', 'pycocotools.cocoeval', "
        "'pycocotools.mask', 'pycocotools.added'):\n"
        "    sys.modules[key] = ModuleType('fast_' + key)\n"
        "captured_coco = sys.modules['pycocotools.coco']\n"
    )
    if failure:
        body += f"raise {failure}('failed private import')\n"
    (engine / "__init__.py").write_text(body)
    if failure:
        error = ValueError if failure == "ValueError" else KeyboardInterrupt
        with pytest.raises(error, match="failed private import"):
            _load_package(namespace, engine)
        assert namespace not in sys.modules
    else:
        loaded = _load_package(namespace, engine)
        assert loaded.captured_coco.__name__ == "fast_pycocotools.coco"
    restored = {
        name: module
        for name, module in sys.modules.items()
        if name == "pycocotools" or name.startswith("pycocotools.")
    }
    assert restored.keys() == original.keys()
    assert all(restored[name] is module for name, module in original.items())


def test_deim_native_dataset_alias_scope_preserves_original_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.deim import source

    native_modules = {
        name: ModuleType(name)
        for name in (
            "faster_coco_eval",
            "faster_coco_eval.core.coco",
            "faster_coco_eval.core.faster_eval_api",
            "faster_coco_eval.core.mask",
        )
    }
    monkeypatch.setattr(
        "clearml_yolo.adapters.deim.source.importlib.import_module",
        lambda name: native_modules[name],
    )
    original = {
        name: module
        for name, module in sys.modules.items()
        if name == "pycocotools" or name.startswith("pycocotools.")
    }
    captured: list[ModuleType] = []

    def construct_dataset() -> None:
        with source.native_coco_modules():
            captured.append(sys.modules["pycocotools.coco"])
            assert captured[0] is native_modules["faster_coco_eval.core.coco"]
            raise RuntimeError("dataset failure")

    with pytest.raises(RuntimeError, match="dataset failure"):
        construct_dataset()
    assert captured[0] is native_modules["faster_coco_eval.core.coco"]
    restored = {
        name: module
        for name, module in sys.modules.items()
        if name == "pycocotools" or name.startswith("pycocotools.")
    }
    assert restored.keys() == original.keys()
    assert all(restored[name] is module for name, module in original.items())


def test_deim_native_postprocessor_receives_original_width_then_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import nullcontext

    from clearml_yolo.adapters.deim import backend

    class Tensor:
        def float(self) -> "Tensor":
            return self

        def __truediv__(self, _value: Any) -> "Tensor":
            return self

        def to(self, _device: str) -> "Tensor":
            return self

    class Model:
        def to(self, _device: str) -> "Model":
            return self

        def eval(self) -> "Model":
            return self

        def __call__(self, _tensor: Tensor) -> None:
            return None

    dimensions: list[list[list[int]]] = []
    empty_values = SimpleNamespace(cpu=lambda: SimpleNamespace(tolist=list))

    class Postprocessor:
        def to(self, _device: str) -> "Postprocessor":
            return self

        def __call__(self, _outputs: Any, sizes: list[list[int]]) -> list[dict[str, Any]]:
            dimensions.append(sizes)
            return [{"boxes": empty_values, "labels": empty_values, "scores": empty_values}]

    image = SimpleNamespace(width=96, height=48)
    image.convert = lambda _: image
    native_modules = {
        "torch": SimpleNamespace(
            inference_mode=nullcontext,
            stack=lambda _: Tensor(),
            tensor=lambda values, **_kwargs: values,
        ),
        "torchvision.transforms.v2.functional": SimpleNamespace(
            pil_to_tensor=lambda _: Tensor(),
            resize=lambda value, _: value,
            normalize=lambda value, *_args: value,
        ),
        "PIL.Image": SimpleNamespace(open=lambda _: nullcontext(image)),
    }
    monkeypatch.setattr(
        "clearml_yolo.adapters.deim.backend.importlib.import_module",
        lambda name: native_modules[name],
    )
    monkeypatch.setattr(backend, "_load_weights", lambda *_args: None)
    descriptor = CheckpointMetadata(
        backend="deimv2",
        preset="s",
        class_names=("square",),
        preprocessing=Preprocessing(resize="stretch", size=128),
    )
    backend._native_predict(
        SimpleNamespace(model=Model(), postprocessor=Postprocessor()),
        descriptor,
        Path("unused.pth"),
        ["wide-image.png"],
        PredictSettings(device="cpu"),
        (128, 128),
    )
    assert dimensions == [[[96, 48]]]
