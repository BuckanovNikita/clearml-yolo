"""Private process composition for one complete single-GPU batch search."""

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import override

from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.application.batch_ports import BatchProbe
from clearml_yolo.application.training_workers import BatchCaseRequest, BatchCaseResult
from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
from clearml_yolo.core.batch_estimation import EstimateCase


class _PendingBatchStore(FileBatchEstimateStore):
    """Only the invocation owner publishes success after process cleanup."""

    @override
    def save(self, case: EstimateCase) -> None:
        if case.usable:
            case = case.model_copy(update={
                "status": "failed", "global_batch": None, "per_gpu_batch": None,
                "diagnostic": "Independent confirmation complete; case owner cleanup pending",
            })
        super().save(case)


def _make_probe() -> BatchProbe:
    from clearml_yolo.adapters.integrations.batch_probe import NativeBatchProbe

    return NativeBatchProbe()


def run(request_path: Path) -> int:
    request = BatchCaseRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    output = write_path(request.output)
    store = _PendingBatchStore(request.catalogue_path)
    (case,) = estimate_batches(
        (request.profile,),
        request.workload,
        request.settings,
        probe=_make_probe(),
        store=store,
        now=lambda: datetime.now(UTC).isoformat(),
        # The parent has already resolved cache hits and invalidated this key.
        refresh=True,
    )
    result = BatchCaseResult(token=request.token, estimate_key=request.estimate_key, case=case)
    pending = write_path(output / "result.json.pending")
    pending.write_text(result.model_dump_json(), encoding="utf-8")
    pending.replace(write_path(output / "result.json"))
    # A complete failed measurement is a valid case receipt. Process failure is
    # reserved for incomplete execution, invalid requests and persistence errors.
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Private CY batch case worker")
    parser.add_argument("request", type=Path)
    arguments = parser.parse_args()
    with runtime_environment():
        raise SystemExit(run(arguments.request))


if __name__ == "__main__":
    main()
