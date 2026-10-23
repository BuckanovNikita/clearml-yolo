"""Fresh-process prerequisites, generated inputs and actual ClearML readback for GPU tests."""

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from ddp_gpu_harness import checkpoint_sha256, resolve_devices
from ddp_gpu_instrumentation import write


def _preflight(root: Path, request: dict[str, Any]) -> None:
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version,
        "executable": sys.executable,
        "inherited_cuda_visibility": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "inventory": [],
    }
    try:
        if sys.platform != "linux":
            raise RuntimeError("Physical DDP acceptance requires Linux/WSL process supervision")
        from clearml_yolo.adapters.runtime.process_tree import require_process_supervision

        require_process_supervision()
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        try:
            for index in range(pynvml.nvmlDeviceGetCount()):
                device = pynvml.nvmlDeviceGetHandleByIndex(index)
                uuid = pynvml.nvmlDeviceGetUUID(device)
                name = pynvml.nvmlDeviceGetName(device)
                result["inventory"].append(
                    {
                        "index": index,
                        "uuid": uuid.decode() if isinstance(uuid, bytes) else uuid,
                        "name": name.decode() if isinstance(name, bytes) else name,
                    }
                )
            result["driver"] = pynvml.nvmlSystemGetDriverVersion()
        finally:
            pynvml.nvmlShutdown()
        resolve_devices(tuple(request["indexes"]), result["inventory"])
        result["versions"] = {
            name: importlib.metadata.version(name)
            for name in (
                "clearml-yolo",
                "ultralytics",
                "torch",
                "clearml",
                "hydra-core",
            )
        }
        repository = Path(__file__).resolve().parents[1]
        git = shutil.which("git")
        if git is None:
            raise RuntimeError("Git is required to retain reproducible source identity")
        source = subprocess.run(  # noqa: S603 - read-only Git evidence
            [git, "-C", str(repository), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        diff = subprocess.run(  # noqa: S603 - read-only Git evidence
            [git, "-C", str(repository), "diff", "--binary"],
            capture_output=True,
            check=False,
            timeout=10,
        )
        result["git_head"] = source.stdout.strip()
        result["tracked_diff_sha256"] = hashlib.sha256(diff.stdout).hexdigest()
        files = subprocess.run(  # noqa: S603 - read-only source inventory
            [
                git,
                "-C",
                str(repository),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            check=True,
            timeout=10,
        )
        write(
            root,
            "source-manifest.json",
            {
                name: checkpoint_sha256(repository / name)
                for name in files.stdout.decode().split("\0")
                if name and (repository / name).is_file()
            },
        )
        from clearml import Task

        # Read-only authenticated request: missing credentials/storage/service never skips.
        Task.get_tasks(project_name=request["project"], task_filter={"tags": [request["tag"]]})
        result["clearml_authenticated_read"] = True
    finally:
        write(root, "preflight.json", result)


def _cuda(root: Path, request: dict[str, Any]) -> None:
    import torch
    import torch.distributed as dist

    assert torch.cuda.is_available(), "Torch CUDA is unavailable"
    assert dist.is_available(), "Torch distributed is unavailable"
    assert dist.is_nccl_available(), "Torch NCCL is unavailable"
    assert torch.cuda.device_count() == len(request["indexes"]), (
        "UUID CUDA mapping did not expose selected devices"
    )
    if request["compiled"]:
        assert callable(torch.compile), "torch.compile is unavailable"
    devices = []
    for index in range(torch.cuda.device_count()):
        tensor = torch.ones(2, device=f"cuda:{index}")
        assert tensor.sum().item() == 2
        devices.append(
            {"logical_index": index, "uuid": str(torch.cuda.get_device_properties(index).uuid)}
        )
    write(root, "cuda-preflight.json", {"torch_cuda": torch.version.cuda, "devices": devices})


def _prepare(root: Path, request: dict[str, Any]) -> None:
    import matplotlib as mpl
    import ultralytics
    import yaml
    from PIL import Image, ImageDraw
    from ultralytics.utils import get_user_config_dir

    from clearml_yolo.adapters.yolo.ground_truth import build_ground_truth

    config_dir = cast(Callable[[], Path], get_user_config_dir)()
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        Path(mpl.get_data_path()) / "fonts/ttf/DejaVuSans.ttf", config_dir / "Arial.ttf"
    )
    data: dict[str, Any] = {"path": str(root / "dataset"), "names": {0: "box"}}
    for split, count in (("train", max(8, 4 * len(request["indexes"]))), ("val", 4), ("test", 4)):
        images = root / "dataset" / "images" / split
        labels = root / "dataset" / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        data[split] = f"images/{split}"
        for index in range(count):
            image = Image.new("RGB", (64, 64), (20 + index * 3, 24, 32))
            annotation = ""
            if index:
                ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill=(210, 110, 80))
                annotation = "0 0.5 0.5 0.5 0.5\n"
            image.save(images / f"{split}-{index}.png")
            (labels / f"{split}-{index}.txt").write_text(annotation, encoding="utf-8")
    (root / "data.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    build_ground_truth(root / "data.yaml", root / "ground_truth.csv")
    architecture = Path(ultralytics.__file__).parent / "cfg/models/v8/yolov8.yaml"
    model = yaml.safe_load(architecture.read_text())
    model.update(scale="n", nc=1)
    (root / "yolov8n.yaml").write_text(yaml.safe_dump(model), encoding="utf-8")
    settings = {
        "defaults": ["pipeline", "_self_"],
        "ground_truth": str(root / "ground_truth.csv"),
        "run_dir": str(root / "pipeline"),
        "splits": ["val", "test"],
        "skip_compare": True,
        "skip_report": True,
        "fiftyone": {"enabled": False},
        "clearml": {
            "project_name": request["project"],
            "task_name": f"physical-{request['scenario']}",
            "tags": [request["tag"]],
        },
        "ultralytics": {
            "model": str(root / "yolov8n.yaml"),
            "pretrained": False,
            "epochs": 2,
            "imgsz": 64,
            "batch": 4 * len(request["indexes"]),
            "nbs": 4 * len(request["indexes"]),
            "workers": 0,
            "amp": False,
            "compile": request["compiled"],
            "plots": False,
            "optimizer": "SGD",
            "lr0": 0.01,
            "warmup_epochs": 0,
            "close_mosaic": 0,
            "mosaic": 0.0,
            "mixup": 0.0,
            "val": True,
            "save": True,
        },
        "ultralytics_predict": {"imgsz": 64, "batch": 2, "verbose": False},
    }
    directory = root / "config"
    directory.mkdir()
    (directory / "ddp.yaml").write_text(yaml.safe_dump(settings), encoding="utf-8")
    instrumentation = root / "instrumentation"
    instrumentation.mkdir()
    (instrumentation / "sitecustomize.py").write_text(
        "import os, sys\n"
        'if os.environ.get("CY_DDP_TRACE") and (\n'
        '    "clearml_yolo.entrypoints.pipeline" in sys.orig_argv\n'
        '    or os.environ.get("LOCAL_RANK") not in {None, "-1"}\n'
        "):\n"
        "    from ddp_gpu_instrumentation import install\n"
        "    try:\n        install()\n"
        "    except BaseException:\n"
        "        import traceback\n        traceback.print_exc()\n"
        "        os._exit(86)\n",
        encoding="utf-8",
    )


def _events(root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for path in root.glob("events-*.jsonl")
        for line in path.read_text().splitlines()
    ]


def _verify(root: Path, request: dict[str, Any]) -> None:
    events = _events(root)
    ranks = [json.loads(path.read_text()) for path in sorted(root.glob("rank-*-started.json"))]
    count = len(request["indexes"])
    assert len(ranks) == count
    assert {rank["rank"] for rank in ranks} == set(range(count))
    mapped = os.environ["CUDA_VISIBLE_DEVICES"].split(",")
    for rank in ranks:
        assert rank["world_size"] == count
        assert rank["backend"] == "nccl"
        assert (
            rank["uuid"].removeprefix("GPU-").lower()
            == mapped[rank["local_rank"]].removeprefix("GPU-").lower()
        )
        assert rank["compiled"] == request["compiled"]
    for event in events:
        if event["kind"] in {"artifact-attempt", "model-attempt"}:
            assert event["rank"] == -1
    assert len({rank["initial_parameters"] for rank in ranks}) == 1, (
        "Native initial rank parameters were not synchronized"
    )
    task_events = [event for event in events if event["kind"] == "task-init"]
    assert len(task_events) == 1, "Expected exactly one real invocation ClearML task"
    task_id = task_events[0]["task_id"]
    owner_pid = task_events[0]["pid"]
    assert all(
        event["pid"] == owner_pid
        for event in events
        if event["kind"] in {"artifact-attempt", "model-attempt"}
    )
    from clearml import Task

    tasks: list[Any] = Task.get_tasks(
        project_name=request["project"], task_filter={"tags": [request["tag"]]}
    )
    assert [task.id for task in tasks] == [task_id], "Server task inventory differs from sole owner"
    task: Any = Task.get_task(task_id=task_id)
    successful = request["scenario"] not in {
        "queued-rank-exit",
        "queued-cancel",
        "queued-guardian-death",
    }
    status = str(task.status)
    result: dict[str, Any] = {
        "task_id": task_id,
        "owner_pid": owner_pid,
        "task_status": status,
        "ranks": ranks,
    }
    write(root, "task-readback.json", result)
    if not successful:
        assert status.rsplit(".", 1)[-1] in {"failed", "stopped"}, (
            "Interrupted native task must not report completed"
        )
        if request["scenario"] == "queued-rank-exit":
            assert any(
                event["kind"] == "injected-rank-exit" and event["exit_code"] == 73
                for event in events
            )
        write(root, "verification.json", result)
        return
    assert status.rsplit(".", 1)[-1] == "completed", "Native task did not complete"
    epochs = [event for event in events if event["kind"] == "rank-epoch"]
    for rank in ranks:
        observed = [event for event in epochs if event["rank"] == rank["rank"]]
        assert len(observed) == 2, "Each NCCL rank must finish both optimizer epochs"
        assert observed[-1]["parameters"] != rank["initial_parameters"], (
            "Model parameters did not train"
        )
        assert all(len(set(event["synchronized"])) == 1 for event in observed)
    assert any(event["kind"] == "on_train_end" for event in events)
    assert any(event["kind"] == "native-validation" for event in events), (
        "Native CUDA validation did not run"
    )
    assert any(event["kind"] == "pipeline-predict-complete" for event in events), (
        "Production validation/prediction did not run"
    )
    _verify_publications(root, task, result)
    write(root, "verification.json", result)


def _verify_publications(root: Path, task: Any, result: dict[str, Any]) -> None:
    expected = {"gt_csv", "predicts_csv", "metrics_best_confidences_val"}
    expected |= {
        f"metrics_dashboard_{mode}_{split}"
        for mode in ("full", "dtrk")
        for split in ("val", "test")
    }
    uploads = _events(root)
    for name in ("gt_csv", "predicts_csv"):
        assert (
            sum(
                event["kind"] == "artifact-attempt" and event.get("name") == name
                for event in uploads
            )
            == 1
        ), f"Canonical CSV {name} was not uploaded exactly once by its owner"
    scalars = task.get_reported_scalars()
    assert scalars, "Native owner telemetry is missing from ClearML"
    write(root, "scalars-readback.json", scalars)
    plots = task.get_reported_plots(max_iterations=10)
    write(root, "plots-readback.json", plots)
    titles = {plot.get("metric") for plot in plots}
    assert "Confusion matrix" in titles, "Required evaluated confusion charts are missing"
    assert "Precision-recall" in titles, "Required test precision-recall chart is missing"
    assert expected <= set(task.artifacts), (
        f"Required real artifacts missing: {expected - set(task.artifacts)}"
    )
    downloads = root / "downloads"
    downloads.mkdir(exist_ok=True)
    hashes: dict[str, str] = {}
    for name in sorted(expected):
        source = Path(task.artifacts[name].get_local_copy(force_download=True, raise_on_error=True))
        assert source.is_file()
        assert source.stat().st_size
        destination = downloads / f"{name}{source.suffix}"
        shutil.copyfile(source, destination)
        hashes[name] = checkpoint_sha256(destination)
    import pandas as pd

    truth = pd.read_csv(downloads / "gt_csv.csv")
    predictions = pd.read_csv(downloads / "predicts_csv.csv")
    source_truth = pd.read_csv(root / "ground_truth.csv")
    assert set(truth["image_name"]) == set(source_truth["image_name"])
    assert set(predictions["row_type"]) >= {"gt"}
    assert {"val", "test"} <= set(predictions["split"])
    for split in ("val", "test"):
        assert f"{split}-0.png" in set(predictions["image_name"]), (
            "Empty images were dropped from publication"
        )
    for mode in ("full", "dtrk"):
        for split in ("val", "test"):
            with pd.ExcelFile(downloads / f"metrics_dashboard_{mode}_{split}.xlsx") as workbook:
                assert workbook.sheet_names
    result["artifacts"] = hashes
    _verify_checkpoint(root, task, downloads, result)


def _verify_checkpoint(root: Path, task: Any, downloads: Path, result: dict[str, Any]) -> None:
    assert len(task.models["output"]) == 1, "Expected one native best Output Model"
    remote_model = task.models["output"][0]
    downloaded = Path(remote_model.get_local_copy(force_download=True, raise_on_error=True))
    checkpoint = downloads / "best.pt"
    shutil.copyfile(downloaded, checkpoint)
    native = list((root / "pipeline").rglob("best.pt"))
    assert native, "Native best checkpoint is missing"
    assert checkpoint_sha256(checkpoint) == checkpoint_sha256(native[0]), (
        "Downloaded model differs from trained native checkpoint"
    )
    from ultralytics.models import YOLO

    reload = YOLO(str(checkpoint))
    test_images = sorted((root / "dataset/images/test").glob("*.png"))
    predicted = list(
        reload.predict([str(path) for path in test_images], device="cpu", imgsz=64, verbose=False)
    )
    assert len(predicted) == len(test_images), (
        "Downloaded checkpoint failed independent inference reload"
    )
    metadata = remote_model.get_all_metadata()
    metadata_hash = metadata.get("clearml_yolo_calibration_checkpoint_sha256", {})
    assert metadata_hash.get("value") == checkpoint_sha256(checkpoint), (
        "Remote calibration metadata is not bound to checkpoint bytes"
    )
    with (downloads / "metrics_best_confidences_val.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        header, *rows = list(csv.reader(stream))
    class_column = header.index("class_name") if "class_name" in header else 0
    confidence_column = header.index("confidence") if "confidence" in header else 1
    thresholds = {row[class_column]: float(row[confidence_column]) for row in rows}
    assert thresholds, "Downloaded validation calibration is empty"
    assert json.loads(metadata["clearml_yolo_confidence_thresholds"]["value"]) == thresholds, (
        "Remote best-model thresholds differ from downloaded full-precision calibration"
    )
    assert metadata["clearml_yolo_calibration_split"]["value"] == "val"
    result.update(
        checkpoint_sha256=checkpoint_sha256(checkpoint),
        output_model_id=remote_model.id,
        checkpoint_reload_images=len(predicted),
    )


def _owned_processes(root: Path) -> list[tuple[int, int]]:
    from ddp_gpu_instrumentation import process_birth

    known = {
        int(record["pid"]): record["born"]
        for record in (json.loads(path.read_text()) for path in root.glob("process-*.json"))
    }
    owned = []
    uninspected = []
    for path in Path("/proc").iterdir():
        try:
            if not path.name.isdigit() or path.stat().st_uid != os.geteuid():
                continue
            environment = (path / "environ").read_bytes().split(b"\0")
            if f"CY_DDP_TRACE={root}".encode() not in environment:
                continue
            status = (path / "stat").read_text().rsplit(")", 1)[1].split()[0]
            born = process_birth(int(path.name))
            if status != "Z" and born is not None:
                owned.append((int(path.name), born))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as error:
            if int(path.name) in known and process_birth(int(path.name)) == known[int(path.name)]:
                write(root, "cleanup-unverified.json", {"pid": path.name, "reason": str(error)})
                raise RuntimeError(
                    "Cannot inspect a known owned process; native cleanup is unverified"
                ) from error
            uninspected.append(path.name)
    if uninspected:
        write(root, "cleanup-unrelated-uninspected.json", {"pids": uninspected})
    return owned


def _cleanup(root: Path) -> None:
    from ddp_gpu_instrumentation import process_birth

    initial = _owned_processes(root)
    for signum, seconds in ((signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        for pid, born in _owned_processes(root):
            try:
                descriptor = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                if process_birth(pid) == born:
                    signal.pidfd_send_signal(descriptor, signum)
            except ProcessLookupError:
                pass
            finally:
                os.close(descriptor)
        deadline = time.monotonic() + seconds
        while _owned_processes(root) and time.monotonic() < deadline:
            time.sleep(0.1)
    remaining = _owned_processes(root)
    write(root, "cleanup.json", {"initial_survivors": initial, "remaining": remaining})
    assert not remaining, f"Owned native processes survived cleanup: {remaining}"
    assert not initial, (
        "Production cleanup left native processes alive; "
        f"harness terminated only owned survivors: {initial}"
    )


def main() -> None:
    operation, root = sys.argv[1], Path(sys.argv[2])
    request = json.loads((root / "request.json").read_text())
    if operation == "cleanup":
        _cleanup(root)
    else:
        {"preflight": _preflight, "cuda": _cuda, "prepare": _prepare, "verify": _verify}[operation](
            root, request
        )


if __name__ == "__main__":
    main()
