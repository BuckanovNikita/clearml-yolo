"""Bounded task-owned native publication and real ClearML cache acceptance."""

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path

from clearml import Task
from clearml.automation.job import ClearmlJob
from PIL import Image, ImageDraw

from clearml_yolo.adapters.clearml.cache import normalize_task_hash

EVIDENCE = Path(os.environ.get("CY_ACCEPT_EVIDENCE", str(Path(__file__).resolve().parent)))
ROOT = Path(os.environ["CY_RUN_DIR"]).resolve()
TAG = os.environ["CY_RUN_TAG"]
PROJECT = f"{TAG} clearml-yolo"
REPO = Path(os.environ["CY_PROJECT_ROOT"])
SUMMARY = {"tag": TAG, "project": PROJECT, "runs": [], "cache": []}


def save():
    (EVIDENCE / "summary.json").write_text(json.dumps(SUMMARY, indent=2) + "\n")


def snapshot(task):
    task.reload()
    return {
        "id": task.id, "name": task.name, "status": str(task.status),
        "output_uri": task.output_uri,
        "output_models": [
            {"id": model.id, "name": model.name, "url": model.url, "task": model.task,
             "published": model.published}
            for model in task.models["output"]
        ],
    }


def dataset():
    inputs = ROOT / "inputs"
    inputs.mkdir()
    source = inputs / "ground_truth.csv"
    with source.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "image_name", "image_path", "instance_label", "bbox_x_tl",
            "bbox_y_tl", "bbox_x_br", "bbox_y_br", "split",
        ])
        for split, count in [("train", 4), ("val", 2), ("test", 2)]:
            for index in range(count):
                path = inputs / f"{split}-{index}.PNG"
                image = Image.new("RGB", (96, 64), (20 + 12 * index, 30, 40))
                background = split != "train" and index == 1
                if not background:
                    ImageDraw.Draw(image).rectangle((20, 12, 60, 48), fill=(220, 120, 90))
                image.save(path)
                box = ["", "", "", "", ""] if background else ["object", 20, 12, 60, 48]
                writer.writerow([path.name, path.name, *box, split])
    return source


def run_native(name, source, *, device="cpu", task=None, lr=0.01):
    args = [
        sys.executable, "-m", "clearml_yolo.entrypoints.train",
        f"ground_truth={source}",
        f"clearml.project_name={PROJECT}", f"clearml.tags=[{TAG}]",
        f"clearml.task_name={name}", "ultralytics.model=yolo11n.yaml",
        "ultralytics.pretrained=false", "ultralytics.epochs=1",
        "ultralytics.batch=2", "ultralytics.imgsz=64", "ultralytics.workers=0",
        f"ultralytics.device={device}", f"ultralytics_predict.device={device}",
        "ultralytics.compile=false", "ultralytics.amp=false",
        "ultralytics.plots=true", "ultralytics.optimizer=SGD",
        "ultralytics.mosaic=0", f"ultralytics.lr0={lr}",
        f"ultralytics.project={ROOT / name}", "ultralytics.name=train",
        f"dataset_cache_dir={ROOT / 'dataset-cache'}",
        f"hydra.run.dir={ROOT / 'hydra' / name}",
    ]
    environment = dict(os.environ)
    environment["CY_HOME"] = str(ROOT)
    environment["OMP_NUM_THREADS"] = "2"
    environment["MKL_NUM_THREADS"] = "2"
    environment["OPENBLAS_NUM_THREADS"] = "2"
    if task:
        for key in ("CLEARML_PROC_MASTER_ID", "TRAINS_PROC_MASTER_ID"):
            environment.pop(key, None)
        environment["CLEARML_TASK_ID"] = task.id
        environment["TRAINS_TASK_ID"] = task.id
        environment["CLEARML_LOG_TASK_TO_BACKEND"] = "1"
        environment["CLEARML_SIMULATE_REMOTE_TASK"] = "1"
        task.mark_started()
        if os.environ.get("CY_ACCEPT_TRACE") == "1":
            args = [sys.executable, str(Path(__file__).parent / "trace_remote.py"), *args[3:]]
            environment["CY_ACCEPT_TRACE_OUTPUT"] = str(EVIDENCE / "sdk-reopen-trace.jsonl")
    record = {"name": name, "device": device, "command": args, "task_id": task.id if task else None}
    if task:
        record["before"] = snapshot(task)
        record["remote_environment"] = {
            key: environment[key] for key in (
                "CLEARML_TASK_ID", "TRAINS_TASK_ID", "CLEARML_LOG_TASK_TO_BACKEND",
                "CLEARML_SIMULATE_REMOTE_TASK",
            )
        }
    SUMMARY["runs"].append(record)
    save()
    print(f"RUN {name} device={device}", flush=True)
    started = time.monotonic()
    with (EVIDENCE / f"{name}.log").open("w") as stream:
        completed = subprocess.run(args, cwd=REPO, env=environment, stdout=stream,
                                   stderr=subprocess.STDOUT, timeout=600, check=False)
    record["exit_code"] = completed.returncode
    record["seconds"] = round(time.monotonic() - started, 2)
    if task:
        record["after"] = snapshot(task)
    save()
    if completed.returncode:
        raise RuntimeError(f"{name} exited {completed.returncode}; see its log")
    if task is None:
        tasks = Task.get_tasks(project_name=PROJECT, task_name=f"^{name}/train$")
        if len(tasks) != 1:
            raise AssertionError(f"Expected exactly one {name!r} task; got {len(tasks)}")
        task = tasks[0]
    task.reload()
    record["task_id"] = task.id
    record["status"] = str(task.status)
    assert str(task.status) == "completed", record
    record["general"] = task.get_parameters(backwards_compatibility=False)
    for key in ("device", "project", "name", "save_dir", "exist_ok", "data"):
        assert f"General/{key}" not in record["general"], (name, key)
    run = json.loads(task.get_configuration_object("run"))
    assert run["ultralytics"]["device"] in (device, int(device) if device.isdigit() else device)
    assert run["ultralytics"]["project"] == str(ROOT / name), run["ultralytics"]["project"]
    assert run["ultralytics"]["epochs"] == 1
    assert run["prepared_dataset"]["cache_identity"]
    record["canonical_run"] = run
    record["artifacts"] = {}
    for artifact_name, artifact in task.artifacts.items():
        path = Path(artifact.get_local_copy(force_download=True))
        record["artifacts"][artifact_name] = {
            "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    assert "gt_csv" in record["artifacts"]
    models = task.models["output"]
    assert len(models) == 1, [model.id for model in models]
    model_path = Path(models[0].get_local_copy(force_download=True, raise_on_error=True))
    from ultralytics import YOLO
    loaded = YOLO(str(model_path))
    assert loaded.names == {0: "object"}, loaded.names
    local_best = ROOT / name / "train" / "weights" / "best.pt"
    assert model_path.read_bytes() == local_best.read_bytes()
    record["model"] = {
        "id": models[0].id, "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "bytes": model_path.stat().st_size, "names": loaded.names,
    }
    record["scalar_titles"] = sorted(task.get_reported_scalars())
    assert record["scalar_titles"]
    save()
    print(f"PASS {name} task={task.id}", flush=True)
    return task, run


def main():
    source = dataset()
    if os.environ.get("CY_ACCEPT_MODE") == "direct-gpu":
        run_gpu(source)
        return
    seed, seed_run = run_native("native-cpu-template", source)
    ClearmlJob.register_hashing_callback(normalize_task_hash)
    first_run = deepcopy(seed_run)
    first_run["ultralytics"]["project"] = str(ROOT / "controller-first")
    first_run["clearml"]["task_name"] = "controller-first"
    first = ClearmlJob(
        base_task_id=seed.id, allow_caching=True, tags=[TAG],
        configuration_overrides={"run": json.dumps(first_run, ensure_ascii=False)},
        task_overrides={"name": "controller-first"},
    )
    assert not first.is_cached_task()
    SUMMARY["cache"].append({"case": "initial_miss", "task_id": first.task.id, "cached": False})
    save()
    run_native("controller-first", source, task=first.task)

    rerouted = deepcopy(first_run)
    rerouted["ultralytics"]["project"] = str(ROOT / "cache-hit-output")
    rerouted["clearml"]["task_name"] = "cache-hit-output"
    second = ClearmlJob(
        base_task_id=seed.id, allow_caching=True, tags=[TAG],
        configuration_overrides={"run": json.dumps(rerouted, ensure_ascii=False)},
        task_overrides={"name": "cache-hit-output"},
    )
    assert second.is_cached_task(), second.task.id
    assert second.task.id == first.task.id
    assert not (ROOT / "cache-hit-output").exists()
    SUMMARY["cache"].append({
        "case": "routing_hit", "task_id": second.task.id, "cached": True,
        "no_new_output_directory": True,
    })
    save()
    print(f"PASS routing cache hit task={second.task.id}", flush=True)

    changed = deepcopy(rerouted)
    changed["ultralytics"]["project"] = str(ROOT / "controller-scientific-miss")
    changed["clearml"]["task_name"] = "controller-scientific-miss"
    changed["ultralytics"]["lr0"] = 0.02
    third = ClearmlJob(
        base_task_id=seed.id, allow_caching=True, tags=[TAG],
        configuration_overrides={"run": json.dumps(changed, ensure_ascii=False)},
        parameter_override={"General/lr0": 0.02},
        task_overrides={"name": "controller-scientific-miss"},
    )
    assert not third.is_cached_task()
    assert third.task.id != first.task.id
    SUMMARY["cache"].append({
        "case": "scientific_miss", "task_id": third.task.id, "cached": False, "lr0": 0.02,
    })
    save()
    run_native("controller-scientific-miss", source, task=third.task, lr=0.02)
    SUMMARY["t008"] = "passed"
    save()
    if os.environ.get("CY_ACCEPT_GPU") == "1":
        run_gpu(source)
    save()


def run_gpu(source):
    capacity = subprocess.run(
        ["python3", os.environ["CY_INFRA_SKILL_DIR"] + "/scripts/infra.py", "room"],
        text=True, capture_output=True, check=True,
    )
    (EVIDENCE / "gpu-capacity.log").write_text(capacity.stdout)
    gpu = subprocess.run(["nvidia-smi"], text=True, capture_output=True, check=True)
    (EVIDENCE / "gpu-before.log").write_text(gpu.stdout)
    processes = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory",
         "--format=csv,noheader"],
        text=True, capture_output=True, check=True,
    )
    assert not processes.stdout.strip(), "Pre-existing GPU compute process; GPU gate deferred"
    run_native("native-single-gpu", source, device="0")
    SUMMARY["single_gpu"] = "passed"
    save()


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        SUMMARY["error"] = f"{type(error).__name__}: {error}"
        save()
        raise
