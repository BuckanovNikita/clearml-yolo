"""Measure single-GPU training capacity and extrapolate selected allocations."""

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice, discover_gpus, require_idle
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.batch_ports import BatchProbe
from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
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


class _Options(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    imgsz: int = Field(gt=0)
    models: tuple[ModelVariant, ...]
    devices: tuple[int, ...] | None
    gpu_counts: tuple[int, ...] | None
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


def _execute(options: _Options) -> bool:
    devices, counts = _devices(options)
    probe = _make_probe()
    store = FileBatchEstimateStore()
    successful = True
    cached_sources: dict[str, bool] = {}

    def prepare(profile: TrainingProfile) -> TrainingProfile:
        return _idle_profile(profile, devices)

    for model in options.models:
        allocation = probe.profile(model, options.imgsz, tuple(device.index for device in devices))
        cached_sources.clear()

        def observed(case: EstimateCase, cached: bool) -> None:
            cached_sources[estimate_key(case.profile, case.workload, case.settings)] = cached
            if not case.usable:
                sys.stdout.write(
                    f"{case.profile.model.selection}\tgpus=1\t{case.status}\t{case.diagnostic}\n"
                )
                sys.stdout.flush()

        cases = estimate_batches(
            tuple(allocation.model_copy(update={"gpus": (gpu,)}) for gpu in allocation.gpus),
            options.workload,
            options.settings,
            probe=probe,
            store=store,
            now=_timestamp,
            refresh=options.refresh,
            on_case=observed,
            prepare_profile=prepare,
        )
        successful = all(case.usable for case in cases) and successful
        for count in counts:
            target = allocation.model_copy(update={"gpus": allocation.gpus[:count]})
            try:
                recommendation = select_recommendation(store.read().cases, target, options.workload)
            except ValueError as error:
                sys.stdout.write(f"{model.selection}\tgpus={count}\tunavailable\t{error}\n")
                successful = False
                continue
            _report(
                recommendation,
                all(cached_sources.get(key, True) for key in recommendation.source_estimate_keys),
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
