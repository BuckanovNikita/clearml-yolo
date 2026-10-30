"""Numerical failures retain only independently confirmed, explicitly limited evidence."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.adapters.integrations.batch_lookup import resolve_batch_estimate
from clearml_yolo.adapters.integrations.batch_resolution import batch_provenance
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    EstimateCatalogue,
    GPUHardware,
    SearchSettings,
    SyntheticWorkload,
    TrialResult,
    select_recommendation,
)
from clearml_yolo.entrypoints import batch_estimate as cli
from clearml_yolo.entrypoints.batch_estimate import _report
from test_batch_estimate_cli import _install
from test_batch_estimate_workflow import MemoryStore, RecordingProbe, sample_case, sample_profile
from test_batch_estimation import _case, _profile, _search, _trial
from test_batch_lookup import _dataset

CAUSE = "FloatingPointError: YOLO probe produced nonfinite validation loss"


def _pending() -> BatchSearch:
    search = BatchSearch.start(_profile(), SearchSettings())
    for _ in range(2):
        search = search.observe(_trial(search))
    search = search.observe(_trial(search, "nonfinite", diagnostic=CAUSE))
    assert search.next_batch == 2
    assert search.confirming
    assert search.status == "searching"
    assert search.upper is None
    assert search.global_batch is None
    return search


def limited_case() -> EstimateCase:
    search = _pending()
    return _case(search.observe(_trial(search, diagnostic="")))


def test_reported_binary_search_recovers_only_after_fresh_confirmation() -> None:
    profile = _profile().model_copy(
        update={"gpus": (GPUHardware(name="NVIDIA A40", total_memory_bytes=47697690624),)}
    )
    search = BatchSearch.start(profile, SearchSettings())
    for batch, peak in (
        (1, 4756602880), (2, 5726273536), (4, 8884584448), (8, 14624489472),
        (16, 27496808448), (32, 47381217280), (24, 40339767296),
    ):
        assert search.next_batch == batch
        search = search.observe(_trial(search, peak_memory_bytes=(peak,)))
    assert (search.lower, search.upper, search.next_batch) == (24, 32, 28)
    search = search.observe(_trial(search, "nonfinite", diagnostic=CAUSE))
    assert (search.lower, search.upper, search.next_batch) == (24, 32, 24)
    assert search.confirming
    search = search.observe(_trial(search, peak_memory_bytes=(40339767296,), diagnostic=""))
    case = _case(search)
    assert case.usable
    assert case.status == "numerically_limited"
    assert case.global_batch == case.per_gpu_batch == 24
    assert "28" in case.diagnostic
    assert CAUSE in case.diagnostic
    assert "maximum" in case.diagnostic
    assert case.trials[-2].status == "nonfinite"
    assert case.trials[-1].global_batch == 24
    assert len({trial.trial_id for trial in case.trials}) == len(case.trials)


def test_first_numerical_failure_still_has_no_recommendation() -> None:
    search = BatchSearch.start(_profile(), SearchSettings())
    search = search.observe(_trial(search, "nonfinite", diagnostic=CAUSE))
    assert search.status == "failed"
    assert search.next_batch is None
    assert not _case(search).usable


@pytest.mark.parametrize(
    "failure",
    ["nonfinite", "oom", "memory_limit", "timeout", "crash", "error", "missing_asset",
     "cancelled", "contaminated"],
)
def test_any_failed_recovery_confirmation_invalidates_recommendation(failure: str) -> None:
    search = _pending()
    search = search.observe(_trial(search, failure, diagnostic="repeat failed"))
    assert search.status == "failed"
    assert search.next_batch is None
    assert search.global_batch is None
    assert not _case(search).usable
    assert CAUSE in search.diagnostic
    assert "repeat failed" in search.diagnostic


@pytest.mark.parametrize(
    "updates",
    [
        {"measured_steps": 9}, {"warmup_steps": 4}, {"validation_steps": 0},
        {"optimizer_paths": ("AdamW",)}, {"actual_global_batch": 1},
        {"peak_memory_bytes": (901,)}, {"peak_memory_bytes": ()},
    ],
)
def test_incomplete_or_overbudget_confirmation_is_unusable(updates: dict[str, Any]) -> None:
    search = _pending()
    search = search.observe(_trial(search, **updates))
    assert search.status == "failed"
    assert not _case(search).usable


def test_recovery_cannot_reuse_trial_identity_or_forge_confirmation() -> None:
    search = _pending()
    with pytest.raises(ValueError, match="fresh"):
        search.observe(_trial(search, trial_id=search.trials[0].trial_id))
    case = limited_case()
    raw = case.model_dump(mode="json")
    raw["trials"] = raw["trials"][:-1]
    with pytest.raises(ValidationError, match="evidence"):
        EstimateCase.model_validate(raw)


def test_legacy_terminal_numerical_failure_remains_readable_without_promotion() -> None:
    search = _pending()
    raw = {
        "profile": search.profile.model_dump(mode="json"),
        "workload": SyntheticWorkload().model_dump(mode="json"),
        "settings": search.settings.model_dump(mode="json"),
        "status": "failed", "trials": [t.model_dump(mode="json") for t in search.trials],
        "created_at": "2026-10-30T00:00:00Z", "diagnostic": "",
    }
    catalogue = EstimateCatalogue.model_validate({"schema_version": 1, "cases": [raw]})
    assert catalogue.cases[0].status == "failed"
    assert not catalogue.cases[0].usable


def test_schema_upgrade_is_write_only_and_preserves_peer_cases(tmp_path: Path) -> None:
    peer = sample_case()
    store = FileBatchEstimateStore(tmp_path / "estimates.json")
    payload = json.dumps({"schema_version": 1, "cases": [peer.model_dump(mode="json")]})
    store.path.write_text(payload)
    assert store.read().cases == (peer,)
    assert store.path.read_text() == payload
    case = limited_case()
    store.save(case)
    assert json.loads(store.path.read_text())["schema_version"] == 2
    assert store.read().cases == (peer, case)
    with pytest.raises(ValidationError, match="schema"):
        EstimateCatalogue.model_validate(
            {"schema_version": 1, "cases": [case.model_dump(mode="json")]}
        )


def test_limited_lookup_extrapolation_cli_and_training_preserve_cause(
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = limited_case()
    exact = select_recommendation((case,), case.profile, case.workload)
    target = case.profile.model_copy(update={"gpus": case.profile.gpus * 2})
    target = target.model_copy(
        update={"gpus": tuple(gpu.model_copy(update={"uuid": None}) for gpu in target.gpus)}
    )
    derived = select_recommendation((case,), target, case.workload)
    assert exact.status == derived.status == "numerically_limited"
    assert derived.origin == "extrapolated"
    assert derived.global_batch == 4
    assert derived.source_statuses == ("numerically_limited",)
    provenance = batch_provenance(derived)
    assert provenance["sources"][0]["diagnostic"] == case.diagnostic
    _report(derived, cached=True)
    output = capsys.readouterr().out
    assert "numerically_limited" in output
    assert CAUSE in output
    assert "cached" in output


def test_application_progress_cache_and_refresh_keep_confirmation_safety(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, probe = MemoryStore(), RecordingProbe(capacity=100)
    original = probe.run

    def run(*args: Any) -> TrialResult:
        result = original(*args)
        return (
            result.model_copy(update={"status": "nonfinite", "diagnostic": CAUSE})
            if result.global_batch == 4 else result
        )

    monkeypatch.setattr(probe, "run", run)
    kwargs: dict[str, Any] = {
        "probe": probe, "store": store, "now": lambda: "2026-10-30T00:00:00Z"
    }
    args = ((sample_profile(),), SyntheticWorkload(), SearchSettings())
    (case,) = estimate_batches(*args, **kwargs)
    assert case.status == "numerically_limited"
    assert [trial.global_batch for trial in case.trials] == [1, 2, 4, 2]
    assert all(not snapshot.usable for snapshot in store.writes[:-1])
    assert "pending" in store.writes[0].diagnostic
    assert "running" in store.writes[0].diagnostic
    calls, writes = probe.calls, len(store.writes)
    assert estimate_batches(*args, **kwargs) == (case,)
    assert (probe.calls, len(store.writes)) == (calls, writes)
    estimate_batches(*args, **kwargs, refresh=True)
    assert probe.calls == calls * 2
    assert not store.writes[writes].usable


def test_mixed_hardware_preserves_numerical_limit_over_ceiling_status() -> None:
    case = limited_case()
    other_profile = case.profile.model_copy(
        update={"gpus": (GPUHardware(name="Other GPU", total_memory_bytes=1000),)}
    )
    other = _case(_search(4, ceiling=4, profile=other_profile))
    target = case.profile.model_copy(update={"gpus": (*case.profile.gpus, *other.profile.gpus)})
    result = select_recommendation((case, other), target, case.workload)
    assert result.global_batch == 4
    assert result.source_statuses == ("numerically_limited", "ceiling_limited")
    assert result.status == "numerically_limited"


def test_null_batch_lookup_accepts_confirmed_limited_source_within_dataset_bounds(
    tmp_path: Path,
) -> None:
    case, store = limited_case(), MemoryStore()
    store.save(case)
    result = resolve_batch_estimate(case.profile, _dataset(tmp_path), store)
    assert result.status == "numerically_limited"
    assert result.global_batch == 2
    with pytest.raises(ValueError, match="explicit training batch"):
        resolve_batch_estimate(
            case.profile,
            _dataset(tmp_path, images=[{"split": "train", "boxes": 301}]),
            store,
        )


def test_cli_returns_usable_limited_result_and_reuses_it_without_more_trials(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    probe, _ = _install(monkeypatch, capacity=100)
    original = probe.run

    def run(*args: Any) -> TrialResult:
        result = original(*args)
        return (
            result.model_copy(update={"status": "nonfinite", "diagnostic": CAUSE})
            if result.global_batch == 4 else result
        )

    monkeypatch.setattr(probe, "run", run)
    args = ["--imgsz", "960", "--models", "yolov3u", "--gpu-counts", "1,2"]
    cli.main(args)
    output = capsys.readouterr().out
    assert "gpus=1\tglobal_batch=2" in output
    assert "gpus=2\tglobal_batch=4" in output
    assert output.count(CAUSE) == 2
    assert "unavailable" not in output
    calls = probe.calls
    cli.main(args)
    assert probe.calls == calls
    assert "cached" in capsys.readouterr().out
