"""Torchrun child process for the native CPU distributed-training integration test."""

import json
import os
import signal
import sys
import traceback
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


def _prohibit_worker_tracking(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("Native DDP workers must not create tasks, publish or use HTTP")


def _train(job: dict[str, Any], evidence: dict[str, Any]) -> None:
    import cloudpickle  # type: ignore[import-untyped]
    import requests
    from clearml import Task
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    from clearml_yolo.adapters.clearml.session import active_task
    from clearml_yolo.adapters.integrations.native_runtime import native_runtime
    from ddp_cpu_trainer import CpuDetectionTrainer

    with ExitStack() as stack:
        for method in ("init", "create", "upload_artifact", "connect"):
            stack.enter_context(patch.object(Task, method, _prohibit_worker_tracking))
        stack.enter_context(patch.object(requests.Session, "request", _prohibit_worker_tracking))
        stack.enter_context(native_runtime())
        evidence["worker_tracking_disabled"] = not SETTINGS["clearml"] and not integration.callbacks
        evidence["active_task_none"] = active_task() is None and Task.current_task() is None
        assert evidence["worker_tracking_disabled"]
        assert evidence["active_task_none"]
        with Path(job["callbacks"]).open("rb") as stream:
            callbacks = cloudpickle.load(stream)
        trainer = CpuDetectionTrainer(
            root=Path(job["root"]),
            scenario=job["scenario"],
            evidence=evidence,
            callbacks=callbacks,
        )
        trainer.train()  # type: ignore[no-untyped-call]
        evidence["completed"] = True


def _terminate(signum: int, frame: Any) -> None:
    raise SystemExit(128 + signum)


def main() -> None:
    import psutil  # type: ignore[import-untyped]
    import torch
    import torch.distributed as dist

    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(job["root"])
    signal.signal(signal.SIGTERM, _terminate)
    rank = int(os.environ["RANK"])
    evidence: dict[str, Any] = {
        "pid": os.getpid(),
        "rank": rank,
        "world_size": int(os.environ["WORLD_SIZE"]),
        "backend": None,
        "device": None,
        "cuda_initialized": False,
        "worker_tracking_disabled": False,
        "active_task_none": False,
        "ddp": False,
        "distributed_sampler": False,
        "epochs": [],
        "validation_calls": 0,
        "final_validation_calls": 0,
        "error": None,
        "completed": False,
    }
    with (
        (root / f"rank-{rank}.log").open("w", encoding="utf-8") as stream,
        redirect_stdout(stream),
        redirect_stderr(stream),
    ):
        try:
            assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
            (root / f"rank-{rank}.pid").write_text(
                json.dumps({"pid": os.getpid(), "create_time": psutil.Process().create_time()}),
                encoding="utf-8",
            )
            _train(job, evidence)
        except BaseException as error:
            # This executable owns reporting even interruption or a failed rank launch.
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            traceback.print_exc()
            raise
        finally:
            evidence["cuda_initialized"] = torch.cuda.is_initialized()  # type: ignore[no-untyped-call]
            try:
                if dist.is_initialized():
                    dist.destroy_process_group()
            finally:
                (root / f"rank-{rank}.json").write_text(
                    json.dumps(evidence, indent=2), encoding="utf-8"
                )


if __name__ == "__main__":
    main()
