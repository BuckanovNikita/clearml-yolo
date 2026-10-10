"""Bounded, isolated subprocess execution for CPU DDP scenarios."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil  # type: ignore[import-untyped]
from PIL import Image, ImageDraw


def _fixtures(root: Path) -> None:
    for split in ("train", "val"):
        images = root / "images" / split
        labels = root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        for index in range(8):
            picture = Image.new("RGB", (64, 64), (index * 20, 20, 40))
            ImageDraw.Draw(picture).rectangle((16, 16, 48, 48), fill=(255, 220, 80))
            picture.save(images / f"{split}-{index}.png")
            (labels / f"{split}-{index}.txt").write_text("0 0.5 0.5 0.5 0.5\n")
    (root / "data.yaml").write_text(
        f"path: {json.dumps(str(root))}\ntrain: images/train\nval: images/val\nnames: [object]\n"
    )


def _environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key in {
            "RANK",
            "LOCAL_RANK",
            "WORLD_SIZE",
            "MASTER_ADDR",
            "MASTER_PORT",
        } or key.startswith(
            ("CLEARML_", "TRAINS_", "CY_CLEARML_OWNER_", "TORCHELASTIC_", "FIFTYONE_")
        ):
            env.pop(key)
    env.update(
        CUDA_VISIBLE_DEVICES="",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        GLOO_SOCKET_IFNAME="lo",
        YOLO_OFFLINE="true",
        YOLO_CONFIG_DIR=str(root / "settings"),
        CY_HOME=str(root / "workspace"),
        MPLCONFIGDIR=str(root / "matplotlib"),
        MPLBACKEND="Agg",
        PYTHONUNBUFFERED="1",
    )
    return env


def _registered_processes(root: Path) -> list[Any]:
    # psutil exposes process handles without typing in the locked environment.
    processes = []
    for path in root.glob("*.pid"):
        identity = json.loads(path.read_text())
        try:
            process = psutil.Process(identity["pid"])
            if process.create_time() == identity["create_time"]:
                processes.append(process)
        except psutil.NoSuchProcess:
            continue
    return processes


def _stop_tree(process: subprocess.Popen[str], root: Path) -> None:
    """Torch elastic workers own sessions, so terminate descendants as well as the owner."""
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []
    descendants = list(
        {child.pid: child for child in [*descendants, *_registered_processes(root)]}.values()
    )
    for child in reversed(descendants):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            continue
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    _, alive = psutil.wait_procs(descendants, timeout=5)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            continue
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    psutil.wait_procs(alive, timeout=5)


def run_scenario(root: Path, ranks: int, scenario: str) -> dict[str, Any]:
    """Run one owner with its ranks, retaining bounded diagnostics in pytest's temp directory."""
    _fixtures(root)
    script = Path(__file__).with_name("ddp_cpu_harness.py")
    with (root / "owner.log").open("w") as output:
        process = subprocess.Popen(  # noqa: S603 - fixed interpreter and task-owned inputs
            [sys.executable, str(script), str(root), str(ranks), scenario],
            cwd=root,
            env=_environment(root),
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            process.wait(timeout=180)
        finally:
            remaining_pids = [child.pid for child in _registered_processes(root)]
            _stop_tree(process, root)
    logs = "\n".join(f"{path.name}:\n{path.read_text()}" for path in sorted(root.glob("*.log")))
    assert process.returncode == 0, logs
    result: dict[str, Any] = json.loads((root / "result.json").read_text())
    result["workers"] = [json.loads(path.read_text()) for path in sorted(root.glob("rank-*.json"))]
    result["remaining_pids"] = remaining_pids
    result["runtime_directories"] = [
        str(path) for path in (root / "workspace" / ".tmp").glob("cy-native*")
    ]
    # Keep failed scenarios' logs/checkpoints; ephemeral runtime state must disappear.
    return result
