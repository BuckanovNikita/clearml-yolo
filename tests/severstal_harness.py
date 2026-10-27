"""Opt-in one-epoch Severstal acceptance; no automatic downloads or full training."""

import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import UserDict
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, assert_never, override
from uuid import uuid4

from clearml_yolo.core.models import PRESETS, model_preset
from ddp_gpu_harness import redact, redact_data
from severstal_helpers import (
    OptimizerObservation,
    file_sha256,
    loss_values,
    validate_observation,
    write_json,
    write_pipeline,
)

MODEL_SELECTIONS = (
    "ultralytics",
    "deimv2/s",
    "deimv2/m",
    "deimv2/l",
    "deimv2/x",
    "rfdetr/nano",
    "rfdetr/small",
    "rfdetr/medium",
    "rfdetr/large",
    "fasterrcnn/resnet50_fpn",
    "fasterrcnn/resnet101_fpn",
    "fasterrcnn/convnext_tiny",
    "fasterrcnn/swin_tiny",
    "fasterrcnn/dinov2_small",
    "fasterrcnn/dinov3_small",
    "fcos/resnet50_fpn",
    "fcos/resnet101_fpn",
    "fcos/convnext_tiny",
    "fcos/swin_tiny",
    "fcos/dinov2_small",
    "fcos/dinov3_small",
)
VARIANTS = ("default", "json", "json_mosaic")
_REPOSITORY = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SeverstalOptions:
    dataset: Path
    artifacts: Path
    project: str
    tags: tuple[str, ...]
    device: str = "0"
    timeout: float = 1800
    backbone_weights: Mapping[str, Path] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "backbone_weights",
            MappingProxyType(
                {
                    selection: _backbone_file(selection, path)
                    for selection, path in self.backbone_weights.items()
                }
            ),
        )


def _backbone_file(selection: str, path: Path) -> Path:
    if selection not in MODEL_SELECTIONS or not selection.startswith(
        ("deimv2/", "fasterrcnn/", "fcos/")
    ):
        raise ValueError(
            "--severstal-backbone supports only registered DEIMv2, Faster R-CNN and FCOS selections"
        )
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or not resolved.stat().st_size:
        raise ValueError(f"Backbone for {selection} must be an existing nonempty local file")
    return resolved


def parse_backbone_options(entries: Sequence[str]) -> dict[str, Path]:
    """Resolve explicit local files without downloading or echoing supplied URLs."""
    result: dict[str, Path] = {}
    for entry in entries:
        selection, separator, value = entry.partition("=")
        selection = selection.strip()
        if not separator or not selection or not value.strip():
            raise ValueError("--severstal-backbone requires MODEL=PATH")
        if selection in result:
            raise ValueError(f"Duplicate backbone selection: {selection}")
        if "://" in value:
            raise ValueError("--severstal-backbone requires a local filesystem path")
        result[selection] = _backbone_file(selection, Path(value))
    return result


def scenario_overrides(
    options: SeverstalOptions, root: Path, selection: str, variant: str, task_name: str
) -> list[str]:
    if selection not in MODEL_SELECTIONS or variant not in VARIANTS:
        raise ValueError("Unknown Severstal model or augmentation scenario")
    if not options.project.strip() or not options.tags or not all(options.tags):
        raise ValueError(
            "Severstal acceptance requires explicit ClearML project and ownership tags"
        )
    config = model_preset(selection)
    resolution = PRESETS[config.backend][config.preset]
    result = [
        f"model={selection}",
        f"ground_truth={json.dumps(str(options.dataset.resolve() / 'smoke.csv'))}",
        f"run_dir={json.dumps(str(root / 'pipeline'))}",
        f"dataset_cache_dir={json.dumps(str(root / 'dataset-cache'))}",
        f"clearml.project_name={json.dumps(options.project)}",
        f"clearml.task_name={json.dumps(task_name)}",
        f"clearml.tags={json.dumps(list(options.tags))}",
        "fiftyone.enabled=false",
        "splits=[val,test]",
        "skip_compare=true",
        "skip_report=true",
    ]
    prefix = "ultralytics" if selection == "ultralytics" else "model.train"
    result += [
        f"{prefix}.epochs=1",
        f"{prefix}.batch=1",
        f"{prefix}.seed=0",
        f"{prefix}.workers=2",
        f"{prefix}.imgsz={resolution}",
        f"{prefix}.device={options.device}",
        # The tiny one-epoch corpus must execute updates, not just AMP scale warm-up.
        f"{prefix}.amp=false",
    ]
    if selection == "ultralytics":
        result += [
            "ultralytics.model=yolo26n.pt",
            "ultralytics.compile=false",
            f"ultralytics_predict.device={options.device}",
        ]
    else:
        result += [f"model.predict.device={options.device}"]
    if selection in options.backbone_weights:
        result.append(
            f"model.train.backbone_weights={json.dumps(str(options.backbone_weights[selection]))}"
        )
    if variant != "default":
        result += [
            "transforms=albumentations",
            f"transforms.pipeline_file={json.dumps(str(root / 'pipeline.json'))}",
        ]
    return result


class _WorkerEnvironment(UserDict[str, str]):
    """Subprocess values stay available without appearing in pytest tracebacks."""

    @override
    def __repr__(self) -> str:
        return "<worker environment values hidden>"


def worker_environment(root: Path) -> Mapping[str, str]:
    """Keep generated data and native outputs within this scenario's allowed home."""
    return _WorkerEnvironment(
        os.environ
        | {
            "CY_HOME": str(root),
            "PYTHONPATH": os.pathsep.join(
                [str(_REPOSITORY / "src"), str(_REPOSITORY), str(_REPOSITORY / "tests")]
            ),
            "HYDRA_FULL_ERROR": "1",
        }
    )


def run_scenario(options: SeverstalOptions, selection: str, variant: str) -> Path:
    root = (
        options.artifacts.resolve() / f"{selection.replace('/', '-')}-{variant}-{uuid4().hex[:10]}"
    )
    root.mkdir(parents=True, exist_ok=False)
    summary: dict[str, Any] = {"selection": selection, "variant": variant, "status": "running"}
    started = time.monotonic()
    try:
        overrides = scenario_overrides(options, root, selection, variant, root.name)
        request = {
            "dataset": str(options.dataset.resolve()),
            "selection": selection,
            "variant": variant,
            "project": options.project,
            "task_name": root.name,
            "tags": list(options.tags),
            "device": options.device,
            "overrides": overrides,
        }
        write_json(root / "request.json", request)
        command = [sys.executable, str(Path(__file__).resolve()), "worker", str(root)]
        environment = worker_environment(root)
        summary["command"] = command
        _run_worker(command, environment, root, options.timeout)
        verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
        validate_observation(verification["optimizer"])
        verification["initialization_comparisons"] = _verify_initialization(
            root, selection, verification
        )
        summary.update(status="passed", verification=verification)
    except BaseException as error:
        summary.update(status="failed", error=redact(str(error)))
        raise
    finally:
        summary["elapsed_seconds"] = time.monotonic() - started
        write_json(root / "summary.json", redact_data(summary))
        log = root / "native.log"
        if log.exists():
            log.write_text(
                redact(log.read_text(encoding="utf-8", errors="replace")), encoding="utf-8"
            )
    return root


def _verify_initialization(root: Path, selection: str, result: dict[str, Any]) -> int:
    comparisons = 0
    for receipt in root.parent.glob("*/summary.json"):
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        if prior.get("status") != "passed" or prior.get("selection") != selection:
            continue
        verified = prior["verification"]
        if verified["manifest_sha256"] != result["manifest_sha256"]:
            continue
        assert (
            verified["optimizer"]["initial_optimizer_parameters_sha256"]
            == result["optimizer"]["initial_optimizer_parameters_sha256"]
        ), f"Per-preset initialization differs from {receipt}; comparison is invalid"
        comparisons += 1
    return comparisons


def _run_worker(
    command: list[str], environment: Mapping[str, str], root: Path, timeout: float
) -> None:
    with (root / "native.log").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(  # noqa: S603 - fixed project test worker, no shell
            command,
            env=environment,
            cwd=_REPOSITORY,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            status = process.wait(timeout=timeout)
        except BaseException:
            # The new session is exclusively this scenario's subprocess tree.
            # A failure can race normal exit; then no process group remains.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            raise
    if status:
        raise AssertionError(
            f"Native Severstal worker exited {status}; inspect {root / 'native.log'}"
        )


def _worker(root: Path) -> None:
    from scripts.severstal import verify_prepared

    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    manifest = verify_prepared(Path(request["dataset"]))
    if manifest["smoke_counts"] != {"train": 160, "val": 40, "test": 40}:
        raise ValueError("Native acceptance requires the frozen 160/40/40 smoke subset")
    if manifest["seed"] != 0:
        raise ValueError("Native acceptance requires the seed-0 split")
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("Selected native Severstal acceptance requires an available CUDA device")
    config = model_preset(request["selection"])
    if request["variant"] != "default":
        write_pipeline(
            root / "pipeline.json", request["variant"], PRESETS[config.backend][config.preset]
        )
    from clearml_yolo.entrypoints.pipeline import main

    observation = OptimizerObservation()
    sys.argv = ["clearml-yolo-pipeline", *request["overrides"]]
    try:
        with observation.installed():
            main()
    finally:
        write_json(root / "optimizer.json", observation.result())
    validate_observation(observation.result())
    result = _verify_publication(root, request, manifest)
    result.update(optimizer=observation.result(), manifest_sha256=manifest["sha256"])
    write_json(root / "verification.json", redact_data(result))


def _completed_task(request: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Resolve the invocation despite legitimate paired task/model display renaming."""
    from clearml import Task

    tasks: list[Any] = Task.get_tasks(
        project_name=request["project"],
        task_name=rf"\A{re.escape(request['task_name'])}(?:-[a-z]+-[a-z]+)?\Z",
        tags=request["tags"],
    )
    assert len(tasks) == 1, "Expected exactly one independently finalized pipeline task"
    task: Any = tasks[0]
    assert str(task.get_status()) == "completed", "Native pipeline task did not complete"
    canonical = task.get_configuration_object_as_dict("run")
    assert isinstance(canonical, dict), "Canonical replay configuration is absent"
    assert canonical["display_names"]["requested_task_name"] == request["task_name"], (
        "Readback selected a different invocation"
    )
    return task, canonical


def _verify_publication(
    root: Path, request: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    import pandas as pd

    task, canonical = _completed_task(request)
    write_json(root / "configuration.json", redact_data(canonical))
    if request["variant"] == "default":
        assert canonical["transforms"]["mode"] == "native"
    else:
        from clearml_yolo.core.transforms import TransformSnapshot

        snapshot = TransformSnapshot.model_validate(canonical["transforms"]["snapshot"])
        assert canonical["transforms"]["mode"] == "albumentations"
        assert snapshot.pipeline == json.loads((root / "pipeline.json").read_text(encoding="utf-8"))
    scalars = task.get_reported_scalars()
    write_json(root / "scalars.json", redact_data(scalars))
    losses = loss_values(scalars)
    expected = {"gt_csv", "predicts_csv", "metrics_best_confidences_val"} | {
        f"metrics_dashboard_{mode}_{split}"
        for mode in ("full", "dtrk")
        for split in ("val", "test")
    }
    assert expected <= set(task.artifacts), (
        f"Missing native artifacts: {expected - set(task.artifacts)}"
    )
    downloads = root / "downloads"
    downloads.mkdir()
    hashes: dict[str, str] = {}
    downloaded: dict[str, Path] = {}
    for name in sorted(expected):
        path = Path(task.artifacts[name].get_local_copy(force_download=True, raise_on_error=True))
        assert path.is_file(), f"Missing publication {name}"
        assert path.stat().st_size, f"Empty publication {name}"
        destination = downloads / f"{name}{path.suffix}"
        destination.write_bytes(path.read_bytes())
        hashes[name] = file_sha256(destination)
        downloaded[name] = destination
    predictions = pd.read_csv(downloaded["predicts_csv"])
    expected_names = {
        image["image_name"]
        for image in manifest["images"]
        if image["smoke"] and image["split"] in {"val", "test"}
    }
    assert set(predictions["image_name"]) == expected_names, (
        "Prediction lost evaluated images or backgrounds"
    )
    assert {"val", "test"} <= set(predictions["split"])
    for name, path in downloaded.items():
        if name.startswith("metrics_dashboard_"):
            with pd.ExcelFile(path) as workbook:
                assert workbook.sheet_names, f"Empty workbook {name}"
    assert len(task.models["output"]) == 1, "Expected one trained best Output Model"
    remote = task.models["output"][0]
    weights = Path(remote.get_local_copy(force_download=True, raise_on_error=True))
    digest = file_sha256(weights)
    native_name = remote.get_metadata("clearml_yolo_checkpoint_filename")
    assert isinstance(native_name, str), "Native best Output Model filename is missing"
    native = list((root / "pipeline").rglob(native_name))
    assert native, "Native best checkpoint is missing"
    assert any(file_sha256(path) == digest for path in native), (
        "Downloaded checkpoint differs from native best"
    )
    image = next(
        image for image in manifest["images"] if image["smoke"] and image["split"] == "test"
    )
    _reload_checkpoint(request, weights, image["image_path"])
    return {
        "task_id": task.id,
        "output_model_id": remote.id,
        "checkpoint_sha256": digest,
        "checkpoint_reloaded": True,
        "evaluated_images": len(expected_names),
        "native_loss_values": losses,
        "artifact_sha256": hashes,
    }


def _reload_checkpoint(request: dict[str, Any], weights: Path, image_path: str) -> None:
    config = model_preset(request["selection"])
    if config.backend == "ultralytics":
        from ultralytics.models import YOLO

        results = list(
            YOLO(str(weights)).predict([image_path], device=request["device"], verbose=False)
        )
        assert len(results) == 1, "Downloaded YOLO checkpoint failed inference reload"
        return
    from clearml_yolo.adapters.storage.checkpoint import read_checkpoint_descriptor
    from clearml_yolo.core.models import PredictSettings

    descriptor = read_checkpoint_descriptor(weights)
    assert descriptor is not None, "Native detector checkpoint lost its descriptor"
    settings = PredictSettings(device=request["device"])
    if config.backend == "deimv2":
        from clearml_yolo.adapters.deim.backend import predict
    elif config.backend == "rfdetr":
        from clearml_yolo.adapters.rfdetr.backend import predict
    elif config.backend == "fasterrcnn":
        from clearml_yolo.adapters.fasterrcnn.backend import predict
    elif config.backend == "fcos":
        from clearml_yolo.adapters.fcos.backend import predict
    else:
        assert_never(config.backend)
    predictions = predict(config, descriptor, weights, [image_path], settings)
    assert predictions is not None, "Downloaded detector checkpoint failed inference reload"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "worker":
        raise SystemExit("Use pytest --run-severstal-gpu to run the native smoke matrix")
    _worker(Path(sys.argv[2]))
