"""Supervise isolated model jobs without initializing CUDA or creating tracking tasks."""

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, suppress
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from weakref import WeakKeyDictionary

from hydra.conf import HydraConf
from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import JobReturn, JobStatus
from loguru import logger
from omegaconf import DictConfig, OmegaConf, open_dict

from clearml_yolo.filesystem import temporary_root
from clearml_yolo.gpu_queue import GPUQueue, Ticket
from clearml_yolo.gpu_resources import GPUInventory, device_count, job_request

POLL_SECONDS = 0.5
_ENTRYPOINT: tuple[str, Callable[..., Any]] | None = None
_WINDOWS_JOBS: WeakKeyDictionary[subprocess.Popen[Any], int] = WeakKeyDictionary()
_POSIX_GROUPS: WeakKeyDictionary[subprocess.Popen[Any], int] = WeakKeyDictionary()


def configure_entrypoint(name: str, function: Callable[..., Any]) -> None:
    global _ENTRYPOINT  # noqa: PLW0603 - one entrypoint per CLI process, before Hydra launches
    _ENTRYPOINT = name, function


def entrypoint() -> tuple[str, Callable[..., Any]]:
    if _ENTRYPOINT is None:
        raise RuntimeError("The queue launcher requires a cy model entrypoint")
    return _ENTRYPOINT


def effective_configuration(config: DictConfig, devices: tuple[str, ...]) -> DictConfig:
    """Translate requests to reserved child ordinals without rewriting provenance."""
    effective = deepcopy(config)
    if not devices:
        return effective
    with open_dict(effective):
        for group, limit in (("ultralytics", len(devices)), ("ultralytics_predict", 1)):
            if group in effective:
                count = min(device_count(effective[group].get("device")), limit)
                if count:
                    effective[group].device = list(range(count))
    return effective


def _windows_error(message: str) -> OSError:
    import ctypes

    return OSError(ctypes.get_last_error(), message)  # type: ignore[attr-defined]


def _close_windows_handle(handle: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    if not kernel32.CloseHandle(handle):
        raise _windows_error("Could not close the Windows worker job")


def _create_windows_job(process: subprocess.Popen[Any]) -> int:
    """Assign a spawned worker to a kill-on-close Windows Job Object."""
    import ctypes
    from ctypes import wintypes

    class _IOCounters(ctypes.Structure):
        _fields_ = [  # type: ignore[mutable-override]
            ("read_operations", ctypes.c_ulonglong),
            ("write_operations", ctypes.c_ulonglong),
            ("other_operations", ctypes.c_ulonglong),
            ("read_bytes", ctypes.c_ulonglong),
            ("write_bytes", ctypes.c_ulonglong),
            ("other_bytes", ctypes.c_ulonglong),
        ]

    class _BasicLimits(ctypes.Structure):
        _fields_ = [  # type: ignore[mutable-override]
            ("per_process_time", ctypes.c_longlong),
            ("per_job_time", ctypes.c_longlong),
            ("limit_flags", wintypes.DWORD),
            ("minimum_working_set", ctypes.c_size_t),
            ("maximum_working_set", ctypes.c_size_t),
            ("active_process_limit", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority_class", wintypes.DWORD),
            ("scheduling_class", wintypes.DWORD),
        ]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [  # type: ignore[mutable-override]
            ("basic", _BasicLimits),
            ("io", _IOCounters),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process_memory", ctypes.c_size_t),
            ("peak_job_memory", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise _windows_error("Could not create the Windows worker job")
    handle_value = int(handle)
    try:
        limits = _ExtendedLimits()
        limits.basic.limit_flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise _windows_error(  # noqa: TRY301 - cleanup requires the surrounding try
                "Could not configure the Windows worker job"
            )
        process_handle = wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]  # noqa: SLF001
        if not kernel32.AssignProcessToJobObject(handle, process_handle):
            raise _windows_error(  # noqa: TRY301 - cleanup requires the surrounding try
                "Could not assign the worker to its Windows job"
            )
    except BaseException:
        _close_windows_handle(handle_value)
        raise
    return handle_value


def _attach_windows_job(process: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        _WINDOWS_JOBS[process] = _create_windows_job(process)


def _attach_process_tree(process: subprocess.Popen[Any]) -> None:
    if os.name == "posix":
        _POSIX_GROUPS[process] = process.pid
    else:
        _attach_windows_job(process)


def _release_windows_job(process: subprocess.Popen[Any]) -> None:
    handle = _WINDOWS_JOBS.pop(process, None)
    if handle is not None:
        _close_windows_handle(handle)


def _terminate_windows_process_tree(process: subprocess.Popen[Any]) -> None:
    handle = _WINDOWS_JOBS.get(process)
    if handle is None:
        process.terminate()
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    if not kernel32.TerminateJobObject(handle, 1):
        raise _windows_error("Could not terminate the Windows worker process tree")


def _signal_posix_process(process: subprocess.Popen[Any], signum: signal.Signals) -> None:
    try:
        group = os.getpgid(process.pid)
    except ProcessLookupError:
        return
    try:
        if group == process.pid:
            os.killpg(group, signum)
        elif signum == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except ProcessLookupError:
        pass


def _signal_posix_group(group: int, signum: signal.Signals) -> None:
    with suppress(ProcessLookupError):
        os.killpg(group, signum)


def _release_process_tree(process: subprocess.Popen[Any]) -> None:
    group = _POSIX_GROUPS.pop(process, None)
    if group is not None:
        _signal_posix_group(group, signal.SIGKILL)
    _release_windows_job(process)


def cancel_process(process: subprocess.Popen[Any]) -> None:
    """Terminate only this child's process tree, then reap it before releasing capacity."""
    try:
        if process.poll() is not None:
            return
        group = _POSIX_GROUPS.get(process)
        if group is not None:
            _signal_posix_group(group, signal.SIGTERM)
        elif os.name == "posix":
            # Ordinary caller-owned test processes are not assumed to own their group.
            _signal_posix_process(process, signal.SIGTERM)
        elif os.name == "nt":
            _terminate_windows_process_tree(process)
        else:
            process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            if group is not None:
                _signal_posix_group(group, signal.SIGKILL)
            elif os.name == "posix":
                _signal_posix_process(process, signal.SIGKILL)
            elif os.name == "nt":
                _terminate_windows_process_tree(process)
            else:
                process.kill()
            process.wait()
    finally:
        _release_process_tree(process)


def wait_process(process: subprocess.Popen[Any]) -> int:
    try:
        code = process.wait()
    except BaseException:
        cancel_process(process)
        raise
    _release_process_tree(process)
    return code


def _interrupt(signum: int, _frame: Any) -> None:
    raise SystemExit(128 + signum)


@contextmanager
def interruption() -> Iterator[None]:
    previous = signal.signal(signal.SIGTERM, _interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _application_config(config: DictConfig) -> DictConfig:
    application = deepcopy(config)
    with open_dict(application):
        application.pop("hydra", None)
    return application


@dataclass
class ModelJob:
    """One composed job; admission and process polling never mutate Hydra global state."""

    command: str
    function: Callable[..., Any]
    config: DictConfig
    sweep: bool = False
    queue: GPUQueue | None = None
    ticket: Ticket | None = None
    process: subprocess.Popen[Any] | None = None
    result: JobReturn | None = None
    temporary: TemporaryDirectory[str] | None = None
    previous_position: int | None = None
    launch_cwd: str = field(default_factory=os.getcwd)

    def prepare(self) -> None:
        from clearml_yolo.apps.common import validate_wrapper_keys

        application = _application_config(self.config)
        old_hydra = HydraConfig.instance().cfg
        try:
            HydraConfig.instance().set_config(self.config)
            validate_wrapper_keys(application, self.function)
            resolved = OmegaConf.to_container(application, resolve=True, throw_on_missing=True)
            if not isinstance(resolved, dict):
                raise TypeError("Command configuration must be a mapping")
            count = job_request(self.command, {str(key): value for key, value in resolved.items()})
        finally:
            HydraConfig.instance().cfg = old_hydra
        if count:
            inventory = GPUInventory()
            # The job's environment may further restrict its inherited device visibility.
            from hydra.core.utils import env_override

            env = {str(k): str(v) for k, v in self.config.hydra.job.env_set.items()}
            with env_override(env):
                visible = inventory.visible()
            self.queue = GPUQueue(inventory=inventory)
            self.ticket = self.queue.register(count, visible)

    def start(self) -> None:
        if self.process is not None or self.result is not None:
            return
        devices: tuple[str, ...] = ()
        if self.ticket is not None:
            selected = self.ticket.try_acquire()
            if selected is None:
                position = self.ticket.position()
                if position != self.previous_position:
                    logger.info(
                        "{} waiting for GPUs: ticket {} position {}",
                        self.command,
                        self.ticket.id,
                        position,
                    )
                    self.previous_position = position
                return
            devices = selected
        self.temporary = TemporaryDirectory(prefix="cy-job-", dir=temporary_root())
        directory = Path(self.temporary.name)
        document = directory / "job.yaml"
        start_gate = directory / "start.ready"
        payload = OmegaConf.create(
            {
                "command": self.command,
                "module": self.function.__module__,
                "function": self.function.__name__,
                "sweep": self.sweep,
                "queue_root": str(self.queue.root) if self.queue else None,
                "ticket": self.ticket.id if self.ticket else None,
                "config": self.config,
                "result": str(directory / "result.json"),
                "start_gate": str(start_gate),
                "sys_path": sys.path,
            }
        )
        OmegaConf.save(payload, document)
        environment = dict(os.environ)
        if devices:
            environment["CUDA_VISIBLE_DEVICES"] = ",".join(devices)
        logger.info("Starting {} on GPUs {}", self.command, list(devices))
        process = subprocess.Popen(  # noqa: S603 - current interpreter and owned payload
            [sys.executable, "-m", "clearml_yolo.apps.job_worker", str(document)],
            cwd=self.launch_cwd,
            env=environment,
            start_new_session=os.name == "posix",
        )
        self.process = process
        try:
            _attach_process_tree(process)
            start_gate.touch()
        except BaseException:
            cancel_process(process)
            raise

    def poll(self) -> None:
        if self.process is None or self.result is not None:
            return
        code = self.process.poll()
        if code is None:
            return
        code = wait_process(self.process)
        self.result = JobReturn()
        self.result.cfg = _application_config(self.config)
        self.result.hydra_cfg = OmegaConf.masked_copy(self.config, "hydra")
        self.result.task_name = self.command
        self.result.overrides = list(self.config.hydra.overrides.task)
        self.result.working_dir = self.launch_cwd
        failure: RuntimeError | None = None
        if self.sweep:
            try:
                status, working_dir = self._read_sweep_receipt()
                self.result.status = status
                self.result.working_dir = working_dir
            except RuntimeError as error:
                self.result.status = JobStatus.FAILED
                failure = error
        else:
            self.result.status = JobStatus.COMPLETED if code == 0 else JobStatus.FAILED
        if code != 0:
            self.result.status = JobStatus.FAILED
            failure = RuntimeError(
                f"{self.command} process exited with status {code}; see its console output"
            )
        elif self.result.status != JobStatus.COMPLETED and failure is None:
            failure = RuntimeError(f"{self.command} sweep job reported failed status")
        self.result.return_value = failure
        self.close()

    def _read_sweep_receipt(self) -> tuple[JobStatus, str]:
        if self.temporary is None:
            raise RuntimeError(f"{self.command} sweep result receipt is missing")
        path = Path(self.temporary.name) / "result.json"
        try:
            value: object = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise RuntimeError(f"{self.command} sweep result receipt is missing") from None
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"{self.command} sweep result receipt is invalid: {error}") from None
        if not isinstance(value, dict) or set(value) != {"status", "working_dir"}:
            raise RuntimeError(f"{self.command} sweep result receipt is invalid")
        status_name = value["status"]
        working_dir = value["working_dir"]
        if not isinstance(status_name, str) or status_name not in {
            JobStatus.COMPLETED.name,
            JobStatus.FAILED.name,
        }:
            raise RuntimeError(f"{self.command} sweep result receipt has invalid status")
        if not isinstance(working_dir, str) or not working_dir:
            raise RuntimeError(f"{self.command} sweep result receipt has invalid working directory")
        return JobStatus[status_name], working_dir

    def close(self) -> None:
        if self.process is not None:
            if self.process.poll() is None:
                cancel_process(self.process)
            else:
                wait_process(self.process)
            self.process = None
        errors: list[BaseException] = []
        if self.ticket is not None:
            ticket, self.ticket = self.ticket, None
            try:
                ticket.close()
            except BaseException as error:  # noqa: BLE001 - finish independent cleanup steps
                errors.append(error)
        if self.temporary is not None:
            temporary, self.temporary = self.temporary, None
            try:
                temporary.cleanup()
            except BaseException as error:  # noqa: BLE001 - finish independent cleanup steps
                errors.append(error)
        if errors:
            raise BaseExceptionGroup(f"{self.command} job cleanup failed", errors)


def _close_jobs(jobs: Sequence[ModelJob]) -> list[BaseException]:
    errors: list[BaseException] = []
    for job in jobs:
        try:
            job.close()
        except BaseException as error:  # noqa: BLE001 - every job must be cleaned independently
            errors.append(error)
    return errors


def run_jobs(jobs: Sequence[ModelJob]) -> list[JobReturn]:
    """Submit in order, then fill free capacity while preserving FIFO admission."""
    try:
        with interruption():
            for job in jobs:
                job.prepare()
            while any(job.result is None for job in jobs):
                for job in jobs:
                    job.start()
                    job.poll()
                if any(job.result is None for job in jobs):
                    time.sleep(POLL_SECONDS)
            results = [job.result for job in jobs if job.result is not None]
    except BaseException as primary:
        cleanup_errors = _close_jobs(jobs)
        if cleanup_errors:
            raise BaseExceptionGroup(
                "Queued job execution and cleanup failed", [primary, *cleanup_errors]
            ) from None
        raise
    cleanup_errors = _close_jobs(jobs)
    if cleanup_errors:
        raise BaseExceptionGroup("Queued job cleanup failed", cleanup_errors)
    return results


def schedule_single(name: str, function: Callable[..., Any], config: DictConfig) -> None:
    full = deepcopy(config)
    if not HydraConfig.initialized():
        raise RuntimeError("A queued command requires Hydra runtime configuration")
    with open_dict(full):
        full.hydra = deepcopy(HydraConfig.get())
    result = run_jobs([ModelJob(name, function, full)])[0]
    _ = result.return_value


def restore_hydra_config(config: DictConfig) -> DictConfig:
    """YAML transfers values; restore Hydra's structured node before installing context."""
    hydra_node = OmegaConf.structured(HydraConf)
    OmegaConf.set_struct(hydra_node, False)
    hydra_node = OmegaConf.merge(hydra_node, config.hydra)
    with open_dict(config):
        config.hydra = hydra_node
    return config
