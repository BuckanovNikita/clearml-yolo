"""Storage diagnostics distinguish cache waits and retain consumer lock lifetime."""

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from filelock import FileLock, Timeout
from loguru import logger

from clearml_yolo.adapters.storage.dataset_cache import cached_dataset
from clearml_yolo.adapters.storage.file_io import read_csv, read_text, write_csv, write_text
from clearml_yolo.adapters.storage.identity import checkpoint_sha256
from clearml_yolo.adapters.storage.native_archive import archive_native_outputs
from test_dataset_cache import _source


@pytest.fixture
def trace_messages(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(message.record["message"]), level="TRACE")
    try:
        yield messages
    finally:
        logger.remove(sink)


def test_cache_acquisition_finishes_before_yield_and_lock_lifetime_outlives_consumer(
    tmp_path: Path, trace_messages: list[str]
) -> None:
    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with cached_dataset(source, cache_dir) as prepared:
        assert prepared.data.is_file()
        assert any(
            message.startswith("DONE storage.cache.lock.acquire ") for message in trace_messages
        )
        assert not any(
            message.startswith("DONE storage.cache.lock.lifetime ") for message in trace_messages
        )
        lock_path = next((cache_dir / ".locks").glob("*.lock"))
        with pytest.raises(Timeout), FileLock(lock_path, timeout=0):
            pytest.fail("Native-consumer lock must remain held across yield")
    assert any(
        message.startswith("DONE storage.cache.lock.lifetime ") for message in trace_messages
    )
    with FileLock(lock_path, timeout=0):
        pass


def test_cache_hit_avoids_export_and_consumer_error_releases_lock(
    tmp_path: Path, trace_messages: list[str]
) -> None:
    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with cached_dataset(source, cache_dir):
        pass
    assert any(message.startswith("START storage.cache.miss ") for message in trace_messages)
    assert (
        sum(message.startswith("START storage.dataset.materialize ") for message in trace_messages)
        == 1
    )
    trace_messages.clear()
    original = ValueError("token=private-consumer-token")
    with (
        pytest.raises(ValueError, match="private-consumer-token") as caught,
        cached_dataset(source, cache_dir),
    ):
        raise original
    assert caught.value is original
    assert any(message.startswith("DONE storage.cache.hit ") for message in trace_messages)
    assert any(
        message.startswith("FAILED storage.cache.lock.lifetime ") for message in trace_messages
    )
    assert not any(
        message.startswith("START storage.dataset.export ") for message in trace_messages
    )
    assert all("private-consumer-token" not in message for message in trace_messages)
    with FileLock(next((cache_dir / ".locks").glob("*.lock")), timeout=0):
        pass


def test_file_io_returns_original_contents_and_logs_only_scalar_shape(
    tmp_path: Path, trace_messages: list[str]
) -> None:
    text = tmp_path / "notes.txt"
    write_text(text, "token=private-text-token")
    assert read_text(text) == "token=private-text-token"
    csv = tmp_path / "rows.csv"
    frame = pd.DataFrame({"label": ["private-row-value"], "value": [0.25]})
    write_csv(frame, csv)
    pd.testing.assert_frame_equal(read_csv(csv), frame)
    assert any(
        message.startswith("DONE storage.csv.write ") and "rows=1 columns=2" in message
        for message in trace_messages
    )
    assert all("private-text-token" not in message for message in trace_messages)
    assert all("private-row-value" not in message for message in trace_messages)


def test_missing_read_and_checkpoint_hash_preserve_failure_contract(
    tmp_path: Path, trace_messages: list[str]
) -> None:
    path = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        read_text(path)
    assert any(message.startswith("FAILED storage.text.read ") for message in trace_messages)
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"checkpoint bytes")
    assert checkpoint_sha256(checkpoint) == hashlib.sha256(b"checkpoint bytes").hexdigest()
    assert any(message.startswith("DONE storage.checkpoint.hash ") for message in trace_messages)


def test_native_archive_has_one_aggregate_span_for_many_files(
    tmp_path: Path, trace_messages: list[str]
) -> None:
    source = tmp_path / "native"
    source.mkdir()
    for index in range(12):
        (source / f"{index}.txt").write_text("content", encoding="utf-8")
    destination = tmp_path / "artifacts"
    destination.mkdir()
    path = archive_native_outputs(source, destination, role="prediction", split="val")
    assert path.is_file()
    assert (
        sum(message.startswith("START storage.native.archive ") for message in trace_messages) == 1
    )


def test_storage_is_silent_without_trace_opt_in(
    tmp_path: Path, trace_messages: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "DEBUG")
    path = tmp_path / "notes.txt"
    write_text(path, "contents")
    assert read_text(path) == "contents"
    assert trace_messages == []


def test_lock_acquisition_failure_is_distinct_from_consumer_lifetime(
    tmp_path: Path, trace_messages: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.adapters.storage.dataset_cache as cache

    source = _source(tmp_path / "input")
    original = Timeout("controlled-cache.lock")

    class FailedLock:
        def __enter__(self) -> None:
            raise original

        def __exit__(self, *args: object) -> None:
            pytest.fail("Failed acquisition must not attempt lock exit")

    monkeypatch.setattr(cache, "FileLock", lambda path: FailedLock())
    with pytest.raises(Timeout) as caught, cached_dataset(source, tmp_path / "cache"):
        pytest.fail("Cache lock failure must precede consumer entry")
    assert caught.value is original
    assert any(
        message.startswith("FAILED storage.cache.lock.acquire ") for message in trace_messages
    )
    assert not any(
        message.startswith("START storage.cache.lock.lifetime ") for message in trace_messages
    )
