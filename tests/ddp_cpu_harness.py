"""Isolated invocation owner for the real CPU DDP integration scenarios."""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from ddp_cpu_recording import CallbackModel, RecordingTask


def _prepare_native_inputs(root: Path) -> None:
    import matplotlib as mpl
    import ultralytics
    import yaml
    from ultralytics.utils import SETTINGS, get_user_config_dir

    architecture = Path(ultralytics.__file__).parent / "cfg/models/v8/yolov8.yaml"
    values = yaml.safe_load(architecture.read_text())
    values.update(scale="n", nc=1)
    (root / "yolov8n.yaml").write_text(yaml.safe_dump(values))
    # Dataset checks ask for Arial even with plots off. Supply a bundled local font.
    font = Path(mpl.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
    shutil.copyfile(font, cast(Callable[[], Path], get_user_config_dir)() / "Arial.ttf")
    for name in (
        "clearml",
        "comet",
        "dvc",
        "mlflow",
        "neptune",
        "raytune",
        "sync",
        "tensorboard",
        "wandb",
    ):
        dict.__setitem__(SETTINGS, name, False)


def _read_scalars(path: Path, task: RecordingTask, offset: int) -> int:
    with path.open("rb") as stream:
        stream.seek(offset)
        payload = stream.read()
    complete = payload.rfind(b"\n") + 1
    for line in payload[:complete].splitlines():
        task.report_scalar(**json.loads(line))
    return offset + complete


def _wait_workers(
    process: subprocess.Popen[str],
    root: Path,
    task: RecordingTask,
    scalar_journal: Path,
) -> tuple[bool, RuntimeError | None]:
    live = False
    offset = 0
    failure: RuntimeError | None = None
    while process.poll() is None:
        if failure is None:
            try:
                offset = _read_scalars(scalar_journal, task, offset)
            except RuntimeError as error:
                failure = error
        first_epoch = root / "first-epoch-ready"
        release = root / "release-first-epoch"
        observed = any(
            item["title"] == "metrics" and item["iteration"] == 0 for item in task.scalars
        )
        if first_epoch.exists() and not release.exists() and (observed or task.callback_failed):
            live = observed
            release.write_text("Owner consumed telemetry while workers were still running.\n")
        time.sleep(0.02)
    if failure is None:
        offset = _read_scalars(scalar_journal, task, offset)
    return live, failure


def _serialize_custom_trainer(root: Path, result: dict[str, Any]) -> dict[str, str]:
    import albumentations as augmentation
    import cloudpickle  # type: ignore[import-untyped]

    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config
    from clearml_yolo.adapters.integrations.native_trainer import trainer_with_transforms
    from clearml_yolo.core.transforms import TransformConfig

    pipeline_file = root / "augmentation.json"
    augmentation.save(
        augmentation.Compose(
            [
                augmentation.Mosaic(
                    grid_yx=(2, 2),
                    target_size=(64, 64),
                    cell_shape=(32, 32),
                    center_range=(0.5, 0.5),
                    fit_mode="contain",
                    p=1,
                ),
                # Deliberately differ from imgsz: native final geometry must still run.
                augmentation.Resize(height=48, width=80, p=1),
            ],
            bbox_params=augmentation.BboxParams(format="pascal_voc", label_fields=["labels"]),
        ),
        pipeline_file,
    )
    config = resolve_transform_config(
        TransformConfig(mode="albumentations", pipeline_file=pipeline_file)
    )
    assert config.snapshot is not None
    trainer_file = root / "trainer.pkl"
    # Use the production factory, serialized by value as in Ultralytics' DDP launch.
    trainer_file.write_bytes(cloudpickle.dumps(trainer_with_transforms(config)))
    pipeline_file.unlink()
    result["pipeline_source_removed"] = not pipeline_file.exists()
    result["pipeline_sha256"] = config.snapshot.sha256
    return {"trainer": str(trainer_file), "pipeline_source": str(pipeline_file)}


def _training(root: Path, ranks: int, scenario: str, result: dict[str, Any]) -> None:
    import cloudpickle
    from ultralytics.utils import get_user_config_dir

    from clearml_yolo.adapters.integrations.native_ddp import native_ddp_relay
    from clearml_yolo.adapters.integrations.native_runtime import native_runtime
    from clearml_yolo.adapters.storage.filesystem import initialize_filesystem

    task = RecordingTask.current
    assert task is not None
    model = CallbackModel()
    model.trainer = SimpleNamespace(ddp=True, args=SimpleNamespace())
    original_callbacks = {event: items.copy() for event, items in model.callbacks.items()}
    # Filesystem defaults intentionally persist for descendants; snapshot after initialization.
    initialize_filesystem()
    original_env = os.environ.copy()
    scalar_journal = Path(os.environ["CY_HOME"]) / "scalars.jsonl"
    scalar_journal.write_text("")
    try:
        with (
            patch.dict(os.environ, {"CY_SCALAR_JOURNAL": str(scalar_journal)}),
            native_runtime(),
            native_ddp_relay(task, model) as relay,
        ):
            # Workers inherit this temporary native settings directory, including its font.
            import matplotlib as mpl

            shutil.copyfile(
                Path(mpl.get_data_path()) / "fonts/ttf/DejaVuSans.ttf",
                cast(Callable[[], Path], get_user_config_dir)() / "Arial.ttf",
            )
            callbacks_file = root / "callbacks.pkl"
            callbacks_file.write_bytes(cloudpickle.dumps(model.callbacks))
            job = {"root": str(root), "callbacks": str(callbacks_file), "scenario": scenario}
            if scenario == "custom_mosaic":
                job.update(_serialize_custom_trainer(root, result))
            (root / "job.json").write_text(json.dumps(job))
            command = [
                sys.executable,
                "-m",
                "torch.distributed.run",
                "--standalone",
                "--nnodes=1",
                f"--nproc-per-node={ranks}",
                str(Path(__file__).with_name("ddp_cpu_worker.py")),
                str(root / "job.json"),
            ]
            with (root / "launcher.log").open("w") as output:
                process = subprocess.Popen(  # noqa: S603 - fixed interpreter and local test script
                    command, stdout=output, stderr=subprocess.STDOUT, text=True
                )
                live, publication_failure = _wait_workers(process, root, task, scalar_journal)
                result["live_telemetry"] = live
                result["launcher_returncode"] = process.returncode
            journal = relay._directory / "events.jsonl"
            if journal.exists():
                result["captured_events"] = [
                    json.loads(line)["event"] for line in journal.read_text().splitlines()
                ]
            _check_returncode(process.returncode)
            if publication_failure is not None:
                raise publication_failure
            relay.replay(model.trainer)
            result["effective_args"] = vars(model.trainer.args)
            result["best"] = str(model.trainer.best)
    except RuntimeError as error:
        result["error"] = str(error)
    finally:
        result["callbacks_restored"] = model.callbacks == original_callbacks
        result["environment_restored"] = dict(os.environ) == original_env
        result["changed_environment_keys"] = [
            key
            for key in original_env.keys() | os.environ.keys()
            if original_env.get(key) != os.environ.get(key)
        ]
        result["relay_threads"] = [
            thread.name for thread in threading.enumerate() if thread.name == "cy-native-ddp-relay"
        ]


def _check_returncode(returncode: int | None) -> None:
    if returncode:
        raise RuntimeError(f"Distributed workers failed with exit code {returncode}")


def main() -> None:
    import clearml
    import requests

    from clearml_yolo.adapters.integrations.native_ddp import NativeDDPRelay
    from clearml_yolo.adapters.integrations.native_runtime import OWNER_PID_ENV, OWNER_TASK_ENV

    root, ranks, scenario = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    task = RecordingTask(fail_callback=scenario == "owner_error")
    RecordingTask.current = task
    owner: ContextVar[RecordingTask | None] = ContextVar("ddp_test_owner", default=None)
    owner_token = owner.set(task)
    os.environ[OWNER_PID_ENV] = str(os.getpid())
    os.environ[OWNER_TASK_ENV] = task.id
    _prepare_native_inputs(root)
    result: dict[str, Any] = {
        "owner_pid": os.getpid(),
        "error": None,
        "captured_events": [],
        "replayed_events": [],
        "effective_args": {},
        "inference_images": 0,
    }
    dispatch = NativeDDPRelay._dispatch

    def record_dispatch(relay: NativeDDPRelay, record: dict[str, Any]) -> None:
        assert owner.get() is task
        dispatch(relay, record)
        result["replayed_events"].append(record["event"])

    def prohibit_http(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("CPU DDP tests must not access HTTP services")

    with (
        patch.object(clearml, "Task", RecordingTask),
        patch("clearml_yolo.adapters.clearml.session.active_task", owner.get),
        patch.object(NativeDDPRelay, "_dispatch", record_dispatch),
        patch.object(requests.Session, "request", prohibit_http),
    ):
        _training(root, ranks, scenario, result)
        if result["error"] is None:
            from ultralytics.models import YOLO

            prediction = YOLO(result["best"]).predict(
                str(root / "images/val/val-0.png"), device="cpu", imgsz=64, verbose=False
            )
            result["inference_images"] = sum(1 for _ in prediction)
    owner.reset(owner_token)
    result.update(
        publications=task.publications,
        scalars=task.scalars,
        output_models=task.output_models,
        owner_callback_failed=task.callback_failed,
    )
    (root / "result.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
