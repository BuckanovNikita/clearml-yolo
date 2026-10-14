"""Missing supervision capabilities must fail before a model can start."""

import errno
import os
import signal
import sys
from pathlib import Path
from types import ModuleType

import pytest

from clearml_yolo.adapters.runtime import process_tree

pytestmark = [
    pytest.mark.process_capabilities,
    pytest.mark.skipif(sys.platform != "linux", reason="Linux supervision contract"),
]


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (os, "pidfd_open"),
        (signal, "pidfd_send_signal"),
        (os, "waitid"),
        (os, "P_PIDFD"),
        (os, "pipe2"),
        (os, "register_at_fork"),
    ],
)
def test_missing_capability_rejects_before_native_work(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType, name: str
) -> None:
    entered: list[str] = []
    previous = os.environ.get(process_tree.DIRECT_OWNER_ENV)
    monkeypatch.delattr(module, name, raising=False)
    with (
        pytest.raises(RuntimeError, match=name) as captured,
        process_tree.native_descendant_scope(),
    ):
        entered.append("training")
    assert entered == []
    assert sys.executable in str(captured.value)
    assert os.environ.get(process_tree.DIRECT_OWNER_ENV) == previous


@pytest.mark.parametrize("number", [errno.ENOSYS, errno.EINVAL, errno.EPERM])
def test_unavailable_kernel_pidfd_fails_before_native_work(
    monkeypatch: pytest.MonkeyPatch, number: int
) -> None:
    def unavailable(_pid: int) -> int:
        raise OSError(number, "capability probe rejected")

    monkeypatch.setattr(os, "pidfd_open", unavailable)
    with pytest.raises(RuntimeError, match="pidfd_open"), process_tree.native_descendant_scope():
        pytest.fail("Training was entered despite unavailable supervision")


def test_failed_signal_probe_closes_descriptor(monkeypatch: pytest.MonkeyPatch) -> None:
    descriptors: list[int] = []
    original = os.pidfd_open

    def opened(pid: int) -> int:
        descriptor = original(pid)
        descriptors.append(descriptor)
        return descriptor

    def denied(_descriptor: int, _signal: int) -> None:
        raise PermissionError(errno.EPERM, "denied")

    monkeypatch.setattr(os, "pidfd_open", opened)
    monkeypatch.setattr(signal, "pidfd_send_signal", denied)
    with pytest.raises(RuntimeError, match="pidfd_send_signal"):
        process_tree.require_process_supervision()
    assert len(descriptors) == 1
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(descriptors[0])


def test_waitid_kernel_support_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(_kind: int, _descriptor: int, _flags: int) -> None:
        raise OSError(errno.EINVAL, "P_PIDFD unavailable")

    monkeypatch.setattr(os, "waitid", unavailable)
    with pytest.raises(RuntimeError, match="waitid"):
        process_tree.require_process_supervision()


def test_real_probe_preserves_subreaper_and_descriptors() -> None:
    before = process_tree._subreaper()
    descriptors = set(Path("/proc/self/fd").iterdir())
    process_tree.require_process_supervision()
    assert process_tree._subreaper() == before
    assert set(Path("/proc/self/fd").iterdir()) == descriptors


def test_current_interpreter_probe_succeeds() -> None:
    process_tree.check_interpreter_supervision(sys.executable)


def test_selected_interpreter_without_pidfd_is_rejected(tmp_path: Path) -> None:
    wrapper = tmp_path / "python-no-pidfd"
    wrapper.write_text(
        f"#!{sys.executable}\nimport os,sys\ndel os.pidfd_open\nexec(sys.argv[2])\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o700)
    with pytest.raises(RuntimeError, match="pidfd_open") as captured:
        process_tree.check_interpreter_supervision(str(wrapper))
    assert str(wrapper) in str(captured.value)


def test_hung_interpreter_probe_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wrapper = tmp_path / "hung-python"
    wrapper.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n", encoding="utf-8")
    wrapper.chmod(0o700)
    monkeypatch.setattr(process_tree, "_SUPERVISION_PROBE_TIMEOUT_SECONDS", 0.1)
    with pytest.raises(RuntimeError, match="timed out"):
        process_tree.check_interpreter_supervision(str(wrapper))
