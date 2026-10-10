"""Publication traces distinguish waiting, writes and optional backend failures."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from filelock import FileLock
from loguru import logger

from clearml_yolo.adapters.fiftyone import publisher as module
from clearml_yolo.core.publication import FiftyOneConfig, PublicationRequest


def test_preflight_failure_has_trace_without_changing_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda record: messages.append(str(record)), level="TRACE")

    def unavailable() -> Any:
        raise ImportError("missing optional backend")

    monkeypatch.setattr(module, "_backend", unavailable)
    try:
        with pytest.raises(RuntimeError, match="requires the project dependencies"):
            module.FiftyOnePublisher(FiftyOneConfig()).preflight()
    finally:
        logger.remove(sink)
    assert any("START fiftyone.backend.import" in line for line in messages)
    assert any("FAILED fiftyone.backend.import" in line for line in messages)


def test_publication_records_lock_and_aggregate_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda record: messages.append(str(record)), level="TRACE")
    snapshot = SimpleNamespace(images={}, sha256="truth", membership={})
    dataset = SimpleNamespace(info={}, save=lambda: None, add_dynamic_sample_fields=lambda: None)
    monkeypatch.setattr(module, "read_snapshot", lambda _: snapshot)
    monkeypatch.setattr(module, "read_predictions", lambda *_: {})
    monkeypatch.setattr(module, "prediction_aliases", lambda *_: {})
    monkeypatch.setattr(
        module, "_backend", lambda: SimpleNamespace(config=SimpleNamespace(database_dir=tmp_path))
    )
    monkeypatch.setattr(module, "_dataset", lambda *_: (dataset, False))
    monkeypatch.setattr(module, "_remove_evaluations", lambda *_: None)
    monkeypatch.setattr(module, "_write_run", lambda *_: None)
    monkeypatch.setattr(module, "_publish_evaluations", lambda *_: {})
    try:
        receipt = module.FiftyOnePublisher(FiftyOneConfig()).publish(
            PublicationRequest(task_id="trace-task", ground_truth=tmp_path / "truth.csv")
        )
    finally:
        logger.remove(sink)
    assert receipt.run_complete
    for operation in (
        "snapshot",
        "predictions",
        "lock.acquire",
        "dataset",
        "run.start.save",
        "overlays.write",
        "run.complete.save",
    ):
        assert any(f"START fiftyone.{operation}" in line for line in messages)
        assert any(f"DONE fiftyone.{operation}" in line for line in messages)
    acquisition = next(
        index for index, line in enumerate(messages) if "DONE fiftyone.lock.acquire" in line
    )
    writing = next(index for index, line in enumerate(messages) if "START fiftyone.dataset" in line)
    assert acquisition < writing


def test_failed_dataset_write_releases_publication_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    snapshot = SimpleNamespace(images={}, sha256="truth", membership={})
    monkeypatch.setattr(module, "read_snapshot", lambda _: snapshot)
    monkeypatch.setattr(module, "read_predictions", lambda *_: {})
    monkeypatch.setattr(module, "prediction_aliases", lambda *_: {})
    monkeypatch.setattr(
        module,
        "_backend",
        lambda: SimpleNamespace(config=SimpleNamespace(database_dir=tmp_path)),
    )
    original = RuntimeError("dataset unavailable")

    def unavailable(*_: object) -> Any:
        raise original

    monkeypatch.setattr(module, "_dataset", unavailable)
    with pytest.raises(RuntimeError) as failure:
        module.FiftyOnePublisher(FiftyOneConfig()).publish(
            PublicationRequest(task_id="trace-task", ground_truth=tmp_path / "truth.csv")
        )
    assert failure.value is original
    lock_path = next((tmp_path / "clearml-yolo-locks").glob("*.lock"))
    with FileLock(lock_path, timeout=0):
        pass


def test_interrupted_lock_completion_releases_publication_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    snapshot = SimpleNamespace(images={}, sha256="truth", membership={})
    monkeypatch.setattr(module, "read_snapshot", lambda _: snapshot)
    monkeypatch.setattr(module, "read_predictions", lambda *_: {})
    monkeypatch.setattr(module, "prediction_aliases", lambda *_: {})
    monkeypatch.setattr(
        module, "_backend", lambda: SimpleNamespace(config=SimpleNamespace(database_dir=tmp_path))
    )
    owned_lock = FileLock(tmp_path / "owned.lock")
    monkeypatch.setattr(module, "FileLock", lambda _: owned_lock)

    def interrupt(message: object) -> None:
        if "DONE fiftyone.lock.acquire " in str(message):
            raise KeyboardInterrupt

    sink = logger.add(interrupt, level="TRACE", catch=False)
    try:
        with pytest.raises(KeyboardInterrupt):
            module.FiftyOnePublisher(FiftyOneConfig()).publish(
                PublicationRequest(task_id="trace-task", ground_truth=tmp_path / "truth.csv")
            )
        assert not owned_lock.is_locked
        with FileLock(owned_lock.lock_file, timeout=0):
            pass
    finally:
        logger.remove(sink)
        owned_lock.release()
