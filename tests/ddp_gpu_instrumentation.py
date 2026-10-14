"""Observers/fault gates installed only in acceptance-owned fresh Python processes."""

import hashlib
import json
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any


def write(root: Path, name: str, value: Any) -> None:
    temporary = root / f".{name}-{os.getpid()}.tmp"
    temporary.write_text(json.dumps(value, default=str), encoding="utf-8")
    temporary.replace(root / name)


def _event(root: Path, kind: str, **values: Any) -> None:
    with (root / f"events-{os.getpid()}.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps({"kind": kind, "pid": os.getpid(), "at": time.time(), **values}, default=str)
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def _gate(root: Path, name: str) -> None:
    request = json.loads((root / "request.json").read_text())
    deadline = time.monotonic() + float(request["timeout"])
    while not (root / name).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Acceptance controller did not open {name}")
        time.sleep(0.05)


def _parameters(model: Any) -> str:
    from ultralytics.utils.torch_utils import unwrap_model

    digest = hashlib.sha256()
    for name, parameter in unwrap_model(model).named_parameters():
        if parameter.requires_grad:
            digest.update(name.encode())
            digest.update(parameter.detach().float().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def install() -> None:
    """Observe real native/SDK boundaries; do not replace trainers, transports or queue effects."""
    root = Path(os.environ["CY_DDP_TRACE"])
    request = json.loads((root / "request.json").read_text())
    scenario = request["scenario"]
    from clearml_yolo.adapters.queue.identity import process_birth

    write(
        root,
        f"process-{os.getpid()}.json",
        {
            "pid": os.getpid(),
            "born": process_birth(os.getpid()),
            "argv": sys.argv,
            "rank": os.environ.get("RANK"),
            "uid": os.geteuid(),
        },
    )
    rank = int(os.environ.get("RANK", "-1"))
    _install_native(root, request, rank)
    _install_predict(root, scenario, rank)
    _install_sdk(root, rank)


def _install_native(root: Path, request: dict[str, Any], rank: int) -> None:
    import torch
    import torch.distributed as dist
    from ultralytics.engine.trainer import BaseTrainer
    from ultralytics.engine.validator import BaseValidator

    scenario = request["scenario"]
    # Installed native classes expose dynamic method replacement at this observer boundary.
    trainer_type: Any = BaseTrainer
    original_callbacks = trainer_type.run_callbacks

    @wraps(original_callbacks)
    def callbacks(trainer: Any, event: str) -> Any:
        if rank >= 0 and event == "on_train_start":
            assert dist.is_initialized()
            assert dist.get_backend() == "nccl"
            assert trainer.device.type == "cuda"
            assert torch.cuda.current_device() == int(os.environ["LOCAL_RANK"])
            native = trainer.model.module
            compiled = hasattr(native, "_orig_mod")
            assert compiled == request["compiled"], (
                "Requested torch.compile did not wrap the native model"
            )
            record = {
                "pid": os.getpid(),
                "rank": rank,
                "local_rank": int(os.environ["LOCAL_RANK"]),
                "world_size": dist.get_world_size(),
                "backend": dist.get_backend(),
                "device": str(trainer.device),
                "uuid": str(torch.cuda.get_device_properties(trainer.device).uuid),
                "visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
                "compiled": compiled,
                "initial_parameters": _parameters(trainer.model),
            }
            write(root, f"rank-{rank}-started.json", record)
            _event(root, "rank-started", **record)
            descriptor = os.open(
                root / f"rank-{rank}.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
            )
            os.dup2(descriptor, 1)
            os.dup2(descriptor, 2)
            os.close(descriptor)
            if scenario.startswith("queued"):
                _gate(root, "release-training")
        if rank == 1 and scenario == "queued-rank-exit" and event == "on_train_batch_start":
            _event(root, "injected-rank-exit", exit_code=73)
            os._exit(73)
        if rank >= 0 and event == "on_train_epoch_end":
            digest = _parameters(trainer.model)
            synchronized: list[Any] = [None] * dist.get_world_size()
            dist.all_gather_object(synchronized, digest)
            _event(
                root,
                "rank-epoch",
                rank=rank,
                epoch=int(trainer.epoch),
                parameters=digest,
                synchronized=synchronized,
            )
            assert len(set(synchronized)) == 1, "Actual NCCL rank parameters diverged"
        if rank >= 0 and event in {"on_val_start", "on_val_end", "on_train_end"}:
            _event(root, event, rank=rank)
        return original_callbacks(trainer, event)

    trainer_type.run_callbacks = callbacks
    validator_type: Any = BaseValidator
    original_validator_callbacks = validator_type.run_callbacks

    @wraps(original_validator_callbacks)
    def validator_callbacks(validator: Any, event: str) -> Any:
        if rank >= 0 and event == "on_val_end":
            assert validator.device.type == "cuda", "Native DDP validation left CUDA"
            _event(root, "native-validation", rank=rank, device=str(validator.device))
        return original_validator_callbacks(validator, event)

    validator_type.run_callbacks = validator_callbacks


def _install_predict(root: Path, scenario: str, rank: int) -> None:
    from ultralytics.engine.model import Model

    model_type: Any = Model
    original_predict = model_type.predict

    @wraps(original_predict)
    def predict(model: Any, *args: Any, **kwargs: Any) -> Any:
        if rank == -1:
            _event(
                root,
                "pipeline-predict",
                device=kwargs.get("device"),
                checkpoint=str(model.ckpt_path),
            )
            if not (root / "pipeline-predict-started.json").exists():
                write(
                    root, "pipeline-predict-started.json", {"pid": os.getpid(), "at": time.time()}
                )
                if scenario.startswith("queued"):
                    _gate(root, "release-predict")
        result = original_predict(model, *args, **kwargs)
        if rank == -1:
            assert model.predictor.device.type == "cuda", "Production prediction left CUDA"
            _event(root, "pipeline-predict-complete", device=str(model.predictor.device))
        return result

    model_type.predict = predict


def _install_sdk(root: Path, rank: int) -> None:
    from clearml import OutputModel, Task

    task_type: Any = Task
    output_model_type: Any = OutputModel
    for name in ("init", "create"):
        original = getattr(task_type, name)

        def task_factory(
            *args: Any, _original: Any = original, _name: str = name, **kwargs: Any
        ) -> Any:
            _event(root, f"task-{_name}-attempt", rank=rank)
            assert rank == -1, "A native DDP child attempted to create a real ClearML task"
            task = _original(*args, **kwargs)
            _event(root, f"task-{_name}", task_id=task.id, project=kwargs.get("project_name"))
            return task

        setattr(task_type, name, staticmethod(task_factory))
    original_upload = task_type.upload_artifact

    @wraps(original_upload)
    def upload(task: Any, name: str, *args: Any, **kwargs: Any) -> Any:
        _event(root, "artifact-attempt", name=name, task_id=task.id, rank=rank)
        assert rank == -1, "A native DDP child attempted a real ClearML artifact upload"
        return original_upload(task, name, *args, **kwargs)

    task_type.upload_artifact = upload
    original_weights = output_model_type.update_weights

    @wraps(original_weights)
    def weights(model: Any, *args: Any, **kwargs: Any) -> Any:
        _event(root, "model-attempt", model_id=model.id, rank=rank)
        assert rank == -1, "A native DDP child attempted a real ClearML model upload"
        return original_weights(model, *args, **kwargs)

    output_model_type.update_weights = weights
