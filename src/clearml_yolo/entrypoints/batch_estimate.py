"""Measure single-GPU training capacity and extrapolate selected allocations."""

import argparse
import json
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
from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.application.batch_ports import BatchProbe
from clearml_yolo.application.training_workers import BatchCaseRequest, BatchCaseResult
from clearml_yolo.core.batch_estimation import (
    EstimateCase,
    GPUHardware,
    ModelVariant,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    estimate_diagnostic,
    estimate_key,
    select_models,
)
from clearml_yolo.core.batch_sizes import BatchSizeEntry, BatchSizeFailure, BatchSizeTable
from clearml_yolo.entrypoints.options import OPTION_DECLARATIONS, parser_for

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
    selections = tuple(value.strip() for value in arguments.models.split(",")) if arguments.models is not None else None
    return _Options(
        imgsz=arguments.imgsz,
        models=select_models(selections),
        devices=arguments.devices,
        gpu_counts=arguments.gpu_counts,
        refresh=arguments.refresh or selections is not None,
        jobs=arguments.jobs,
        workload=SyntheticWorkload(objects_per_image=arguments.objects_per_image),
        settings=SearchSettings(
            force=arguments.force,
            memory_fraction=arguments.memory_budget,
            max_global_batch=arguments.search_limit,
            trial_timeout_seconds=arguments.trial_timeout,
        ),
    )


def _devices(options: _Options) -> tuple[tuple[GPUDevice, ...], tuple[int, ...]]:
    visible = discover_gpus()
    indexes = options.devices if options.devices is not None else tuple(device.index for device in visible)
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


def _idle_profile(profile: TrainingProfile, devices: tuple[GPUDevice, ...], *, force: bool = False) -> TrainingProfile:
    hardware = profile.gpus[0]
    failures = []
    for device in devices:
        if (device.name, device.total_memory_bytes) != (hardware.name, hardware.total_memory_bytes):
            continue
        try:
            require_idle((device,), force=force)
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
        raise ValueError(f"Case process exited {outcome.exit_code}; {outcome.diagnostic}; inspect {request.output}")
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
    table_store: BatchSizeStore = field(default_factory=BatchSizeStore)
    results: dict[str, EstimateCase] = field(default_factory=dict)
    cached: set[str] = field(default_factory=set)
    active: dict[str, BatchCaseRequest] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)

    def run(self) -> None:
        saved = {
            estimate_key(case.profile, case.workload, case.settings): case
            for case in self.store.read().cases
            if case.usable
        }
        if not self.options.refresh:
            table = self.table_store.load()
            for key in tuple(self.pending):
                profile = self.pending[key]
                gpu = profile.gpus[0]
                failure = BatchSizeFailure(
                    gpu_name=gpu.name,
                    total_memory_bytes=gpu.total_memory_bytes,
                    image_size=self.options.imgsz,
                    model=profile.model.selection,
                )
                if failure in table.failures:
                    continue
                if key in saved:
                    self.results[key] = saved[key]
                    self.cached.add(key)
                    del self.pending[key]
            self.table_store.publish(tuple(self.results.values()), replace=False)
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
                device
                for device in self.devices
                if device.uuid not in occupied | self.unavailable and _hardware_matches(profile, device)
            )
            try:
                selected = _idle_profile(profile, candidates, force=self.options.settings.force)
            except RuntimeError as error:
                # Another owned case can release a compatible GPU. Foreign busy
                # devices alone never make this command wait indefinitely.
                if any(device.uuid in occupied and _hardware_matches(profile, device) for device in self.devices):
                    continue
                self._failed(key, profile, str(error))
                del self.pending[key]
                continue
            del self.pending[key]
            self._launch(pool, key, selected)

    def _launch(self, pool: "IndependentWorkerPool", key: str, profile: TrainingProfile) -> None:
        token = uuid4().hex
        request = BatchCaseRequest(
            token=token,
            estimate_key=key,
            profile=profile,
            workload=self.options.workload,
            settings=self.options.settings,
            catalogue_path=self.store.path,
            output=temporary_root() / "batch-cases" / token,
        )
        self.store.save(
            EstimateCase(
                profile=profile,
                workload=request.workload,
                settings=request.settings,
                status="failed",
                created_at=_timestamp(),
                diagnostic="Independent confirmation pending; case process has not completed",
            )
        )
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
        self.table_store.publish((case,))
        self.results[outcome.key] = case

    def _failed(self, key: str, profile: TrainingProfile, diagnostic: str) -> None:
        prior = next(
            (
                case
                for case in self.store.read().cases
                if estimate_key(case.profile, case.workload, case.settings) == key
            ),
            None,
        )
        case = EstimateCase(
            profile=profile,
            workload=self.options.workload,
            settings=self.options.settings,
            status="failed",
            trials=prior.trials if prior is not None else (),
            created_at=_timestamp(),
            diagnostic=diagnostic,
        )
        self.store.save(case)
        self.results[key] = case


def _source_description(entry: BatchSizeEntry) -> str:
    details: list[str] = [entry.origin]
    if entry.source_status is not None:
        details.append(f"source_status={entry.source_status}")
    if entry.source_diagnostic:
        details.append(f"source_diagnostic={entry.source_diagnostic}")
    if entry.source_estimate_key is not None:
        details.append(f"source_estimate_key={entry.source_estimate_key}")
    return f"{entry.gpu_label}: {entry.per_gpu_batch} ({'; '.join(details)})"


def _report_table(table: BatchSizeTable, allocation: TrainingProfile, count: int, *, cached: bool) -> None:
    selected = tuple(
        table.resolve(gpu, allocation.nominal_size[0], allocation.model.selection) for gpu in allocation.gpus[:count]
    )
    batch = min(item.per_gpu_batch for item in selected)
    for item in selected:
        if item.fallback:
            sys.stderr.write(
                f"Warning: {_cell(item.target_gpu.name)} uses fallback from {_cell(item.entry.gpu_label)}; "
                f"run cy-batch-estimate --imgsz {allocation.nominal_size[0]} --models {allocation.model.selection} "
                "--devices <current-device> to measure this GPU.\n"
            )
    sources = ", ".join(dict.fromkeys(_source_description(item.entry) for item in selected))
    message = (
        f"{allocation.model.selection}\tgpus={count}\tglobal_batch={count * batch}\tper_gpu_batch={batch}"
        f"\ttable\tdigest={table.digest}\tsources={_cell(sources)}"
    )
    if cached:
        message += "\tcached"
    if any(item.entry.forced for item in selected):
        message += "\tforced/background-sensitive"
    sys.stdout.write(message + "\n")


def _execute(options: _Options) -> bool:
    devices, counts = _devices(options)
    probe, store, table_store = _make_probe(), FileBatchEstimateStore(), BatchSizeStore()
    table = table_store.load()
    allocations = tuple(
        probe.profile(model, options.imgsz, tuple(device.index for device in devices)) for model in options.models
    )
    profiles = dict[str, TrainingProfile]()
    for allocation in allocations:
        for gpu in allocation.gpus:
            if not options.refresh and table.exact(gpu, options.imgsz, allocation.model.selection) is not None:
                continue
            profile = allocation.model_copy(update={"gpus": (gpu,)})
            key = estimate_key(profile, options.workload, options.settings)
            profiles.setdefault(key, profile)
    scheduler = _CaseScheduler(options, devices, store, profiles, table_store)
    scheduler.run()
    successful = all(case.usable for case in scheduler.results.values())
    table = table_store.load()
    for case in scheduler.results.values():
        if not case.usable:
            sys.stdout.write(f"{case.profile.model.selection}\tgpus=1\t{case.status}\t{_cell(case.diagnostic)}\n")
        elif case.status == "numerically_limited" or case.settings.force:
            detail = "forced/background-sensitive; " if case.settings.force else ""
            sys.stdout.write(
                f"Measurement: {case.profile.model.selection}\t{case.status}\t{detail}{_cell(case.diagnostic)}\n"
            )
    for allocation in allocations:
        for count in counts:
            try:
                keys = (
                    estimate_key(allocation.model_copy(update={"gpus": (gpu,)}), options.workload, options.settings)
                    for gpu in allocation.gpus[:count]
                )
                cached = all(key in scheduler.cached or key not in scheduler.results for key in keys)
                _report_table(table, allocation, count, cached=cached)
            except ValueError as error:
                sys.stdout.write(f"{allocation.model.selection}\tgpus={count}\tunavailable\t{error}\n")
                successful = False
    sys.stdout.write(f"Results: {table_store.path}; evidence: {store.path}\n")
    return successful


def _list_arguments(argument_parser: argparse.ArgumentParser, tokens: Sequence[str]) -> None:
    # parse_args already resolved abbreviations and rejected ambiguous/unknown flags.
    # Inspect explicit tokens so even measurement values equal to defaults are rejected.
    measurement_flags = tuple(
        flag
        for option in OPTION_DECLARATIONS["cy-batch-estimate"]
        for flag in option.flags
        if flag not in {"--list", "--models", "--help", "-h"}
    )
    for token in tokens:
        name = token.partition("=")[0]
        if name.startswith("--") and name != "--" and any(flag.startswith(name) for flag in measurement_flags):
            argument_parser.error(f"{name} cannot be used with --list")


def _cell(value: str) -> str:
    # Keep Unicode names readable while escaping embedded controls and terminal escapes.
    encoded = json.dumps(value, ensure_ascii=False)[1:-1]
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in encoded)


def _list_saved(selections: str | None) -> None:
    models = select_models(tuple(value.strip() for value in selections.split(",")) if selections is not None else None)
    store = BatchSizeStore()
    table = store.load()
    attempts = FileBatchEstimateStore().read().cases
    covered = 0
    sys.stdout.write(
        "Editable table coverage across recorded GPUs and image sizes; no CUDA required.\n"
        "MODEL\tSTATUS\tREASON\tCONTEXT\n"
    )
    for model in (model for model in select_models() if model in models):
        entries = tuple(entry for entry in table.entries if entry.model == model.selection)
        failures = tuple(failure for failure in table.failures if failure.model == model.selection)
        unsuccessful = tuple(
            case for case in attempts if case.profile.model.selection == model.selection and case.status == "failed"
        )
        covered += bool(entries)
        for entry in entries:
            context = (
                f"{entry.gpu_label}; imgsz={entry.image_size}; per_gpu_batch={entry.per_gpu_batch}; {entry.origin}"
            )
            sys.stdout.write(f"{model.selection}\tcovered\tEditable table entry\t{_cell(context)}\n")
        for failure in failures:
            context = f"{failure.gpu_name} ({failure.total_memory_bytes} bytes); imgsz={failure.image_size}"
            sys.stdout.write(f"{model.selection}\tno_capacity\tConfirmed capacity failure\t{_cell(context)}\n")
        for case in unsuccessful:
            context = f"imgsz={case.profile.nominal_size[0]}; GPUs={','.join(gpu.name for gpu in case.profile.gpus)}"
            sys.stdout.write(f"{model.selection}\tfailed\t{_cell(estimate_diagnostic(case))}\t{_cell(context)}\n")
        if not entries and not failures and not unsuccessful:
            sys.stdout.write(f"{model.selection}\tnot_attempted\tNo table entry or known capacity failure\t-\n")
    sys.stdout.write(
        f"Summary: selected={len(models)}\tcovered={covered}\tmissing={len(models) - covered}"
        f"\nResults: {_cell(str(store.path))}\n"
    )


def main(argv: Sequence[str] | None = None) -> None:
    argument_parser = parser()
    tokens = list(argv) if argv is not None else sys.argv[1:]
    arguments = argument_parser.parse_args(tokens)
    try:
        if arguments.list:
            _list_arguments(argument_parser, tokens)
            _list_saved(arguments.models)
            return
        if arguments.imgsz is None:
            argument_parser.error("--imgsz is required unless --list is used")
        options = _options(arguments)
        with runtime_environment():
            successful = _execute(options)
    except (OSError, RuntimeError, ValueError) as error:
        argument_parser.error(str(error))
    if not successful:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
