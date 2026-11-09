"""CPU smoke run of the top-level ``ultralytics`` pipeline against the shared ClearML stand.

A tiny synthetic YOLO dataset (disjoint train/val/test, one empty image per split) becomes
ground truth through ``cy-ground-truth``; ``cy`` trains one CPU epoch, predicts, calibrates on
val and evaluates. Both commands publish into the run's tagged project, and the ClearML SDK
then proves the pipeline task completed with an Output Model and its evaluation artifacts.
``live_run`` removes every object of the run tag afterwards.

Weights are explicit and local: ``CY_SMOKE_WEIGHTS``, else ``yolo11n.pt`` in this checkout or
the main checkout of this repository (``*.pt`` is ignored, so worktrees usually lack it).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from integration import lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]
WEIGHTS_VARIABLE = "CY_SMOKE_WEIGHTS"
WEIGHTS_NAME = "yolo11n.pt"
COMMAND_TIMEOUT_SECONDS = 1800
IMAGE_SIZE = 96
# Images per split with one box each; every split also gets one empty image.
SPLITS = {"train": 4, "val": 2, "test": 2}
PIPELINE_TASK = "cpu-smoke-pipeline"
REQUIRED_ARTIFACTS = frozenset(
    {
        "gt_csv",
        "predicts_csv",
        "metrics_best_confidences_val",
        "metrics_dashboard_full_test",
        "pipeline_outcome",
    }
)


def _main_checkout() -> Path | None:
    completed = subprocess.run(  # noqa: S603 - fixed git query
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],  # noqa: S607 - git on PATH
        check=False,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).parent if completed.returncode == 0 and completed.stdout.strip() else None


def _weights() -> Path:
    explicit = os.environ.get(WEIGHTS_VARIABLE, "")
    if explicit:
        if not Path(explicit).is_file():
            pytest.fail(f"{WEIGHTS_VARIABLE}={explicit} is not a file", pytrace=False)
        return Path(explicit).resolve()
    for root in (REPO_ROOT, _main_checkout()):
        if root is not None and (root / WEIGHTS_NAME).is_file():
            return (root / WEIGHTS_NAME).resolve()
    pytest.fail(
        f"no local {WEIGHTS_NAME} in this or the main checkout; place it there or set {WEIGHTS_VARIABLE}",
        pytrace=False,
    )


def _write_dataset(root: Path) -> Path:
    """Write a one-class YOLO dataset whose split image names never overlap."""
    for split, boxed in SPLITS.items():
        images = root / "images" / split
        labels = root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        for index in range(boxed + 1):
            name = f"{split}-{index}"
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (40, 40, 40))
            label = ""
            if index < boxed:
                left = 8 + 12 * index
                top = 10 + 8 * index
                size = 36
                ImageDraw.Draw(image).rectangle((left, top, left + size, top + size), fill=(230, 200, 30))
                center_x = (left + size / 2) / IMAGE_SIZE
                center_y = (top + size / 2) / IMAGE_SIZE
                label = f"0 {center_x:.6f} {center_y:.6f} {size / IMAGE_SIZE:.6f} {size / IMAGE_SIZE:.6f}\n"
            image.save(images / f"{name}.png")
            (labels / f"{name}.txt").write_text(label, encoding="utf-8")
    data = root / "data.yaml"
    data.write_text(
        f"path: {root}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: box\n",
        encoding="utf-8",
    )
    return data


def _command(name: str) -> str:
    executable = Path(sys.executable).parent / name
    if not executable.is_file():
        pytest.fail(f"{name} is not installed next to {sys.executable}", pytrace=False)
    return str(executable)


def _run(arguments: list[str], cwd: Path, environment: dict[str, str], log: Path) -> None:
    with log.open("w", encoding="utf-8") as output:
        completed = subprocess.run(  # noqa: S603 - project entrypoint with test-owned arguments
            arguments,
            check=False,
            cwd=cwd,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    if completed.returncode != 0:
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-60:])
        pytest.fail(f"{Path(arguments[0]).name} exited {completed.returncode}; log {log}:\n{tail}", pytrace=False)


def test_cpu_pipeline_publishes_a_completed_tagged_task(live_run: lifecycle.Run, tmp_path: Path) -> None:
    from clearml import Task

    project = lifecycle.tagged_project_name(live_run.tag)
    tags = f"clearml.tags=[{live_run.tag}]"
    environment = dict(os.environ)
    # The invocation workspace owns the dataset, ground truth and run directory.
    environment["CY_HOME"] = str(tmp_path)
    data = _write_dataset(tmp_path / "dataset")
    truth = tmp_path / "ground_truth.csv"

    _run(
        [
            _command("cy-ground-truth"),
            f"data_yaml={data}",
            f"output={truth}",
            f"clearml.project_name={project}",
            "clearml.task_name=cpu-smoke-ground-truth",
            tags,
        ],
        tmp_path,
        environment,
        tmp_path / "ground-truth.log",
    )
    assert truth.is_file()
    _run(
        [
            _command("cy"),
            f"ground_truth={truth}",
            f"ultralytics.model={_weights()}",
            "ultralytics.device=cpu",
            "ultralytics.epochs=1",
            "ultralytics.imgsz=64",
            "ultralytics.batch=2",
            "ultralytics.workers=0",
            "ultralytics.plots=false",
            # The packaged default compiles; eager CPU keeps the smoke run short.
            "ultralytics.compile=false",
            "ultralytics_predict.device=cpu",
            "fiftyone.enabled=false",
            f"run_dir={tmp_path / 'run'}",
            f"clearml.project_name={project}",
            f"clearml.task_name={PIPELINE_TASK}",
            tags,
        ],
        tmp_path,
        environment,
        tmp_path / "pipeline.log",
    )

    candidates: list[Task] = Task.get_tasks(project_name=project, task_name=PIPELINE_TASK, tags=[live_run.tag])
    found = [candidate for candidate in candidates if candidate.name == PIPELINE_TASK]
    assert len(found) == 1, [candidate.id for candidate in found]
    task = found[0]
    assert task.get_status() in {"completed", "published"}
    assert live_run.tag in task.get_tags()
    assert task.models["output"], "the pipeline published no Output Model"
    missing = REQUIRED_ARTIFACTS - set(task.artifacts)
    assert not missing, f"missing artifacts {sorted(missing)}; present {sorted(task.artifacts)}"
    outcome = task.artifacts["pipeline_outcome"].get_local_copy()
    assert outcome is not None
    assert Path(outcome).exists()
