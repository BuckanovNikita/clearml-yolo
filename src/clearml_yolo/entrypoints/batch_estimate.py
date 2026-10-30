"""Measure single-GPU training capacity and extrapolate selected allocations."""

import argparse
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice, discover_gpus, require_idle
from clearml_yolo.adapters.runtime.workers import WorkerCommand
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.application.batch_ports import BatchProbe
from clearml_yolo.application.training_workers import BatchCaseRequest, BatchCaseResult
from clearml_yolo.core.batch_estimation import (
    EstimateCase,
    GPUHardware,
    ModelVariant,
    ResolvedRecommendation,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    estimate_key,
    select_models,
    select_recommendation,
)
from clearml_yolo.entrypoints.options import parser_for

if TYPE_CHECKING:
    from clearml_yolo.adapters.runtime.worker_pool import IndependentWorkerPool, WorkerCompletion


class _Options(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    imgsz: int = Field(gt=0)
    models: tuple[ModelVariant, ...]
    devices: tuple[int, ...] | None
    gpu_counts: tuple[int, ...] | None
    jobs: int | None = Field(default=None, gt=0)
    workload: SyntheticWorkload
    settings: SearchSettings
    refresh: bool


def parser() -> argparse.ArgumentParser:
    """Return an inert parser backed by shared option declarations."""
    return parser_for("cy-batch-estimate")


def _options(arguments: argparse.Namespace) -> _Options:
    selections = (
        tuple(value.strip() for value in arguments.models.split(","))
        if arguments.models is not None
        else None
    )
    return _Options(
        imgsz=arguments.imgsz,
        models=select_models(selections),
        devices=arguments.devices,
        gpu_counts=arguments.gpu_counts,
        refresh=arguments.refresh,
        jobs=arguments.jobs,
        workload=SyntheticWorkload(
            classes=arguments.classes, objects_per_image=arguments.objects_per_image
        ),
        settings=SearchSettings(
            memory_fraction=arguments.memory_budget,
            max_global_batch=arguments.search_limit,
            trial_timeout_seconds=arguments.trial_timeout,
        ),
    )


def _devices(options: _Options) -> tuple[tuple[GPUDevice, ...], tuple[int, ...]]:
    visible = discover_gpus()
    indexes = (
        options.devices
        if options.devices is not None
        else tuple(device.index for device in visible)
    )
    by_index = {device.index: device for device in visible}
    if not indexes or any(index not in by_index for index in indexes):
        raise ValueError("--devices must select GPUs inside the inherited CUDA visibility")
    devices = tuple(by_index[index] for index in indexes)
    counts = options.gpu_counts or tuple(range(1, len(devices) + 1))
    if any(count < 1 or count > len(devices) for count in counts):
        raise ValueError("--gpu-counts must be between 1 and the selected device count")
    return devices, counts


def _make_probe() -> BatchProbe:
    from clearml_yolo.adapters.integrations.batch_probe import NativeBatchProbe

    return NativeBatchProbe()


def _make_pool() -> "IndependentWorkerPool":
    from clearml_yolo.adapters.runtime.worker_pool import IndependentWorkerPool

    return IndependentWorkerPool()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _report(case: ResolvedRecommendation, cached: bool) -> None:
    message = (
        f"{case.profile.model.selection}\tgpus={case.profile.world_size}"
        f"\tglobal_batch={case.global_batch}\tper_gpu_batch={case.per_gpu_batch}"
        f"\t{case.status}\t{case.origin}"
        f"\tsources={','.join(case.source_estimate_keys)}"
        f"\tsource_statuses={','.join(case.source_statuses)}"
    )
    if cached:
        message += "\tcached"
    limitations = dict.fromkeys(
        source.diagnostic for source in case.sources if source.status == "numerically_limited"
    )
    if limitations:
        message += "\tdiagnostic=" + "; ".join(limitations)
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def _idle_profile(profile: TrainingProfile, devices: tuple[GPUDevice, ...]) -> TrainingProfile:
    hardware = profile.gpus[0]
    failures = []
    for device in devices:
        if (device.name, device.total_memory_bytes) != (hardware.name, hardware.total_memory_bytes):
            continue
        try:
            require_idle((device,))
        except RuntimeError as error:
            failures.append(str(error))
            continue
        return profile.model_copy(
            update={
                "gpus": (
                    GPUHardware(
                        name=device.name,
                        total_memory_bytes=device.total_memory_bytes,
                        uuid=device.uuid,
                    ),
                )
            }
        )
    raise RuntimeError(f"No idle selected GPU for {hardware.name}: {'; '.join(failures)}")


def _hardware_matches(profile: TrainingProfile, device: GPUDevice) -> bool:
    gpu = profile.gpus[0]
    return (gpu.name, gpu.total_memory_bytes) == (device.name, device.total_memory_bytes)


def _case_command(request: BatchCaseRequest) -> WorkerCommand:
    request.output.mkdir(parents=True)
    path = request.output / "request.json"
    path.write_text(request.model_dump_json(), encoding="utf-8")
    return WorkerCommand(
        argv=(sys.executable, "-m", "clearml_yolo.entrypoints.batch_estimate_worker", str(path)),
        environment={"CUDA_VISIBLE_DEVICES": str(request.profile.gpus[0].uuid)},
        log_path=request.output / "case.log",
    )


def _completed_case(request: BatchCaseRequest, outcome: "WorkerCompletion") -> EstimateCase:
    if outcome.exit_code != 0 or not outcome.cleanup_complete:
        raise ValueError(
            f"Case process exited {outcome.exit_code}; {outcome.diagnostic}; "
            f"inspect {request.output}"
        )
    path = request.output / "result.json"
    result = BatchCaseResult.model_validate_json(path.read_text(encoding="utf-8"))
    if (result.token, result.estimate_key) != (request.token, request.estimate_key):
        raise ValueError("Case receipt identity does not match its invocation")
    if result.case.profile.gpus != request.profile.gpus:
        raise ValueError("Case receipt GPU identity does not match its assigned GPU")
    return result.case


@dataclass
class _CaseScheduler:
    """Compose independent cases without sharing a GPU or trusting partial receipts."""

    options: _Options
    devices: tuple[GPUDevice, ...]
    store: FileBatchEstimateStore
    pending: dict[str, TrainingProfile]
    results: dict[str, EstimateCase] = field(default_factory=dict)
    cached: set[str] = field(default_factory=set)
    active: dict[str, BatchCaseRequest] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)

    def run(self) -> None:
        saved = {
            estimate_key(case.profile, case.workload, case.settings): case
            for case in self.store.read().cases if case.usable
        }
        if not self.options.refresh:
            for key in tuple(self.pending):
                if key in saved:
                    self.results[key] = saved[key]
                    self.cached.add(key)
                    del self.pending[key]
        if not self.pending:
            return
        with _make_pool() as pool:
            while self.pending or self.active:
                self._admit(pool)
                completed = pool.poll()
                for outcome in completed:
                    self._receive(outcome)
                if self.active and not completed:
                    time.sleep(0.05)

    def _admit(self, pool: "IndependentWorkerPool") -> None:
        limit = min(self.options.jobs or len(self.devices), len(self.devices))
        for key, profile in tuple(self.pending.items()):
            if len(self.active) >= limit:
                break
            occupied = {request.profile.gpus[0].uuid for request in self.active.values()}
            candidates = tuple(
                device for device in self.devices
                if device.uuid not in occupied | self.unavailable
                and _hardware_matches(profile, device)
            )
            try:
                selected = _idle_profile(profile, candidates)
            except RuntimeError as error:
                # Another owned case can release a compatible GPU. Foreign busy
                # devices alone never make this command wait indefinitely.
                if any(
                    device.uuid in occupied and _hardware_matches(profile, device)
                    for device in self.devices
                ):
                    continue
                self._failed(key, profile, str(error))
                del self.pending[key]
                continue
            del self.pending[key]
            self._launch(pool, key, selected)

    def _launch(self, pool: "IndependentWorkerPool", key: str, profile: TrainingProfile) -> None:
        token = uuid4().hex
        request = BatchCaseRequest(
            token=token, estimate_key=key, profile=profile,
            workload=self.options.workload, settings=self.options.settings,
            catalogue_path=self.store.path,
            output=temporary_root() / "batch-cases" / token,
        )
        self.store.save(EstimateCase(
            profile=profile, workload=request.workload, settings=request.settings,
            status="failed", created_at=_timestamp(),
            diagnostic="Independent confirmation pending; case process has not completed",
        ))
        try:
            pool.start(key, _case_command(request))
        except (OSError, RuntimeError) as error:
            # A failed launch may include unverifiable cleanup. Quarantine its
            # GPU for this invocation rather than starting another measurement.
            self.unavailable.add(str(profile.gpus[0].uuid))
            self._failed(key, profile, f"Case launch failed: {error}")
            return
        self.active[key] = request

    def _receive(self, outcome: "WorkerCompletion") -> None:
        request = self.active.pop(outcome.key)
        if not outcome.cleanup_complete:
            self.unavailable.add(str(request.profile.gpus[0].uuid))
        try:
            case = _completed_case(request, outcome)
        except (OSError, ValueError) as error:
            self._failed(outcome.key, request.profile, f"Incomplete case: {error}")
            return
        self.store.save(case)
        self.results[outcome.key] = case

    def _failed(self, key: str, profile: TrainingProfile, diagnostic: str) -> None:
        prior = next((
            case for case in self.store.read().cases
            if estimate_key(case.profile, case.workload, case.settings) == key
        ), None)
        case = EstimateCase(
            profile=profile, workload=self.options.workload, settings=self.options.settings,
            status="failed", trials=prior.trials if prior is not None else (),
            created_at=_timestamp(), diagnostic=diagnostic,
        )
        self.store.save(case)
        self.results[key] = case


def _execute(options: _Options) -> bool:
    devices, counts = _devices(options)
    probe, store = _make_probe(), FileBatchEstimateStore()
    allocations = tuple(
        probe.profile(model, options.imgsz, tuple(device.index for device in devices))
        for model in options.models
    )
    profiles = dict[str, TrainingProfile]()
    model_keys: list[tuple[str, ...]] = []
    for allocation in allocations:
        keys = []
        for gpu in allocation.gpus:
            profile = allocation.model_copy(update={"gpus": (gpu,)})
            key = estimate_key(profile, options.workload, options.settings)
            profiles.setdefault(key, profile)
            keys.append(key)
        model_keys.append(tuple(dict.fromkeys(keys)))
    scheduler = _CaseScheduler(options, devices, store, profiles)
    scheduler.run()
    successful = all(case.usable for case in scheduler.results.values())
    catalogue = store.read().cases
    for allocation, case_keys in zip(allocations, model_keys, strict=True):
        for key in case_keys:
            case = scheduler.results[key]
            if not case.usable:
                sys.stdout.write(
                    f"{case.profile.model.selection}\tgpus=1\t{case.status}\t{case.diagnostic}\n"
                )
        for count in counts:
            target = allocation.model_copy(update={"gpus": allocation.gpus[:count]})
            try:
                recommendation = select_recommendation(catalogue, target, options.workload)
            except ValueError as error:
                sys.stdout.write(f"{allocation.model.selection}\tgpus={count}\tunavailable\t{error}\n")
                successful = False
                continue
            _report(
                recommendation,
                all(key in scheduler.cached for key in recommendation.source_estimate_keys),
            )
    sys.stdout.write(f"Results: {store.path}\n")
    return successful


def main(argv: Sequence[str] | None = None) -> None:
    argument_parser = parser()
    arguments = argument_parser.parse_args(argv)
    try:
        options = _options(arguments)
        with runtime_environment():
            successful = _execute(options)
    except (OSError, RuntimeError, ValueError) as error:
        argument_parser.error(str(error))
    if not successful:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
