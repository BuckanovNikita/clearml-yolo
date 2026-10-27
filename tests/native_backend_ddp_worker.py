"""Fresh-process fixture preparation, rank observation and real ClearML readback."""

import csv
import importlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from ddp_gpu_harness import checkpoint_sha256
from ddp_gpu_instrumentation import _event, write
from native_backend_ddp_harness import (
    validate_failure,
    validate_publication,
    validate_ranks,
    validate_ready,
)


def prepare(root: Path, request: dict[str, Any]) -> None:
    from PIL import Image, ImageDraw

    rows: list[list[Any]] = []
    for split in ("train", "val", "test"):
        folder = root / "images" / split
        folder.mkdir(parents=True)
        for index in range(request[f"{split}_count"]):
            path = folder / f"{split}-{index}.png"
            image = Image.new("RGB", (128, 128), (30 + index % 100, 40, 50))
            box = [24, 24, 96, 96]
            if index:
                ImageDraw.Draw(image).rectangle(tuple(box), fill=(220, 110, 80))
            image.save(path)
            rows.append(
                [path.name, str(path), "box" if index else "", *(box if index else [""] * 4), split]
            )
    with (root / "ground_truth.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "image_name",
                "image_path",
                "instance_label",
                "bbox_x_tl",
                "bbox_y_tl",
                "bbox_x_br",
                "bbox_y_br",
                "split",
            ]
        )
        writer.writerows(rows)
    directory = root / "instrumentation"
    directory.mkdir()
    (directory / "sitecustomize.py").write_text(
        "import os, sys\n"
        'if os.environ.get("CY_DDP_TRACE") and '
        '"clearml_yolo.entrypoints.pipeline" in sys.orig_argv:\n'
        "    try:\n"
        "        from native_backend_ddp_observers import install_owner\n"
        "        install_owner()\n"
        "    except BaseException:\n"
        "        import traceback\n"
        "        traceback.print_exc()\n"
        "        os._exit(86)\n"
    )


def events_at(root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for path in root.glob("events-*.jsonl")
        for line in path.read_text().splitlines()
    ]


def _task(root: Path, request: dict[str, Any]) -> tuple[Any, list[str]]:
    from clearml import Task

    events = events_at(root)
    owners = [event for event in events if event["kind"] == "task-init"]
    assert len(owners) == 1, "Expected one real native invocation task"
    owner = owners[0]
    tasks: list[Any] = Task.get_tasks(
        project_name=request["project"], task_filter={"tags": [request["tag"]]}
    )
    identifiers = [task.id for task in tasks]
    assert identifiers == [owner["task_id"]], "Unexpected server task inventory"
    for event in events:
        if event["kind"].endswith("-attempt"):
            assert event["rank"] == -1, "Worker publication"
            assert event["pid"] == owner["pid"], "Worker publication"
    return Task.get_task(task_id=owner["task_id"]), identifiers


def publication(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    import torch

    from clearml_yolo.adapters.storage.checkpoint import read_checkpoint_descriptor
    from clearml_yolo.application.training_workers import TrainingWorkerRequest
    from clearml_yolo.core.models import PredictSettings

    task, identifiers = _task(root, request)
    outputs = task.models["output"]
    assert len(outputs) == 1, "Expected one selected native Output Model"
    downloads = root / "downloads"
    downloads.mkdir()
    downloaded = downloads / "selected.pth"
    shutil.copyfile(outputs[0].get_local_copy(force_download=True, raise_on_error=True), downloaded)
    receipts = list((root / "pipeline").rglob("workers/*/rank-0.json"))
    assert len(receipts) == 1, "Expected one supervised rank-zero result"
    receipt = json.loads(receipts[0].read_text())
    assert receipt["status"] == "success"
    native_weights = Path(receipt["result"]["weights"])
    config = TrainingWorkerRequest.model_validate_json(
        (root / "native-request-0.json").read_text()
    ).config
    descriptor = read_checkpoint_descriptor(downloaded, expected=config)
    assert descriptor is not None, "Downloaded native metadata is missing"
    assert descriptor.class_names == ("box",), "Checkpoint foreground vocabulary changed"
    images = [str(path) for path in sorted((root / "images/test").glob("*.png"))]
    family = "deim" if config.backend == "deimv2" else config.backend
    backend = importlib.import_module(f"clearml_yolo.adapters.{family}.backend")
    frame = backend.predict(
        config, descriptor, downloaded, images, PredictSettings(device="cpu", imgsz=128)
    )
    assert frame.attrs["image_paths"] == images, (
        "Downloaded checkpoint reload lost image membership"
    )
    payload = torch.load(downloaded, map_location="cpu", weights_only=False)
    if config.backend in {"fasterrcnn", "fcos"}:
        state = payload["state_dict"]
    elif config.backend == "deimv2" and "ema" in payload:
        state = payload["ema"]["module"]
    else:
        state = payload["model"]
    result = {
        "task_ids": identifiers,
        "status": str(task.status).rsplit(".", 1)[-1],
        "output_models": len(outputs),
        "download_sha256": checkpoint_sha256(downloaded),
        "native_sha256": checkpoint_sha256(native_weights),
        "selection": f"{descriptor.backend}/{descriptor.preset}",
        "reload_images": len(frame.attrs["image_paths"]),
        "unwrapped": bool(state) and not any(key.startswith("module.") for key in state),
    }
    write(root, "publication.json", result)
    return result


def verify(root: Path, request: dict[str, Any]) -> None:
    cleanup = json.loads((root / "cleanup.json").read_text())
    assert cleanup["initial_survivors"] == [], "Native cleanup leaked workers"
    assert cleanup["remaining"] == [], "Native fallback cleanup leaked workers"
    events = events_at(root)
    if request["fault"] == "none":
        ranks = [
            json.loads(path.read_text())
            for path in sorted(root.glob("native-rank-*.json"))
            if "-ready" not in path.name
        ]
        validate_ranks(request, ranks)
        published = publication(root, request)
        validate_publication(request, events, published)
        result = {"status": "passed", "ranks": ranks, "publication": published}
    else:
        ready = [json.loads(path.read_text()) for path in root.glob("native-rank-*-ready.json")]
        validate_ready(request, ready)
        if request["fault"] == "oom":
            receipts = list((root / "pipeline").rglob("workers/*/rank-1.json"))
            assert len(receipts) == 1, "Missing native OOM receipt"
            assert json.loads(receipts[0].read_text())["status"] == "oom", "OOM misclassified"
        validate_failure(request, events, json.loads((root / "exit-code.json").read_text()))
        task, identifiers = _task(root, request)
        status = str(task.status).rsplit(".", 1)[-1]
        assert status in {"failed", "stopped"}, "Faulted native task reported success"
        result = {
            "status": "expected-failure-verified",
            "fault": request["fault"],
            "task_ids": identifiers,
            "task_status": status,
        }
    write(root, "verification.json", result)


def rank(request_path: Path, number: int) -> int:
    from clearml_yolo.adapters.integrations import training_worker
    from clearml_yolo.application.training_workers import TrainingWorkerRequest
    from native_backend_ddp_observers import install_rank

    request = TrainingWorkerRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    root = Path(os.environ["CY_DDP_TRACE"])
    observer = install_rank(root, request, number)
    try:
        return training_worker.run(request_path, number)
    finally:
        observer.finish()


def main() -> None:
    action, directory = sys.argv[1:3]
    root = Path(directory)
    if action == "rank":
        raise SystemExit(rank(root, int(sys.argv[3])))
    request = json.loads((root / "request.json").read_text())
    if action == "prepare":
        prepare(root, request)
    elif action == "idle":
        from clearml_yolo.adapters.runtime.gpu_inventory import discover_gpus, require_idle

        require_idle(discover_gpus())
    elif action == "cancel-record":
        target = json.loads((root / "cancel-target.json").read_text())
        _event(root, "fault-cancel", rank=-1, target_pid=target, signal="SIGINT")
    elif action == "verify":
        verify(root, request)
    else:
        raise ValueError(f"Unknown native acceptance helper operation: {action}")


if __name__ == "__main__":
    main()
