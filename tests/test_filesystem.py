"""Project filesystem paths and preserved external configuration."""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from clearml_yolo.adapters.storage.dataset_cache import dataset_cache_root
from clearml_yolo.adapters.storage.filesystem import model_weights_path, temporary_root, write_path


def test_external_application_write_is_rejected_without_creating_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    outside = tmp_path / "outside" / "output.csv"
    with pytest.raises(ValueError, match="CY_HOME"):
        write_path(outside)
    assert not outside.parent.exists()


def test_project_write_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("CY_HOME", str(root))
    with pytest.raises(ValueError, match="CY_HOME"):
        write_path(root / "link" / "output.csv")
    assert list(outside.iterdir()) == []


def test_external_temp_is_rejected_before_workspace_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment

    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    monkeypatch.setenv("CY_HOME", str(root))
    monkeypatch.setenv("CY_RUNTIME_TEMP_ROOT", str(outside))
    with pytest.raises(ValueError, match="CY_HOME"):
        initialize_runtime_environment()
    assert not root.exists()
    assert not outside.exists()


@pytest.mark.parametrize("operation", ["mkdir", "text", "csv", "dataset"])
def test_storage_operations_validate_destination_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    import pandas as pd

    from clearml_yolo.adapters.storage import file_io
    from clearml_yolo.adapters.storage.dataset import prepare_dataset

    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    external = tmp_path / "external"
    external.mkdir()
    selected = external / "existing.csv"
    selected.write_text("unchanged")
    operations: dict[str, Callable[[], object]] = {
        "mkdir": lambda: file_io.mkdir(external / "created"),
        "text": lambda: file_io.write_text(selected, "changed"),
        "csv": lambda: file_io.write_csv(pd.DataFrame({"value": [1]}), selected),
        "dataset": lambda: prepare_dataset(tmp_path / "input.csv", external / "dataset"),
    }
    with pytest.raises(ValueError, match="CY_HOME"):
        operations[operation]()
    assert selected.read_text() == "unchanged"
    assert list(external.iterdir()) == [selected]


def test_dataset_default_uses_cy_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    assert dataset_cache_root(None) == tmp_path / ".cache" / "clearml-yolo" / "datasets"


def test_dataset_default_ignores_general_xdg_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "home" / ".cache"))
    expected = tmp_path / "workspace" / ".cache" / "clearml-yolo" / "datasets"
    assert dataset_cache_root(None) == expected
    with pytest.raises(ValueError, match="CY_HOME"):
        dataset_cache_root(tmp_path / "chosen")


@pytest.mark.parametrize(
    "value",
    [
        "ul://user/project/model",
        "http://host/model",
        "s3://bucket/m.pt",
        "yolo11n.pt",
        "./explicit-yolo11n.pt",
        Path("yolo11n.pt"),
    ],
)
def test_model_references_reach_library_without_routing_or_type_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | Path
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert model_weights_path(value) is value
    assert not (tmp_path / ".cache").exists()


def test_existing_checkpoint_string_is_a_local_path_without_cache_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    old_download = tmp_path / ".cache/ultralytics/weights/model.pt"
    old_download.parent.mkdir(parents=True)
    old_download.write_bytes(b"legacy download")
    assert model_weights_path("model.pt") == "model.pt"
    selected = tmp_path / "model.pt"
    selected.write_bytes(b"native download")
    assert model_weights_path("model.pt") == Path("model.pt")
    assert model_weights_path(str(selected)) == selected
    assert model_weights_path(str(old_download)) == old_download


@pytest.mark.parametrize("selection", [None, "workspace", "absolute"])
def test_initialization_freezes_project_root_without_library_configuration(
    tmp_path: Path, selection: str | None
) -> None:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith("CY_"):
            environment.pop(name)
    expected = tmp_path
    if selection:
        expected = tmp_path / "workspace"
        environment["CY_HOME"] = str(expected) if selection == "absolute" else selection
    script = """
import json, os
from pathlib import Path
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem
before = dict(os.environ)
initialize_filesystem()
os.chdir(Path.cwd().parent)
from clearml_yolo.adapters.storage.filesystem import cy_home, runs_root, temporary_root
assert all(os.environ.get(name) == value for name, value in before.items() if name != 'CY_HOME')
assert all(name in before for name in os.environ if not name.startswith('CY_'))
print(json.dumps([str(cy_home()), str(runs_root()), str(temporary_root())]))
"""
    result = subprocess.run(  # noqa: S603 - fixed script with task-owned paths
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        str(expected),
        str(expected / "runs"),
        str(expected / ".tmp"),
    ]


def test_contained_home_destination_is_accepted_without_relocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("CY_HOME", str(home))
    selected = home / "chosen.csv"
    assert write_path(selected) == selected
    assert not selected.exists()


def test_symlinks_within_workspace_remain_valid_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    assert write_path(link / "output.csv") == link / "output.csv"


def test_project_temp_directory_rejects_explicit_external_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    selected = tmp_path / "chosen-temp"
    monkeypatch.setenv("CY_RUNTIME_TEMP_ROOT", str(selected))
    with pytest.raises(ValueError, match="CY_HOME"):
        temporary_root()
    assert not selected.exists()


def test_project_temp_files_use_invocation_arena_without_changing_global_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    from clearml_yolo.adapters.runtime.bootstrap import runtime_environment

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("CY_RUNTIME_TEMP_ROOT", raising=False)
    before = tempfile.tempdir
    with runtime_environment() as arena:
        assert temporary_root() == arena
        descriptor, name = tempfile.mkstemp(dir=temporary_root())
        os.close(descriptor)
        retained = Path(name)
        retained.write_text("project temporary file", encoding="utf-8")
        assert tempfile.tempdir == before
    assert retained.read_text(encoding="utf-8") == "project temporary file"


def test_filesystem_does_not_read_or_rewrite_optional_library_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage.filesystem import initialize_filesystem

    selected = tmp_path / "outside" / "private-config.json"
    selected.parent.mkdir()
    selected.write_bytes(b"\xff malformed input belongs to the library")
    original = selected.read_bytes()
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    monkeypatch.setenv("FIFTYONE_CONFIG_PATH", str(selected))
    initialize_filesystem()
    assert os.environ["FIFTYONE_CONFIG_PATH"] == str(selected)
    assert selected.read_bytes() == original
    assert not (tmp_path / "workspace" / ".config").exists()


def test_atomic_publication_cleans_partial_output_on_failure(tmp_path: Path) -> None:
    from clearml_yolo.adapters.yolo.reinfer import _atomic_text

    output = tmp_path / "predictions.csv"
    output.write_text("existing result\n")

    def fail_serialization() -> None:
        with _atomic_text(output) as stream:
            stream.write("partial result\n")
            raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        fail_serialization()
    assert output.read_text() == "existing result\n"
    assert list(tmp_path.iterdir()) == [output]
