"""Offline coverage comes from editable entries and confirmed capacity failures."""

from pathlib import Path

import pytest

from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.core.batch_estimation import model_catalogue
from clearml_yolo.entrypoints import batch_estimate as cli
from test_batch_estimation import _case, _search, _trial


def _forbid_measurement(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("runtime_environment", "discover_gpus", "require_idle", "_make_probe", "_make_pool"):
        monkeypatch.setattr(cli, name, lambda *args: pytest.fail("listing entered measurement"))
    monkeypatch.setattr(BatchSizeStore, "publish", lambda *args: pytest.fail("listing wrote table"))


def test_list_missing_table_needs_no_imgsz_gpu_or_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "rfdetr/small,yolo11n.pt"])
    output = capsys.readouterr().out
    assert "MODEL\tSTATUS\tREASON" in output
    assert "ultralytics/yolo11n\tnot_attempted" in output
    assert "rfdetr/small\tnot_attempted" in output
    assert output.index("ultralytics/yolo11n") < output.index("rfdetr/small")
    assert "selected=2\tcovered=0\tmissing=2" in output
    assert str(tmp_path / ".config/clearml-yolo/batch-sizes.yaml") in output
    assert list(tmp_path.iterdir()) == []


def test_list_manual_coverage_and_known_failure_preserves_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = BatchSizeStore()
    store.publish((_case(_search(0)),))
    store.path.write_text(
        store.path.read_text().replace("{}\n#", '"Manual GPU [24 GiB]":\n  640:\n    ultralytics/yolo11n: 3 # keep\n#')
    )
    before = store.path.read_bytes()
    paths = sorted(tmp_path.rglob("*"))
    _forbid_measurement(monkeypatch)
    cli.main(["--li", "--models=yolo11n"])
    output = capsys.readouterr().out
    assert "ultralytics/yolo11n\tcovered" in output
    assert "per_gpu_batch=3; manual" in output
    assert "ultralytics/yolo11n\tno_capacity" in output
    assert "imgsz=960" in output
    assert "selected=1\tcovered=1\tmissing=0" in output
    assert store.path.read_bytes() == before
    assert sorted(tmp_path.rglob("*")) == paths


@pytest.mark.parametrize(
    "option",
    [
        ["--imgsz", "640"],
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
    ],
)
def test_list_rejects_measurement_flags(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], option: list[str]
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


@pytest.mark.parametrize(
    "payload", ['"GPU [24 GiB]": [broken', '"GPU [24 GiB]":\n  640:\n    ultralytics/yolo11n: 0\n']
)
def test_list_corrupt_table_reports_error_without_writes(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    store = BatchSizeStore()
    store.path.parent.mkdir(parents=True)
    store.path.write_text(payload)
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list"])
    assert stopped.value.code == 2
    assert store.path.read_text() == payload


@pytest.mark.parametrize("models", ["unknown", "yolo11n,yolo11n.pt"])
def test_list_rejects_invalid_models(monkeypatch: pytest.MonkeyPatch, models: str) -> None:
    _forbid_measurement(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--list", "--models", models])
    assert stopped.value.code == 2


def test_list_default_includes_entire_catalogue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _forbid_measurement(monkeypatch)
    cli.main(["--list"])
    names = [line.split("\t")[0] for line in capsys.readouterr().out.splitlines() if "\tnot_attempted\t" in line]
    assert names == [model.selection for model in model_catalogue()]


def test_list_reports_unsuccessful_refresh_diagnostics_without_promoting_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    case = _case(_search(0, observe=lambda search: _trial(search, "timeout", diagnostic="Worker timed out")))
    FileBatchEstimateStore().save(case)
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "yolo11n"])
    output = capsys.readouterr().out
    assert "ultralytics/yolo11n\tfailed\tWorker timed out" in output
    assert "covered=0" in output
    assert not BatchSizeStore().path.exists()


@pytest.mark.parametrize("control", ["\u0085", "\u009b", "\u2028", "\u2029"])
def test_list_escapes_controls_in_hardware_names(
    control: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    case = _case(_search(0))
    gpu = case.profile.gpus[0].model_copy(update={"name": f"GPU 猫{control}name"})
    case = case.model_copy(update={"profile": case.profile.model_copy(update={"gpus": (gpu,)})})
    BatchSizeStore().publish((case,))
    _forbid_measurement(monkeypatch)
    cli.main(["--list", "--models", "yolo11n"])
    output = capsys.readouterr().out
    assert control not in output
    assert "GPU 猫" in output
