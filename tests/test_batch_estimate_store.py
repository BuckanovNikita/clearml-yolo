"""Atomic cache replacement never discards peer cases or overwrites corruption."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.core.batch_estimation import EstimateCase, EstimateCatalogue
from test_batch_estimate_workflow import sample_case


def test_default_path_and_missing_cache_are_local_and_inert(tmp_path: Path) -> None:
    store = FileBatchEstimateStore()
    assert store.path == tmp_path / ".config/clearml-yolo/batch-estimates.json"
    assert store.read() == EstimateCatalogue()
    assert not store.path.parent.exists()


def test_cache_round_trip_replaces_only_the_same_case(tmp_path: Path) -> None:
    store = FileBatchEstimateStore(tmp_path / "estimates.json")
    first, second = sample_case(), sample_case(2)
    store.save(first)
    store.save(second)
    newer = first.model_copy(update={"created_at": "later"})
    store.save(newer)
    assert store.read().cases == (second, newer)
    assert not list(tmp_path.glob(".batch-estimates-*.tmp"))


@pytest.mark.parametrize("payload", [b"truncated{", b'{"schema_version":3,"cases":[]}', b"\xff"])
def test_corrupted_cache_is_preserved_and_blocks_reads_and_writes(
    tmp_path: Path,
    payload: bytes,
) -> None:
    store = FileBatchEstimateStore(tmp_path / "estimates.json")
    store.path.write_bytes(payload)
    with pytest.raises(ValueError, match="Invalid batch estimate catalogue"):
        store.read()
    with pytest.raises(ValueError, match="Invalid batch estimate catalogue"):
        store.save(sample_case())
    assert store.path.read_bytes() == payload


def test_interrupted_replacement_preserves_previous_catalogue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileBatchEstimateStore(tmp_path / "estimates.json")
    first = sample_case()
    store.save(first)
    previous = store.path.read_bytes()

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("simulated interruption before atomic replacement")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        store.save(sample_case(2))
    assert store.path.read_bytes() == previous
    assert not list(tmp_path.glob(".batch-estimates-*.tmp"))


def test_concurrent_writers_preserve_every_distinct_case(tmp_path: Path) -> None:
    path = tmp_path / "estimates.json"
    template = sample_case()
    cases = tuple(
        template.model_copy(
            update={
                "profile": template.profile.model_copy(
                    update={"dependencies": {"torch": str(index)}}
                )
            }
        )
        for index in range(8)
    )

    def save(case: EstimateCase) -> None:
        FileBatchEstimateStore(path).save(case)

    with ThreadPoolExecutor(max_workers=4) as executor:
        tuple(executor.map(save, cases))
    loaded = FileBatchEstimateStore(path).read().cases
    assert len(loaded) == len(cases)
    assert {case.profile.dependencies["torch"] for case in loaded} == {
        str(index) for index in range(8)
    }


def test_rejects_copied_success_with_missing_confirmation(tmp_path: Path) -> None:
    case = sample_case()
    forged = case.model_copy(update={"trials": case.trials[:-1]})
    store = FileBatchEstimateStore(tmp_path / "estimates.json")
    with pytest.raises(ValueError, match="evidence"):
        store.save(forged)
    assert not store.path.exists()


def test_outside_symlink_destination_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "config").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError, match="CY_HOME"):
        FileBatchEstimateStore(tmp_path / "config/estimates.json")
