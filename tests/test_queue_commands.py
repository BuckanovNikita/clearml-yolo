"""Immutable submission composition and explicit allocation bindings."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf


def test_queue_bindings_preserve_native_settings_and_explicit_cpu() -> None:
    from clearml_yolo.entrypoints.hydra.queue_config import bind_devices

    config = OmegaConf.create(
        {
            "ultralytics": {"device": None, "compile": True, "batch": 20, "amp": False},
            "ultralytics_predict": {"device": "cpu", "batch": 3},
        }
    )
    bound = bind_devices(config, 5)
    assert bound.ultralytics.device == [0, 1, 2, 3, 4]
    assert bound.ultralytics_predict.device == "cpu"
    assert (bound.ultralytics.compile, bound.ultralytics.batch, bound.ultralytics.amp) == (
        True,
        20,
        False,
    )
    assert config.ultralytics.device is None


def test_queue_binds_backend_inference_to_first_gpu() -> None:
    from clearml_yolo.entrypoints.hydra.queue_config import bind_devices

    config = OmegaConf.create(
        {
            "model": {
                "backend": "fasterrcnn",
                "train": {"device": "cuda"},
                "predict": {"device": "cuda"},
            }
        }
    )
    bound = bind_devices(config, 2)
    assert bound.model.train.device == [0, 1]
    assert bound.model.predict.device == [0]


def test_submission_resolves_whole_sweep_and_freezes_settings(tmp_path: Path) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    snapshots = compose_snapshots(
        [
            "-m",
            "ground_truth=outside.csv",
            "ultralytics.epochs=1,2",
            "ultralytics.compile=false",
            "ultralytics_predict.device=cpu",
        ],
        ResourceRequest(gpus=2),
        project_root=tmp_path,
    )
    assert len(snapshots) == 2
    assert [json.loads(item.config_json)["ultralytics"]["epochs"] for item in snapshots] == [1, 2]
    assert all(item.request.count == 2 for item in snapshots)
    assert all(item.cwd == str(Path.cwd()) for item in snapshots)
    assert all(
        json.loads(item.config_json)["ultralytics"]["compile"] is False for item in snapshots
    )


@pytest.mark.parametrize("override", ["ultralytics.device=0", "ultralytics_predict.device=[1,2]"])
def test_queue_rejects_conflicting_native_gpu_overrides(tmp_path: Path, override: str) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    with pytest.raises(ValueError, match=r"cy-queue.*--devices|allocation"):
        compose_snapshots(
            ["ground_truth=input.csv", override], ResourceRequest(gpus=1), project_root=tmp_path
        )


def test_snapshot_rejects_execution_after_package_identity_change(tmp_path: Path) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots, validate_snapshot

    snapshot = compose_snapshots(
        ["ground_truth=input.csv"], ResourceRequest(gpus=1), project_root=tmp_path
    )[0]
    with pytest.raises(ValueError, match="identity"):
        validate_snapshot(snapshot.model_copy(update={"package_identity": "old-code"}))


@pytest.mark.parametrize(
    "override",
    [
        "run_dir={outside}",
        "hydra.output_subdir={outside}",
        "+hydra.job.env_set.CUDA_VISIBLE_DEVICES=2",
    ],
)
def test_submission_rejects_escaping_paths_and_environment_allocation_override(
    tmp_path: Path, override: str
) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    with pytest.raises(ValueError, match=r"contained|allocation"):
        compose_snapshots(
            ["ground_truth=input.csv", override.format(outside=tmp_path.parent / "escape")],
            ResourceRequest(gpus=1),
            project_root=tmp_path,
        )


def test_sweep_freezes_hydra_output_and_logging_configuration(tmp_path: Path) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    snapshots = compose_snapshots(
        [
            "-m",
            "ground_truth=input.csv",
            "ultralytics.epochs=1,2",
            f"hydra.sweep.dir={tmp_path}/sweep",
            "hydra.sweep.subdir=${hydra.job.num}",
            "hydra.output_subdir=config",
            "hydra/job_logging=disabled",
        ],
        ResourceRequest(gpus=1),
        project_root=tmp_path,
    )
    for index, snapshot in enumerate(snapshots):
        settings = json.loads(snapshot.config_json)["hydra"]
        assert settings["run"]["dir"] == str(tmp_path / "sweep" / str(index))
        assert settings["output_subdir"] == "config"
        assert settings["job_logging"]["disable_existing_loggers"] is True


def test_cli_submits_lists_reorders_and_cancels_without_runtime(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "clearml_yolo.entrypoints.queue",
        "--root",
        str(tmp_path / "queue"),
    ]
    environment = dict(os.environ, CY_HOME=str(tmp_path))

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - fixed package CLI and isolated local records
            [*command, *arguments],
            env=environment,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    submitted = run(
        "submit", "--gpus", "2", "--", "-m", "ground_truth=input.csv", "ultralytics.epochs=1,2"
    )
    assert submitted.returncode == 0, submitted.stderr
    ids = submitted.stdout.splitlines()
    assert len(ids) == 2
    assert len(set(ids)) == 2
    listed = run("list", "--json")
    assert listed.returncode == 0, listed.stderr
    view = json.loads(listed.stdout)
    assert [job["id"] for job in view["jobs"]] == ids
    assert all(job["state"] == "pending" for job in view["jobs"])
    assert "config_json" not in listed.stdout
    moved = run("move", ids[1], "top", "--revision", str(view["revision"]))
    assert moved.returncode == 0, moved.stderr
    stale = run("move", ids[0], "top", "--revision", str(view["revision"]))
    assert stale.returncode != 0
    cancelled = run("cancel", ids[1])
    assert cancelled.returncode == 0, cancelled.stderr
    assert json.loads(cancelled.stdout)["state"] == "cancelled"
    assert run("list", "--json").returncode == 0


@pytest.mark.parametrize(
    "overrides",
    [
        ["ultralytics.device=cpu,0"],
        ["metrics.evaluation.iou_threshold=0.5,2.0"],
        ["compare.q=0.05,2.0"],
        ["compare.bootstrap_iterations=100,0"],
        ["weights=model.pt", "skip_train=true,false"],
        ["+report.output=bad.csv"],
        ["compare.baseline_model.source=clearml,local"],
        ["clearml.output_uri=true,false"],
        ["fiftyone.publish_timeout_seconds=60,-1"],
        ["ultralytics_predict.imgsz=64,0"],
        ["ultralytics_predict.batch=1,0"],
        ["ultralytics_predict.mode=predict,train"],
        ["skip_train=false,garbage"],
        ["ground_truth=input.csv,123"],
        ["splits=[val,test],[123]"],
        ["ultralytics_predict.conf=0.001,2.0"],
        ["ultralytics_predict.iou=0.7,-0.1"],
        ["ultralytics_predict.save=false,1"],
        ["ultralytics.epochs=1,0"],
        ["ultralytics.compile=false,2"],
        ["ultralytics.amp=true,broken"],
    ],
)
def test_invalid_sweep_does_not_commit_partial_batch(tmp_path: Path, overrides: list[str]) -> None:
    result = subprocess.run(  # noqa: S603 - fixed CLI with invalid user-input fixture
        [
            sys.executable,
            "-m",
            "clearml_yolo.entrypoints.queue",
            "--root",
            str(tmp_path / "queue"),
            "submit",
            "--gpus",
            "1",
            "--",
            "-m",
            "ground_truth=input.csv",
            *overrides,
        ],
        env=dict(os.environ, CY_HOME=str(tmp_path)),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert not list((tmp_path / "queue").rglob("snapshot.json"))


def test_queue_rejects_auto_gpu_with_migration_guidance_before_composition(tmp_path: Path) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    with pytest.raises(ValueError, match=r"Legacy.*cy-queue allocation"):
        compose_snapshots(
            ["ground_truth=input.csv", "+auto_gpu.enabled=true"],
            ResourceRequest(gpus=1),
            project_root=tmp_path,
        )


@pytest.mark.parametrize(
    "legacy",
    ["queue: default", "autogpu: default", "auto_gpu: default", "hydra/launcher: cy_queue"],
)
def test_saved_legacy_defaults_report_queue_migration(tmp_path: Path, legacy: str) -> None:
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    directory = tmp_path / "config"
    directory.mkdir()
    (directory / "legacy.yaml").write_text(
        f"defaults:\n  - pipeline\n  - {legacy}\n  - _self_\nground_truth: input.csv\n"
    )
    with pytest.raises(ValueError, match=r"Legacy.*cy-queue"):
        compose_snapshots(
            ["--config-dir", str(directory), "--config-name", "legacy"],
            ResourceRequest(gpus=1),
            project_root=tmp_path,
        )


def test_tui_moves_and_cancels_real_pending_jobs(tmp_path: Path) -> None:
    pytest.importorskip("textual")
    from clearml_yolo.adapters.queue.identity import current_identity
    from clearml_yolo.adapters.queue.inventory import QueueGPUInventory
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import ResourceRequest
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots
    from clearml_yolo.entrypoints.queue_tui import QueueApp

    identity = current_identity()
    storage = NFSQueueStore(tmp_path / "queue", identity)
    service = QueueService(
        storage,
        QueueGPUInventory(),
        QueueProcesses(storage, identity, local_root=tmp_path / "locks"),
        identity,
    )
    jobs = service.submit(
        compose_snapshots(
            ["-m", "ground_truth=input.csv", "ultralytics.epochs=1,2"],
            ResourceRequest(gpus=1),
            project_root=tmp_path,
        )
    )

    async def exercise() -> None:
        application = QueueApp(service)
        async with application.run_test(size=(150, 35)) as pilot:
            await pilot.press("d")
            assert service.list().jobs[0].id == jobs[1].id
            await pilot.press("c")
            assert (
                next(job for job in service.list().jobs if job.id == jobs[0].id).state
                == "cancelled"
            )
            await pilot.press("q")

    asyncio.run(exercise())
    assert next(job for job in service.list().jobs if job.id == jobs[1].id).state == "pending"
