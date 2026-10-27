"""Owner-side native worker composition and scalar replay."""

import os
import socket
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from clearml_yolo.adapters.runtime.distributed import global_batch_per_rank
from clearml_yolo.adapters.runtime.workers import WorkerCommand, run_workers
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.application.training_workers import (
    TrainingWorkerRequest,
    TrainingWorkerResult,
    WorkerScalar,
)
from clearml_yolo.core.models import BackendTrainResult, ModelConfig
from clearml_yolo.core.transforms import TransformConfig


def _visibility(devices: tuple[int, ...]) -> str:
    selected = os.environ.get("CUDA_VISIBLE_DEVICES")
    if selected is None:
        return ",".join(map(str, devices))
    visible = selected.split(",")
    if any(index >= len(visible) for index in devices):
        raise ValueError("Training device is outside CUDA_VISIBLE_DEVICES")
    return ",".join(visible[index] for index in devices)


def _port() -> str:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return str(candidate.getsockname()[1])


class _WorkerEvents:
    def __init__(
        self, directory: Path, report: Callable[[str, float, int], None], world_size: int
    ) -> None:
        self.directory = directory
        self.report = report
        self.offsets: dict[Path, int] = {}
        self.world_size = world_size

    def poll(self, _owned_pids: Callable[[], tuple[int, ...]]) -> None:
        """Relay complete scalar lines and native console output while ranks run."""
        for rank in range(self.world_size):
            log = self.directory / f"rank-{rank}.log"
            if log.is_file():
                with log.open("rb") as stream:
                    stream.seek(self.offsets.get(log, 0))
                    data = stream.read(65536)
                    self.offsets[log] = stream.tell()
                if data:
                    os.write(1, data)
        events = self.directory / "rank-0.jsonl"
        if not events.is_file():
            return
        with events.open("rb") as stream:
            stream.seek(self.offsets.get(events, 0))
            for line in stream:
                if not line.endswith(b"\n"):
                    break
                event = WorkerScalar.model_validate_json(line)
                self.report(event.name, event.value, event.step)
                self.offsets[events] = self.offsets.get(events, 0) + len(line)

    def finish(self) -> None:
        """Drain events emitted between the last live poll and worker completion."""
        self.poll(lambda: ())
        while any(
            path.is_file() and path.stat().st_size > self.offsets.get(path, 0)
            for rank in range(self.world_size)
            for path in (self.directory / f"rank-{rank}.log",)
        ):
            self.poll(lambda: ())


def train_distributed(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
    *,
    devices: tuple[int, ...],
    transforms: TransformConfig | None = None,
) -> BackendTrainResult:
    """The invocation owner stays outside ranks and publishes their validated result."""
    global_batch_per_rank(config.train.batch, len(devices))
    token = uuid4().hex
    directory = output / "workers" / token
    directory.mkdir(parents=True)
    request = TrainingWorkerRequest(
        token=token,
        config=config,
        prepared=prepared,
        output=output.resolve(),
        world_size=len(devices),
        transforms=transforms,
    )
    request_path = directory / "request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    environment = {
        "CUDA_VISIBLE_DEVICES": _visibility(devices),
        "MASTER_ADDR": "127.0.0.1",
        "MASTER_PORT": _port(),
        "WORLD_SIZE": str(len(devices)),
        "LOCAL_WORLD_SIZE": str(len(devices)),
        # Lightning detects an externally created rank environment and must not relaunch CY.
        "TORCHELASTIC_RUN_ID": token,
    }
    commands = [
        WorkerCommand(
            argv=(
                sys.executable,
                "-m",
                "clearml_yolo.adapters.integrations.training_worker",
                str(request_path.resolve()),
                str(rank),
            ),
            environment=environment | {"RANK": str(rank), "LOCAL_RANK": str(rank)},
            log_path=directory / f"rank-{rank}.log",
        )
        for rank in range(len(devices))
    ]
    events = _WorkerEvents(directory, report, len(devices))
    outcome = run_workers(commands, timeout_seconds=86400 * 30, monitor=events.poll)
    events.finish()
    receipts = [
        TrainingWorkerResult.model_validate_json(path.read_text(encoding="utf-8"))
        for rank in range(len(devices))
        if (path := directory / f"rank-{rank}.json").is_file()
    ]
    if outcome.status != "success":
        details = "; ".join(item.diagnostic for item in receipts if item.status != "success")
        raise RuntimeError(f"Native distributed training {outcome.status}: {details or directory}")
    if len(receipts) != len(devices) or any(
        item.token != token or item.rank != rank or item.status != "success"
        for rank, item in enumerate(receipts)
    ):
        raise RuntimeError("Native workers exited without matching successful receipts")
    result = receipts[0].result
    if result is None:
        raise RuntimeError("Rank zero did not return its training result")
    return result
