"""Test-only observers around real native loops, never replacement training algorithms."""

import hashlib
import importlib
import json
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from ddp_gpu_instrumentation import _event, _install_sdk, process_birth, write


def record_process(root: Path) -> None:
    write(
        root,
        f"process-{os.getpid()}.json",
        {"pid": os.getpid(), "born": process_birth(os.getpid())},
    )


def install_owner() -> None:
    """The public command remains the invocation owner; only rank argv is wrapped."""
    # Opaque test seams preserve the production call while observing private SDK hooks.
    distributed_training: Any = importlib.import_module(
        "clearml_yolo.adapters.integrations.distributed_training"
    )
    from native_backend_ddp_harness import instrument_command

    root = Path(os.environ["CY_DDP_TRACE"])
    record_process(root)
    _install_sdk(root, -1)
    original = distributed_training.run_workers

    def observed_workers(commands: Any, **kwargs: Any) -> Any:
        return original([instrument_command(command) for command in commands], **kwargs)

    distributed_training.run_workers = observed_workers


def state_digest(value: Any) -> tuple[str, bool]:
    import torch

    digest = hashlib.sha256()
    finite = True

    def visit(item: Any) -> None:
        nonlocal finite
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            if tensor.is_floating_point() or tensor.is_complex():
                finite = finite and bool(torch.isfinite(tensor).all())
            digest.update(str((str(tensor.dtype), tuple(tensor.shape))).encode())
            digest.update(tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item, key=str):
                digest.update(str(key).encode())
                visit(item[key])
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
        else:
            digest.update(repr(item).encode())

    visit(value)
    return digest.hexdigest(), finite


class ObservedBatches:
    def __init__(self, batches: Any, observer: "RankObserver", phase: str) -> None:
        self.batches, self.observer, self.phase = batches, observer, phase

    def __len__(self) -> int:
        return len(self.batches)

    def __iter__(self) -> Iterator[Any]:
        for batch in self.batches:
            self.observer.targets(batch[1], self.phase)
            yield batch


class RankObserver:
    def __init__(self, root: Path, request: Any, rank: int) -> None:
        self.root, self.request, self.rank = root, request, rank
        self.options = json.loads((root / "request.json").read_text())
        self.model: Any = None
        self.optimizer: Any = None
        self.ema: Callable[[], tuple[Any, int]] | None = None
        self.state: dict[str, Any] = {
            "rank": rank,
            "selection": f"{request.config.backend}/{request.config.preset}",
            "global_batch": request.config.train.batch,
            "per_rank_batch": request.config.train.batch // request.world_size,
            "accumulation": request.config.train.grad_accum_steps,
            "train_ids": [],
            "validation_ids": [],
            "train_batches": [],
            "train_labels": [],
            "checkpoints": [],
            "optimizer_steps": 0,
        }
        for phase, folder in (("train", "train"), ("val", "valid")):
            annotation = request.prepared.data.parent / folder / "_annotations.coco.json"
            contents = json.loads(annotation.read_text())
            self.state[f"expected_{phase}_ids"] = [image["id"] for image in contents["images"]]
        write(root, f"native-request-{rank}.json", json.loads(request.model_dump_json()))

    def targets(self, targets: Any, phase: str) -> None:
        self.state[f"{phase}_ids"].extend(int(target["image_id"]) for target in targets)
        if phase == "train":
            self.state["train_batches"].append(len(targets))
            self.state["train_labels"].extend(
                int(label) for target in targets for label in target["labels"]
            )

    def _stepped(self, _optimizer: Any, _args: Any, _kwargs: Any) -> None:
        self.state["optimizer_steps"] += 1

    def start(self, model: Any, optimizer: Any, ema: Callable[[], tuple[Any, int]]) -> None:
        import torch
        from torch import distributed

        assert distributed.is_initialized(), "Native rank did not initialize distribution"
        assert distributed.get_backend() == "nccl", "Native acceptance requires NCCL"
        self.model = (
            model.module if isinstance(model, torch.nn.parallel.DistributedDataParallel) else model
        )
        self.optimizer, self.ema = optimizer, ema
        local_rank = int(os.environ["LOCAL_RANK"])
        assert torch.cuda.current_device() == local_rank
        self.state.update(
            local_rank=local_rank,
            world_size=distributed.get_world_size(),
            backend=distributed.get_backend(),
            uuid=str(torch.cuda.get_device_properties(local_rank).uuid),
            initial_parameters=state_digest(dict(self.model.named_parameters()))[0],
        )
        optimizer.register_step_post_hook(self._stepped)
        write(self.root, f"native-rank-{self.rank}-ready.json", self.state)
        self._fault_gate()

    def _fault_gate(self) -> None:
        fault = self.options["fault"]
        if fault == "none":
            return
        deadline = time.monotonic() + self.options["timeout"]
        while not (self.root / "release-fault").is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError("Native acceptance fault gate was not released")
            time.sleep(0.1)
        if self.rank != 1:
            return
        if fault == "crash":
            _event(self.root, "fault-crash", rank=self.rank, exit_code=73)
            os._exit(73)
        if fault == "oom":
            import torch

            capacity = torch.cuda.get_device_properties(self.rank).total_memory
            try:
                # A single impossible allocation fails without consuming peer capacity.
                torch.empty(capacity * 2, dtype=torch.uint8, device=f"cuda:{self.rank}")
            except torch.cuda.OutOfMemoryError:
                _event(self.root, "fault-oom", rank=self.rank, confirmed_cuda_oom=True)
                raise
            raise AssertionError("The deliberate CUDA allocation unexpectedly succeeded")

    def snapshot(self) -> None:
        assert self.ema is not None
        averaged, updates = self.ema()
        assert averaged is not None, "Native EMA was not constructed"
        values = {
            "parameters": dict(self.model.named_parameters()),
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "ema": averaged if isinstance(averaged, dict) else averaged.state_dict(),
        }
        self.state["finite"] = True
        for name, value in values.items():
            digest, finite = state_digest(value)
            self.state[name] = digest
            self.state["finite"] = self.state["finite"] and finite
        self.state["ema_updates"] = updates

    def save_observer(self) -> None:
        torch: Any = importlib.import_module("torch")

        original = torch.save

        def save(value: Any, destination: Any, *args: Any, **kwargs: Any) -> Any:
            result = original(value, destination, *args, **kwargs)
            candidate = (
                destination
                if isinstance(destination, (str, Path))
                else getattr(destination, "name", None)
            )
            if isinstance(candidate, (str, Path)):
                path = Path(candidate).resolve()
                if path.is_relative_to(self.request.output.resolve()) and path.suffix in {
                    ".pth",
                    ".ckpt",
                }:
                    self.state["checkpoints"].append(str(path))
            return result

        torch.save = save

    def finish(self) -> None:
        write(self.root, f"native-rank-{self.rank}.json", self.state)


def install_torchvision(observer: RankObserver) -> None:
    training: Any = importlib.import_module("clearml_yolo.adapters.torchvision.training")
    evaluation: Any = importlib.import_module("clearml_yolo.adapters.torchvision.evaluation")

    constructor = training._TrainingRun.__init__
    epoch = training._training_epoch
    evaluate = training.evaluate_coco
    detections = evaluation._detections

    def initialize(run: Any, *args: Any, **kwargs: Any) -> None:
        constructor(run, *args, **kwargs)
        observer.start(run.model, run.optimizer, lambda: (run.ema.module, int(run.ema.n_averaged)))

    def train_epoch(model: Any, loader: Any, *args: Any, **kwargs: Any) -> Any:
        return epoch(model, ObservedBatches(loader, observer, "train"), *args, **kwargs)

    def validate(*args: Any, **kwargs: Any) -> Any:
        observer.snapshot()
        return evaluate(*args, **kwargs)

    def predict(model: Any, batches: Any, *args: Any, **kwargs: Any) -> Any:
        return detections(model, ObservedBatches(batches, observer, "validation"), *args, **kwargs)

    training._TrainingRun.__init__ = initialize
    training._training_epoch = train_epoch
    training.evaluate_coco = validate
    evaluation._detections = predict


def install_deim(observer: RankObserver) -> None:
    backend: Any = importlib.import_module("clearml_yolo.adapters.deim.backend")

    configuration = backend.training_configuration
    initialize = backend._DistributedSolver.train

    def start(solver: Any) -> None:
        initialize(solver)
        observer.start(
            solver.model,
            solver.optimizer,
            lambda: (solver.ema.module, int(solver.ema.state_dict()["updates"])),
        )

    def configure(*args: Any, **kwargs: Any) -> Any:
        cfg, registry = configuration(*args, **kwargs)
        native: Any = importlib.import_module(registry.TASKS["detection"].__module__)
        epoch, evaluate = native.train_one_epoch, native.evaluate

        def train_epoch(*values: Any, **options: Any) -> Any:
            items = list(values)
            items[4] = ObservedBatches(items[4], observer, "train")
            return epoch(*items, **options)

        def validate(*values: Any, **options: Any) -> Any:
            observer.snapshot()
            items = list(values)
            items[3] = ObservedBatches(items[3], observer, "validation")
            return evaluate(*items, **options)

        native.train_one_epoch, native.evaluate = train_epoch, validate
        return cfg, registry

    backend._DistributedSolver.train = start
    backend.training_configuration = configure


def install_rfdetr(observer: RankObserver) -> None:
    backend: Any = importlib.import_module("clearml_yolo.adapters.rfdetr.backend")

    native: Any = importlib.import_module("rfdetr.training")
    lightning: Any = importlib.import_module("pytorch_lightning")
    callbacks: Any = importlib.import_module("rfdetr.training.callbacks")
    train_step = native.RFDETRModelModule.training_step
    val_step = backend._UniqueValidation.validation_step
    build = native.build_trainer

    class Lifecycle:
        def on_train_start(self, trainer: Any, module: Any) -> None:
            ema = next(
                item for item in trainer.callbacks if isinstance(item, callbacks.RFDETREMACallback)
            )
            observer.start(
                module.model,
                trainer.optimizers[0],
                lambda: (ema.get_ema_model_state_dict(), int(ema._average_model.n_averaged)),
            )

        def on_validation_start(self, trainer: Any, _module: Any) -> None:
            if not trainer.sanity_checking:
                observer.snapshot()

    def train(module: Any, batch: Any, *args: Any, **kwargs: Any) -> Any:
        observer.targets(batch[1], "train")
        return train_step(module, batch, *args, **kwargs)

    def validate(module: Any, *args: Any, **kwargs: Any) -> Any:
        result = val_step(module, *args, **kwargs)
        if not module.trainer.sanity_checking:
            observer.targets(result["targets"], "validation")
        return result

    def trainer(*args: Any, **kwargs: Any) -> Any:
        result = build(*args, **kwargs)
        result.callbacks.append(
            type("NativeAcceptanceObserver", (Lifecycle, lightning.Callback), {})()
        )
        return result

    native.RFDETRModelModule.training_step = train
    backend._UniqueValidation.validation_step = validate
    native.build_trainer = trainer


def install_rank(root: Path, request: Any, rank: int) -> RankObserver:
    record_process(root)
    _install_sdk(root, rank)
    observer = RankObserver(root, request, rank)
    observer.save_observer()
    if request.config.backend == "deimv2":
        install_deim(observer)
    elif request.config.backend == "rfdetr":
        install_rfdetr(observer)
    else:
        install_torchvision(observer)
    return observer
