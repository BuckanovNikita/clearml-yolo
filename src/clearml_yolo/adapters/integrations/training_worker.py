"""Private rank entrypoint: native execution and receipts, without ClearML publication."""

import argparse
import traceback
from collections.abc import Callable
from pathlib import Path

from clearml_yolo.adapters.runtime.distributed import global_batch_per_rank, native_rank
from clearml_yolo.application.training_workers import (
    TrainingWorkerRequest,
    TrainingWorkerResult,
    WorkerScalar,
)
from clearml_yolo.core.models import BackendTrainResult


def _execute(
    request: TrainingWorkerRequest, rank: int, report: Callable[[str, float, int], None]
) -> BackendTrainResult:
    config = request.config.model_copy(deep=True)
    global_batch_per_rank(config.train.batch, request.world_size)
    if config.backend == "deimv2":
        from clearml_yolo.adapters.deim.backend import train
    elif config.backend == "rfdetr":
        from clearml_yolo.adapters.rfdetr.backend import train
    elif config.backend == "fasterrcnn":
        from clearml_yolo.adapters.fasterrcnn.backend import train
    elif config.backend == "fcos":
        from clearml_yolo.adapters.fcos.backend import train
    else:
        raise ValueError("YOLO uses its own native distributed trainer")
    config.train.device = rank
    with native_rank(initialize=config.backend != "rfdetr"):
        return train(
            config, request.prepared, request.output, report, transforms=request.transforms
        )


def run(request_path: Path, rank: int) -> int:
    request = TrainingWorkerRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    if rank >= request.world_size:
        raise ValueError("Worker rank outside requested world")
    receipt = request_path.parent / f"rank-{rank}.json"
    events = request_path.parent / f"rank-{rank}.jsonl"

    def report(name: str, value: float, step: int) -> None:
        if rank == 0:
            event = WorkerScalar(name=name, value=value, step=step)
            with events.open("a", encoding="utf-8") as stream:
                stream.write(event.model_dump_json() + "\n")

    try:
        result = _execute(request, rank, report)
        record = TrainingWorkerResult(
            token=request.token, rank=rank, status="success", result=result
        )
    except Exception as error:  # noqa: BLE001 - private process boundary records every failure
        import torch

        status: str = "error"
        if isinstance(error, torch.cuda.OutOfMemoryError):
            status = "oom"
        elif isinstance(error, FloatingPointError):
            status = "nonfinite"
        elif isinstance(error, FileNotFoundError):
            status = "missing_asset"
        traceback.print_exc()
        record = TrainingWorkerResult.model_validate(
            {
                "token": request.token,
                "rank": rank,
                "status": status,
                "diagnostic": f"{type(error).__name__}: {error}",
            }
        )
    receipt.write_text(record.model_dump_json(), encoding="utf-8")
    return 0 if record.status == "success" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Private CY native rank")
    parser.add_argument("request", type=Path)
    parser.add_argument("rank", type=int)
    args = parser.parse_args()
    raise SystemExit(run(args.request, args.rank))


if __name__ == "__main__":
    main()
