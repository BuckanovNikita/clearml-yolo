"""Fresh-process GPU trials with real native execution and conservative telemetry."""

import sys
import time
from collections.abc import Callable
from uuid import uuid4

from clearml_yolo.adapters.assets.execution import prepare_model_assets
from clearml_yolo.adapters.integrations.batch_profiles import training_profile
from clearml_yolo.adapters.integrations.distributed_training import _port, _visibility
from clearml_yolo.adapters.runtime.gpu_inventory import (
    GPUDevice,
    discover_gpus,
    monitor_devices,
    require_idle,
)
from clearml_yolo.adapters.runtime.workers import WorkerCommand, run_workers
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.adapters.yolo.assets import configure_weights_directory
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult
from clearml_yolo.core.batch_estimation import (
    ModelVariant,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialResult,
)
from clearml_yolo.core.models import model_preset

_TELEMETRY_INTERVAL_SECONDS = 0.25


def _devices(profile: TrainingProfile) -> tuple[GPUDevice, ...]:
    lookup = {device.uuid: device for device in discover_gpus()}
    try:
        devices = tuple(lookup[str(gpu.uuid)] for gpu in profile.gpus)
    except KeyError as error:
        raise RuntimeError("Selected GPU visibility changed before the trial") from error
    if any(
        device.name != expected.name or device.total_memory_bytes != expected.total_memory_bytes
        for device, expected in zip(devices, profile.gpus, strict=True)
    ):
        raise RuntimeError("Selected GPU hardware changed before the trial")
    return devices


class NativeBatchProbe:
    def __init__(self) -> None:
        self._profile_devices: dict[int, GPUDevice] | None = None

    def profile(self, model: ModelVariant, imgsz: int, devices: tuple[int, ...]) -> TrainingProfile:
        # Catalogue construction shares one metadata snapshot. Every actual trial
        # independently revalidates visibility, hardware and idle state in _devices.
        if self._profile_devices is None:
            self._profile_devices = {device.index: device for device in discover_gpus()}
        selected = tuple(self._profile_devices[index] for index in devices)
        return training_profile(model, imgsz, selected)

    def run(
        self,
        profile: TrainingProfile,
        workload: SyntheticWorkload,
        settings: SearchSettings,
        global_batch: int,
    ) -> TrialResult:
        if profile.world_size != 1:
            raise ValueError("Batch estimation trials require exactly one GPU")
        trial_id = uuid4().hex
        start = time.monotonic()
        records: list[ProbeRankResult] = []
        path_peaks: list[tuple[int, ...]] = []
        try:
            devices = _devices(profile)
            require_idle(devices)
            for optimizer in profile.optimizers:
                path_results, peaks = self._path(
                    profile,
                    workload,
                    settings,
                    global_batch,
                    optimizer,
                    trial_id,
                    devices,
                )
                records.extend(path_results)
                path_peaks.append(peaks)
                failures = [record for record in path_results if record.status != "success"]
                if failures:
                    # A peer's collective failure after a confirmed rank OOM is capacity
                    # evidence; a timeout/crash with no OOM receipt is never capacity.
                    failure = next((item for item in failures if item.status == "oom"), failures[0])
                    return TrialResult(
                        global_batch=global_batch,
                        trial_id=trial_id,
                        status=failure.status,
                        diagnostic=failure.diagnostic,
                        duration_seconds=time.monotonic() - start,
                    )
        except FileNotFoundError as error:
            return TrialResult(
                global_batch=global_batch,
                trial_id=trial_id,
                status="missing_asset",
                diagnostic=str(error),
                duration_seconds=time.monotonic() - start,
            )
        except RuntimeError as error:
            status = "contaminated" if "GPU" in str(error) else "error"
            return TrialResult.model_validate(
                {
                    "global_batch": global_batch,
                    "trial_id": trial_id,
                    "status": status,
                    "diagnostic": str(error),
                    "duration_seconds": time.monotonic() - start,
                }
            )
        return TrialResult(
            global_batch=global_batch,
            trial_id=trial_id,
            status="success",
            actual_global_batch=min(item.actual_global_batch or 0 for item in records),
            peak_memory_bytes=tuple(
                max(peaks[r] for peaks in path_peaks) for r in range(profile.world_size)
            ),
            warmup_steps=min(item.warmup_steps for item in records),
            measured_steps=min(item.measured_steps for item in records),
            validation_steps=min(item.validation_steps for item in records),
            optimizer_paths=profile.optimizers,
            duration_seconds=time.monotonic() - start,
        )

    def _path(
        self,
        profile: TrainingProfile,
        workload: SyntheticWorkload,
        settings: SearchSettings,
        global_batch: int,
        optimizer: str,
        token: str,
        devices: tuple[GPUDevice, ...],
    ) -> tuple[list[ProbeRankResult], tuple[int, ...]]:
        output = temporary_root() / "batch-estimate" / token / optimizer
        output.mkdir(parents=True)
        config = None
        if profile.model.backend == "ultralytics":
            configure_weights_directory()
        else:
            config = model_preset(profile.model.selection)
            config.train.imgsz = profile.nominal_size[0]
            config.train.batch = global_batch
            config.train.workers = 0
            config, _assets = prepare_model_assets(config, training=True)
        request = BatchProbeRequest(
            token=token,
            profile=profile,
            workload=workload,
            settings=settings,
            global_batch=global_batch,
            optimizer=optimizer,
            output=output,
            config=config,
        )
        request_path = output / "request.json"
        request_path.write_text(request.model_dump_json(), encoding="utf-8")
        environment = {
            "CUDA_VISIBLE_DEVICES": _visibility(tuple(device.index for device in devices)),
            "MASTER_ADDR": "127.0.0.1",
            "MASTER_PORT": _port(),
            "WORLD_SIZE": str(profile.world_size),
            "LOCAL_WORLD_SIZE": str(profile.world_size),
            "TORCHELASTIC_RUN_ID": token,
        }
        commands = [
            WorkerCommand(
                argv=(
                    sys.executable,
                    "-m",
                    "clearml_yolo.adapters.integrations.probe_worker",
                    str(request_path),
                ),
                environment=environment | {"RANK": str(rank), "LOCAL_RANK": str(rank)},
                log_path=output / f"rank-{rank}.log",
            )
            for rank in range(profile.world_size)
        ]
        # Asset setup can take time and previous optimizer paths can leave driver
        # reservations behind. Recheck idle state and baseline immediately before launch.
        baseline = require_idle(devices)
        peaks = list(baseline)
        checked_at = 0.0

        def monitor(owned_pids: Callable[[], tuple[int, ...]]) -> None:
            nonlocal checked_at
            if time.monotonic() - checked_at < _TELEMETRY_INTERVAL_SECONDS:
                return
            checked_at = time.monotonic()
            # A receipt fences completed GPU work. Its CUDA context may be tearing
            # down while telemetry still reports utilization or a retired PID.
            active = tuple(
                (rank, device)
                for rank, device in enumerate(devices)
                if not (output / f"rank-{rank}.json").is_file()
            )
            if not active:
                return
            current = monitor_devices(tuple(device for _, device in active), owned_pids)
            for (rank, _device), used in zip(active, current, strict=True):
                peaks[rank] = max(peaks[rank], used)

        outcome = run_workers(
            commands, timeout_seconds=settings.trial_timeout_seconds, monitor=monitor
        )
        records = []
        for rank in range(profile.world_size):
            path = output / f"rank-{rank}.json"
            if path.is_file():
                record = ProbeRankResult.model_validate_json(path.read_text(encoding="utf-8"))
                if record.token != token or record.rank != rank:
                    raise RuntimeError("Probe receipt identity does not match its worker")
            else:
                record = ProbeRankResult(
                    token=token,
                    rank=rank,
                    status="timeout" if outcome.status == "timeout" else "crash",
                    diagnostic=f"Worker has no complete receipt; inspect {output}",
                )
            records.append(record)
        if outcome.status != "success" and all(item.status == "success" for item in records):
            records[0] = records[0].model_copy(
                update={
                    "status": "timeout" if outcome.status == "timeout" else "crash",
                    "diagnostic": f"Worker {outcome.status} after writing a success receipt",
                }
            )
        budget_peaks = tuple(
            max(
                peaks[rank],
                record.peak_memory_bytes + max(baseline[rank], record.non_allocator_memory_bytes),
            )
            for rank, record in enumerate(records)
        )
        return records, budget_peaks
