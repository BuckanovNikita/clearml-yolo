"""Real FD/child capture and bounded attach-only publisher supervision."""

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))


def test_capture_includes_native_children_partial_lines_and_restores(tmp_path: Path) -> None:
    code = """
import os, subprocess, sys
from pathlib import Path
from clearml_yolo.adapters.observability.capture import capture_output, terminal_isatty
root = Path(sys.argv[1])
os.environ["CY_HOME"] = str(root.parent)
before = os.environ.get("PYTHONUNBUFFERED")
with capture_output(root) as capture:
    assert terminal_isatty() is False
    print("python-marker")
    os.write(1, b"native-partial")
    os.write(2, b"stderr-marker\\n")
    child_code = "import os; os.write(1,b'child-marker\\\\n')"
    subprocess.run([sys.executable, "-c", child_code], check=True)
    with capture_output(root / "unused") as nested:
        assert nested is capture
assert os.environ.get("PYTHONUNBUFFERED") == before
print("restored-marker")
"""
    result = subprocess.run(  # noqa: S603 - fixed test source and isolated output directory
        [sys.executable, "-c", code, str(tmp_path / "capture")],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    stdout = (tmp_path / "capture/stdout.log").read_text()
    stderr = (tmp_path / "capture/stderr.log").read_text()
    assert stdout == "python-marker\nnative-partialchild-marker\n"
    assert stderr == "stderr-marker\n"
    for marker in ("python-marker", "native-partial", "child-marker", "restored-marker"):
        assert result.stdout.count(marker) == 1
    assert result.stderr.count("stderr-marker") == 1
    assert not (tmp_path / "capture/unused").exists()


def test_capture_cleanup_preserves_original_exception_when_mirror_fails(tmp_path: Path) -> None:
    code = """
import os, sys
from pathlib import Path
from clearml_yolo.adapters.observability.capture import capture_output
root = Path(sys.argv[1])
error = ValueError('original')
try:
    with capture_output(root) as capture:
        assert capture.mirror is not None
        capture.mirror.kill()
        raise error
except ValueError as caught:
    assert caught is error
else:
    raise AssertionError('Original error missing')
print('restored')
"""
    result = subprocess.run(  # noqa: S603 - fixed test script, isolated subprocess
        [sys.executable, "-c", code, str(tmp_path / "capture")],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "restored" in result.stdout


def test_reopening_capture_appends_without_mirroring_old_bytes(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from clearml_yolo.adapters.observability.capture import capture_output
root = Path(sys.argv[1])
with capture_output(root):
    print('first-capture')
with capture_output(root):
    print('second-capture')
"""
    result = subprocess.run(  # noqa: S603 - fixed test script
        [sys.executable, "-c", code, str(tmp_path / "capture")],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("first-capture") == 1
    assert result.stdout.count("second-capture") == 1
    assert (tmp_path / "capture/stdout.log").read_text() == "first-capture\nsecond-capture\n"


@pytest.mark.parametrize("mode", ["failure", "hang"])
def test_publisher_failure_is_bounded_and_does_not_erase_logs(tmp_path: Path, mode: str) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublicationError, ConsolePublisher
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path)
    capture.prepare()
    capture.paths["stdout"].write_bytes(b"retained")
    command = [
        sys.executable,
        "-c",
        "raise SystemExit(3)" if mode == "failure" else "import time; time.sleep(90)",
    ]
    publisher = ConsolePublisher("existing-task", capture, timeout=0.15, command=command)
    publisher.start()
    with pytest.raises(ConsolePublicationError, match=r"publication|publisher"):
        publisher.finish()
    assert publisher.process is not None
    assert publisher.process.poll() is not None
    assert capture.paths["stdout"].read_bytes() == b"retained"


def test_publication_barrier_waits_for_advancing_receipts_without_stopping_worker(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublisher
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path / "capture")
    capture.prepare()
    offline = tmp_path / "sdk-task"
    offline.mkdir()
    publisher = ConsolePublisher("existing-task", capture, timeout=3, offline_folder=offline)
    publisher.start()
    try:
        capture.paths["stdout"].write_bytes(b"training-before-close\n")
        publisher.barrier()
        acknowledged = json.loads((publisher.directory / "publisher-receipt.json").read_text())
        assert acknowledged["stdout"] >= capture.paths["stdout"].stat().st_size
        assert publisher.process is not None
        assert publisher.process.poll() is None
        assert not (publisher.directory / "publisher-final.json").exists()
        with capture.paths["stderr"].open("ab") as stream:
            stream.write(b"second-barrier-output\n")
        publisher.barrier()
        acknowledged = json.loads((publisher.directory / "publisher-receipt.json").read_text())
        assert acknowledged["stderr"] >= capture.paths["stderr"].stat().st_size
    finally:
        publisher.finish()


def test_blocked_publication_barrier_is_bounded_and_stops_owned_worker(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublicationError, ConsolePublisher
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path)
    capture.prepare()
    capture.paths["stdout"].write_bytes(b"unacknowledged training output")
    publisher = ConsolePublisher(
        "existing-task",
        capture,
        timeout=0.1,
        command=[sys.executable, "-c", "import time; time.sleep(90)"],
    )
    publisher.start()
    try:
        with pytest.raises(ConsolePublicationError, match="barrier"):
            publisher.barrier()
    finally:
        publisher._stop_owned_process()
    assert publisher.process is not None
    assert publisher.process.poll() is not None
    assert capture.paths["stdout"].read_bytes() == b"unacknowledged training output"


def test_worker_publishes_partial_utf8_and_scalars_without_task_lifecycle(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.console_worker import publish_batch
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path)
    capture.prepare()
    capture.paths["stdout"].write_bytes("partial \u03b1".encode())
    capture.paths["stderr"].write_bytes(b"warning\n")
    capture.paths["scalars"].write_text(
        json.dumps({"title": "train", "series": "loss", "value": 1.5, "iteration": 2}) + "\n"
    )
    events: list[object] = []

    class Sink:
        def report_text(self, message: str, **kwargs: object) -> None:
            assert kwargs == {"print_console": False}
            events.append(message)

        def report_scalar(self, **kwargs: object) -> None:
            events.append(kwargs)

        def flush(self, wait: bool) -> bool:
            assert wait is True
            return True

    offsets = dict.fromkeys(capture.paths, 0)
    assert publish_batch(capture.paths, offsets, Sink(), final=True) == capture.offsets()
    assert "partial \u03b1" in events
    assert "warning" in events
    assert {"title": "train", "series": "loss", "value": 1.5, "iteration": 2} in events
    assert publish_batch(capture.paths, capture.offsets(), Sink(), final=True) == capture.offsets()
    assert len(events) == 3


def test_progress_is_rate_limited_without_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from loguru import logger

    from clearml_yolo.adapters.observability import progress

    messages: list[str] = []
    monkeypatch.setattr(progress, "terminal_isatty", lambda: False)
    monkeypatch.setattr(
        logger, "info", lambda message, *args: messages.append(message.format(*args))
    )
    monkeypatch.setattr(progress, "monotonic", lambda: 1.0)
    assert list(progress.track(range(100), "Inference", unit="img")) == list(range(100))
    assert len(messages) == 1
    assert "100 img" in messages[0]


def test_scalar_journal_does_not_call_network_and_preserves_native_non_scalar_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.integrations.native_runtime import _ScalarLogger
    from clearml_yolo.adapters.observability.capture import OutputCapture

    capture = OutputCapture(tmp_path)
    capture.prepare()
    monkeypatch.setenv("CY_SCALAR_JOURNAL", str(capture.paths["scalars"]))
    images: list[str] = []

    class Logger:
        def report_scalar(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("Scalar callback must not wait for network")

        def report_image(self, name: str) -> None:
            images.append(name)

    proxy = _ScalarLogger(Logger())
    proxy.report_scalar("train", "loss", 1.25, 2)
    proxy.report_image("Mosaic")
    assert images == ["Mosaic"]
    record = json.loads(capture.paths["scalars"].read_text())
    assert record == {"title": "train", "series": "loss", "value": 1.25, "iteration": 2}


def test_image_progress_counts_partial_last_batch_and_closes_failed_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.observability import progress

    updates: list[int] = []
    closed: list[bool] = []

    class Bar:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["total"] == 5

        def update(self, count: int) -> None:
            updates.append(count)

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(progress, "terminal_isatty", lambda: True)
    monkeypatch.setattr(progress, "tqdm", Bar)
    with progress.image_progress(5) as advance:
        advance(3)
        advance(2)
    assert updates == [3, 2]
    assert closed == [True]
    original = ValueError("batch failed")

    def fail_batch() -> None:
        with progress.image_progress(5) as advance:
            advance(3)
            raise original

    with pytest.raises(ValueError, match="batch failed") as caught:
        fail_batch()
    assert caught.value is original
    assert closed == [True, True]


def test_local_progress_merges_task_url_and_epoch_without_queue_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.observability.capture import (
        OutputCapture,
        append_scalar,
        write_progress,
    )

    capture = OutputCapture(tmp_path / "capture")
    capture.prepare()
    status = tmp_path / "status.json"
    monkeypatch.setenv("CY_PROGRESS_FILE", str(status))
    monkeypatch.setenv("CY_SCALAR_JOURNAL", str(capture.paths["scalars"]))
    write_progress(task_url="https://clearml.example/tasks/task-id")
    assert append_scalar("train", "loss", 1.25, 3)
    values = json.loads(status.read_text())
    assert values["task_url"] == "https://clearml.example/tasks/task-id"
    assert values["progress"] == "Training step 3"
    assert stat.S_IMODE(status.stat().st_mode) == 0o600
