"""Private estimator rank entrypoint; receipts distinguish capacity from failures."""

import argparse
import os
import traceback
from contextlib import chdir
from pathlib import Path

from clearml_yolo.adapters.runtime.distributed import native_rank
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult


def run(request_path: Path) -> int:
    request = BatchProbeRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    rank = int(os.environ["LOCAL_RANK"])
    try:
        backend = request.profile.model.backend
        if backend == "ultralytics":
            from clearml_yolo.adapters.yolo.batch_probe import probe
        elif backend == "deimv2":
            from clearml_yolo.adapters.deim.probe import probe
        elif backend == "rfdetr":
            from clearml_yolo.adapters.rfdetr.probe import probe
        elif backend == "fcos":
            from clearml_yolo.adapters.fcos.backend import probe
        else:
            from clearml_yolo.adapters.fasterrcnn.backend import probe
        with chdir(request.output), native_rank(initialize=backend != "rfdetr"):
            record = probe(request)
    except Exception as error:  # noqa: BLE001 - every private-process failure needs a receipt
        import torch

        status = "error"
        if isinstance(error, torch.cuda.OutOfMemoryError):
            status = "oom"
        elif isinstance(error, FloatingPointError):
            status = "nonfinite"
        elif isinstance(error, FileNotFoundError):
            status = "missing_asset"
        traceback.print_exc()
        record = ProbeRankResult.model_validate(
            {
                "token": request.token,
                "rank": rank,
                "status": status,
                "diagnostic": f"{type(error).__name__}: {error}",
            }
        )
    receipt = request_path.parent / f"rank-{rank}.json"
    pending = receipt.with_suffix(".json.pending")
    pending.write_text(record.model_dump_json(), encoding="utf-8")
    pending.replace(receipt)
    return 0 if record.status == "success" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Private CY batch probe")
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.request))


if __name__ == "__main__":
    main()
