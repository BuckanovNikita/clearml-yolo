"""Bound optional SDK execution, including imports, service shutdown and cleanup."""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import mkdtemp
from typing import Literal
from uuid import uuid4

from clearml_yolo.adapters.fiftyone.protocol import WorkerRequest, WorkerResult
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.core.publication import FiftyOneConfig, PublicationReceipt, PublicationRequest
from clearml_yolo.core.redaction import redact_text

_DIAGNOSTIC_BYTES = 4096
_CLEANUP_SECONDS = 5.0
_KILL_SIGNAL = 9


def _worker_command(request: Path, result: Path, phase: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "clearml_yolo.adapters.fiftyone.worker",
        str(request),
        str(result),
        str(phase),
    ]


def _worker_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("CY_CLEARML_OWNER_", "CY_GPU_QUEUE_", "CY_QUEUE_"))
    }
    environment["CUDA_VISIBLE_DEVICES"] = ""
    environment["NVIDIA_VISIBLE_DEVICES"] = "none"
    environment["HIP_VISIBLE_DEVICES"] = ""
    environment["ROCR_VISIBLE_DEVICES"] = ""
    return environment


class _OutputTail:
    """Drain the pipe continuously; retain a small tail rather than unbounded output."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._data = bytearray()
        self._lock = threading.Lock()
        self._stream = process.stdout
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self) -> None:
        if self._stream is None:
            return
        try:
            while chunk := self._stream.read(1024):
                with self._lock:
                    self._data.extend(chunk)
                    del self._data[:-_DIAGNOSTIC_BYTES]
        except (OSError, ValueError):
            # The supervisor may close its pipe after forcibly reaping a worker.
            return

    def diagnostic(self) -> str:
        with self._lock:
            value = bytes(self._data).decode("utf-8", errors="replace")
        return redact_text(value)[-2048:]

    def close(self) -> None:
        self._thread.join(timeout=0.1)
        if not self._thread.is_alive() and self._stream is not None:
            self._stream.close()


def _process_table() -> dict[int, tuple[int, int, str, str]]:
    """Linux process identity plus ancestry; no command lines or credentials are read."""
    table: dict[int, tuple[int, int, str, str]] = {}
    proc = Path("/proc")
    if not proc.is_dir():
        return table
    for path in proc.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
            table[int(path.name)] = (int(fields[1]), int(fields[3]), fields[19], fields[0])
        except (OSError, ValueError, IndexError):
            continue
    return table


def _platform() -> str:
    return os.name


def _windows_error(message: str) -> OSError:
    import ctypes

    return OSError(ctypes.get_last_error(), message)  # type: ignore[attr-defined]


def _close_windows_job(handle: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    if not kernel32.CloseHandle(handle):
        raise _windows_error("Could not close the Windows worker job")


def _create_windows_job(process: subprocess.Popen[bytes]) -> int:
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
        _close_windows_job(handle_value)
        raise
    return handle_value


def _windows_job_running(handle: int) -> bool:
    import ctypes
    from ctypes import wintypes

    class Accounting(ctypes.Structure):
        _fields_ = [  # type: ignore[mutable-override]
            ("total_user", ctypes.c_longlong),
            ("total_kernel", ctypes.c_longlong),
            ("period_user", ctypes.c_longlong),
            ("period_kernel", ctypes.c_longlong),
            ("page_faults", wintypes.DWORD),
            ("total_processes", wintypes.DWORD),
            ("active_processes", wintypes.DWORD),
            ("terminated_processes", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    accounting = Accounting()
    if not kernel32.QueryInformationJobObject(
        handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
    ):
        raise _windows_error("Could not verify Windows worker process cleanup")
    return bool(accounting.active_processes)


def _terminate_windows_job(handle: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    if not kernel32.TerminateJobObject(handle, 1):
        raise _windows_error("Could not terminate the FiftyOne worker job")


class _OwnedProcesses:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self.identities: dict[int, str] = {}
        self.job: int | None = None
        self.attached = False

    def attach(self) -> None:
        if _platform() == "nt":
            self.job = _create_windows_job(self.process)
        elif _platform() != "posix" or not Path("/proc/self/stat").is_file():
            raise RuntimeError("FiftyOne worker process ownership is unsupported on this platform")
        self.attached = True

    def refresh(self) -> None:
        if _platform() == "nt":
            return
        table = _process_table()
        owners = {
            pid for pid, born in self.identities.items() if pid in table and table[pid][2] == born
        }
        if self.process.poll() is None:
            owners.add(self.process.pid)
        changed = True
        while changed:
            changed = False
            for pid, (parent, session, born, _) in table.items():
                if pid not in owners and (parent in owners or session == self.process.pid):
                    owners.add(pid)
                    self.identities[pid] = born
                    changed = True
        if self.process.pid in table:
            self.identities[self.process.pid] = table[self.process.pid][2]

    def alive(self) -> list[int]:
        if _platform() == "nt":
            return (
                [self.process.pid]
                if self.job is not None and _windows_job_running(self.job)
                else []
            )
        table = _process_table()
        return [
            pid
            for pid, born in self.identities.items()
            if pid in table and table[pid][2] == born and table[pid][3] != "Z"
        ]

    def signal(self, value: int) -> None:
        if _platform() == "nt":
            if value == _KILL_SIGNAL and self.job is not None:
                _terminate_windows_job(self.job)
            elif self.process.poll() is None:
                self.process.terminate()
            return
        self.refresh()
        for pid in reversed(self.alive()):
            with suppress(ProcessLookupError):
                os.kill(pid, value)
        if self.process.poll() is None:
            if value == signal.SIGTERM:
                self.process.terminate()
            else:
                self.process.kill()

    def cleanup(self) -> None:
        self.signal(signal.SIGTERM)
        deadline = time.monotonic() + _CLEANUP_SECONDS
        while (self.alive() or self.process.poll() is None) and time.monotonic() < deadline:
            time.sleep(0.02)
            self.refresh()
        if self.alive() or self.process.poll() is None:
            self.signal(_KILL_SIGNAL)
        deadline = time.monotonic() + _CLEANUP_SECONDS
        while (self.alive() or self.process.poll() is None) and time.monotonic() < deadline:
            time.sleep(0.02)
        # poll() reaps the directly owned worker even when cancellation interrupted wait().
        if self.process.poll() is None or self.alive():
            raise RuntimeError("FiftyOne worker cleanup unsafe: owned processes remain alive")
        if self.job is not None:
            _close_windows_job(self.job)
            self.job = None


class _OperationScratch:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.retained = False

    def retain(self, owned: _OwnedProcesses, error: BaseException) -> None:
        # Set before writing: a failed marker write must not permit directory deletion.
        self.retained = True
        owners: list[dict[str, str | int]] = []
        if _platform() == "posix":
            try:
                boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                table = _process_table()
                for pid, start in owned.identities.items():
                    if pid in table and table[pid][2] == start and table[pid][3] != "Z":
                        owners.append(
                            {
                                "version": 1,
                                "pid": pid,
                                "start": start,
                                "boot": boot,
                                "host": socket.gethostname(),
                                "token": uuid4().hex,
                            }
                        )
            except OSError:
                owners = []
        # Empty owners means unproved identity/accounting, not permission to recover.
        marker = {"version": 1, "owners": owners, "reason": redact_text(str(error))[:512]}
        try:
            (self.path / ".cy-unsafe-cleanup.json").write_text(json.dumps(marker), encoding="utf-8")
        except OSError as marker_error:
            sys.stderr.write(
                "Cannot record unsafe FiftyOne scratch ownership: "
                f"{redact_text(str(marker_error))[:512]}\n"
            )


@contextmanager
def _operation_scratch() -> Iterator[_OperationScratch]:
    scratch = _OperationScratch(Path(mkdtemp(prefix="fiftyone-", dir=temporary_root())))
    try:
        (scratch.path / ".cy-unsafe-cleanup.json").write_text(
            json.dumps(
                {"version": 1, "owners": [], "reason": "Publication cleanup not yet proved"}
            ),
            encoding="utf-8",
        )
    except OSError as error:
        shutil.rmtree(scratch.path)
        raise RuntimeError("Cannot establish durable FiftyOne scratch ownership") from error
    try:
        yield scratch
    finally:
        if not scratch.retained:
            shutil.rmtree(scratch.path)


def _preserve_cleanup_failure(
    scratch: _OperationScratch,
    owned: _OwnedProcesses,
    original_error: BaseException | None,
    error: BaseException,
) -> None:
    scratch.retain(owned, error)
    unsafe = RuntimeError(
        "FiftyOne worker cleanup unsafe; "
        f"scratch retained at {scratch.path}; {redact_text(str(error))[:512]}"
    )
    if not isinstance(error, Exception):
        sys.stderr.write(f"{unsafe}\n")
        raise error
    if original_error is not None and not isinstance(original_error, Exception):
        sys.stderr.write(f"{unsafe}\n")
    else:
        raise unsafe from error


def _phase(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as stream:
            return redact_text(stream.read(160)).strip() or "startup"
    except OSError:
        return "startup"


def _validated_result(result_path: Path, phase_path: Path, message: WorkerRequest) -> WorkerResult:
    try:
        result = WorkerResult.model_validate_json(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"FiftyOne {message.operation} worker returned an invalid receipt; "
            f"phase={_phase(phase_path)}"
        ) from error
    expected_task = None if message.request is None else message.request.task_id
    if (
        result.operation != message.operation
        or result.operation_id != message.operation_id
        or result.task_id != expected_task
    ):
        raise RuntimeError("FiftyOne worker receipt identity mismatch")
    if message.operation == "publish" and (
        result.receipt is None
        or result.receipt.task_id != expected_task
        or not result.receipt.run_complete
        or not result.receipt.dataset_complete
    ):
        raise RuntimeError("FiftyOne worker publication receipt is incomplete or mismatched")
    return result


class BoundedFiftyOnePublisher:
    enabled = True

    def __init__(self, config: FiftyOneConfig) -> None:
        self.config = config

    def preflight(self) -> None:
        self._execute("preflight", None, self.config.preflight_timeout_seconds)

    def publish(self, request: PublicationRequest) -> PublicationReceipt:
        result = self._execute("publish", request, self.config.publish_timeout_seconds)
        if result.receipt is None:
            raise RuntimeError("FiftyOne publish worker returned no publication receipt")
        return result.receipt

    def _execute(
        self,
        operation: Literal["preflight", "publish"],
        request: PublicationRequest | None,
        timeout: float,
    ) -> WorkerResult:
        deadline = time.monotonic() + timeout
        if request is not None:
            request = request.model_copy(
                update={
                    "ground_truth": request.ground_truth.resolve(),
                    "source_ground_truth": None
                    if request.source_ground_truth is None
                    else request.source_ground_truth.resolve(),
                    "predictions": None
                    if request.predictions is None
                    else request.predictions.resolve(),
                    "evaluations": {
                        split: path.resolve() for split, path in request.evaluations.items()
                    },
                }
            )
        message = WorkerRequest(
            operation=operation, operation_id=uuid4().hex, config=self.config, request=request
        )
        # Request/receipt scratch is explicit; the SDK keeps its native temp selection.
        with _operation_scratch() as scratch:
            arena = scratch.path
            request_path, result_path, phase_path = (
                arena / name for name in ("request.json", "result.json", "phase")
            )
            request_path.write_text(message.model_dump_json(), encoding="utf-8")
            gate = arena / "start"
            environment = _worker_environment()
            environment["CY_FIFTYONE_START_GATE"] = str(gate)
            process = subprocess.Popen(  # noqa: S603 - trusted interpreter and module
                _worker_command(request_path, result_path, phase_path),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            output = _OutputTail(process)
            owned = _OwnedProcesses(process)
            try:
                owned.attach()
                gate.touch()
                while True:
                    owned.refresh()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError(
                            f"FiftyOne {operation} deadline exceeded; "
                            f"phase={_phase(phase_path)}; {output.diagnostic()}"
                        )
                    try:
                        status = process.wait(timeout=min(0.05, remaining))
                    except subprocess.TimeoutExpired:
                        continue
                    break
                if status != 0:
                    raise RuntimeError(
                        f"FiftyOne {operation} worker exited {status}; "
                        f"phase={_phase(phase_path)}; {output.diagnostic()}"
                    )
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"FiftyOne {operation} deadline exceeded; phase={_phase(phase_path)}"
                    )
                result = _validated_result(result_path, phase_path, message)
            finally:
                original_error = sys.exception()
                try:
                    owned.cleanup()
                except BaseException as error:  # noqa: BLE001 - cleanup must retain cancellation
                    # Every interrupted/failed cleanup leaves ownership unproved.
                    _preserve_cleanup_failure(scratch, owned, original_error, error)
                finally:
                    output.close()
            if time.monotonic() >= deadline:
                raise RuntimeError(f"FiftyOne {operation} deadline exceeded; phase=shutdown")
            return result
