"""Prepared datasets are reused atomically under per-entry consumer locks."""

import csv
import hashlib
import json
import multiprocessing
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol

import pytest
import yaml
from PIL import Image


def _process_cache_consumer(
    source: str,
    cache_dir: str,
    copy_log: str,
    ready: Any,
    start: Any,
    results: Any,
) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    original_copy = shutil.copyfile

    def counted_copy(source_path: Any, target_path: Any) -> Any:
        with Path(copy_log).open("a", encoding="utf-8") as stream:
            stream.write("copy\n")
        return original_copy(source_path, target_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(shutil, "copyfile", counted_copy)
        ready.set()
        if not start.wait(timeout=10):
            results.put({"error": "start timeout"})
            return
        try:
            with cached_dataset(source, cache_dir) as prepared:
                entered = time.monotonic_ns()
                time.sleep(0.2)
                leaving = time.monotonic_ns()
                root = str(prepared.data.parent)
            results.put({"root": root, "entered": entered, "leaving": leaving})
        except Exception as error:  # noqa: BLE001 - serialize child failures for assertion.
            results.put({"error": repr(error)})


def _process_interrupted_builder(
    source: str,
    cache_dir: str,
    staging_ready: Any,
) -> None:
    import clearml_yolo.dataset_cache as cache

    def stall_in_staging(*args: Any, **kwargs: Any) -> Any:
        staging = Path(args[1])
        staging.mkdir(parents=True)
        (staging / "partial.txt").write_text("partial", encoding="utf-8")
        staging_ready.set()
        while True:
            time.sleep(1)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(cache, "prepare_dataset", stall_in_staging)
        with cache.cached_dataset(source, cache_dir):
            pass


class _ManagedProcess(Protocol):
    def is_alive(self) -> bool: ...

    def terminate(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...


def _terminate_process(process: _ManagedProcess) -> None:
    if process.is_alive():
        process.terminate()
    process.join(timeout=5)


def _source(directory: Path, *, include_test: bool = False) -> Path:
    directory.mkdir(parents=True)
    fields = [
        "image_name",
        "image_path",
        "instance_label",
        "bbox_x_tl",
        "bbox_y_tl",
        "bbox_x_br",
        "bbox_y_br",
        "split",
    ]
    source = directory / "truth.csv"
    splits = ["train", "val"] + (["test"] if include_test else [])
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        for split in splits:
            image = directory / f"{split}.PNG"
            Image.new("RGB", (16, 12), (20, 30, 40)).save(image)
            writer.writerow([image.name, image.name, "cat", 1, 2, 10, 9, split])
    return source


def test_cache_hit_reuses_completed_files_without_preparation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.dataset_cache as cache

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with cache.cached_dataset(source, cache_dir) as first:
        first_root = first.data.parent

    monkeypatch.setattr(
        cache,
        "prepare_dataset",
        lambda *args, **kwargs: pytest.fail("cache hit must not validate, copy, or convert images"),
    )
    with cache.cached_dataset(source, cache_dir) as second:
        assert second.data.parent == first_root
        assert second.data.is_file()


def test_changed_csv_bytes_or_format_create_distinct_entries(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with cached_dataset(source, cache_dir, "ndjson") as first:
        ndjson_root = first.data.parent
    with cached_dataset(source, cache_dir, "flat") as flat:
        flat_root = flat.data.parent
    source.write_bytes(source.read_bytes() + b"\n")
    with cached_dataset(source, cache_dir, "ndjson") as changed:
        changed_root = changed.data.parent

    assert len({ndjson_root, flat_root, changed_root}) == 3


def test_identical_csv_bytes_at_another_path_reuse_one_entry(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    moved = tmp_path / "copy" / "truth.csv"
    moved.parent.mkdir()
    moved.write_bytes(source.read_bytes())
    cache_dir = tmp_path / "cache"

    with cached_dataset(source, cache_dir) as first:
        first_root = first.data.parent
    with cached_dataset(moved, cache_dir) as second:
        assert second.data.parent == first_root


def test_concurrent_requests_build_once_and_serialize_consumers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    original_copy = shutil.copyfile
    copy_count = 0
    copy_guard = threading.Lock()
    consumer_active = 0
    max_consumer_active = 0
    start = threading.Barrier(2)

    def counted_copy(source_path: Any, target_path: Any) -> Any:
        nonlocal copy_count
        with copy_guard:
            copy_count += 1
        time.sleep(0.02)
        return original_copy(source_path, target_path)

    def consume() -> Path:
        nonlocal consumer_active, max_consumer_active
        start.wait()
        with cached_dataset(source, cache_dir) as prepared:
            with copy_guard:
                consumer_active += 1
                max_consumer_active = max(max_consumer_active, consumer_active)
            time.sleep(0.04)
            with copy_guard:
                consumer_active -= 1
            return prepared.data.parent

    monkeypatch.setattr(shutil, "copyfile", counted_copy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        roots = list(executor.map(lambda _: consume(), range(2)))

    assert roots[0] == roots[1]
    assert copy_count == 2
    assert max_consumer_active == 1


def test_different_entries_can_be_consumed_concurrently(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    first_source = _source(tmp_path / "first")
    second_source = _source(tmp_path / "second")
    second_source.write_bytes(second_source.read_bytes() + b"\n")
    cache_dir = tmp_path / "cache"
    ready = threading.Barrier(2, timeout=5)

    def consume(source: Path) -> None:
        with cached_dataset(source, cache_dir):
            ready.wait()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(consume, source) for source in (first_source, second_source)]
        for future in futures:
            future.result(timeout=10)


def test_separate_processes_build_once_and_serialize_consumers(tmp_path: Path) -> None:
    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    copy_log = tmp_path / "copies.txt"
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    ready = [context.Event(), context.Event()]
    results = context.Queue()
    processes = [
        context.Process(
            target=_process_cache_consumer,
            args=(str(source), str(cache_dir), str(copy_log), ready[index], start, results),
        )
        for index in range(2)
    ]

    try:
        for process in processes:
            process.start()
        assert all(event.wait(timeout=10) for event in ready)
        start.set()
        for process in processes:
            process.join(timeout=15)
        assert [process.exitcode for process in processes] == [0, 0]
        observations = [results.get(timeout=5), results.get(timeout=5)]
    finally:
        for process in processes:
            _terminate_process(process)
        results.close()
        results.join_thread()

    assert all("error" not in observation for observation in observations)
    assert len({observation["root"] for observation in observations}) == 1
    intervals = sorted(
        (observation["entered"], observation["leaving"]) for observation in observations
    )
    assert intervals[1][0] >= intervals[0][1]
    assert copy_log.read_text(encoding="utf-8").splitlines() == ["copy", "copy"]
    assert len([path for path in cache_dir.iterdir() if not path.name.startswith(".")]) == 1


def test_terminated_builder_leaves_no_consumable_partial_entry(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    context = multiprocessing.get_context("spawn")
    staging_ready = context.Event()
    process = context.Process(
        target=_process_interrupted_builder,
        args=(str(source), str(cache_dir), staging_ready),
    )

    try:
        process.start()
        assert staging_ready.wait(timeout=10)
        process.terminate()
        process.join(timeout=5)
        assert process.exitcode is not None
        assert process.exitcode != 0
    finally:
        _terminate_process(process)

    assert list(cache_dir.glob(".*.staging-*"))
    with cached_dataset(source, cache_dir) as prepared:
        assert prepared.data.is_file()
    assert not list(cache_dir.glob(".*.staging-*"))
    assert len([path for path in cache_dir.iterdir() if not path.name.startswith(".")]) == 1


def test_failed_build_is_cleaned_and_retry_can_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.dataset_cache as cache

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    from clearml_yolo.dataset import prepare_dataset as original_prepare

    attempts = 0

    def fail_once(*args: Any, **kwargs: Any) -> Any:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            staging = Path(args[1])
            staging.mkdir(parents=True)
            (staging / "partial.txt").write_text("partial")
            raise RuntimeError("interrupted")
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(cache, "prepare_dataset", fail_once)
    with pytest.raises(RuntimeError, match="interrupted"), cache.cached_dataset(source, cache_dir):
        pass

    assert not list(cache_dir.glob(".*.staging-*"))
    with cache.cached_dataset(source, cache_dir) as prepared:
        assert prepared.data.is_file()
    assert attempts == 2


def test_corrupt_complete_entry_is_rebuilt_under_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.dataset_cache as cache

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with cache.cached_dataset(source, cache_dir) as first:
        first.ground_truth.unlink()
        root = first.data.parent

    from clearml_yolo.dataset import prepare_dataset as original_prepare

    rebuilds = 0

    def counted_prepare(*args: Any, **kwargs: Any) -> Any:
        nonlocal rebuilds
        rebuilds += 1
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(cache, "prepare_dataset", counted_prepare)
    with cache.cached_dataset(source, cache_dir) as rebuilt:
        assert rebuilt.data.parent == root
        assert rebuilt.ground_truth.is_file()
    assert rebuilds == 1


def test_csv_change_during_preparation_uses_the_bytes_that_defined_the_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.dataset_cache as cache

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    from clearml_yolo.dataset import prepare_dataset as original_prepare

    original_bytes = source.read_bytes()

    def prepare_changed_source(*args: Any, **kwargs: Any) -> Any:
        source.write_bytes(source.read_bytes() + b"\n")
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(cache, "prepare_dataset", prepare_changed_source)
    with cache.cached_dataset(source, cache_dir) as prepared:
        first_root = prepared.data.parent
        manifest = json.loads(prepared.manifest.read_text(encoding="utf-8"))

    assert manifest["input_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    monkeypatch.setattr(cache, "prepare_dataset", original_prepare)
    with cache.cached_dataset(source, cache_dir) as changed:
        assert changed.data.parent != first_root


def test_completion_paths_are_final_and_requested_splits_are_validated(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input", include_test=True)
    cache_dir = tmp_path / "cache"
    with cached_dataset(source, cache_dir, required_splits=("train", "val", "test")) as prepared:
        root = prepared.data.parent
        config = yaml.safe_load(prepared.data.read_text())
        preparation = json.loads(prepared.manifest.read_text())
        completion = json.loads((root / "completion.json").read_text())

    assert config["path"] == str(root)
    assert all(str(root) in item["generated_path"] for item in preparation["images"])
    assert completion["split_counts"] == {"test": 1, "train": 1, "val": 1}
    assert all(not Path(path).is_absolute() for path in completion["required_files"])


def test_missing_requested_split_fails_without_complete_entry(tmp_path: Path) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    cache_dir = tmp_path / "cache"
    with (
        pytest.raises(ValueError, match=r"test"),
        cached_dataset(source, cache_dir, required_splits=("train", "val", "test")),
    ):
        pass

    assert not any(path.is_dir() and not path.name.startswith(".") for path in cache_dir.iterdir())


def test_default_cache_root_uses_workspace_despite_xdg_cache_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CACHE_HOME", str(xdg))
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))

    with cached_dataset(source) as prepared:
        assert prepared.data.is_relative_to(
            tmp_path / "workspace" / ".cache" / "clearml-yolo" / "datasets"
        )
    assert not xdg.exists()


@pytest.mark.parametrize("corruption", [{"train": "images/missing"}, {"names": {}}])
def test_cache_rebuilds_invalid_native_yaml(tmp_path: Path, corruption: dict[str, Any]) -> None:
    from clearml_yolo.dataset_cache import cached_dataset

    source = _source(tmp_path / "input")
    with cached_dataset(source, tmp_path / "cache") as first:
        valid = yaml.safe_load(first.data.read_text())
        first.data.write_text(yaml.safe_dump(valid | corruption))
    with cached_dataset(source, tmp_path / "cache") as reused:
        assert yaml.safe_load(reused.data.read_text()) == valid


def test_dataset_cache_missing_metadata_is_quiet_but_permission_failure_diagnosed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from loguru import logger

    from clearml_yolo.dataset_cache import _read_json_object

    source = tmp_path / "preparation.json"
    messages: list[str] = []
    sink = logger.add(messages.append, level="DEBUG", format="{message}")
    try:
        assert _read_json_object(source) is None
        assert messages == []

        def denied(*args: Any, **kwargs: Any) -> str:
            raise PermissionError("cache file access denied")

        monkeypatch.setattr(Path, "read_text", denied)
        assert _read_json_object(source) is None
    finally:
        logger.remove(sink)
    output = "".join(messages)
    assert "PermissionError" in output
    assert "cache file access denied" in output
    assert str(source) in output
