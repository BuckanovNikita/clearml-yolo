"""Offline coverage reports preserve evidence and never enter the measurement path."""

from pathlib import Path

import pytest

from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.core.batch_estimation import EstimateCase, SearchSettings, SyntheticWorkload
from clearml_yolo.entrypoints import batch_estimate as cli
from test_batch_estimate_workflow import sample_profile


def _forbid_measurement(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "runtime_environment",
        "discover_gpus",
        "require_idle",
        "_make_probe",
        "_make_pool",
    ):
        monkeypatch.setattr(cli, name, lambda *args: pytest.fail("listing entered measurement"))
    monkeypatch.setattr(
        FileBatchEstimateStore,
        "save",
        lambda *args: pytest.fail("listing wrote estimates"),
    )


def test_list_missing_catalogue_needs_no_imgsz_gpu_or_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "rfdetr/small,yolo11n.pt"])
    output = capsys.readouterr().out
    assert "MODEL\tSTATUS\tREASON" in output
    assert "ultralytics/yolo11n\tnot_attempted\tNo saved attempt" in output
    assert "rfdetr/small\tnot_attempted\tNo saved attempt" in output
    assert output.index("ultralytics/yolo11n") < output.index("rfdetr/small")
    assert "selected=2\tcovered=0\tmissing=2" in output
    assert str(tmp_path / ".config/clearml-yolo/batch-estimates.json") in output
    assert list(tmp_path.iterdir()) == []


def test_list_reports_saved_failure_context_and_preserves_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FileBatchEstimateStore()
    store.save(
        EstimateCase(
            profile=sample_profile(),
            workload=SyntheticWorkload(),
            settings=SearchSettings(),
            status="failed",
            created_at="2026-11-03",
            diagnostic="Timeout\n\t\x1b[31mworker",
        )
    )
    before = store.path.read_bytes()
    entries = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models=yolo11n"])
    output = capsys.readouterr().out
    assert "ultralytics/yolo11n\tfailed\tTimeout\\n\\t\\u001b[31mworker" in output
    assert "imgsz=960x960" in output
    assert "GPU" in output
    assert "1000" in output
    assert "classes=150" in output
    assert "objects_per_image=300" in output
    assert "not current training compatibility" in output
    assert store.path.read_bytes() == before
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == entries


@pytest.mark.parametrize(
    "option",
    [
        ["--imgsz", "640"],
        ["--classes=150"],
        ["--objects-per-image", "300"],
        ["--devices", "0"],
        ["--gpu-counts", "1"],
        ["--jobs", "1"],
        ["--refresh"],
        ["--force"],
        ["--memory-budget", "0.9"],
        ["--search-limit", "1024"],
        ["--trial-timeout", "300"],
        ["--img=640"],
        ["--class", "150"],
    ],
)
def test_list_rejects_explicit_measurement_flags_even_default_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    option: list[str],
) -> None:
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list", *option])
    assert stopped.value.code == 2
    assert "cannot be used with --list" in capsys.readouterr().err


def test_measurement_still_requires_imgsz(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main([])
    assert stopped.value.code == 2


def test_list_corrupt_catalogue_reports_error_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FileBatchEstimateStore()
    store.path.parent.mkdir(parents=True)
    store.path.write_text('{"schema_version": 999}')
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list"])
    assert stopped.value.code == 2
    assert "Invalid batch estimate catalogue" in capsys.readouterr().err
    assert store.path.read_text() == '{"schema_version": 999}'


@pytest.mark.parametrize("models", ["unknown", "yolo11n,yolo11n.pt"])
def test_list_rejects_invalid_model_selection(monkeypatch: pytest.MonkeyPatch, models: str) -> None:
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list", "--models", models])
    assert stopped.value.code == 2


def test_list_all_covered_uses_historical_evidence_without_compatibility_checks(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
    from test_batch_estimate_workflow import RecordingProbe

    store = FileBatchEstimateStore()
    estimate_batches(
        (sample_profile(),),
        SyntheticWorkload(),
        SearchSettings(max_global_batch=8),
        probe=RecordingProbe(),
        store=store,
        now=lambda: "2026-11-03",
    )
    _forbid_measurement(monkeypatch)
    cli.main(["--li", "--models=yolo11n"])
    output = capsys.readouterr().out
    assert "All selected models have a usable saved estimate." in output
    assert "selected=1\tcovered=1\tmissing=0" in output
    assert "ultralytics/yolo11n\t" not in output


def test_list_preserves_distinct_failed_configurations(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FileBatchEstimateStore()
    for size, reason in ((640, "No idle GPU"), (960, "Independent confirmation pending")):
        store.save(
            EstimateCase(
                profile=sample_profile().model_copy(
                    update={
                        "nominal_size": (size, size),
                        "effective_size": (size, size),
                    }
                ),
                workload=SyntheticWorkload(),
                settings=SearchSettings(),
                status="failed",
                created_at="2026-11-03",
                diagnostic=reason,
            )
        )
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "yolo11n"])
    output = capsys.readouterr().out
    assert "No idle GPU" in output
    assert "Independent confirmation pending" in output
    assert "imgsz=640x640" in output
    assert "imgsz=960x960" in output
    assert "selected=1\tcovered=0\tmissing=1" in output


def test_list_unreadable_catalogue_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FileBatchEstimateStore()
    store.path.mkdir(parents=True)
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list"])
    assert stopped.value.code == 2
    assert "Is a directory" in capsys.readouterr().err


def test_list_default_includes_entire_catalogue(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.core.batch_estimation import model_catalogue

    _forbid_measurement(monkeypatch)
    cli.main(["--list"])
    output = capsys.readouterr().out
    names = [line.split("\t")[0] for line in output.splitlines() if "\tnot_attempted\t" in line]
    assert names == [model.selection for model in model_catalogue()]


@pytest.mark.parametrize("control", ["\u0085", "\u009b", "\u2028", "\u2029"])
def test_list_escapes_unicode_controls_and_line_separators(
    control: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    profile = sample_profile()
    profile = profile.model_copy(
        update={
            "gpus": (profile.gpus[0].model_copy(update={"name": f"GPU{control}name"}),),
        }
    )
    FileBatchEstimateStore().save(
        EstimateCase(
            profile=profile,
            workload=SyntheticWorkload(),
            settings=SearchSettings(),
            status="failed",
            created_at="2026-11-03",
            diagnostic=f"Причина 猫{control}failed",
        )
    )
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "yolo11n"])
    output = capsys.readouterr().out
    assert control not in output
    assert "Причина 猫" in output
    assert len(output.splitlines()) == 5
