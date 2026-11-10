"""Editable batch selection and atomic publication exercise product storage."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    GPUHardware,
    SearchSettings,
    SyntheticWorkload,
    TrialResult,
)
from clearml_yolo.core.batch_sizes import gpu_label
from test_batch_estimate_workflow import sample_profile

_GIB = 1024**3
_MODEL = "ultralytics/yolo11n"


def _gpu(name: str = "GPU", memory: int = 24 * _GIB) -> GPUHardware:
    return GPUHardware(name=name, total_memory_bytes=memory)


def _case(capacity: int = 8, *, gpu: GPUHardware | None = None, size: int = 960) -> EstimateCase:
    gpu = gpu or _gpu()
    profile = sample_profile().model_copy(
        update={"gpus": (gpu,), "nominal_size": (size, size), "effective_size": (size, size)}
    )
    settings = SearchSettings(max_global_batch=32)
    search = BatchSearch.start(profile, settings)
    while search.next_batch is not None:
        search = search.observe(
            TrialResult(
                global_batch=search.next_batch,
                actual_global_batch=search.next_batch,
                status="success" if search.next_batch <= capacity else "oom",
                trial_id=f"trial-{len(search.trials)}",
                peak_memory_bytes=(gpu.total_memory_bytes // 2,),
                warmup_steps=settings.warmup_steps,
                measured_steps=settings.measured_steps,
                validation_steps=1,
                optimizer_paths=profile.optimizers,
            )
        )
    return EstimateCase(
        profile=profile,
        workload=SyntheticWorkload(),
        settings=settings,
        status=search.status,
        global_batch=search.global_batch,
        per_gpu_batch=search.per_gpu_batch,
        trials=search.trials,
        created_at="2026-11-10T00:00:00Z",
        diagnostic=search.diagnostic,
    )


def test_missing_table_is_inert_and_default_path_is_project_local(tmp_path: Path) -> None:
    store = BatchSizeStore()
    assert store.path == tmp_path / ".config/clearml-yolo/batch-sizes.yaml"
    assert not store.load().entries
    assert not store.path.parent.exists()


@pytest.mark.parametrize("batch", [1, 3, 7, 8, 13, 64])
def test_manual_positive_batches_and_exact_precedence(tmp_path: Path, batch: int) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(
        f'"GPU [24 GiB]":\n  960:\n    {_MODEL}: {batch}\n"Other [24 GiB]":\n  960:\n    {_MODEL}: 1\n'
    )
    selected = store.load().resolve(_gpu(), 960, _MODEL)
    assert selected.per_gpu_batch == batch
    assert not selected.fallback
    assert selected.entry.origin == "manual"


def test_fallback_prefers_capacity_then_smallest_batch_then_name(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(
        f"A [12 GiB]:\n  960:\n    {_MODEL}: 2\nZ [16 GiB]:\n  960:\n    {_MODEL}: 8\n"
        f"B [16 GiB]:\n  960:\n    {_MODEL}: 3\nA [16 GiB]:\n  960:\n    {_MODEL}: 3\n"
        f"Huge [32 GiB]:\n  960:\n    {_MODEL}: 1\n"
    )
    snapshot = store.load()
    assert snapshot.exact(_gpu(), 960, _MODEL) is None
    selected = snapshot.resolve(_gpu(), 960, _MODEL)
    assert selected.fallback
    assert selected.entry.gpu_name == "A"
    assert selected.entry.total_memory_bytes == 16 * _GIB
    assert selected.per_gpu_batch == 3
    with pytest.raises(ValueError, match="No batch table"):
        snapshot.resolve(_gpu(), 640, _MODEL)
    with pytest.raises(ValueError, match="No batch table"):
        snapshot.resolve(_gpu(memory=8 * _GIB), 960, _MODEL)


def test_precise_generated_capacity_and_literal_manual_capacity(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    source = _gpu(memory=24 * _GIB - 1000)
    store.publish((_case(gpu=source),))
    snapshot = store.load()
    assert snapshot.resolve(source, 960, _MODEL).fallback is False
    assert snapshot.entries[0].total_memory_bytes == source.total_memory_bytes
    assert snapshot.entries[0].origin == "measurement"
    with pytest.raises(ValueError, match="No batch table"):
        snapshot.resolve(_gpu("Target", source.total_memory_bytes - 1), 960, _MODEL)
    store.path.write_text(f"Manual [23.5 GiB]:\n  960:\n    {_MODEL}: 5\n")
    assert store.load().entries[0].total_memory_bytes == int(23.5 * _GIB)


def test_publish_preserves_comments_unrelated_entries_and_detects_manual_edit(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(
        f"# user guidance\nGPU [24 GiB]: # my card\n  960:\n    {_MODEL}: 3 # conservative\n    rfdetr/small: 2\n"
    )
    store.publish((_case(16),))
    payload = store.path.read_text()
    assert "# user guidance" in payload
    assert "# my card" in payload
    assert "# conservative" in payload
    assert "rfdetr/small: 2" in payload
    before = store.load()
    assert before.resolve(_gpu(), 960, _MODEL).per_gpu_batch == 16
    store.path.write_text(payload.replace(f"{_MODEL}: 16", f"{_MODEL}: 7"))
    after = store.load()
    assert after.digest != before.digest
    assert after.resolve(_gpu(), 960, _MODEL).entry.origin == "manual"
    assert after.resolve(_gpu(), 960, _MODEL).per_gpu_batch == 7


def test_missing_only_publication_preserves_exact_and_never_treats_fallback_as_coverage(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.publish((_case(8, gpu=_gpu("Other", 16 * _GIB)),))
    assert store.load().resolve(_gpu(), 960, _MODEL).fallback
    store.publish((_case(16),), replace=False)
    assert not store.load().resolve(_gpu(), 960, _MODEL).fallback
    store.publish((_case(8),), replace=False)
    assert store.load().resolve(_gpu(), 960, _MODEL).per_gpu_batch == 16


def test_refresh_uses_smallest_current_result_not_historical(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.publish((_case(8),))
    store.publish((_case(32), _case(16)))
    assert store.load().resolve(_gpu(), 960, _MODEL).per_gpu_batch == 16


def test_no_capacity_blocks_fallback_manual_override_and_success_clears_marker(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.publish((_case(8), _case(8, gpu=_gpu("Other", 16 * _GIB))))
    store.publish((_case(0),))
    snapshot = store.load()
    assert snapshot.exact(_gpu(), 960, _MODEL) is None
    assert len(snapshot.failures) == 1
    with pytest.raises(ValueError, match="no_capacity"):
        snapshot.resolve(_gpu(), 960, _MODEL)
    payload = store.path.read_text()
    store.path.write_text(payload.replace("960: {}", f"960:\n    {_MODEL}: 3"))
    assert store.load().resolve(_gpu(), 960, _MODEL).per_gpu_batch == 3
    assert store.load().resolve(_gpu(), 960, _MODEL).entry.origin == "manual"
    store.publish((_case(16),))
    assert not store.load().failures
    assert store.load().resolve(_gpu(), 960, _MODEL).per_gpu_batch == 16


@pytest.mark.parametrize("status", ["timeout", "cancelled", "error"])
def test_unsuccessful_refresh_preserves_bytes(tmp_path: Path, status: str) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    case = _case()
    store.publish((case,))
    previous = store.path.read_bytes()
    failed = EstimateCase.model_validate(
        case.model_dump()
        | {"status": "failed", "global_batch": None, "per_gpu_batch": None, "trials": [], "diagnostic": status}
    )
    store.publish((failed,))
    assert store.path.read_bytes() == previous


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        "null",
        "broken: [",
        "GPU [24 GiB]: {}\nGPU [24 GiB]: {}\n",
        f"GPU [24 GiB]:\n  960:\n    {_MODEL}: 3\n    {_MODEL}: 4\n",
        f"GPU [24 GiB]:\n  960:\n    {_MODEL}: 0\n",
        f"GPU [24 GiB]:\n  960:\n    {_MODEL}: true\n",
        f"GPU [24 GiB]:\n  960:\n    {_MODEL}: 2.5\n",
        f'GPU [24 GiB]:\n  "960":\n    {_MODEL}: 3\n',
        "GPU [24 GiB]:\n  960:\n    unknown/model: 3\n",
        '# clearml-yolo-batch-metadata: {"schema_version":2}\n',
    ],
)
def test_malformed_table_rejected_without_overwrite(tmp_path: Path, payload: str) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(payload)
    with pytest.raises(ValueError, match="Invalid batch size table"):
        store.load()
    with pytest.raises(ValueError, match="Invalid batch size table"):
        store.publish((_case(),))
    assert store.path.read_text() == payload


def test_concurrent_updates_preserve_peer_entries(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    cases = tuple(_case(gpu=_gpu(f"GPU {index}")) for index in range(8))
    with ThreadPoolExecutor(max_workers=4) as executor:
        tuple(executor.map(lambda case: BatchSizeStore(store.path).publish((case,)), cases))
    assert {entry.gpu_name for entry in store.load().entries} == {f"GPU {index}" for index in range(8)}
    assert not tuple(tmp_path.glob(".batch-sizes-*.tmp"))


def test_replacement_failure_preserves_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.publish((_case(),))
    before = store.path.read_bytes()

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("replacement interrupted")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="interrupted"):
        store.publish((_case(16),))
    assert store.path.read_bytes() == before
    assert not tuple(tmp_path.glob(".batch-sizes-*.tmp"))


def test_rounded_label_collision_keeps_both_precise_devices(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    first, second = _gpu(memory=24 * _GIB - 1000), _gpu(memory=24 * _GIB - 2000)
    assert gpu_label(first) == gpu_label(second)
    store.publish((_case(8, gpu=first),))
    store.publish((_case(16, gpu=second),))
    table = store.load()
    assert len(table.entries) == 2
    assert table.resolve(first, 960, _MODEL).per_gpu_batch == 8
    assert table.resolve(second, 960, _MODEL).per_gpu_batch == 16


def test_generated_rounded_label_does_not_overwrite_literal_manual_capacity(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(f"GPU [24 GiB]:\n  960:\n    {_MODEL}: 3\n")
    gpu = _gpu(memory=24 * _GIB - 1000)
    store.publish((_case(16, gpu=gpu),))
    table = store.load()
    assert len(table.entries) == 2
    assert table.resolve(_gpu(), 960, _MODEL).per_gpu_batch == 3
    assert table.resolve(gpu, 960, _MODEL).per_gpu_batch == 16


def test_refresh_replaces_all_exact_aliases(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(f"GPU [24 GiB]:\n  960:\n    {_MODEL}: 3\nGPU [24.0 GiB]:\n  960:\n    {_MODEL}: 5\n")
    store.publish((_case(16),))
    assert store.load().resolve(_gpu(), 960, _MODEL).per_gpu_batch == 16
    assert {entry.per_gpu_batch for entry in store.load().entries} == {16}


def test_unconfirmed_copied_case_is_rejected(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    case = _case()
    with pytest.raises(ValueError, match="evidence"):
        store.publish((case.model_copy(update={"trials": case.trials[:-1]}),))
    assert not store.path.exists()


@pytest.mark.parametrize("capacity", [0, 16])
def test_publication_does_not_mutate_unrelated_yaml_aliases(tmp_path: Path, capacity: int) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    store.path.write_text(
        f"GPU [24 GiB]: &gpu\n  960: &batches\n    {_MODEL}: 3 # retain\n  640: *batches\nOther [24 GiB]: *gpu\n"
    )
    store.publish((_case(capacity),))
    table = store.load()
    assert table.resolve(_gpu(), 640, _MODEL).per_gpu_batch == 3
    assert table.resolve(_gpu("Other"), 960, _MODEL).per_gpu_batch == 3
    assert table.resolve(_gpu("Other"), 640, _MODEL).per_gpu_batch == 3
    assert "# retain" in store.path.read_text()
    if capacity:
        assert table.resolve(_gpu(), 960, _MODEL).per_gpu_batch == capacity
    else:
        with pytest.raises(ValueError, match="no_capacity"):
            table.resolve(_gpu(), 960, _MODEL)


def test_forced_evidence_is_visible_but_manual_override_does_not_claim_it(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    case = _case()
    forced = case.model_copy(update={"settings": case.settings.model_copy(update={"force": True})})
    store.publish((forced,))
    assert store.load().resolve(_gpu(), 960, _MODEL).entry.forced
    store.path.write_text(store.path.read_text().replace(f"{_MODEL}: 8", f"{_MODEL}: 3"))
    manual = store.load().resolve(_gpu(), 960, _MODEL).entry
    assert manual.origin == "manual"
    assert manual.forced is False
    store.publish((case,))
    assert store.load().resolve(_gpu(), 960, _MODEL).entry.forced is False


def test_distinct_rows_retain_their_own_measurement_provenance(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    first = _case(8)
    first = first.model_copy(update={"settings": first.settings.model_copy(update={"force": True})})
    second = _case(32, gpu=_gpu("Other"))
    store.publish((first, second))

    table = store.load()
    first_entry = table.resolve(_gpu(), 960, _MODEL).entry
    second_entry = table.resolve(_gpu("Other"), 960, _MODEL).entry
    assert first_entry.per_gpu_batch == 8
    assert first_entry.origin == "measurement"
    assert first_entry.forced is True
    assert first_entry.source_status == "validated"
    assert second_entry.per_gpu_batch == 32
    assert second_entry.origin == "measurement"
    assert second_entry.forced is False
    assert second_entry.source_status == "ceiling_limited"
    assert first_entry.source_estimate_key is not None
    assert second_entry.source_estimate_key is not None
    assert first_entry.source_estimate_key != second_entry.source_estimate_key


def test_saved_v1_compact_metadata_keys_preserve_measurement_provenance(tmp_path: Path) -> None:
    store = BatchSizeStore(tmp_path / "table.yaml")
    # A persisted document is intentionally independent of the current writer:
    # changes to metadata-key encoding must not silently discard saved evidence.
    payload = (
        "GPU [24 GiB]:\n  960:\n    ultralytics/yolo11n: 3\n"
        '# clearml-yolo-batch-metadata: {"schema_version": 1, '
        '"capacities": {"GPU [24 GiB]": 25769803776}, '
        r'"measured": {"[\"GPU [24 GiB]\",960,\"ultralytics/yolo11n\"]": 3}, '
        r'"forced": {"[\"GPU [24 GiB]\",960,\"ultralytics/yolo11n\"]": true}, '
        r'"sources": {"[\"GPU [24 GiB]\",960,\"ultralytics/yolo11n\"]": '
        '{"status": "numerically_limited", "diagnostic": "Larger batch produced nonfinite loss", '
        '"estimate_key": "saved-measurement-key"}}, "failures": []}\n'
    )
    store.path.write_text(payload)

    entry = store.load().resolve(_gpu(), 960, _MODEL).entry
    assert entry.per_gpu_batch == 3
    assert entry.origin == "measurement"
    assert entry.forced is True
    assert entry.source_status == "numerically_limited"
    assert entry.source_diagnostic == "Larger batch produced nonfinite loss"
    assert entry.source_estimate_key == "saved-measurement-key"
    assert store.path.read_text() == payload
