"""Generic owned-process cleanup, independent of scheduling and Hydra."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

from clearml_yolo.adapters.runtime.process_tree import (
    LinuxProcessTree,
    UnverifiableProcessTreeError,
    defer_interruptions,
)

_WINDOWS_JOBS: WeakKeyDictionary[subprocess.Popen[Any], int] = WeakKeyDictionary()
_POSIX_GROUPS: WeakKeyDictionary[subprocess.Popen[Any], int] = WeakKeyDictionary()
_LINUX_TREES: WeakKeyDictionary[subprocess.Popen[Any], LinuxProcessTree] = WeakKeyDictionary()


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


def _attach_process_tree(process: subprocess.Popen[Any], token: str | None = None) -> None:
    if os.name == "posix":
        _POSIX_GROUPS[process] = process.pid
        if sys.platform == "linux":
            _LINUX_TREES[process] = LinuxProcessTree(process.pid, token)
    else:
        _attach_windows_job(process)


def _release_windows_job(process: subprocess.Popen[Any], *, deadline: float | None = None) -> None:
    handle = _WINDOWS_JOBS.get(process)
    if handle is not None:
        _terminate_windows_process_tree(process)
        deadline = deadline if deadline is not None else time.monotonic() + 5
        while _windows_job_running(handle):
            if time.monotonic() >= deadline:
                raise RuntimeError("Worker descendants survived cleanup; GPU lease remains owned")
            time.sleep(0.05)
        _close_windows_handle(handle)
        _WINDOWS_JOBS.pop(process, None)


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


def _posix_group_running(group: int) -> bool:
    proc = Path("/proc")
    if proc.is_dir():
        for directory in proc.iterdir():
            if not directory.name.isdecimal():
                continue
            try:
                fields = (directory / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
            except (FileNotFoundError, ProcessLookupError):
                continue
            if int(fields[2]) == group and fields[0] != "Z":
                return True
        return False
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_for_posix_cleanup(group: int, tree: LinuxProcessTree | None, deadline: float) -> None:
    """Keep ownership until a fresh complete scan succeeds within the existing budget."""
    while True:
        verification_error: UnverifiableProcessTreeError | None = None
        try:
            if not (tree.running() if tree is not None else _posix_group_running(group)):
                return
        except UnverifiableProcessTreeError as error:
            verification_error = error
        if time.monotonic() >= deadline:
            if verification_error is not None:
                raise verification_error
            raise RuntimeError("Worker descendants survived cleanup; GPU lease remains owned")
        if tree is not None:
            tree.signal(signal.SIGKILL)
        time.sleep(0.05)


def _release_process_tree(process: subprocess.Popen[Any], *, deadline: float | None = None) -> None:
    group = _POSIX_GROUPS.get(process)
    if group is not None:
        deadline = deadline if deadline is not None else time.monotonic() + 5
        tree = _LINUX_TREES.get(process)
        if tree is not None:
            tree.signal(signal.SIGKILL)
        else:
            _signal_posix_group(group, signal.SIGKILL)
        _wait_for_posix_cleanup(group, tree, deadline)
        _POSIX_GROUPS.pop(process, None)
        _LINUX_TREES.pop(process, None)
    _release_windows_job(process, deadline=deadline)


def _signal_process_tree(process: subprocess.Popen[Any], signum: signal.Signals) -> None:
    tree = _LINUX_TREES.get(process)
    group = _POSIX_GROUPS.get(process)
    if tree is not None:
        tree.signal(signum)
    elif group is not None:
        _signal_posix_group(group, signum)
    elif os.name == "posix":
        _signal_posix_process(process, signum)
    elif os.name == "nt":
        _terminate_windows_process_tree(process)
    elif signum == signal.SIGTERM:
        process.terminate()
    else:
        process.kill()


@defer_interruptions()
def cancel_process(process: subprocess.Popen[Any]) -> None:
    """Terminate only this child's process tree, then reap it before releasing capacity."""
    deadline = time.monotonic() + 10
    try:
        if process.poll() is not None:
            return
        _signal_process_tree(process, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _signal_process_tree(process, signal.SIGKILL)
            process.wait(timeout=5)
    finally:
        if process.poll() is not None:
            _release_process_tree(process, deadline=deadline)


@defer_interruptions()
def wait_process(process: subprocess.Popen[Any]) -> int:
    try:
        code = process.wait(timeout=5)
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
